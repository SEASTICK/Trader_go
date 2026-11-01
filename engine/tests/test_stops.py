import numpy as np
import pandas as pd
import pytest

from traderlab import backtest
from traderlab.costs import ZERO, CostModel
from traderlab.synthetic import from_closes


def bars_with(opens, highs, lows, closes):
    idx = pd.date_range("2024-01-01", periods=len(opens), freq="4h", tz="UTC")
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1.0}, index=idx)


def test_long_stop_exits_at_stop_level():
    b = bars_with([100, 100, 100, 100, 100], [101, 101, 101, 101, 101], [99, 99, 94, 99, 99], [100, 100, 100, 100, 100])
    tgt = pd.Series(1.0, index=b.index)
    res = backtest.run(b, tgt, ZERO, stop_distance=pd.Series(5.0, index=b.index))
    t = res.trades[0]
    assert t.stop_price == 95 and t.exit_reason == "stop" and t.exit_price == 95
    assert t.exit_time == b.index[2]
    assert res.equity.iloc[-1] == pytest.approx(0.95)
    assert len(res.trades) == 1          # ingen ny long trots att signalen fortfarande är long


def test_gap_through_stop_fills_at_open():
    b = bars_with([100, 100, 90, 90, 90], [101, 101, 91, 91, 91], [99, 99, 89, 89, 89], [100, 100, 90, 90, 90])
    res = backtest.run(b, pd.Series(1.0, index=b.index), ZERO, stop_distance=pd.Series(5.0, index=b.index))
    assert res.trades[0].exit_price == 90


def test_short_take_profit_and_costs():
    b = bars_with([100, 100, 100, 100, 100], [101, 101, 101, 101, 101], [99, 99, 89, 99, 99], [100] * 5)
    c = CostModel(10, 0, 0)
    res = backtest.run(b, pd.Series(-1.0, index=b.index), c, take_profit_distance=pd.Series(10.0, index=b.index))
    t = res.trades[0]
    assert t.exit_reason == "take_profit" and t.exit_price == 90
    # Storleken räknas på kapitalet före inträdesavgiften (som i resten av motorn): qty = 1/100.
    qty = 1 / 100
    assert res.equity.iloc[-1] == pytest.approx(1 - 0.001 + qty * 10 - qty * 90 * 0.001)


def test_both_hit_same_bar_counts_stop_first():
    b = bars_with([100, 100, 100, 100], [101, 101, 111, 101], [99, 99, 94, 99], [100] * 4)
    res = backtest.run(b, pd.Series(1.0, index=b.index), ZERO, stop_distance=pd.Series(5.0, index=b.index),
                       take_profit_distance=pd.Series(10.0, index=b.index))
    assert res.trades[0].exit_reason == "stop"


def test_new_signal_after_flat_reenters():
    b = from_closes([100] * 8, interval="4h")
    b.loc[b.index[2], "low"] = 90
    tgt = pd.Series([1, 1, 1, 0, 1, 1, 1, 1], index=b.index, dtype=float)
    res = backtest.run(b, tgt, ZERO, stop_distance=pd.Series(5.0, index=b.index))
    assert [t.exit_reason for t in res.trades][:1] == ["stop"]
    assert len(res.trades) == 2 and res.trades[1].entry_time == b.index[5]


def test_no_stops_means_unchanged_behaviour():
    from traderlab.synthetic import make_bars
    b = make_bars(500, seed=3)
    tgt = pd.Series(np.sign(np.sin(np.arange(500) / 7)), index=b.index)
    a = backtest.run(b, tgt, CostModel())
    c = backtest.run(b, tgt, CostModel(), stop_distance=pd.Series(np.nan, index=b.index))
    assert a.equity.equals(c.equity)
