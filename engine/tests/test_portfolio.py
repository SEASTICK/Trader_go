import numpy as np
import pandas as pd
import pytest

from traderlab import portfolio, xs
from traderlab.costs import ZERO, CostModel


def opens_frame(data, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(next(iter(data.values()))), freq="1D", tz="UTC")
    return pd.DataFrame(data, index=idx, dtype=float)


def test_long_short_pnl_and_next_open_fill():
    o = opens_frame({"A": [100, 100, 110, 110], "B": [100, 100, 90, 90]})
    w = pd.DataFrame({"A": [0.5], "B": [-0.5]}, index=o.index[:1])
    res = portfolio.run(o, w, ZERO)
    # Beslut dag 0, fyllt dag 1, rörelse dag 1→2: +10 % på A (0,5) och −10 % på B (short 0,5) = +10 %.
    assert res.equity.iloc[0] == 1.0
    assert res.equity.iloc[1] == pytest.approx(1.10)


def test_costs_on_turnover_and_holding_between_rebalances():
    o = opens_frame({"A": [100] * 6, "B": [100] * 6})
    w = pd.DataFrame({"A": [0.5, -0.5], "B": [-0.5, 0.5]}, index=[o.index[0], o.index[2]])
    res = portfolio.run(o, w, CostModel(10, 0, 0))
    assert res.turnover.iloc[1] == pytest.approx(1.0)       # öppna 0,5 + 0,5
    assert res.turnover.iloc[3] == pytest.approx(2.0, rel=1e-3)  # vända båda: 1,0 + 1,0
    # Storleken räknas på kapitalet efter förra avgiften: vändningen omsätter 2 × (0,5 + 0,4995).
    assert res.total_costs == pytest.approx(0.001 * 1.0 + 0.001 * 2 * (0.5 + 0.5 * 0.999), rel=1e-9)


def test_funding_short_receives():
    o = opens_frame({"A": [100] * 4, "B": [100] * 4})
    w = pd.DataFrame({"A": [-0.5], "B": [0.5]}, index=o.index[:1])
    f = {"A": pd.Series([0.001], index=[o.index[1] + pd.Timedelta(hours=8)])}
    res = portfolio.run(o, w, ZERO, f)
    assert res.total_funding == pytest.approx(-0.0005)
    assert res.equity.iloc[-1] == pytest.approx(1.0005)


def test_delisted_asset_is_closed():
    o = opens_frame({"A": [100, 100, 100, np.nan, np.nan], "B": [100] * 5})
    w = pd.DataFrame({"A": [0.5], "B": [-0.5]}, index=o.index[:1])
    res = portfolio.run(o, w, CostModel(10, 0, 0))
    assert res.weights["A"].iloc[3] == 0.0 and np.isfinite(res.equity.iloc[-1])


def _panel(n=400, k=14, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="1D", tz="UTC")
    closes = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.03, (n, k)), axis=0)), index=idx,
                          columns=[f"C{i}" for i in range(k)])
    closes.iloc[:150, 0] = np.nan   # listas sent
    return closes


def test_momentum_weights_are_dollar_neutral_and_weekly():
    w = xs.momentum_weights(_panel())
    assert (w.index.dayofweek == 6).all()
    live = w[(w != 0).any(axis=1)]
    assert len(live) > 30
    assert np.allclose(live.sum(axis=1), 0) and np.allclose(live.abs().sum(axis=1), 1)
    assert (live.iloc[:, 0][live.index < pd.Timestamp("2020-07-29", tz="UTC")] == 0).all()  # för kort historik


def test_signals_have_no_lookahead():
    closes = _panel()
    funding = {c: pd.Series(np.sin(np.arange(1200) + i) * 1e-4,
                            index=pd.date_range("2020-01-01", periods=1200, freq="8h", tz="UTC")) for i, c in enumerate(closes)}
    portfolio.check_no_lookahead(lambda p: xs.momentum_weights(p["c"]), {"c": closes}, [200, 300, 390])
    portfolio.check_no_lookahead(lambda p: xs.carry_weights(p["c"], {k: v for k, v in p.items() if k != "c"}),
                                 {"c": closes, **funding}, [200, 300, 390],
                                 known_until={k: pd.Timedelta(days=1) for k in funding})


def test_carry_shorts_highest_funding():
    closes = _panel(200, 12)
    f = {c: pd.Series(1e-4 * i, index=pd.date_range("2020-01-01", periods=600, freq="8h", tz="UTC")) for i, c in enumerate(closes)}
    w = xs.carry_weights(closes, f)
    last = w[(w != 0).any(axis=1)].iloc[-1]
    assert last["C11"] < 0 and last["C1"] > 0


def test_bankruptcy_is_absorbing():
    """Granskningsfynd (Edwin): short −1 och priset fyrdubblas ska ge konkurs, inte återuppståndelse."""
    idx = pd.date_range("2024-01-01", periods=5, freq="1D", tz="UTC")
    opens = pd.DataFrame({"X": [100.0, 100.0, 400.0, 100.0, 100.0]}, index=idx)
    w = pd.DataFrame({"X": [-1.0, np.nan, np.nan, np.nan, np.nan]}, index=idx)
    res = portfolio.run(opens, w, CostModel(0, 0, 0))
    assert (res.equity >= 0).all()
    assert res.equity.iloc[-1] == 0.0


def test_funding_gaps_counts_held_days_without_settlement():
    idx = pd.date_range("2024-01-01", periods=4, freq="1D", tz="UTC")
    held = pd.DataFrame({"A": [0.5, 0.5, 0.0, 0.5], "B": [0.0, 0.0, 0.0, 0.0]}, index=idx)
    fund = {"A": pd.Series([0.0001, 0.0001], index=[idx[0] + pd.Timedelta(hours=8), idx[3] + pd.Timedelta(hours=16)])}
    assert portfolio.funding_gaps(held, fund) == {"A": 1}
    assert portfolio.funding_gaps(held, {}) == {"A": 3}
