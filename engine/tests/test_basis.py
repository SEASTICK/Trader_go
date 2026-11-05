import numpy as np
import pandas as pd

from traderlab import basis
from traderlab.costs import CostModel


def _market(prices, premium_per_day=0.0005, start="2021-01-01", n=200, expiries=("210401", "210701", "211001")):
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    s = pd.Series(prices[:n] if prices is not None else np.full(n, 100.0), index=idx)
    spot = pd.DataFrame({"open": s, "high": s, "low": s, "close": s})
    futs = {}
    for e in expiries:
        sym = f"BTCUSDT_{e}"
        left = np.array([basis.days_left(sym, t) for t in idx], dtype=float)
        keep = left >= 0
        f = s[keep] * (1 + premium_per_day * left[keep])
        futs[sym] = pd.DataFrame({"open": f, "high": f, "low": f, "close": f})
    return spot, futs


def test_expiry_and_active_contract():
    spot, futs = _market(None)
    assert basis.expiry_of("BTCUSDT_210326") == pd.Timestamp("2021-03-26", tz="UTC")
    assert basis.active(futs, pd.Timestamp("2021-01-10", tz="UTC")) == "BTCUSDT_210401"
    # 14 dagar kvar: nästa kontrakt är aktivt
    assert basis.active(futs, pd.Timestamp("2021-03-18", tz="UTC")) == "BTCUSDT_210701"


def test_converging_premium_earns_about_two_thirds_of_the_basis():
    spot, futs = _market(None)   # 0,05 % per dag = 18 % per år, över tröskeln
    leg = basis.simulate(spot, futs, CostModel(0, 0, 0), capital=1.0)
    assert leg.trades >= 2 and leg.min_cash >= 0
    days_short = leg.days_hedged
    assert np.isclose(leg.equity.iloc[-1] - 1, basis.SPOT_SHARE * 0.0005 * days_short, rtol=0.05)


def test_hedge_is_market_neutral_and_never_borrows():
    rng = np.random.default_rng(1)
    prices = 100 * np.exp(np.cumsum(rng.normal(0.004, 0.03, 200)))   # stark uppgång
    spot, futs = _market(prices)
    leg = basis.simulate(spot, futs, CostModel(10, 2, 5), capital=1.0)
    assert leg.min_cash >= 0
    r = leg.equity.pct_change().dropna()
    m = spot["close"].pct_change().reindex(r.index)
    assert abs(r.cov(m) / m.var()) < 0.05


def test_no_lookahead():
    spot, futs = _market(None)
    full = basis.simulate(spot, futs, CostModel(10, 2, 5), capital=1.0).equity
    cut = pd.Timestamp("2021-05-01", tz="UTC")
    spot2 = spot.copy()
    spot2.loc[spot2.index > cut, ["open", "high", "low", "close"]] *= 3   # framtiden ändras
    futs2 = {k: v.copy() for k, v in futs.items()}
    for v in futs2.values():
        v.loc[v.index > cut] *= 0.5
    part = basis.simulate(spot2, futs2, CostModel(10, 2, 5), capital=1.0).equity
    assert np.allclose(full.loc[:cut], part.loc[:cut])
