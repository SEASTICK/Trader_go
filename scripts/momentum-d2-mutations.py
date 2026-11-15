#!/usr/bin/env python3
"""Reproducerbar felprovsmatris för H-0026 (tidigare H-0017) D2 (mom-bh/1.0.0 och eventlagrets buy_and_hold-väg).

Byggd på D1:s godkända skript (scripts/momentum-d1-mutations.py, granskat på 7345f06) med samma klassning; bara
prov, felinjektioner och utdatafil skiljer. D1:s skript är oförändrat.

Varje fel införs i en kopia av engine/ och de testresurser proven läser (docs/momentum-a1-orakel.json) i en temporär
katalog med samma struktur, aldrig i källfilerna. Först körs en oförändrad baslinje, som måste passera med exakt det
antal prov som samlas in; annars avbryts skriptet. Därefter körs per fel först de riktade proven i TARGETS; om de
passerar körs hela D2-sviten (tests/test_momentum_control.py och tests/test_momentum_control_integration.py), så att
MISSAD alltid bygger på hela sviten. FÅNGAD kräver att ett prov fallerade eller fick fel med
mutanten (exit 1, inga insamlingsfel) och att exakt samma prov passerar i en tvillingkopia av samma arbetsyta där
bara mutationen är återställd, med samma provurval i samma ordning. Annars är felet inte orsakat av mutationen och
blir MILJÖFEL, oavsett fas, undantagstyp och ordningsberoende. Prov, orsak, fas och tvillingens utfall sparas. Ett självtest injicerar setupfel (RuntimeError,
AssertionError, FileNotFoundError) med en neutral källändring och kräver MILJÖFEL, och kräver FÅNGAD för en verklig
mutation. Körtider
sparas inte, eftersom de inte är reproducerbara. MISSAD betyder att alla prov passerade.
Insamlings- eller miljöfel ger MILJÖFEL och gör att skriptet fallerar. Bevisat ekvivalenta fel är märkta EKVIVALENT
med motivering. Matrisen skrivs till docs/momentum-D2-mutationer.json.
Med --check körs allt om och jämförs mot den sparade matrisen. Python-tolken ges med --python (standard: projektets
venv).

    python3 scripts/momentum-d2-mutations.py [--check] [--python PATH]
"""
from __future__ import annotations

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
OUT = ROOT / "docs/momentum-D2-mutationer.json"
TESTS = ["tests/test_momentum_benchmark.py", "tests/test_momentum_event.py", "tests/test_momentum_control.py"]
DEFAULT_PY = Path("/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python")

