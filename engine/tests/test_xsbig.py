import numpy as np
import pandas as pd

from traderlab import portfolio, xsbig


def _panel(n=300, k=40, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2021-01-01", periods=n, freq="1D", tz="UTC")
    closes = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.04, (n, k)), axis=0)), index=idx,
                          columns=[f"C{i}USDT" for i in range(k)])
    dvol = pd.DataFrame(2e7, index=idx, columns=closes.columns)
    dvol.iloc[:, :5] = 1e6   # illikvida: får aldrig väljas
    return closes, dvol


def test_illiquid_coins_are_never_traded_and_deciles_are_neutral():
    closes, dvol = _panel()
    w = xsbig.weights("momentum", closes, dvol, {})
    live = w[(w != 0).any(axis=1)]
    assert len(live) > 20
    assert (live.iloc[:, :5] == 0).all().all()
    assert np.allclose(live.sum(axis=1), 0) and np.allclose(live.abs().sum(axis=1), 1)
    assert ((live > 0).sum(axis=1) == 5).all()   # 35 likvida -> tiondel 3, men minst 5


def test_weights_have_no_lookahead():
    closes, dvol = _panel()
    portfolio.check_no_lookahead(lambda p: xsbig.weights("momentum", p["c"], p["v"], {}), {"c": closes, "v": dvol}, [120, 200, 280])


def test_decile_grows_with_universe():
    idx = pd.date_range("2021-01-03", periods=1, freq="7D", tz="UTC")
    score = pd.DataFrame([np.arange(120.0)], index=idx, columns=[f"S{i}" for i in range(120)])
    elig = pd.DataFrame(True, index=idx, columns=score.columns)
    w = xsbig.decile_long_short(score, elig, long_high=True)
    assert (w.iloc[0] > 0).sum() == 12 and w.iloc[0]["S119"] > 0 and w.iloc[0]["S0"] < 0
