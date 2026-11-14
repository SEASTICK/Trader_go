"""H-0027–H-0029 (research/intradag-protokoll.md): tidsregler på syntetiska staplar, ingen riktig data."""
import numpy as np
import pandas as pd
import pytest

from traderlab import backtest, intradag
from traderlab.costs import ZERO


def _bars(start, periods, freq, closes=None, seed=0):
    idx = pd.date_range(start, periods=periods, freq=freq, tz="UTC")
    if closes is None:
        rng = np.random.default_rng(seed)
        closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, periods)))
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    return pd.DataFrame({"open": opens, "high": np.maximum(opens, closes) * 1.0005,
                         "low": np.minimum(opens, closes) * 0.9995, "close": closes, "volume": 1.0}, index=idx)


# ---------- H-0027 ----------

def _with_shock(day_hour: str, move: float, periods=800):
    b = _bars("2021-01-01", periods, "1h")
    t = pd.Timestamp(day_hour, tz="UTC")
    i = b.index.get_loc(t)
    c = b["close"].to_numpy().copy()
    c[i:] *= 1 + move
    return _bars("2021-01-01", periods, "1h", closes=c)


def test_h0027_trades_against_first_extreme_hour_for_three_hours():
    b = _with_shock("2021-01-31 10:00", -0.05)
    tgt = intradag.extreme_hour_reversal(b)
    on = tgt[tgt != 0]
    assert list(on.index.hour) == [10, 11, 12] and (on == 1.0).all()   # mot en nedgång = long
    res = backtest.run(b, tgt, ZERO)
    tr = res.closed_trades[0]
    assert tr.entry_time == pd.Timestamp("2021-01-31 11:00", tz="UTC")
    assert tr.exit_time == pd.Timestamp("2021-01-31 14:00", tz="UTC")


def test_h0027_never_holds_over_midnight_and_skips_23h_signal():
    b = _with_shock("2021-01-31 22:00", 0.05)
    on = intradag.extreme_hour_reversal(b)
    assert list(on[on != 0].index.hour) == [22] and (on[on != 0] == -1.0).all()
    b = _with_shock("2021-01-31 23:00", 0.05)
    assert (intradag.extreme_hour_reversal(b) == 0).all()


def test_h0027_only_first_extreme_per_day_and_needs_720_returns():
    b = _with_shock("2021-01-31 10:00", -0.05)
    c = b["close"].to_numpy().copy()
    i = b.index.get_loc(pd.Timestamp("2021-01-31 16:00", tz="UTC"))
    c[i:] *= 1.05
    b2 = _bars("2021-01-01", len(b), "1h", closes=c)
    on = intradag.extreme_hour_reversal(b2)
    assert list(on[on != 0].index.hour) == [10, 11, 12]
    early = _with_shock("2021-01-20 10:00", -0.05)       # färre än 720 föregående timmar
    assert (intradag.extreme_hour_reversal(early).loc[:"2021-01-21"] == 0).all()


def test_h0027_respects_period_end():
    b = _with_shock("2021-01-31 21:00", -0.05)
    end = pd.Timestamp("2021-01-31 23:00", tz="UTC")       # utträde 00:00 ligger efter sista öppningen
    assert (intradag.extreme_hour_reversal(b, last_open=end) == 0).all()


# ---------- H-0028 ----------

def _ny_day(date: str, path):
    """15m-staplar ett New York-dygn; path = {lokal tid 'HH:MM': close}. Övriga stänger på 100."""
    start = pd.Timestamp(date + " 00:00", tz=intradag.NY).tz_convert("UTC")
    b = _bars(start, 96, "15min", closes=np.full(96, 100.0))
    local = b.index.tz_convert(intradag.NY).strftime("%H:%M")
    c = b["close"].to_numpy().copy()
    for k, v in path.items():
        c[np.flatnonzero(local == k)[0]:] = v
    return _bars(start, 96, "15min", closes=c)


