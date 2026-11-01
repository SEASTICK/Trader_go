"""Motorn läser appens insamlade data med samma schema som appen skriver (app/src-tauri/src/market/schema.sql)."""
import sqlite3
from pathlib import Path

import pytest

from traderlab import quality
from traderlab.data import live
from traderlab.synthetic import make_bars

SCHEMA = Path(__file__).resolve().parents[2] / "app" / "src-tauri" / "src" / "market" / "schema.sql"


def _db(tmp_path, bars, symbol="BTCUSDT", interval="4h", live_bar=True):
    path = tmp_path / "market-data.sqlite"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    step = 4 * 3600 * 1000
    rows = []
    for t, r in bars.iterrows():
        ms = int(t.timestamp() * 1000)
        rows.append(("binance", "spot", symbol, interval, ms, r.open, r.high, r.low, r.close, r.volume, ms + step - 1, "rest", None, 1))
    con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    if live_bar:
        last = rows[-1][4] + step
        con.execute("INSERT INTO live_bar VALUES ('binance','spot',?,?,?,1,2,0.5,1.5,9,?,NULL,1)", (symbol, interval, last, last + step - 1))
    con.commit()
    con.close()
    return path


def test_reads_closed_bars_in_engine_format_and_passes_quality(tmp_path):
    bars = make_bars(300, interval="4h", seed=3)
    db = _db(tmp_path, bars)
    got = live.load(db, "BTCUSDT", "4h")
    assert list(got.columns) == ["open", "high", "low", "close", "volume"]
    assert str(got.index.tz) == "UTC" and got.index.name == "open_time"
    assert len(got) == 300, "the open bar is not analysis data"
    assert (got.index == bars.index).all()
    assert quality.check(got, "4h").ok


def test_other_series_are_not_mixed_in(tmp_path):
    db = _db(tmp_path, make_bars(10, interval="4h", seed=1))
    assert len(live.load(db, "ETHUSDT", "4h")) == 0


def test_reading_never_writes(tmp_path):
    db = _db(tmp_path, make_bars(10, interval="4h", seed=1))
    before = db.read_bytes()
    live.load(db)
    assert db.read_bytes() == before


def test_missing_database_says_how_to_get_one(tmp_path):
    with pytest.raises(FileNotFoundError, match="Starta TraderGO"):
        live.load(tmp_path / "none.sqlite")


def test_default_path_is_the_apps_data_folder():
    p = live.default_db_path()
    assert p.name == "market-data.sqlite" and "com.seastick.tradergo" in str(p)
