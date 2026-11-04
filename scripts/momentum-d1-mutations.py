#!/usr/bin/env python3
"""Reproducerbar felprovsmatris för H-0017 D1 (mom-control/1.0.0).

Varje fel införs i en kopia av engine/ och de testresurser proven läser (docs/momentum-a1-orakel.json) i en temporär
katalog med samma struktur, aldrig i källfilerna. Först körs en oförändrad baslinje, som måste passera med exakt det
antal prov som samlas in; annars avbryts skriptet. Därefter körs per fel först de riktade proven i TARGETS; om de
passerar körs hela D1-sviten (tests/test_momentum_control.py och tests/test_momentum_control_integration.py), så att
MISSAD alltid bygger på hela sviten. FÅNGAD kräver att pytest körde proven och att minst ett prov
fallerade eller fick fel vid körning (exit 1, inga insamlingsfel) med ett undantag som inte tyder på provmiljön
(FileNotFoundError, ImportError och liknande ger MILJÖFEL); första fallerande prov och undantagstyp sparas. Körtider
sparas inte, eftersom de inte är reproducerbara. MISSAD betyder att alla prov passerade.
Insamlings- eller miljöfel ger MILJÖFEL och gör att skriptet fallerar. Bevisat ekvivalenta fel är märkta EKVIVALENT
med motivering. Matrisen skrivs till docs/momentum-D1-mutationer.json.
Med --check körs allt om och jämförs mot den sparade matrisen. Python-tolken ges med --python (standard: projektets
venv).

    python3 scripts/momentum-d1-mutations.py [--check] [--python PATH]
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/momentum-D1-mutationer.json"
TESTS = ["tests/test_momentum_control.py", "tests/test_momentum_control_integration.py"]
DEFAULT_PY = Path("/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python")

# (namn, fil i engine/traderlab, gammal text, ny text)
MUTATIONS = [
    ("main-s i stället för s_h", "momentum_control.py",
     "used = _real(key, row[key]) if live else math.nan", 'used = _real(key, row["s"]) if live else math.nan'),
    ("växla 7/14", "momentum_control.py",
     'COMPONENTS = {"mom7": "s7", "mom14": "s14", "mom28": "s28"}',
     'COMPONENTS = {"mom7": "s14", "mom14": "s7", "mom28": "s28"}'),
    ("framtida close", "momentum_signal.py",
     "sig = [1.0 if c[i] / lag - 1 > 0 else 0.0 for lag in lags]",
     "sig = [1.0 if c[min(i + 1, n - 1)] / lag - 1 > 0 else 0.0 for lag in lags]"),
    ("cap = 1 alltid", "momentum_control.py",
     'w = _out_w(used * _real("cap", row["cap"])) if live else math.nan', 'w = _out_w(used * 1.0) if live else math.nan'),
    ("komponentens band avstängt", "momentum_risk.py", "BAND = 0.02", "BAND = 0.0"),
    ("komponentens dagsstopp avstängt", "momentum_risk.py", "        if day_ret <= DAY_STOP:", "        if False:"),
    ("komponentens permanenta stopp avstängt", "momentum_risk.py", "        if not permanent and dd <= PERMANENT_STOP:",
     "        if False:"),
    ("A på nya q", "momentum_event.py", '''        if s.order == "A":
            for e in simultaneous:''', '''        if False:
            for e in simultaneous:'''),
    ("B på gamla q", "momentum_event.py", '''            if intent is not None:
                acct, f = risk.fill_intent(''', '''            if s.order == "B":
                for e in simultaneous:
                    acct, fs, fr = fund.apply_funding(acct, fs, e, "funding_B")
                simultaneous = []
            if intent is not None:
                acct, f = risk.fill_intent('''),
    ("normal återupplivad efter riskexit", "momentum_risk.py",
     '        suppressed = [(k, f"strykt av {kind}") for k, _, _ in candidates[1:]]',
     '        suppressed = [(k, f"strykt av {kind}") for k, _, _ in candidates[1:]]\n'
     '        kind, w, reason = next((cc for cc in candidates if cc[0] == NORMAL), candidates[0])'),
    ("köp efter permanent stopp", "momentum_risk.py", '''        if permanent:
            decision = PERMANENT if q != 0 else HOLD''', '''        if False:
            decision = PERMANENT if q != 0 else HOLD'''),
    ("startpunkt tappad", "momentum_event.py", "            return cls(state=state, close_points=((None, START, INITIAL),),",
     "            return cls(state=state, close_points=(),"),
    ("sista close/terminalpunkt tappad", "momentum_event.py", "            cps += ((T, T, E),)", "            pass"),
    ("terminalkostnad tappad", "momentum_ledger.py", "COST_NORMAL = (10 + 2 / 2 + 5) / 10_000      # 0,0016 per sida",
     "COST_NORMAL = 0.0"),
    ("kort horisont godtas", "momentum_control.py", "if not self.mark.index.equals(TEST_BARS):", "if False:"),
    ("otillgänglig signal godtas som platt", "momentum_control.py", '''        if cs is None or not cs.available:
            raise ControlError''', '''        if False:
            raise ControlError'''),
    ("adapterns earliest_fill okontrollerad", "momentum_control.py",
     'for name in ("decision_time", "earliest_fill"):', 'for name in ("decision_time",):'),
    ("adapterns koherens okontrollerad", "momentum_control.py",
     "if any(x not in (0.0, 1.0) for x in subs) or vals[\"s_main\"] != sum(subs) / 3:", "if False:"),
    ("adapterns cap/vol okontrollerad", "momentum_control.py",
     "if not (math.isfinite(vol) and vol > 0) or vals[\"cap\"] != min(1.0, sigmod.TARGET_VOL / vol):", "if False:"),
    ("strikt bool available okontrollerad", "momentum_control.py",
     "        if not isinstance(self.available, (bool, np.bool_)):\n            raise ControlError",
     "        if False:\n            raise ControlError"),
    ("underlaget återvalideras inte", "momentum_control.py", "    market = market.verified()\n", "\n"),
    ("underlaget kopieras inte", "momentum_control.py",
     '            object.__setattr__(self, name, getattr(self, name).copy(deep=True))   # egen kopia, inte anroparens',
     '            pass'),
    ("2025-data i tabeller godtas", "momentum_control.py", "if len(idx) and idx.max() >= ev.END:", "if False:"),
    ("2025-funding godtas", "momentum_control.py", "if e.time >= ev.END:", "if False:"),
    ("legacy-identitet saknas", "momentum_control.py",
     'scenario = ev.Scenario(f"{component}/{legacy_order}", order, mmr, cost)',
     'scenario = ev.Scenario(component, order, mmr, cost)'),
    ("pre-start räknas inte", "momentum_control.py", "            pre += 1", "            pass"),
    ("delat förlopp och state mellan konton (peak, lås, funding-id)", "momentum_control.py",
     "    out = {k: run_component(market, k, order, mmr, legacy_order, cost) for k in COMPONENTS}\n",
     "    first = run_component(market, \"mom7\", order, mmr, legacy_order, cost)\n"
     "    out = {k: __import__(\"dataclasses\").replace(first, component=k) for k in COMPONENTS}\n"),
    ("delad kontoidentitet mellan konton", "momentum_control.py", "    state = ev.EngineState.start(scenario)\n",
     "    state = ev.EngineState.start(ev.Scenario(\"mom7/\" + legacy_order, order, mmr, cost))\n"),
    ("peakreset vid årsskifte", "momentum_risk.py", "        peak = max(peak, E)\n",
     "        peak = max(E, state.initial) if (T.month, T.day, T.hour) == (1, 1, 0) else max(peak, E)\n"),
    ("adapterns dubblettkontroll av", "momentum_control.py",
     "    if idx.has_duplicates or not idx.is_monotonic_increasing:\n        raise ControlError(\"Signaltabellens",
     "    if False:\n        raise ControlError(\"Signaltabellens"),
    ("adapterns numerik efter aritmetik", "momentum_control.py",
     "        used = _real(key, row[key]) if live else math.nan          # numerik prövas före all aritmetik\n"
     "        w = _out_w(used * _real(\"cap\", row[\"cap\"])) if live else math.nan",
     "        used = row[key] if live else math.nan\n        w = used * row[\"cap\"] if live else math.nan"),
]

# Riktade prov per fel (pytest -k-uttryck). De körs först; fallerar ett av dem är felet fångat av ett verkligt prov.
# Passerar de körs hela D1-sviten innan felet får klassas som MISSAD, så ett för smalt urval kan inte dölja en miss.
TARGETS = {
    "main-s i stället för s_h": "test_component_signals_match_independent_computation",
    "växla 7/14": "test_component_signals_match_independent_computation",
    "framtida close": "test_component_signals_match_independent_computation",
    "cap = 1 alltid": "test_component_signals_match_independent_computation",
    "komponentens band avstängt": "test_O9_component_full_capital_vs_main or test_band_exact_float_boundary",
    "komponentens dagsstopp avstängt": "test_O9_component_full_capital_vs_main or test_day_and_permanent_stop",
    "komponentens permanenta stopp avstängt": "test_day_and_permanent_stop or test_public_component_run_permanent",
    "A på nya q": "test_O5_O16_component_entry_decrease_exit",
    "B på gamla q": "test_O5_O16_component_entry_decrease_exit",
    "normal återupplivad efter riskexit": "test_O6_component_day_stop",
    "köp efter permanent stopp": "test_public_component_run_permanent",
    "startpunkt tappad": "test_full_horizon_per_component or test_independent_full_horizon",
    "sista close/terminalpunkt tappad": "test_full_horizon_per_component or test_independent_full_horizon",
    "terminalkostnad tappad": "test_O2_full_capital_entry or test_independent_full_horizon",
    "kort horisont godtas": "test_invalid_market_is_rejected",
    "otillgänglig signal godtas som platt": "test_invalid_signal_day_via_constant_window",
    "adapterns earliest_fill okontrollerad": "test_adapter_rejects_inconsistent_source_rows",
    "adapterns koherens okontrollerad": "test_adapter_rejects_inconsistent_source_rows",
    "adapterns cap/vol okontrollerad": "test_adapter_rejects_inconsistent_source_rows",
    "strikt bool available okontrollerad": "test_direct_construction_is_validated or test_adapter_rejects",
    "underlaget återvalideras inte": "test_market_owns_a_copy",
    "underlaget kopieras inte": "test_market_owns_a_copy",
    "2025-data i tabeller godtas": "test_invalid_market_is_rejected",
    "2025-funding godtas": "test_invalid_market_is_rejected",
    "legacy-identitet saknas": "test_full_horizon_per_component or test_L1_L2",
    "pre-start räknas inte": "test_funding_ids_are_booked_independently",
    "delat förlopp och state mellan konton (peak, lås, funding-id)": "test_components_differ_from_each_other",
    "delad kontoidentitet mellan konton": "test_full_horizon_per_component or test_funding_ids_are_booked",
    "peakreset vid årsskifte": "test_permanent_stop_across_new_year",
    "adapterns dubblettkontroll av": "test_adapter_huge_cap_and_duplicate_days",
    "adapterns numerik efter aritmetik": "test_adapter_huge_cap_and_duplicate_days",
}

EQUIVALENT = [
    ("observationsdagar i stället för kalenderdagar",
     "Market kräver exakt 4H-raster från 2021-11-01 till terminal, så varje kalenderdag är komplett. Den h:te föregående "
     "observationen är då exakt h kalenderdagar bak, och mutationen ger identiska signaler på varje giltigt D1-underlag. "
     "Skillnaden prövas i signalmodulens egna B-prov med ofullständiga dagar."),
]

NOT_APPLICABLE = []


# Undantag som tyder på provmiljön, inte på mutantens beteende. De klassas som MILJÖFEL och gör att skriptet fallerar.
ENV_ERRORS = {"FileNotFoundError", "ImportError", "ModuleNotFoundError", "PermissionError", "OSError",
              "IsADirectoryError", "NotADirectoryError", "fixture"}


def _workspace(tmp: Path) -> Path:
    dst = tmp / "engine"
    shutil.copytree(ROOT / "engine", dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    (tmp / "docs").mkdir()
    shutil.copy(ROOT / "docs/momentum-a1-orakel.json", tmp / "docs/momentum-a1-orakel.json")
    return dst


def _exception_kind(typ, msg: str) -> str:
    """Undantagstyp ur JUnit-elementet: type-attributet om det finns, annars första 'Namn(Error|Exception):' i
    meddelandet; ett rent assert-meddelande är AssertionError."""
    if typ:
        return typ.rsplit(".", 1)[-1]
    m = re.search(r"([A-Za-z_][\w.]*(?:Error|Exception))\s*:", msg)
    if m:
        return m.group(1).rsplit(".", 1)[-1]
    if msg.lstrip().startswith("assert"):
        return "AssertionError"
    return "Failed" if msg.lstrip().startswith(("Failed", "DID NOT RAISE")) else "okänd"   # pytest.raises/pytest.fail


def _pytest(py, cwd, k=None):
    """Kör D1-proven. Returnerar exitkod, sammanfattning utan körtid och första fallerade prov med undantagstyp ur
    pytests JUnit-XML (failure/error-elementens type-attribut), eller None."""
    xml = Path(cwd) / "_d1_junit.xml"
    p = subprocess.run([str(py), "-m", "pytest", "-p", "no:cacheprovider", "-o", "addopts=", "-q", "-x",
                        f"--junitxml={xml}", *(["-k", k] if k else []), *TESTS], cwd=cwd, capture_output=True, text=True)
    out = p.stdout + p.stderr
    lines = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    summary = re.sub(r" in [0-9.]+s( \([0-9:]+\))?$", "", lines[-1].strip()) if lines else ""   # körtid ej reproducerbar
    first = None
    if "ERROR collecting" not in out and "errors during collection" not in out and xml.exists():
        for case in ET.parse(xml).getroot().iter("testcase"):
            bad = case.find("failure")
            bad = bad if bad is not None else case.find("error")
            if bad is not None:
                kind = _exception_kind(bad.get("type"), bad.get("message") or "")
                first = (f"{case.get('classname')}::{case.get('name')}", kind, "error" if bad.tag == "error" else "failure")
                break
    return p.returncode, summary, first


def baseline(py) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        code, summary, _ = _pytest(py, _workspace(Path(tmp)))
    if code != 0 or "failed" in summary or "error" in summary or "passed" not in summary:
        sys.exit(f"MILJÖFEL: den oförändrade baslinjen är inte grön ({code}: {summary}).")
    return summary


def env_selftest(py) -> str:
    """Ett syntetiskt miljöfel (autouse-fixtur med FileNotFoundError) måste klassas som MILJÖFEL, aldrig FÅNGAD."""
    with tempfile.TemporaryDirectory() as tmp:
        dst = _workspace(Path(tmp))
        (dst / "tests" / "conftest.py").write_text(
            "import pytest\n\n\n@pytest.fixture(autouse=True)\ndef _synthetic_env_fault():\n"
            "    raise FileNotFoundError(\"synthetic missing test resource\")\n")
        code, _, first = _pytest(py, dst)
    if not (code == 1 and first and first[1] in ENV_ERRORS):
        sys.exit(f"Självtestet klassade inte ett miljöfel som MILJÖFEL: {code} {first}")
    return f"MILJÖFEL ({first[1]}) som väntat"


def run_one(py, name, rel, old, new):
    with tempfile.TemporaryDirectory() as tmp:
        dst = _workspace(Path(tmp))
        f = dst / "traderlab" / rel
        src = f.read_text()
        if src.count(old) != 1:
            return {"utfall": "MÖNSTER_SAKNAS"}
        f.write_text(src.replace(old, new))
        scope = "riktade"
        code, summary, first = _pytest(py, dst, TARGETS.get(name))
        if code == 0 or (code == 5 and not first):          # riktade prov passerade (eller inga valdes): hela sviten
            scope = "hela D1-sviten"
            code, summary, first = _pytest(py, dst)
    if code == 0:
        return {"utfall": "MISSAD", "pytest": summary, "körda_prov": scope}
    if code == 1 and first:                        # prov fallerade eller fick fel vid körning (inte insamling)
        test_id, kind, tag = first
        row = {"pytest": summary, "första_fel": test_id, "orsak": kind, "typ": tag, "körda_prov": scope}
        if kind in ENV_ERRORS or kind == "okänd":
            return {"utfall": "MILJÖFEL", **row}
        return {"utfall": "FÅNGAD", **row}
    return {"utfall": "MILJÖFEL", "pytest": summary}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--python", default=str(DEFAULT_PY))
    a = ap.parse_args()
    base = baseline(a.python)
    selftest = env_selftest(a.python)
    rows = [{"fel": n, "fil": f, **run_one(a.python, n, f, o, w)} for n, f, o, w in MUTATIONS]
    rows += [{"fel": n, "fil": "momentum_signal.py", "utfall": "EKVIVALENT", "motivering": m} for n, m in EQUIVALENT]
    rows += [{"fel": n, "fil": None, "utfall": "EJ_TILLÄMPLIG", "motivering": m} for n, m in NOT_APPLICABLE]
    result = {"leverans": "H-0017 D1", "modul": "mom-control/1.0.0", "prov": TESTS, "baslinje": base, "miljöfel_självtest": selftest,
              "felprov": rows,
              "fångade": sum(r["utfall"] == "FÅNGAD" for r in rows), "missade": sum(r["utfall"] == "MISSAD" for r in rows),
              "ekvivalenta": len(EQUIVALENT), "ej_tillämpliga": len(NOT_APPLICABLE)}
    bad = [r for r in rows if r["utfall"] in ("MILJÖFEL", "MÖNSTER_SAKNAS")]
    if bad:
        sys.exit(f"MILJÖFEL eller saknat mönster: {bad}")
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if a.check:
        if OUT.read_text() != text:
            print("FAIL: felprovsmatrisen skiljer sig från", OUT.relative_to(ROOT))
            print(text)
            sys.exit(1)
        print(f"PASS: {result['fångade']} fångade, {result['missade']} missade, {result['ekvivalenta']} ekvivalenta, "
              f"{result['ej_tillämpliga']} ej tillämpliga")
        return
    OUT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
