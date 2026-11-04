"""Dagliga aktiekurser (Stooq, justerade för split och utdelning) och CUSIP → ticker (OpenFIGI).

Båda är gratis och kräver ingen nyckel. Allt sparas under data/raw/ och hämtas inte igen.
"""
from __future__ import annotations

import io
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

STOOQ = "https://stooq.com/q/d/l/?s={sym}.us&i=d"
FIGI = "https://api.openfigi.com/v3/mapping"


def _open(req, opener=None) -> bytes:
    if opener:
        return opener(req)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def stooq_symbol(ticker: str) -> str:
    return ticker.lower().replace("/", "-").replace(".", "-")


def load_prices(ticker: str, data_dir: Path, opener=None) -> pd.DataFrame | None:
    """Dagsstaplar (open, high, low, close, volume) i UTC, eller None om källan inte har aktien."""
    path = data_dir / "raw" / "stooq" / f"{stooq_symbol(ticker)}.csv"
    if not path.exists():
        url = STOOQ.format(sym=stooq_symbol(ticker))
        raw = _open(urllib.request.Request(url, headers={"User-Agent": "TraderGo research"}), opener)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        time.sleep(0.3)
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text.lower().startswith("date"):
        return None   # "No data" eller felsida
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.lower() for c in df.columns]
    if df.empty:
        return None
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("date")), name="date").tz_localize("UTC")
    return df[["open", "high", "low", "close"] + (["volume"] if "volume" in df else [])].astype(float)


def map_cusips(cusips: list[str], data_dir: Path, opener=None) -> dict[str, str | None]:
    """CUSIP → amerikansk ticker via OpenFIGI. Okända blir None. Svaren sparas och frågas aldrig igen."""
    path = data_dir / "raw" / "figi" / "cusip_ticker.json"
    known: dict[str, str | None] = json.loads(path.read_text()) if path.exists() else {}
    todo = [c for c in dict.fromkeys(cusips) if c not in known]
    for i in range(0, len(todo), 10):   # utan nyckel: högst 10 per anrop och 25 anrop per minut
        batch = todo[i:i + 10]
        body = json.dumps([{"idType": "ID_CUSIP", "idValue": c, "exchCode": "US"} for c in batch]).encode()
        req = urllib.request.Request(FIGI, data=body, headers={"Content-Type": "application/json"}, method="POST")
        res = json.loads(_open(req, opener))
        for c, r in zip(batch, res):
            data = r.get("data") or []
            eq = [d for d in data if d.get("marketSector") == "Equity"] or data
            known[c] = eq[0]["ticker"] if eq else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(known, indent=0, sort_keys=True))
        if opener is None:
            time.sleep(2.5)
    return {c: known.get(c) for c in cusips}
