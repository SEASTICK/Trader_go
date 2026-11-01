import math

import numpy as np
import pandas as pd
import pytest

from traderlab import stats


def test_t_krav_matches_skill_and_app():
    assert stats.t_krav(0) == 2.0
    assert stats.t_krav(1) == 2.0                      # 1,645 < golvet 2,0
    assert stats.t_krav(10) == pytest.approx(2.576, abs=1e-3)
    assert stats.t_krav(17) == pytest.approx(2.75, abs=1e-2)
    assert stats.t_krav(100) == pytest.approx(3.291, abs=1e-3)


def test_t_stat_hand_computed():
    x = [0.01, 0.03, -0.01, 0.02, 0.0]
    m, sd = np.mean(x), np.std(x, ddof=1)
    assert stats.t_stat(x) == pytest.approx(m / (sd / math.sqrt(5)))
    assert stats.t_stat([1.0]) == 0.0
    assert stats.t_stat([0.5, 0.5, 0.5]) == 0.0


def test_newey_west_equals_plain_without_lags_and_shrinks_with_positive_autocorrelation():
    rng = np.random.default_rng(1)
    x = rng.normal(0.001, 0.01, 2000)
    n = x.size
    plain_pop = x.mean() / (x.std(ddof=0) / math.sqrt(n))
    assert stats.newey_west_t(x, lags=0) == pytest.approx(plain_pop)
    # Starkt positivt beroende: Newey-West ska ge lägre t än det naiva.
    e = rng.normal(0, 0.01, 3000)
    y = 0.0005 + np.convolve(e, np.ones(10) / 10, mode="same")
    assert stats.newey_west_t(y) < stats.newey_west_t(y, lags=0)


def test_daily_returns_compound():
    idx = pd.date_range("2024-01-01", periods=12, freq="4h", tz="UTC")
    r = pd.Series(0.01, index=idx)
    d = stats.daily_returns(r)
    assert len(d) == 2
    assert d.iloc[0] == pytest.approx(1.01**6 - 1)


def test_bootstrap_ci_is_deterministic_and_contains_estimate():
    rng = np.random.default_rng(2)
    d = rng.normal(0.001, 0.02, 1000)
    a = stats.block_bootstrap_sharpe_ci(d, seed=5)
    b = stats.block_bootstrap_sharpe_ci(d, seed=5)
    assert a == b
    assert a[0] < stats.sharpe(d) < a[1]


def test_max_drawdown():
    assert stats.max_drawdown([1.0, 1.2, 0.9, 1.3, 1.0]) == pytest.approx(0.9 / 1.2 - 1)


def test_probabilistic_sharpe_basics():
    rng = np.random.default_rng(3)
    x = rng.normal(0, 0.01, 5000)
    assert 0.0 <= stats.probabilistic_sharpe(x) <= 1.0
    good = rng.normal(0.002, 0.01, 2000)
    assert stats.probabilistic_sharpe(good) > 0.99


def test_deflated_sharpe_falls_with_more_trials():
    rng = np.random.default_rng(4)
    x = rng.normal(0.0008, 0.01, 1500)
    d1, d10, d1000 = (stats.deflated_sharpe(x, n) for n in (1, 10, 1000))
    assert d1 > d10 > d1000
    assert d1 == pytest.approx(stats.probabilistic_sharpe(x))


def test_expected_max_sharpe_grows_with_trials():
    v = 1 / 1000
    assert stats.expected_max_sharpe(1, v) == 0.0
    assert stats.expected_max_sharpe(10, v) < stats.expected_max_sharpe(100, v)