# (namn, fil i engine/traderlab, gammal text, ny text)
MUTATIONS = [
    ("storlek före avgift (ingen kostnad i lösaren)", "momentum_risk.py", "    return fill(acct, intent.w, P, M, c)",
     "    return fill(acct, intent.w, P, M, 0.0)"),
    ("kostnad dubbelt", "momentum_risk.py", "    return fill(acct, intent.w, P, M, c)", "    return fill(acct, intent.w, P, M, 2 * c)"),
    ("fel P/M vid inträde", "momentum_event.py",
     "acct, f = risk.fill_intent(acct, intent, bar.contract_open, bar.mark_open, s.cost)",
     "acct, f = risk.fill_intent(acct, intent, bar.mark_open, bar.contract_open, s.cost)"),
    ("ombalansering vid midnatt", "momentum_event.py", "    if not rs.started:\n        intent = risk.Intent(kind=risk.NORMAL, w=1.0",
     "    if not rs.started or T == T.floor(\"D\"):\n        intent = risk.Intent(kind=risk.NORMAL, w=1.0"),
    ("återköp vid årsskifte", "momentum_event.py", "    if not rs.started:\n        intent = risk.Intent(kind=risk.NORMAL, w=1.0",
     "    if not rs.started or (T.month, T.day, T.hour) == (1, 1, 0):\n        intent = risk.Intent(kind=risk.NORMAL, w=1.0"),
    ("momentumrisk på buy_and_hold", "momentum_event.py", "    if s.policy == BUY_AND_HOLD:\n", "    if False:\n"),
    ("buy_and_hold-policyn läcker till main/komponent", "momentum_event.py", "    if s.policy == BUY_AND_HOLD:\n",
     "    if s.policy in POLICIES:\n"),
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
    ("1 ms-event behandlat som samtidigt", "momentum_event.py",
     "(simultaneous if e.time == bar.open_time else interior).append(e)",
     "(simultaneous if e.time - bar.open_time < pd.Timedelta(seconds=1) else interior).append(e)"),
    ("fel fundingtecken", "momentum_funding.py",
     "    payment = _out(\"fundingbelopp\", 2 * base) if config.stress and base > 0 else base",
     "    payment = -base"),
    ("kredit räddar adverse-prövningen", "momentum_event.py", "                    if fr.payment > 0:", "                    if True:"),
    ("mellanfunding bokförd trots intrastapelträff", "momentum_event.py",
     'delta = _out("justering", lr.adjustment_delta - in_basis)', 'delta = _out("justering", lr.adjustment_delta)'),
    ("fill före gapmarginal", "momentum_event.py",
     "        chk = margin.check(acct, ms, margin.GAP, bar.mark_open, margin.MARK_OPEN, T) if acct.q != 0 else None",
     "        if intent is not None:\n            acct, _f = risk.fill_intent(acct, intent, bar.contract_open, bar.mark_open, s.cost)\n"
     "            intent = None\n        chk = margin.check(acct, ms, margin.GAP, bar.mark_open, margin.MARK_OPEN, T) if acct.q != 0 else None"),
    ("likvidation glöms i kontoregeln (återupplivning)", "momentum_event.py",
     "    liquidated = rs.liquidated or (close is not None and close.liquidated)", "    liquidated = False"),
    ("terminal en stapel sent", "momentum_event.py",
     "rs, rec = _bh_step(rs, T, close, E_close if close is not None else None, terminal=T == TERMINAL)",
     "rs, rec = _bh_step(rs, T, close, E_close if close is not None else None, terminal=T == TERMINAL + BAR)"),
    ("terminalkostnad tappad", "momentum_ledger.py", "COST_NORMAL = (10 + 2 / 2 + 5) / 10_000      # 0,0016 per sida",
     "COST_NORMAL = 0.0"),
    ("startpunkt tappad", "momentum_event.py", "            return cls(state=state, close_points=((None, START, INITIAL),),",
     "            return cls(state=state, close_points=(),"),
    ("sista close/terminalpunkt tappad", "momentum_event.py", "            cps += ((T, T, E),)", "            pass"),
    ("delat kontoförlopp mellan legacy-ordningar", "momentum_benchmark.py",
     'scenario = ev.Scenario(f"buy_and_hold/{legacy_order}", order, mmr, cost, policy=ev.BUY_AND_HOLD)',
     'scenario = ev.Scenario("buy_and_hold", order, mmr, cost, policy=ev.BUY_AND_HOLD)'),
    ("ändrat underlag godtas", "momentum_benchmark.py", "    market = market.verified()\n", "\n"),
    ("policyn utanför etiketten (policybyte oskyddat)", "momentum_event.py",
     'return base if self.policy == MOMENTUM else f"{self.policy}-{base}"', "return base"),
    ("signal godtas för buy_and_hold", "momentum_event.py", "        if signal is not None:\n            raise EventError(\"buy_and_hold tar ingen signal",
     "        if False:\n            raise EventError(\"buy_and_hold tar ingen signal"),
]