@pytest.mark.parametrize("date,entry_utc,exit_utc", [
    ("2023-01-10", "2023-01-10 16:15", "2023-01-10 21:00"),   # vintertid, EST = UTC−5
    ("2023-07-11", "2023-07-11 15:15", "2023-07-11 20:00"),   # sommartid, EDT = UTC−4
])
def test_h0028_breakout_entry_and_exit_follow_new_york_clock(date, entry_utc, exit_utc):
    b = _ny_day(date, {"11:00": 101.0})
    tgt = intradag.us_open_range_breakout(b)
    res = backtest.run(b, tgt, ZERO)
    tr = res.closed_trades[0]
    assert tr.side == "Long"
    assert tr.entry_time == pd.Timestamp(entry_utc, tz="UTC")
    assert tr.exit_time == pd.Timestamp(exit_utc, tz="UTC")
    assert len(res.closed_trades) == 1


def test_h0028_no_trade_after_noon_or_on_weekend():
    assert (intradag.us_open_range_breakout(_ny_day("2023-01-10", {"12:00": 101.0})) == 0).all()
    assert (intradag.us_open_range_breakout(_ny_day("2023-01-14", {"11:00": 101.0})) == 0).all()   # lördag


def test_h0028_short_below_range():
    tgt = intradag.us_open_range_breakout(_ny_day("2023-01-10", {"10:45": 99.0}))
    assert (tgt[tgt != 0] == -1.0).all() and (tgt != 0).sum() > 0


# ---------- H-0029 ----------

def test_h0029_sign_of_early_hours_held_18_to_24():
    c = np.full(48, 100.0)
    c[3:] = 101.0                                  # upp under 00–06
    b = _bars("2022-03-01", 48, "1h", closes=c)
    tgt = intradag.early_late_momentum(b)
    on = tgt[tgt != 0]
    assert list(on.loc["2022-03-01"].index.hour) == [17, 18, 19, 20, 21, 22] and (on == 1.0).all()
    res = backtest.run(b, tgt, ZERO)
    tr = res.closed_trades[0]
    assert tr.entry_time == pd.Timestamp("2022-03-01 18:00", tz="UTC")
    assert tr.exit_time == pd.Timestamp("2022-03-02 00:00", tz="UTC")


def test_h0029_skips_day_with_missing_early_bar_and_last_day():
    b = _bars("2022-03-01", 48, "1h").drop(pd.Timestamp("2022-03-01 02:00", tz="UTC"))
    assert (intradag.early_late_momentum(b).loc["2022-03-01"] == 0).all()
    b = _bars("2022-03-01", 24, "1h")
    end = pd.Timestamp("2022-03-01 23:00", tz="UTC")
    assert (intradag.early_late_momentum(b, last_open=end) == 0).all()


# ---------- gemensamt ----------

@pytest.mark.parametrize("hid", ["H-0027", "H-0028", "H-0029"])
def test_no_lookahead(hid):
    interval, fn = intradag.STRATEGIES[hid]
    freq = "15min" if interval == "15m" else "1h"
    b = _bars("2021-01-01", 3000 if interval == "1h" else 4000, freq, seed=3)
    b = b.assign(close=b["close"] * np.exp(np.random.default_rng(1).normal(0, 0.01, len(b))))
    b["open"] = b["close"].shift(1).fillna(b["close"].iloc[0])
    b["high"] = b[["open", "close"]].max(axis=1) * 1.001
    b["low"] = b[["open", "close"]].min(axis=1) * 0.999
    backtest.check_no_lookahead(fn, b, cutoffs=12)


def test_exit_at_final_open_is_not_allowed():
    """Motorn kör aldrig datasetets sista öppning, så ett utträde där skulle lämna affären öppen (Codex-fynd)."""
    b = _with_shock("2021-01-31 19:00", -0.05)
    end = pd.Timestamp("2021-01-31 23:00", tz="UTC")
    b = b.loc[:end]
    tgt = intradag.extreme_hour_reversal(b, last_open=end)
    assert (tgt == 0).all()
    res = backtest.run(b, tgt, ZERO)
    assert not res.trades
    ok = intradag.extreme_hour_reversal(b, last_open=pd.Timestamp("2021-02-01 00:00", tz="UTC"))
    assert (ok != 0).sum() == 3
