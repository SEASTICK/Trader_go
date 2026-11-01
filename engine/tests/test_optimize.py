import numpy as np
import pandas as pd
import pytest

from traderlab import optimize
from traderlab.costs import CostModel
from traderlab.strategies.rules import SPECS
from traderlab.synthetic import make_ar_bars

BARS = make_ar_bars(4000, phi=0.1, vol=0.01, seed=2, interval="4h", start="2020-01-01")


def test_evaluate_only_trades_inside_window():
    spec = SPECS["donchian_breakout"]
    a, b = BARS.index[2000], BARS.index[3000]
    res = optimize.evaluate(spec, {}, BARS, a, b, CostModel())
    assert all(t.entry_time >= a for t in res.trades)
    assert res.equity.index[-1] < b


def test_window_result_does_not_depend_on_data_after_window():
    spec = SPECS["ema_adx_trend"]
    a, b = BARS.index[2000], BARS.index[3000]
    changed = BARS.copy()
    changed.iloc[3000:, :4] *= 2.0
    r1 = optimize.evaluate(spec, {}, BARS, a, b, CostModel()).equity
    r2 = optimize.evaluate(spec, {}, changed, a, b, CostModel()).equity
    assert r1.equals(r2)


def test_walk_forward_is_reproducible_and_out_of_sample():
    spec = SPECS["donchian_breakout"]
    kw = dict(dev_start="2020-01-01", test_starts=["2021-03-01", "2021-07-01"], dev_end="2021-10-01",
              costs=CostModel(), n_trials=5, seed=1)
    w1 = optimize.walk_forward(spec, BARS, **kw)
    w2 = optimize.walk_forward(spec, BARS, **kw)
    assert w1.final_params == w2.final_params and w1.oos_returns.equals(w2.oos_returns)
    assert w1.oos_returns.index[0] >= pd.Timestamp("2021-03-01", tz="UTC")
    assert w1.oos_returns.index[-1] < pd.Timestamp("2021-10-01", tz="UTC")
    for w in w1.windows:
        assert w["train"][1] == w["test"][0]
    assert 0 <= w1.stability <= 1 and w1.trials == 15
