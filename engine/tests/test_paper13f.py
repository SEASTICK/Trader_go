import json

import numpy as np
import pandas as pd
import pytest

from traderlab import paper13f
from traderlab.data import ftd, sec13f, stocks


@pytest.fixture
def world(tmp_path, monkeypatch):
    days = pd.bdate_range("2026-10-01", "2026-11-30", tz="UTC")
    px = {"AAA": np.linspace(100, 120, len(days)), "BBB": np.linspace(50, 40, len(days)), "SPY": np.linspace(400, 410, len(days))}
    frames = {t: pd.DataFrame({"open": v, "high": v, "low": v, "close": v}, index=days) for t, v in px.items()}
    monkeypatch.setattr(stocks, "load_prices", lambda t, d, opener=None, max_age_hours=None: frames.get(t))
    monkeypatch.setattr(ftd, "load_map", lambda d: {"c1": "AAA", "c2": "BBB"})
    filings = {1067983: [sec13f.Filing(1067983, "a1", "2026-08-14", ""), sec13f.Filing(1067983, "a2", "2026-11-14", "")]}
    rows = {"a1": {"c1": {"name": "A", "value": 100.0, "shares": 1}},
            "a2": {"c2": {"name": "B", "value": 100.0, "shares": 1}}}
    monkeypatch.setattr(sec13f, "list_filings", lambda cik, d, opener=None, refresh=False: filings.get(cik, []))
    monkeypatch.setattr(sec13f, "holdings", lambda f, d, opener=None: rows[f.accession])
    return tmp_path


def test_starts_with_100k_and_switches_after_new_filing(world):
    s = paper13f.update(world, "2026-11-02")
    assert s["history"][0]["value"] == pytest.approx(100_000 * (1 - 0.001))   # köp vid öppning, 10 bp
    assert [e["manager"] for e in s["events"]] == ["Berkshire Hathaway"]
    assert s["events"][0]["day"] == "2026-11-16"            # nästa handelsdag efter lördagen 14/11
    assert [h["ticker"] for h in s["holdings"]] == ["BBB"]
    assert (world / "app/data/paper13f.json").exists()
    on_disk = json.loads((world / "research/paper/13f-observation.json").read_text())
    assert on_disk["kind"] == "observation"


def test_rerun_is_deterministic(world):
    a = paper13f.update(world, "2026-11-02")
    b = paper13f.update(world, "2026-11-02")
    assert a["history"] == b["history"] and a["holdings"] == b["holdings"]


def test_holdings_snapshot_without_prices(tmp_path, monkeypatch):
    from traderlab import holdings13f
    monkeypatch.setattr(ftd, "load_map", lambda d: {"c1": "AAA", "c2": "BBB"})
    fs = {1067983: [sec13f.Filing(1067983, "a1", "2026-08-14", "2026-06-30")],
          1061768: [sec13f.Filing(1061768, "b1", "2026-08-13", "2026-06-30")],
          1649339: [sec13f.Filing(1649339, "x1", "2026-08-15", "2026-06-30")]}
    rows = {"a1": {"c1": {"name": "A", "value": 300.0, "shares": 1}, "c2": {"name": "B", "value": 100.0, "shares": 1}},
            "b1": {"c2": {"name": "B", "value": 50.0, "shares": 1}},
            "x1": {"c1": {"name": "A", "value": 10.0, "shares": 1}}}
    monkeypatch.setattr(sec13f, "list_filings", lambda cik, d, opener=None, refresh=False: fs.get(cik, []))
    monkeypatch.setattr(sec13f, "holdings", lambda f, d, opener=None: rows[f.accession])
    s = holdings13f.snapshot(tmp_path)
    cons = {c["ticker"]: c for c in s["consensus"]}
    assert cons["BBB"]["weight"] == pytest.approx((0.25 + 1.0) / 2) and len(cons["BBB"]["holders"]) == 2
    # Extra investerare visas för sig och påverkar inte den gemensamma listan.
    assert [o["manager"] for o in s["others"]] == ["Scion (Michael Burry)"]
    assert len(s["managers"]) == 2 and cons["AAA"]["holders"] == ["Berkshire Hathaway"]
    assert s["recent_filings"][0]["filed"] == "2026-08-15" and s["recent_filings"][0]["in_portfolio"] is False
    assert (tmp_path / "app/data/investors13f.json").exists()