# Riktade prov per fel (pytest -k-uttryck). De körs först; fallerar ett av dem är felet fångat av ett verkligt prov.
# Passerar de körs hela D2-sviten innan felet får klassas som MISSAD, så ett för smalt urval kan inte dölja en miss.
TARGETS = {
    "storlek före avgift (ingen kostnad i lösaren)": "test_O2_full_weight_entry_after_cost",
    "kostnad dubbelt": "test_O2_full_weight_entry_after_cost",
    "fel P/M vid inträde": "test_entry_with_basis_P_ne_M",
    "ombalansering vid midnatt": "test_fixed_units_no_cap_band_or_stops",
    "återköp vid årsskifte": "test_eight_labels_independent_ledger",
    "momentumrisk på buy_and_hold": "test_O2_full_weight_entry_after_cost",
    "buy_and_hold-policyn läcker till main/komponent": "test_momentum_label_and_path_unchanged or test_O5",
    "A på nya q": "test_funding_times_entry_midnight_and_terminal",
    "B på gamla q": "test_funding_times_entry_midnight_and_terminal",
    "1 ms-event behandlat som samtidigt": "test_funding_times_entry_midnight_and_terminal",
    "fel fundingtecken": "test_fixed_units_no_cap_band_or_stops",
    "kredit räddar adverse-prövningen": "test_mmr_scenarios_differ_and_intrabar",
    "mellanfunding bokförd trots intrastapelträff": "test_mmr_scenarios_differ_and_intrabar",
    "fill före gapmarginal": "test_public_gap_liquidation_at_float_boundary or test_gap_liquidation_before_fill",
    "likvidation glöms i kontoregeln (återupplivning)": "test_mmr_scenarios_differ_and_intrabar or test_liquidated_buy_and_hold",
    "terminal en stapel sent": "test_pre_start_and_2025 or test_constant_close_market",
    "terminalkostnad tappad": "test_O2_full_weight_entry_after_cost",
    "startpunkt tappad": "test_eight_labels_independent_ledger",
    "sista close/terminalpunkt tappad": "test_eight_labels_independent_ledger",
    "delat kontoförlopp mellan legacy-ordningar": "test_eight_labels_independent_ledger",
    "ändrat underlag godtas": "test_pre_start_and_2025_funding_handled_before_economics",
    "policyn utanför etiketten (policybyte oskyddat)": "test_momentum_label_and_path_unchanged",
    "signal godtas för buy_and_hold": "test_policy_binding_and_errors",
}

EQUIVALENT = []

NOT_APPLICABLE = []


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


def _pytest(py, cwd, k=None, extra=()):
    """Kör D2-proven. Returnerar exitkod, sammanfattning utan körtid och första fallerade prov med undantagstyp ur
    pytests JUnit-XML (failure/error-elementens type-attribut), eller None."""
    xml = Path(cwd) / "_d1_junit.xml"
    p = subprocess.run([str(py), "-m", "pytest", "-p", "no:cacheprovider", "-o", "addopts=", "-q", "-x",
                        f"--junitxml={xml}", *(["-k", k] if k else []), *TESTS, *extra], cwd=cwd, capture_output=True, text=True)
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


def _node(test_id: str) -> str:
    """JUnit 'tests.test_x::test_y[p]' till pytest-nod 'tests/test_x.py::test_y[p]'."""
    mod, _, name = test_id.partition("::")
    return mod.replace(".", "/") + ".py::" + name


def _snapshot(dst: Path, tmp: Path, rel: str, original: str | None, label: str = "kontroll") -> Path:
    """Orörd kopia av arbetsytan tagen INNAN något prov har körts. Med `original` återställs bara mutationen
    (kontrollgren); utan den är kopian en färsk mutantgren. Allt annat (testfiler, fixturer, resurser, eventuella
    injicerade fel) är identiskt med utgångsläget."""
    twin = tmp / label / dst.name
    shutil.copytree(dst, twin, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "_d1_junit.xml"))
    for extra in ("docs",):                                   # resurser utanför engine/ följer med
        if (dst.parent / extra).exists():
            shutil.copytree(dst.parent / extra, tmp / label / extra)
    if original is not None:
        (twin / "traderlab" / rel).write_text(original)
    return twin


def _twin_passes(py, twin: Path, k, extra=()) -> bool:
    """Kör exakt samma provurval (samma -k eller hela D2-sviten, samma ordning) i kontrollgrenen. Den har inte rörts
    av mutantens körning och måste passera helt."""
    code, _, _ = _pytest(py, twin, k, extra)
    return code == 0


