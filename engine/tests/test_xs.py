import numpy as np
import pandas as pd

from traderlab import xs


def test_funding_score_ties_do_not_depend_on_history_length():
    idx = pd.date_range("2024-01-01", periods=20, freq="1D", tz="UTC")
    long_hist = pd.Series(np.r_[np.full(3000, 0.000137), np.full(60, 0.0001)],
                          index=pd.date_range(end=idx[-1], periods=3060, freq="8h", tz="UTC"))
    short_hist = long_hist[long_hist.index >= idx[0] - pd.Timedelta(days=10)]
    a = xs.funding_score(idx, {"A": long_hist, "B": short_hist})
    assert (a["A"].iloc[-5:] == a["B"].iloc[-5:]).all()
