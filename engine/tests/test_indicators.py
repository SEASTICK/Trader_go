"""Indikatorer jämförs mot biblioteket `ta` (referens) på slumpdata, efter uppvärmningen."""
import numpy as np
import pandas as pd
import pytest

ta = pytest.importorskip("ta")

from traderlab import indicators as ind
from traderlab.synthetic import make_bars

BARS = make_bars(1500, interval="4h", seed=7, vol=0.02)
WARM = 300  # Wilder-medel och EMA glömmer sin start efter några hundra staplar


def close_enough(a: pd.Series, b: pd.Series, tol=1e-6):
    a, b = a.iloc[WARM:], b.iloc[WARM:]
    assert np.allclose(a.to_numpy(), b.to_numpy(), rtol=tol, atol=tol), (a - b).abs().max()


def test_ema_sma():
    close_enough(ind.ema(BARS.close, 50), ta.trend.EMAIndicator(BARS.close, 50).ema_indicator())
    close_enough(ind.sma(BARS.close, 20), ta.trend.SMAIndicator(BARS.close, 20).sma_indicator())


def test_rsi():
    close_enough(ind.rsi(BARS.close, 14), ta.momentum.RSIIndicator(BARS.close, 14).rsi(), tol=1e-4)


def test_atr():
    close_enough(ind.atr(BARS, 14), ta.volatility.AverageTrueRange(BARS.high, BARS.low, BARS.close, 14).average_true_range(), tol=1e-4)


def test_adx():
    close_enough(ind.adx(BARS, 14), ta.trend.ADXIndicator(BARS.high, BARS.low, BARS.close, 14).adx(), tol=1e-2)


def test_bollinger():
    lo, mid, hi = ind.bollinger(BARS.close, 20, 2.0)
    bb = ta.volatility.BollingerBands(BARS.close, 20, 2)
    close_enough(lo, bb.bollinger_lband()); close_enough(hi, bb.bollinger_hband())


def test_donchian_excludes_current_bar():
    hi, lo = ind.donchian(BARS, 20)
    assert hi.iloc[100] == BARS.high.iloc[80:100].max()
    assert lo.iloc[100] == BARS.low.iloc[80:100].min()


def test_no_future_data():
    """Att ändra framtida staplar får inte ändra ett tidigare indikatorvärde."""
    cut = 900
    changed = BARS.copy()
    changed.iloc[cut:, :4] *= 1.5
    for f in (lambda b: ind.ema(b.close, 50), lambda b: ind.rsi(b.close), lambda b: ind.atr(b), lambda b: ind.adx(b),
              lambda b: ind.bollinger(b.close)[0], lambda b: ind.donchian(b, 20)[0], lambda b: ind.keltner(b)[2]):
        a, b = f(BARS).iloc[:cut], f(changed).iloc[:cut]
        assert np.allclose(a.fillna(0).to_numpy(), b.fillna(0).to_numpy())
