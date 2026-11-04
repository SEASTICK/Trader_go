#!/usr/bin/env python3
"""Reproducerbar felprovsmatris för H-0017 D1 (mom-control/1.0.0).

Varje fel införs i en kopia av engine/ och de testresurser proven läser (docs/momentum-a1-orakel.json) i en temporär
katalog med samma struktur, aldrig i källfilerna. Först körs en oförändrad baslinje, som måste passera med exakt det
antal prov som samlas in; annars avbryts skriptet. Därefter körs D1-proven (tests/test_momentum_control.py och
tests/test_momentum_control_integration.py) per fel. FÅNGAD kräver att pytest körde proven och att minst ett prov
fallerade eller fick fel vid körning (exit 1, inga insamlingsfel); första fallerande prov sparas. MISSAD betyder att alla prov passerade.
Insamlings- eller miljöfel ger MILJÖFEL och gör att skriptet fallerar. Bevisat ekvivalenta fel är märkta EKVIVALENT
med motivering. Matrisen skrivs till docs/momentum-D1-mutationer.json.
Med --check körs allt om och jämförs mot den sparade matrisen. Python-tolken ges med --python (standard: projektets
venv).

    python3 scripts/momentum-d1-mutations.py [--check] [--python PATH]
"""
import argparse
import json
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
    ("delad kontoidentitet/state mellan konton", "momentum_control.py", "    state = ev.EngineState.start(scenario)\n",
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

EQUIVALENT = [
    ("observationsdagar i stället för kalenderdagar",
     "Market kräver exakt 4H-raster från 2021-11-01 till terminal, så varje kalenderdag är komplett. Den h:te föregående "
     "observationen är då exakt h kalenderdagar bak, och mutationen ger identiska signaler på varje giltigt D1-underlag. "
     "Skillnaden prövas i signalmodulens egna B-prov med ofullständiga dagar."),
]

NOT_APPLICABLE = []


def _workspace(tmp: Path) -> Path:
    dst = tmp / "engine"
    shutil.copytree(ROOT / "engine", dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    (tmp / "docs").mkdir()
    shutil.copy(ROOT / "docs/momentum-a1-orakel.json", tmp / "docs/momentum-a1-orakel.json")
    return dst


def _pytest(py, cwd):
    p = subprocess.run([str(py), "-m", "pytest", "-p", "no:cacheprovider", "-o", "addopts=", "-q", "-x", "-rfE", *TESTS], cwd=cwd,
                       capture_output=True, text=True)
    out = p.stdout + p.stderr
    summary = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l][-1:] or [""]
    failed = [l.split(" ")[1] for l in out.splitlines() if l.startswith(("FAILED ", "ERROR ")) and "collecting" not in l]
    collect_error = "ERROR collecting" in out or "errors during collection" in out
    return p.returncode, summary[0].strip(), failed if not collect_error else []


def baseline(py) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        code, summary, _ = _pytest(py, _workspace(Path(tmp)))
    if code != 0 or "failed" in summary or "error" in summary or "passed" not in summary:
        sys.exit(f"MILJÖFEL: den oförändrade baslinjen är inte grön ({code}: {summary}).")
    return summary


def run_one(py, name, rel, old, new):
    with tempfile.TemporaryDirectory() as tmp:
        dst = _workspace(Path(tmp))
        f = dst / "traderlab" / rel
        src = f.read_text()
        if src.count(old) != 1:
            return {"utfall": "MÖNSTER_SAKNAS"}
        f.write_text(src.replace(old, new))
        code, summary, failed = _pytest(py, dst)
    if code == 0:
        return {"utfall": "MISSAD", "pytest": summary}
    if code == 1 and failed:                       # prov fallerade eller fick fel vid körning (inte insamling)
        return {"utfall": "FÅNGAD", "pytest": summary, "första_fel": failed[0]}
    return {"utfall": "MILJÖFEL", "pytest": summary}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--python", default=str(DEFAULT_PY))
    a = ap.parse_args()
    base = baseline(a.python)
    rows = [{"fel": n, "fil": f, **run_one(a.python, n, f, o, w)} for n, f, o, w in MUTATIONS]
    rows += [{"fel": n, "fil": "momentum_signal.py", "utfall": "EKVIVALENT", "motivering": m} for n, m in EQUIVALENT]
    rows += [{"fel": n, "fil": None, "utfall": "EJ_TILLÄMPLIG", "motivering": m} for n, m in NOT_APPLICABLE]
    result = {"leverans": "H-0017 D1", "modul": "mom-control/1.0.0", "prov": TESTS, "baslinje": base, "felprov": rows,
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
