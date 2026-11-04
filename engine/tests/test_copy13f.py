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
