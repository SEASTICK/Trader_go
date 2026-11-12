"""Granskning av hållna positioner där nästa öppning saknas (avnotering eller datalucka).

Skapad efter Codex granskning av H-0021 (PR #110): portfolio.run värderade den sista stapeln till avkastning 0 och stängde
positionen till senast kända öppning, vilket kan ge en retroaktiv och för gynnsam fyllning. Verktyget läser samma data
som H-0021 (periodgränser, slutprovet läses aldrig), räknar fram samma vikter och listar varje sådant fall.
Det ändrar inga resultat och skriver ingen ny hypotesrad.

Klasser:
- `serien_tar_slut`: kontraktets data tar slut och återkommer inte (trolig avnotering).
- `lucka_serien_fortsätter`: dagsstaplar saknas men serien återkommer senare (dataavbrott).
Ingen av dem är *dokumenterad*: arkivet har bara dagsstaplar och innehåller inga tidsstämplade avnoteringsbesked, så alla
räknas som oförklarade enligt protokollets fail-closed-princip.

Körs: `python -m traderlab.gapaudit` (från engine/), skriver research/audits/H-0021-gaps-<tid>.json.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import portfolio, tsmom, xsbig

OUT = Path("research/audits")
NOT_DOCUMENTED = "Ingen tidsstämplad avnoteringskälla ingår i data (arkivet har bara dagsstaplar). Räknas som oförklarad."


def classify(opens: pd.DataFrame, gaps: list) -> list[dict]:
    """Berikar portföljens `gaps` (dag, instrument, vikt) med riktning, klass och datagränser."""
    rows = []
    for day, sym, weight in gaps:
        s = opens[sym].dropna()
        later = s[s.index > pd.Timestamp(day, tz="UTC") + pd.Timedelta(days=1)]
        rows.append({"day": day, "contract": sym, "weight": round(weight, 5), "direction": "short" if weight < 0 else "long",
                     "last_data": str(s.index[-1].date()),
                     "kind": "serien_tar_slut" if later.empty else "lucka_serien_fortsätter",
                     "resumes": None if later.empty else str(later.index[0].date()),
                     "documented": False, "note": NOT_DOCUMENTED})
    return rows


def audit(repo: Path, data_dir: Path | None = None) -> dict:
    data_dir = data_dir or repo / "data"
    syms = xsbig.universe(data_dir)
    opens, highs, lows, closes, dvol, funding = tsmom.load_panel(data_dir, syms)
    assert opens.index.max() < pd.Timestamp(tsmom.HOLDOUT, tz="UTC"), "Slutprovet får inte läsas in."
    start = pd.Timestamp(tsmom.START, tz="UTC")
    w = tsmom.weights(closes, dvol)
    w = w[w.index >= start]
    res = portfolio.run(opens, w, tsmom.COSTS, funding, highs=highs, lows=lows, stop=tsmom.STOP)   # utan strict: för att kunna lista
    rows = classify(opens, res.gaps)
    by_day: dict[str, dict] = {}
    for r in rows:
        d = by_day.setdefault(r["day"], {"positions": 0, "gross_weight": 0.0})
        d["positions"] += 1
        d["gross_weight"] = round(d["gross_weight"] + abs(r["weight"]), 5)
    return {"hypothesis_id": "H-0021", "kind": "gap-audit", "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "period": [str(start.date()), str(opens.index.max().date())], "universe": len(syms),
            "held_transitions_without_next_open": len(rows),
            "contracts": sorted({r["contract"] for r in rows}),
            "by_kind": {k: sum(1 for r in rows if r["kind"] == k) for k in ("serien_tar_slut", "lucka_serien_fortsätter")},
            "by_day": by_day, "rows": rows,
            "series_ending_before_panel_end": {s: str(opens[s].dropna().index[-1].date()) for s in opens.columns
                                               if opens[s].dropna().index[-1] < opens.index[-1]},
            "how_treated_by_engine_before_fix": "Sista stapeln värderades till avkastning 0 och positionen stängdes till senast kända öppning.",
            "note": "Diagnos. Ändrar inget resultat och är ingen ny körning av strategin."}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args()
    d = audit(a.repo)
    folder = a.repo / OUT
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'H-0021-gaps-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: d[k] for k in ("held_transitions_without_next_open", "by_kind", "contracts")}, ensure_ascii=False))
    print(path)


if __name__ == "__main__":
    main()
