import numpy as np
import pandas as pd
import pytest

from traderlab import backtest
from traderlab.costs import ZERO, CostModel
from traderlab.strategies import examples
from traderlab.synthetic import from_closes, make_bars


def const(bars, value):
    return pd.Series(value, index=bars.index, dtype=float)


def test_decision_at_close_fills_next_open():
    # Signal vid stängningen av stapel 0 → position från öppningen av stapel 1.
    bars = from_closes([100, 110, 121, 133.1])
    target = pd.Series([1.0, 1.0, 1.0, 1.0], index=bars.index)
    res = backtest.run(bars, target, ZERO)
    assert res.position.iloc[0] == 0.0
    assert res.position.iloc[1] == 1.0
    t = res.trades[0]
    assert t.entry_time == bars.index[1]
    assert t.entry_price == 100.0  # open för stapel 1 = close för stapel 0
    # Håller från open[1]=100 till open[3]=121: +21 %
    assert res.equity.iloc[-1] == pytest.approx(1.21)


def test_cannot_trade_on_the_bar_that_made_the_signal():
    # Ett hopp i stapel 2. En signal som först syns i stängningen av stapel 2 får inte tjäna på hoppet.
    bars = from_closes([100, 100, 150, 150, 150])
    target = pd.Series([0, 0, 1, 1, 1], index=bars.index, dtype=float)
    res = backtest.run(bars, target, ZERO)
    assert res.equity.iloc[-1] == pytest.approx(1.0)


def test_short_profits_when_price_falls():
    bars = from_closes([100, 100, 90, 81, 81])
    res = backtest.run(bars, const(bars, -1.0), ZERO)
    # Short från open[1]=100 till open[4]=81: +19 %
    assert res.equity.iloc[-1] == pytest.approx(1.19)
    assert res.trades[0].side == "Short"


def test_costs_charged_on_both_sides_exactly():
    bars = from_closes([100] * 10)
    costs = CostModel(fee_bps=10, spread_bps=0, slippage_bps=0)  # 0,1 % per sida
    target = pd.Series([1, 0] * 5, index=bars.index, dtype=float)
    res = backtest.run(bars, target, costs)
    closed = res.closed_trades
    assert len(closed) == 4
    # Fyra affärer, var och en kostar 0,1 % in och 0,1 % ut, priset står still.
    assert res.equity.iloc[-1] == pytest.approx((1 - 0.001) ** 8, rel=1e-4)
    assert res.total_costs == pytest.approx(1 - res.equity.iloc[-1], rel=1e-9)


def test_stressed_costs_are_higher():
    c = CostModel(10, 2, 5)
    assert c.stressed().per_side == pytest.approx(c.per_side * 2.5)


def test_trade_returns_compound_to_equity():
    bars = make_bars(800, seed=3, vol=0.02)
    target = examples.ma_cross(bars, 10, 30)
    res = backtest.run(bars, target, CostModel())
    eq = 1.0
    for t in res.trades:
        eq += t.net_pnl
    assert eq == pytest.approx(res.equity.iloc[-1], rel=1e-9)


def test_funding_paid_by_long_received_by_short():
    bars = from_closes([100] * 6, interval="4h")
    funding = pd.Series([0.001], index=[bars.index[2] + pd.Timedelta(hours=1)])
    long_ = backtest.run(bars, const(bars, 1.0), ZERO, funding=funding)
    short = backtest.run(bars, const(bars, -1.0), ZERO, funding=funding)
    assert long_.equity.iloc[-1] == pytest.approx(1 - 0.001)
    assert short.equity.iloc[-1] == pytest.approx(1 + 0.001)


def test_liquidation_from_bar_high_isolated_margin():
    bars = from_closes([100, 100, 100, 100, 100, 100])
    bars.iloc[3, bars.columns.get_loc("high")] = 125  # spik uppåt mot en short med 5x
    res = backtest.run(bars, const(bars, -0.5), ZERO, leverage=5, maintenance_margin=0.005)
    assert res.liquidations == 1
    t = res.trades[0]
    assert t.liquidated
    # Hela marginalen (50 % av kapitalet) går förlorad, inte mer.
    assert res.equity.iloc[-1] == pytest.approx(0.5)
    # Ingen ny position förrän signalen ändras.
    assert (res.position.iloc[4:] == 0).all()


def test_no_liquidation_for_unlevered_long_on_normal_moves():
    bars = make_bars(1000, seed=4, vol=0.02)
    res = backtest.run(bars, const(bars, 1.0), ZERO)
    assert res.liquidations == 0


def test_lookahead_detected_and_honest_strategies_pass():
    bars = make_bars(600, seed=5)
    with pytest.raises(backtest.LookaheadError):
        backtest.check_no_lookahead(examples.peeking, bars)
    backtest.check_no_lookahead(examples.ma_cross, bars)
    backtest.check_no_lookahead(examples.zscore_reversion, bars)


def test_peeking_strategy_looks_absurdly_good_so_lookahead_check_is_required():
    # Fyllning vid nästa öppning skyddar INTE mot en signal som redan använder framtida data:
    # fusket ser ut att göra kapitalet tusenfalt. Bara check_no_lookahead stoppar det.
    bars = make_bars(1000, seed=6, vol=0.01)
    res = backtest.run(bars, examples.peeking(bars), ZERO)
    assert res.equity.iloc[-1] > 100
    with pytest.raises(backtest.LookaheadError):
        backtest.check_no_lookahead(examples.peeking, bars)


def test_random_labels_have_no_edge_before_costs():
    from traderlab.experiment import random_label_control
    ts = [random_label_control(make_bars(3000, seed=s, vol=0.01), seed=s) for s in range(8)]
    assert np.mean(np.abs(ts)) < 1.5


def test_resizing_in_same_direction_only_pays_for_the_traded_difference():
    bars = from_closes([100] * 50)
    target = pd.Series([0.5 + 0.02 * ((i % 3) - 1) for i in range(50)], index=bars.index)
    res = backtest.run(bars, target, CostModel(fee_bps=10, spread_bps=0, slippage_bps=0))
    held = target.shift(1).fillna(0.0).iloc[:-1]
    traded = held.diff().abs().fillna(held.abs()).sum()
    assert res.total_costs == pytest.approx(traded * 0.001, rel=0.02)
    assert len(res.trades) == 1  # en affär som ändrar storlek, inte 48 affärer


def test_flip_still_pays_close_and_open():
    bars = from_closes([100] * 6)
    target = pd.Series([1, -1, -1, -1, -1, -1], index=bars.index, dtype=float)
    res = backtest.run(bars, target, CostModel(fee_bps=10, spread_bps=0, slippage_bps=0))
    assert res.total_costs == pytest.approx(0.001 + 0.002 * (1 - 0.001), rel=1e-3)  # in, sedan ut + in vid vändning
