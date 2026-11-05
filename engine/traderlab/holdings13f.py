"""Vad de tio investerarna äger just nu, enligt sin senaste 13F (kräver inga aktiekurser).

Skriver app/data/investors13f.json: per förvaltare den senaste redovisningen och dess tio största innehav, en
gemensam lista (samma vikter som portföljen i research/13f-protokoll.md) och de senaste redovisningarna (för "ping"
i appen). Bara offentliga SEC-data.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .copy13f import MANAGERS, TOP
from .data import ftd, sec13f

APP = Path("app/data/investors13f.json")


def snapshot(repo: Path, data_dir: Path | None = None, refresh: bool = True) -> dict:
    data_dir = data_dir or repo / "data"
    fmap = ftd.load_map(data_dir)
    managers, recent = [], []
    consensus: dict[str, dict] = {}
    for cik, name in MANAGERS.items():
        filings = sec13f.list_filings(cik, data_dir, refresh=refresh)
        if not filings:
            continue
        for f in filings[-3:]:
            recent.append({"manager": name, "filed": f.filed, "period": f.period})
        latest = filings[-1]
        rows = sec13f.holdings(latest, data_dir)
        top = sec13f.top_weights(rows, TOP)
        items = [{"ticker": fmap.get(cu), "name": rows[cu]["name"], "cusip": cu, "weight": round(w, 4)} for cu, w in top.items()]
        managers.append({"manager": name, "cik": cik, "filed": latest.filed, "period": latest.period, "top10": items})
        for it in items:
            key = it["ticker"] or it["cusip"]
            c = consensus.setdefault(key, {"ticker": it["ticker"], "name": it["name"], "weight": 0.0, "holders": []})
            c["weight"] += it["weight"]
            c["holders"].append(name)
    n = max(len(managers), 1)
    cons = sorted(({**c, "weight": round(c["weight"] / n, 4)} for c in consensus.values()), key=lambda c: -c["weight"])
    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SEC EDGAR 13F-HR", "rules": "research/13f-protokoll.md",
        "managers": managers, "consensus": cons[:30],
        "recent_filings": sorted(recent, key=lambda r: r["filed"], reverse=True)[:20],
    }
    path = repo / APP
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    s = snapshot(ap.parse_args().repo)
    print(f"{len(s['managers'])} förvaltare, senaste redovisning {s['recent_filings'][0]['filed'] if s['recent_filings'] else '-'}")


if __name__ == "__main__":
    main()
