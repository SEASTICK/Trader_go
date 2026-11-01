import numpy as np
import pandas as pd

from traderlab import backtest
from traderlab.costs import ZERO
from traderlab.risk import risk_overlay
from traderlab.strategies import examples
from traderlab.synthetic import from_closes, make_bars


def always_long(b):
    return pd.Series(1.0, index=b.index)


def test_overlay_is_causal():
    bars = make_bars(600, seed=1, vol=0.02)
    backtest.check_no_lookahead(risk_overlay(lambda b: examples.ma_cross(b, 10, 30)), bars)


def test_vol_targeting_shrinks_size_when_market_is_wild():
    calm = make_bars(400, seed=2, vol=0.005)
    wild = make_bars(400, seed=2, vol=0.06)
    s = risk_overlay(always_long, target_vol=0.02, max_drawdown=None, max_daily_loss=None)
    assert s(calm).iloc[-1] == 1.0                 # tak vid 1
    assert 0 < s(wild).iloc[-1] < 0.5              # krymper när volatiliteten är hög


def test_kill_switch_goes_flat_and_stays_flat():
    closes = [100] * 60 + [90, 80, 70, 60] + [61, 62, 63, 64, 65] * 4
    bars = from_closes(closes, interval="1d")
    s = risk_overlay(always_long, target_vol=None, max_drawdown=0.25, max_daily_loss=None)(bars)
    hit = s.index[np.argmax((s == 0).to_numpy() & (np.arange(len(s)) > 0))]
    assert hit == bars.index[62]                   # 100 → 70 är -30 %: platt vid stängningen den dagen
    assert (s.loc[hit:] == 0).all()                # förblir platt


def test_daily_loss_limit_resets_next_day():
    idx_closes = [100, 100, 100, 100, 100, 100, 94, 94, 94, 94, 94, 94, 95, 96, 97, 98, 99, 100]
    bars = from_closes(idx_closes, interval="4h", start="2024-01-01")
    s = risk_overlay(always_long, target_vol=None, max_drawdown=None, max_daily_loss=0.05)(bars)
    day2 = s[s.index.floor("D") == pd.Timestamp("2024-01-02", tz="UTC")]
    assert (day2 == 0).all()                       # dag 2 föll 6 %: låst resten av dagen
    day3 = s[s.index.floor("D") == pd.Timestamp("2024-01-03", tz="UTC")]
    assert (day3 == 1).all()                       # ny dag: tillbaka


def test_overlay_reduces_worst_drawdown():
    bars = make_bars(3000, seed=4, vol=0.02, drift=-0.0005)
    plain = backtest.run(bars, always_long(bars), ZERO)
    guarded = backtest.run(bars, risk_overlay(always_long, target_vol=0.01)(bars), ZERO)
    dd = lambda e: float((e / e.cummax() - 1).min())
    assert dd(guarded.equity) > dd(plain.equity)


def test_registry_build_applies_risk_overlay():
    from traderlab.strategies.registry import build
    bars = make_bars(300, seed=5, vol=0.06)
    plain = build("buy_and_hold")(bars)
    guarded = build("buy_and_hold", risk={"target_vol": 0.02, "max_drawdown": None, "max_daily_loss": None})(bars)
    assert plain.iloc[-1] == 1.0 and guarded.iloc[-1] < 0.5
