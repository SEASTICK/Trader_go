import numpy as np
import pandas as pd
import pytest

from traderlab import copy13f


def opens(cols, n=30):
    idx = pd.bdate_range("2024-01-02", periods=n, tz="UTC")
    return pd.DataFrame({c: np.linspace(100, 100 + i, n) for i, c in enumerate(cols)}, index=idx)


def test_weights_start_on_first_trading_day_after_filing_and_average_managers():
    o = opens(["AAA", "BBB", "CCC"])
    sat = pd.Timestamp("2024-01-06", tz="UTC")   # lördag
    events = {1: [(sat, {"c1": 0.75, "c2": 0.25})], 2: [(pd.Timestamp("2024-01-10", tz="UTC"), {"c3": 1.0})]}
    tick = {"c1": "AAA", "c2": "BBB", "c3": "CCC"}
    w, log = copy13f.build_weights(events, tick, o)
    assert w.index[0] == pd.Timestamp("2024-01-08", tz="UTC")   # första handelsdag efter lördagen
    assert w.iloc[0].to_dict() == pytest.approx({"AAA": 0.75, "BBB": 0.25, "CCC": 0.0})
    assert w.iloc[1].to_dict() == pytest.approx({"AAA": 0.375, "BBB": 0.125, "CCC": 0.5})
    assert len(log) == 2


def test_unpriced_holdings_are_dropped_and_reweighted():
    o = opens(["AAA", "BBB"])
    o.loc[:, "BBB"] = np.nan
    events = {1: [(pd.Timestamp("2024-01-03", tz="UTC"), {"c1": 0.6, "c2": 0.3, "cx": 0.1})]}
    w, log = copy13f.build_weights(events, {"c1": "AAA", "c2": "BBB", "cx": None}, o)
    assert w.iloc[0]["AAA"] == pytest.approx(1.0)
    assert log[0]["unpriced_share"] == pytest.approx(0.4)


def test_stale_manager_drops_out():
    o = opens(["AAA", "BBB"], n=300)
    events = {1: [(o.index[0], {"c1": 1.0})], 2: [(o.index[250], {"c2": 1.0})]}
    w, _ = copy13f.build_weights(events, {"c1": "AAA", "c2": "BBB"}, o)
    assert w.iloc[-1]["AAA"] == 0 and w.iloc[-1]["BBB"] == 1


def test_two_filings_same_day_last_one_wins():
    """Körfel på riktiga data: två redovisningar samma dag från samma förvaltare kraschade sorteringen."""
    o = opens(["AAA", "BBB"])
    d = pd.Timestamp("2024-01-03", tz="UTC")
    events = {1: [(d, {"c1": 1.0}), (d, {"c2": 1.0})]}
    w, _ = copy13f.build_weights(events, {"c1": "AAA", "c2": "BBB"}, o)
    assert w.iloc[-1]["BBB"] == 1 and w.iloc[-1]["AAA"] == 0


def test_manager_events_put_latest_period_last(monkeypatch):
    from traderlab.data import sec13f
    fs = [sec13f.Filing(1, "b", "2015-02-14", "2014-12-31"), sec13f.Filing(1, "a", "2015-02-14", "2014-09-30")]
    monkeypatch.setattr(sec13f, "list_filings", lambda cik, d, opener=None, refresh=False: fs)
    monkeypatch.setattr(sec13f, "holdings", lambda f, d, opener=None: {f.accession: {"name": "X", "value": 1.0, "shares": 1}})
    ev = copy13f.manager_events(1, None)
    assert [list(w) for _, w in ev] == [["a"], ["b"]]
