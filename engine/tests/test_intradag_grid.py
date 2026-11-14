"""H-0030: gridet är exakt det i protokollet, och kontrollvarianterna återger H-0027–H-0029 (syntetiska staplar)."""
import numpy as np
import pandas as pd
import pytest

from traderlab import backtest, intradag
from traderlab.costs import ZERO
from traderlab.intradag_grid import early_late, opening_range, variants

from test_intradag import _bars, _ny_day, _with_shock


def test_grid_has_50_variants_with_fixed_ids_and_three_controls():
    vs = variants()
    assert len(vs) == 50 and len({v.id for v in vs}) == 50
    assert sum(v.family == "R" for v in vs) == 27
    assert sum(v.family == "O" for v in vs) == 14
    assert sum(v.family == "M" for v in vs) == 9
    assert vs[0].id == "H-0030-R01" and vs[0].interval == "5m" and vs[0].params == {"k": 2.5, "hold_hours": 1}
    ctrl = {v.control_of: v.id for v in vs if v.control_of}
    assert ctrl == {"H-0027": "H-0030-R23", "H-0028": "H-0030-O10", "H-0029": "H-0030-M05"}


def _random_walk(freq, periods, seed):
    b = _bars("2021-01-01", periods, freq, seed=seed)
    c = b["close"].to_numpy() * np.exp(np.cumsum(np.random.default_rng(seed + 1).normal(0, 0.004, periods)))
    return _bars("2021-01-01", periods, freq, closes=c)


@pytest.mark.parametrize("hid", ["H-0027", "H-0028", "H-0029"])
def test_controls_reproduce_original_targets(hid):
    itv, fn = intradag.STRATEGIES[hid]
    v = next(v for v in variants() if v.control_of == hid)
    freq = "15min" if itv == "15m" else "1h"
    b = _random_walk(freq, 6000, 5)
    assert fn(b).equals(v.fn(b))
    b = _with_shock("2021-01-31 10:00", -0.05) if hid == "H-0027" else b
    assert fn(b).equals(v.fn(b))


def test_opening_range_5m_30min_exit_13():
    b = _ny_day("2023-01-10", {})
    start = b.index[0]
    b5 = _bars(start, 288, "5min", closes=np.full(288, 100.0))
    local = b5.index.tz_convert(intradag.NY).strftime("%H:%M")
    c = b5["close"].to_numpy().copy()
    c[np.flatnonzero(local == "10:05")[0]:] = 101.0
    b5 = _bars(start, 288, "5min", closes=c)
    res = backtest.run(b5, opening_range(b5, interval="5m", range_minutes=30, exit_hour=13), ZERO)
    tr = res.closed_trades[0]
    assert tr.entry_time == pd.Timestamp("2023-01-10 15:10", tz="UTC")   # 10:10 EST
    assert tr.exit_time == pd.Timestamp("2023-01-10 18:00", tz="UTC")    # 13:00 EST


def test_opening_range_1h_uses_10_to_11_and_enters_12():
    b = _ny_day("2023-07-11", {"11:00": 101.0})   # 15m-dag; bygg 1h-staplar ur den
    h = b.resample("1h").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    res = backtest.run(h, opening_range(h, interval="1h", range_minutes=60, exit_hour=16), ZERO)
    tr = res.closed_trades[0]
    assert tr.entry_time == pd.Timestamp("2023-07-11 16:00", tz="UTC")   # 12:00 EDT
    assert tr.exit_time == pd.Timestamp("2023-07-11 20:00", tz="UTC")


def test_early_late_12h_window_enters_at_noon():
    c = np.full(48, 100.0)
    c[8:] = 101.0
    b = _bars("2022-03-01", 48, "1h", closes=c)
    res = backtest.run(b, early_late(b, window_hours=12, entry_hour=12), ZERO)
    tr = res.closed_trades[0]
    assert tr.entry_time == pd.Timestamp("2022-03-01 12:00", tz="UTC")
    assert tr.exit_time == pd.Timestamp("2022-03-02 00:00", tz="UTC")


@pytest.mark.parametrize("vid", ["H-0030-R01", "H-0030-R14", "H-0030-O01", "H-0030-O13", "H-0030-M07"])
def test_variants_do_not_look_ahead(vid):
    v = next(v for v in variants() if v.id == vid)
    freq = {"5m": "5min", "15m": "15min", "1h": "1h"}[v.interval]
    n = {"5m": 12000, "15m": 6000, "1h": 3000}[v.interval]
    backtest.check_no_lookahead(v.fn, _random_walk(freq, n, 9), cutoffs=10)
