"""Läser marknadsdata som TraderGO-appen samlat in (app/src-tauri/src/market). Bara läsning.

Databasen ligger i appens datamapp, aldrig i Git:
  macOS:   ~/Library/Application Support/com.seastick.tradergo/market/market-data.sqlite
  Windows: %APPDATA%\\com.seastick.tradergo\\market\\market-data.sqlite
  Linux:   ~/.local/share/com.seastick.tradergo/market/market-data.sqlite

Bara stängda, kontrollerade staplar finns i tabellen `bars`; den pågående stapeln ligger separat och läses
inte här. Resultatet har samma form som `binance.load` (se bars.py), så `quality.check` och experimenten
fungerar som vanligt. Kör alltid `quality.check` innan datan används i en hypotes.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pandas as pd

from ..bars import COLUMNS

APP_ID = "com.seastick.tradergo"


def app_data_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_ID
    if os.name == "nt":
        return Path(os.environ["APPDATA"]) / APP_ID
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_ID


def default_db_path() -> Path:
    return app_data_dir() / "market" / "market-data.sqlite"


def load(db: Path | None = None, symbol: str = "BTCUSDT", interval: str = "4h", provider: str = "binance",
         market: str = "spot") -> pd.DataFrame:
    """Stängda staplar för en serie, indexerade på öppningstid i UTC."""
    path = Path(db) if db else default_db_path()
    if not path.exists():
        raise FileNotFoundError(f"Ingen insamlad data i {path}. Starta TraderGO-appen först.")
    # Skrivskyddat: motorn ändrar aldrig appens databas. closing() stänger anslutningen; ett vanligt
    # `with sqlite3.connect(...)` gör bara commit/rollback och lämnar filen öppen (låser den på Windows).
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as con:
        df = pd.read_sql_query(
            "SELECT open_time, open, high, low, close, volume FROM bars "
            "WHERE provider=? AND market=? AND symbol=? AND interval=? ORDER BY open_time",
            con, params=(provider, market, symbol, interval))
    idx = pd.DatetimeIndex(pd.to_datetime(df["open_time"], unit="ms", utc=True), name="open_time")
    out = df[COLUMNS].astype(float)
    out.index = idx
    return out


def status(path: Path | None = None) -> dict:
    """Insamlingens senaste status (market/status.json)."""
    p = Path(path) if path else app_data_dir() / "market" / "status.json"
    return json.loads(p.read_text(encoding="utf-8"))