def classify(py, twin: Path, code: int, summary: str, first, scope: str, k=None, extra=()) -> dict:
    """FÅNGAD kräver att ett prov fallerar eller får fel med mutanten och att exakt samma provurval, i samma ordning,
    passerar helt i kontrollgrenen: samma orörda utgångsläge som mutanten, med bara mutationen återställd. Annars är felet inte orsakat av mutationen: MILJÖFEL, oavsett fas (setup, anrop, nedstädning)
    och undantagstyp."""
    if code == 0:
        return {"utfall": "MISSAD", "pytest": summary, "körda_prov": scope}
    if code != 1 or not first:
        return {"utfall": "MILJÖFEL", "pytest": summary, "körda_prov": scope}
    test_id, kind, tag = first
    row = {"pytest": summary, "första_fel": test_id, "orsak": kind, "fas": "anrop" if tag == "failure" else "setup/nedstädning",
           "körda_prov": scope}
    if _twin_passes(py, twin, k, extra):
        return {"utfall": "FÅNGAD", **row, "tvilling_utan_mutation": "passerar"}
    return {"utfall": "MILJÖFEL", **row, "tvilling_utan_mutation": "fallerar också"}


def baseline(py) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        code, summary, _ = _pytest(py, _workspace(Path(tmp)))
    if code != 0 or "failed" in summary or "error" in summary or "passed" not in summary:
        sys.exit(f"MILJÖFEL: den oförändrade baslinjen är inte grön ({code}: {summary}).")
    return summary


_FIXTURE = "import pytest\nfrom pathlib import Path\n\n_n = [0]\n\n\n@pytest.fixture(autouse=True)\ndef _synthetic():\n{body}\n"
SELFTEST_FAULTS = {
    "setup RuntimeError": "    raise RuntimeError(\"synthetic missing test resource\")",
    "setup AssertionError": "    raise AssertionError(\"synthetic missing test resource\")",
    "setup FileNotFoundError": "    raise FileNotFoundError(\"synthetic missing test resource\")",
    "ordningsberoende (andra provet)": "    _n[0] += 1\n    if _n[0] == 2:\n        raise RuntimeError(\"synthetic fault on the second test\")",
    # Resurs vid första användning: saknas markören skapas den och felet kastas. En kopia efter körningen skulle ärva
    # markören och passera; kontrollgrenen tas före körningen och fallerar därför också.
    "första användning, setup": "    m = Path(__file__).with_name(\"_marker_setup\")\n    if not m.exists():\n        m.write_text(\"x\")\n        raise RuntimeError(\"synthetic first-use resource failure\")",
    "första användning, anrop": "    yield                                  # felet ligger i provet test_zz_first_use (nedan)",
    "första användning, nedstädning": "    m = Path(__file__).with_name(\"_marker_teardown\")\n    first = not m.exists()\n    yield\n    if first:\n        m.write_text(\"x\")\n        raise RuntimeError(\"synthetic first-use teardown failure\")",
}


