"""Pelosis nya redovisade affärer framåt (från 2026-11-05), för sidan Investerare i appen.

Läser bara redovisningar inlämnade från startdagen. Slutprovet för H-0017 (2025-01-01 till 2026-11-04) läses
inte, så att det kan köras orört senare. Inga kurser behövs, och inga order läggs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .data import house

APP = Path("app/data/pelosi.json")
START = "2026-11-05"


def update(repo: Path, start: str = START, data_dir: Path | None = None, today: str | None = None) -> dict:
    data_dir = data_dir or repo / "data"
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    reports = []
    for year in range(int(start[:4]), int(today[:4]) + 1):
        idx = data_dir / "raw" / "house" / f"{year}FD.zip"
        if idx.exists():
            idx.unlink()   # årsindexet växer under året: hämta om varje gång
        try:
            reports += [r for r in house.reports(year, data_dir) if r.filed >= start]
        except Exception as exc:   # ett år utan index (tidigt i januari) stoppar inte resten
            print(f"Index {year} saknas: {exc}")
    filings = []
    for r in sorted(reports, key=lambda r: r.filed, reverse=True):
        trades = house.parse(house.pdf_text(r, data_dir))
        filings.append({"filed": r.filed, "doc_id": r.doc_id, "trades": [t.__dict__ for t in trades]})
    out = {"updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "start": start,
           "source": "House Clerk PTR", "rules": "research/pelosi-protokoll.md", "filings": filings[:30]}
    path = repo / APP
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out


def main() -> None:
    s = update(Path(__file__).resolve().parents[2])
    print(f"Pelosi: {len(s['filings'])} redovisningar sedan {s['start']}")


if __name__ == "__main__":
    main()
