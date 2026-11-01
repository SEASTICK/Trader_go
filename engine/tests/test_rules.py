import numpy as np
import pandas as pd
import pytest

from traderlab import backtest
from traderlab.costs import CostModel
from traderlab.strategies.rules import SPECS, hold
from traderlab.synthetic import from_closes, make_bars

BARS = make_bars(1500, interval="4h", seed=11, vol=0.02)


def test_hold_state_machine():
    s = lambda xs: pd.Series(xs, dtype=bool)
    t = hold(s([0, 1, 0, 0, 0, 0, 0]), s([0, 0, 0, 1, 0, 0, 0]), s([0, 0, 0, 0, 1, 0, 0]), s([0, 0, 0, 0, 0, 0, 1]))
    assert list(t) == [0, 1, 1, 0, -1, -1, 0]
    assert list(hold(s([0, 0]), s([0, 0]), s([1, 1]), s([0, 0]), allow_short=False)) == [0, 0]


@pytest.mark.parametrize("name", list(SPECS))
def test_every_strategy_has_no_lookahead_and_valid_output(name):
    spec = SPECS[name]
    sig = spec.signals(BARS)
    assert set(np.unique(sig.target)) <= {-1.0, 0.0, 1.0}
    assert sig.target.index.equals(BARS.index)
    backtest.check_no_lookahead(lambda b: spec.signals(b).target, BARS)
    backtest.check_no_lookahead(lambda b: spec.signals(b).stop_distance.fillna(-1), BARS)
    res = backtest.run(BARS, sig.target, CostModel(), stop_distance=sig.stop_distance)
    assert np.isfinite(res.equity.iloc[-1])


def test_run_id_is_stable_and_changes_with_params():
    s = SPECS["donchian_breakout"]
    assert s.run_id({}) == s.run_id({"entry_n": 20})
    assert s.run_id({"entry_n": 30}) != s.run_id({})
    assert s.run_id({}).startswith("donchian_breakout@1.0.0#")


def test_invalid_params_rejected():
    with pytest.raises(ValueError):
        SPECS["ema_adx_trend"].signals(BARS, {"fast": 120, "slow": 200})


def test_donchian_goes_long_on_breakout_and_exits_on_breakdown():
    closes = [100] * 25 + [110, 111, 112] + [95] * 5
    b = from_closes(closes, interval="4h")
    t = SPECS["donchian_breakout"].signals(b, {"entry_n": 20, "exit_n": 10, "allow_short": False}).target
    assert t.iloc[24] == 0 and t.iloc[25] == 1 and t.iloc[27] == 1 and t.iloc[28] == 0


def test_bb_rsi_enters_on_oversold_and_exits_at_mid():
    rng = np.random.default_rng(0)
    closes = list(100 + rng.normal(0, 0.3, 60)) + [92, 91, 90] + [100] * 5
    b = from_closes(closes, interval="4h")
    t = SPECS["bb_rsi_reversion"].signals(b, {"allow_short": False}).target
    assert t.iloc[60:63].max() == 1 and t.iloc[-1] == 0