def env_selftest(py) -> dict:
    """Ett fel som inte orsakas av en beteendemutation får aldrig bli FÅNGAD. För varje fall: neutral kommentarändring
    i källan plus en injicerad autouse-fixtur; kräver MILJÖFEL. Kontroll åt andra hållet: en verklig mutation utan
    injicerat fel ska bli FÅNGAD."""
    out = {}
    rel, marker = "momentum_control.py", 'VERSION = "mom-control/1.0.0"\n'
    for name, body in SELFTEST_FAULTS.items():
        with tempfile.TemporaryDirectory() as tmp:
            dst = _workspace(Path(tmp))
            f = dst / "traderlab" / rel
            original = f.read_text()
            f.write_text(original.replace(marker, marker + "# neutral kommentar (självtest)\n", 1))
            (dst / "tests" / "conftest.py").write_text(_FIXTURE.format(body=body))
            if name == "första användning, anrop":         # anropsfel vid första användning: provet självt fallerar
                (dst / "tests" / "test_zz_first_use.py").write_text(
                    "from pathlib import Path\n\n\ndef test_first_use():\n"
                    "    m = Path(__file__).with_name(\"_marker_call_test\")\n"
                    "    if not m.exists():\n        m.write_text(\"x\")\n        raise RuntimeError(\"synthetic first-use call failure\")\n")
            twin = _snapshot(dst, Path(tmp), rel, original)
            extra = ["tests/test_zz_first_use.py"] if name == "första användning, anrop" else []
            code, summary, first = _pytest(py, dst, None, extra)
            res = classify(py, twin, code, summary, first, "hela D2-sviten", None, extra)
        if res["utfall"] != "MILJÖFEL":
            sys.exit(f"Självtestet klassade {name} utan beteendemutation som {res['utfall']}: {res}")
        out[name] = res["utfall"]
    # D1-11: det riktade provet lämnar en markör; prov i första filen fallerar om markören redan finns. I en orörd
    # helkörning körs första filen före det riktade provet och passerar. En reservkörning i den redan använda
    # arbetsytan skulle fallera och ge falsk FÅNGAD; med orörda grenar blir den neutrala ändringen MISSAD.
    target = "test_signal_input_is_zero_or_cap_never_main_mean"
    leftover = ("import pytest\nfrom pathlib import Path\n\n\n@pytest.fixture(autouse=True)\ndef _leftover(request):\n"
                "    m = Path(__file__).with_name(\"_marker_leftover\")\n"
                f"    if request.node.name == \"{target}\":\n        m.write_text(\"x\")\n"
                "    elif request.node.fspath.basename == \"test_momentum_benchmark.py\" and m.exists():\n"
                "        raise RuntimeError(\"synthetic leftover resource from an earlier run\")\n")
    with tempfile.TemporaryDirectory() as tmp:
        dst = _workspace(Path(tmp))
        f = dst / "traderlab" / rel
        original = f.read_text()
        f.write_text(original.replace(marker, marker + "# neutral kommentar (självtest)\n", 1))
        (dst / "tests" / "conftest.py").write_text(leftover)
        res = _run_flow(py, Path(tmp), dst, rel, original, target)
    if res["utfall"] == "FÅNGAD":
        sys.exit(f"Självtestet: kvarlämnad resurs från den riktade körningen gav falsk FÅNGAD: {res}")
    out["kvarlämnad resurs före reservkörning"] = res["utfall"]
    n, f_rel, o, w = MUTATIONS[0]
    real = run_one(py, n, f_rel, o, w)
    if real["utfall"] != "FÅNGAD":
        sys.exit(f"Självtestet: en verklig mutation ({n}) blev {real['utfall']}, inte FÅNGAD.")
    out["verklig mutation"] = "FÅNGAD"
    return out


def run_one(py, name, rel, old, new):
    with tempfile.TemporaryDirectory() as tmp:
        dst = _workspace(Path(tmp))
        f = dst / "traderlab" / rel
        src = f.read_text()
        if src.count(old) != 1:
            return {"utfall": "MÖNSTER_SAKNAS"}
        f.write_text(src.replace(old, new))
        return _run_flow(py, Path(tmp), dst, rel, src, TARGETS.get(name))


def _run_flow(py, t: Path, dst: Path, rel: str, src: str, k_targeted) -> dict:
    """Riktade prov först, annars hela D2-sviten. Alla ögonblicksbilder tas före varje provkörning: varje jämförelse
    (riktad och hela sviten) har en egen orörd mutantgren och en egen orörd kontrollgren, så ingen körning ärver
    resurser från en tidigare."""
    mut_full = _snapshot(dst, t, rel, None, "mutant_hela")
    ctl_targeted = _snapshot(dst, t, rel, src, "kontroll_riktade")
    ctl_full = _snapshot(dst, t, rel, src, "kontroll_hela")
    scope, k, twin = "riktade", k_targeted, ctl_targeted
    code, summary, first = _pytest(py, dst, k)
    if code == 0 or (code == 5 and not first):          # riktade prov passerade (eller inga valdes): hela sviten
        scope, k, twin = "hela D2-sviten", None, ctl_full
        code, summary, first = _pytest(py, mut_full)
    return classify(py, twin, code, summary, first, scope, k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--python", default=str(DEFAULT_PY))
    a = ap.parse_args()
    base = baseline(a.python)
    selftest = env_selftest(a.python)
    rows = [{"fel": n, "fil": f, **run_one(a.python, n, f, o, w)} for n, f, o, w in MUTATIONS]
    rows += [{"fel": n, "fil": None, "utfall": "EKVIVALENT", "motivering": m} for n, m in EQUIVALENT]
    rows += [{"fel": n, "fil": None, "utfall": "EJ_TILLÄMPLIG", "motivering": m} for n, m in NOT_APPLICABLE]
    result = {"leverans": "H-0026 (tidigare H-0017) D2", "modul": "mom-bh/1.0.0", "prov": TESTS, "baslinje": base, "miljöfel_självtest": selftest,
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
