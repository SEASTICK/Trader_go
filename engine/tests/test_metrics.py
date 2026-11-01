import numpy as np
import pandas as pd
import pytest

from traderlab import backtest, metrics
from traderlab.costs import ZERO, CostModel
from traderlab.synthetic import from_closes, make_bars


def test_buy_and_hold_doubling_over_two_years():
    n = 731
    closes = list(100 * 2 ** (np.arange(n + 1) / n))
    b = from_closes(closes, interval="1d")
    res = backtest.run(b, pd.Series(1.0, index=b.index), ZERO)
    s = metrics.full_stats(res, start_capital=100_000)
    # Köp vid öppningen av stapel 1, sista värdet är öppningen av sista stapeln.
    assert s["net_return"] == pytest.approx(b.open.iloc[-1] / b.open.iloc[1] - 1, rel=1e-9)
    assert s["cagr"] == pytest.approx(2 ** (365.25 / 730) - 1, rel=2e-2)
    assert s["max_drawdown"] == 0.0 and s["calmar"] is None
    assert s["end_capital"] == pytest.approx(100_000 * (1 + s["net_return"]), rel=1e-6)


def test_trade_stats_and_profit_factor():
    b = from_closes([100, 100, 110, 110, 110, 100, 100, 100], interval="1d")
    tgt = pd.Series([1, 1, 0, 0, 1, 0, 0, 0], index=b.index, dtype=float)
    res = backtest.run(b, tgt, ZERO)
    s = metrics.full_stats(res)
    assert s["trades"] == 2 and s["win_rate"] == 0.5
    r = [t.net_return for t in res.closed_trades]
    assert s["profit_factor"] == pytest.approx(sum(x for x in r if x > 0) / -sum(x for x in r if x <= 0))
    assert s["expectancy"] == pytest.approx(np.mean([t.net_return for t in res.closed_trades]))


def test_drawdown_curve_and_monthly():
    b = make_bars(800, interval="4h", seed=5, vol=0.02)
    res = backtest.run(b, pd.Series(1.0, index=b.index), CostModel())
    dd = metrics.drawdown_curve(res.equity)
    assert dd.max() <= 0 and dd.min() == pytest.approx(metrics.full_stats(res)["max_drawdown"])
    m = metrics.monthly_returns(res.equity)
    assert np.prod([1 + v for v in m.values()]) == pytest.approx(res.equity.iloc[-1] / res.equity.iloc[0], rel=1e-6)


def test_regimes_use_only_past_data():
    b = make_bars(3000, interval="4h", seed=9, vol=0.02)
    full = metrics.regimes(b)
    part = metrics.regimes(b.iloc[:2000])
    assert full.iloc[:2000].fillna("-").equals(part.fillna("-"))
    s = metrics.full_stats(backtest.run(b, pd.Series(1.0, index=b.index), ZERO), b)
    assert set(s["by_regime"]) <= {"upp/hög vol", "upp/låg vol", "ned/hög vol", "ned/låg vol"}
