import numpy as np
import pandas as pd
import pytest

from traderlab import backtest
from traderlab.costs import ZERO
from traderlab.ml import cv, features, labels, walkforward
from traderlab.synthetic import from_closes, make_ar_bars, make_bars


def test_every_feature_uses_only_the_past():
    bars = make_bars(400, seed=1)
    for col in features.build_features(bars).columns:
        backtest.check_no_lookahead(lambda b, c=col: features.build_features(b)[c], bars)


def test_label_matches_a_real_trade():
    bars = from_closes([100, 110, 121, 100, 90])  # open = föregående close
    r = labels.forward_return(bars, horizon=1)
    # Beslut vid stängning av stapel 0 → in vid open[1]=100, ut vid open[2]=110.
    assert r.iloc[0] == pytest.approx(0.10)
    assert r.iloc[1] == pytest.approx(0.10)  # open[2]=110 → open[3]=121
    assert np.isnan(r.iloc[-1]) and np.isnan(r.iloc[-2])
    end = labels.label_end(bars, horizon=2)
    assert end.iloc[0] == bars.index[2] and pd.isna(end.iloc[-1])


def test_purged_kfold_never_trains_on_overlapping_labels():
    bars = make_bars(300, seed=2)
    end = labels.label_end(bars, horizon=5)
    t0 = bars.index.to_numpy()
    t1 = end.fillna(bars.index[-1]).to_numpy()
    seen = []
    for train, test in cv.PurgedKFold(5, embargo=0.02).split(end):
        seen.extend(test)
        lo, hi = t0[test[0]], t1[test].max()
        assert not ((t0[train] <= hi) & (t1[train] >= lo)).any()
        after = np.arange(test[-1] + 1, min(len(t0), test[-1] + 1 + 6))
        assert not np.intersect1d(train, after).size  # embargo
    assert sorted(seen) == list(range(len(t0)))


def test_walk_forward_is_causal():
    bars = make_ar_bars(700, seed=3)
    strat = walkforward.ml_strategy(min_train=300, step=60)
    backtest.check_no_lookahead(strat, bars, cutoffs=3)


def test_no_prediction_before_enough_history():
    bars = make_bars(600, seed=4)
    p = walkforward.walk_forward_proba(bars, min_train=400, step=100)
    assert p.iloc[:400].isna().all() and p.iloc[400:].notna().any()


def test_finds_a_signal_that_exists():
    bars = make_ar_bars(4000, phi=0.2, vol=0.01, seed=5)
    p = walkforward.walk_forward_proba(bars, min_train=1000, step=250)
    y = labels.direction(bars)
    m = p.notna() & y.notna()
    acc = ((p[m] > 0.5) == (y[m] == 1)).mean()
    assert acc > 0.55
    res = backtest.run(bars, walkforward.ml_strategy(min_train=1000, step=250, band=0.0)(bars), ZERO)
    assert res.equity.iloc[-1] > 1.2


def test_finds_nothing_in_pure_noise():
    accs = []
    for seed in range(4):
        bars = make_bars(3000, seed=10 + seed, vol=0.01)
        p = walkforward.walk_forward_proba(bars, min_train=1000, step=250)
        y = labels.direction(bars)
        m = p.notna() & y.notna()
        accs.append(((p[m] > 0.5) == (y[m] == 1)).mean())
    assert abs(np.mean(accs) - 0.5) < 0.02


def test_gbm_model_runs_and_is_deterministic():
    bars = make_ar_bars(900, seed=6)
    a = walkforward.walk_forward_proba(bars, model="gbm", min_train=500, step=200)
    b = walkforward.walk_forward_proba(bars, model="gbm", min_train=500, step=200)
    pd.testing.assert_series_equal(a, b)
