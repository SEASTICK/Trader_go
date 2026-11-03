"""mom-signal/1.0.0 (H-0017 leverans B) på syntetiska staplar. Ingen marknadshistorik."""
import math
import statistics

import numpy as np
import pandas as pd
import pytest

from traderlab import momentum_signal as ms

START = pd.Timestamp("2021-01-01", tz="UTC")


def bars_from_daily(closes, start=START):
    """Sex 4H-staplar per dag. 20-stapelns close = dagsclose; övriga staplars close och alla open är brus."""
    idx, close, open_ = [], [], []
    for d, c in enumerate(closes):
        for k in range(6):
            idx.append(start + pd.Timedelta(days=d, hours=4 * k))
            close.append(c if k == 5 else c * (1.5 + 0.1 * k))
            open_.append(c * (0.7 + 0.05 * k))
    df = pd.DataFrame({"open": open_, "high": np.maximum(open_, close) * 1.01,
                       "low": np.minimum(open_, close) * 0.99, "close": close, "volume": 1.0},
                      index=pd.DatetimeIndex(idx, tz="UTC"))
    return df


def returns_closes(rets, first=100.0):
    out = [first]
    for r in rets:
        out.append(out[-1] * (1 + r))
    return out


RETS = [0.01, -0.02, 0.015, -0.005, 0.03, -0.012, 0.007]


def cycling(n):
    return [RETS[i % len(RETS)] for i in range(n)]


def expected_vol(closes):
    r = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - 60, len(closes))]
    assert len(r) == 60
    return statistics.stdev(r) * math.sqrt(365)


def test_version_and_columns():
    sig = ms.signals(bars_from_daily(returns_closes(cycling(60))))
    assert ms.VERSION == "mom-signal/1.0.0"
    assert list(sig.columns) == ms.COLUMNS
    assert (sig["version"] == ms.VERSION).all()


@pytest.mark.parametrize("lags,expected", [
    ((99, 99, 99), (1, 1, 1)),        # stigande mot alla horisonter
    ((101, 101, 101), (0, 0, 0)),     # fallande
    ((100, 100, 100), (0, 0, 0)),     # lika pris ger 0
    ((99, 100, 101), (1, 0, 0)),
    ((99, 99, 101), (1, 1, 0)),
])
def test_horizons_mean_and_target_by_hand(lags, expected):
    closes = returns_closes(cycling(60))
    closes = [c / closes[-1] * 100 for c in closes]  # C_D = 100
    for h, v in zip((7, 14, 28), lags):
        closes[60 - h] = v
    row = ms.signals(bars_from_daily(closes)).iloc[60]
    assert row["available"] and row["reason"] is None
    assert (row["s7"], row["s14"], row["s28"]) == expected
    s = sum(expected) / 3
    assert row["s"] == pytest.approx(s) and row["s"] in (0, 1 / 3, 2 / 3, 1)
    vol = expected_vol(closes)
    assert row["vol"] == pytest.approx(vol, rel=1e-12)
    assert row["cap"] == pytest.approx(min(1, 0.10 / vol), rel=1e-12)
    assert row["w_target"] == pytest.approx(s * min(1, 0.10 / vol), rel=1e-12)


def test_cap_is_one_when_vol_below_target():
    closes = returns_closes([0.001 * (-1) ** i for i in range(60)])
    row = ms.signals(bars_from_daily(closes)).iloc[60]
    assert row["vol"] < 0.10 and row["cap"] == 1.0 and row["w_target"] == row["s"]


def test_vol_uses_61_closes_60_simple_returns_ddof1_sqrt365():
    closes = returns_closes(cycling(70))
    sig = ms.signals(bars_from_daily(closes))
    got = sig.iloc[-1]["vol"]
    r = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    assert got == pytest.approx(statistics.stdev(r[-60:]) * math.sqrt(365), rel=1e-12)
    wrong = {
        "ddof0": statistics.pstdev(r[-60:]) * math.sqrt(365),
        "59 returns": statistics.stdev(r[-59:]) * math.sqrt(365),
        "61 returns": statistics.stdev(r[-61:]) * math.sqrt(365),
        "log returns": statistics.stdev([math.log(1 + x) for x in r[-60:]]) * math.sqrt(365),
        "price std": statistics.stdev(closes[-61:]) * math.sqrt(365),
        "sqrt252": statistics.stdev(r[-60:]) * math.sqrt(252),
    }
    for name, v in wrong.items():
        assert not math.isclose(got, v, rel_tol=1e-9), name


def test_first_available_day_needs_61_closes():
    sig = ms.signals(bars_from_daily(returns_closes(cycling(60))))
    assert len(sig) == 61
    assert sig.iloc[59]["reason"] == ms.WARMUP and not sig.iloc[59]["available"]
    assert math.isnan(sig.iloc[59]["w_target"])
    assert sig.iloc[60]["available"]
    assert sig.index[60] == START + pd.Timedelta(days=60)


def test_decision_time_and_day_boundary():
    bars = bars_from_daily(returns_closes(cycling(65)))
    sig = ms.signals(bars)
    D = sig.index[63]
    assert sig.loc[D, "decision_time"] == D + pd.Timedelta(days=1) == sig.loc[D, "earliest_fill"]
    # Dagens beslut är inte känt på dagens egna staplar, inte ens vid 20-stapelns öppning.
    assert ms.latest_decision(sig, D + pd.Timedelta(hours=20)).name == D - pd.Timedelta(days=1)
    assert ms.latest_decision(sig, D + pd.Timedelta(days=1)).name == D
    with pytest.raises(KeyError):
        ms.latest_decision(sig, START)


def test_only_20_bar_close_is_day_close():
    bars = bars_from_daily(returns_closes(cycling(65)))
    base = ms.signals(bars)
    D = base.index[63]
    other = bars.copy()
    other.loc[D + pd.Timedelta(hours=16), "close"] *= 3
    pd.testing.assert_frame_equal(ms.signals(other), base)
    last = bars.copy()
    last.loc[D + pd.Timedelta(hours=20), "close"] *= 0.5
    changed = ms.signals(last)
    pd.testing.assert_frame_equal(changed.iloc[:63], base.iloc[:63])
    assert changed.loc[D, "close"] != base.loc[D, "close"]


def test_incomplete_or_running_last_day_is_unavailable():
    bars = bars_from_daily(returns_closes(cycling(65)))
    base = ms.signals(bars)
    running = ms.signals(bars.iloc[:-1])          # 20-stapeln för sista dagen saknas
    assert running.iloc[-1]["reason"] == ms.INCOMPLETE_DAY and not running.iloc[-1]["available"]
    assert math.isnan(running.iloc[-1]["close"])
    pd.testing.assert_frame_equal(running.iloc[:-1], base.iloc[:-1])


def test_prefix_and_future_prices_do_not_change_known_decisions():
    bars = bars_from_daily(returns_closes(cycling(120)))
    full = ms.signals(bars)
    for k in (370, 371, 400, 455, 500, 600, len(bars) - 1):
        part = bars.iloc[:k]
        known_at = part.index[-1] + ms.BAR
        got = ms.signals(part)
        got = got[got["decision_time"] <= known_at]
        pd.testing.assert_frame_equal(got, full.loc[got.index])
    cut = full.index[80]
    future = bars.copy()
    after = future.index >= cut + pd.Timedelta(days=1)
    future.loc[after, "close"] *= np.linspace(0.5, 2.0, after.sum())
    pd.testing.assert_frame_equal(ms.signals(future).loc[:cut], full.loc[:cut])


def test_open_high_low_never_affect_decisions():
    bars = bars_from_daily(returns_closes(cycling(90)))
    noisy = bars.copy()
    noisy[["open", "high", "low"]] *= 7.0
    noisy["open"] = np.nan
    pd.testing.assert_frame_equal(ms.signals(noisy), ms.signals(bars))


@pytest.mark.parametrize("drop", ["day", "bar"])
def test_missing_middle_day_or_bar_is_not_replaced(drop):
    bars = bars_from_daily(returns_closes(cycling(160)))
    m = 70
    day = START + pd.Timedelta(days=m)
    gone = (bars.index.floor("D") == day) if drop == "day" else (bars.index == day + pd.Timedelta(hours=8))
    sig = ms.signals(bars[~gone])
    full = ms.signals(bars)
    assert len(sig) == len(full)                                  # kalenderdagar, inte observationer
    assert sig.iloc[m]["reason"] == ms.INCOMPLETE_DAY
    assert (sig.iloc[m + 1:m + 61]["reason"] == ms.MISSING_DAY).all()
    assert not sig.iloc[m:m + 61]["available"].any()
    pd.testing.assert_frame_equal(sig.iloc[m + 61:], full.iloc[m + 61:])
    pd.testing.assert_frame_equal(sig.iloc[:m], full.iloc[:m])


def test_horizon_lookback_into_missing_day_alone_is_unavailable():
    # Volatilitetsfönstret är längre än alla horisonter, så varje horisontlucka ligger också i fönstret.
    assert max(ms.HORIZONS) < ms.VOL_RETURNS


def test_zero_or_invalid_volatility_is_unavailable_not_a_buy():
    sig = ms.signals(bars_from_daily([100.0] * 61))
    row = sig.iloc[60]
    assert row["reason"] == ms.INVALID_VOL and not row["available"]
    assert math.isnan(row["w_target"]) and math.isnan(row["s"]) and math.isnan(row["cap"])


def _bad(kind):
    bars = bars_from_daily(returns_closes(cycling(5)))
    if kind == "misaligned":
        return bars.set_axis(bars.index + pd.Timedelta(hours=1))
    if kind == "minute":
        return bars.set_axis(bars.index.where(bars.index != bars.index[3], bars.index[3] + pd.Timedelta(minutes=1)))
    if kind == "duplicate":
        return pd.concat([bars, bars.iloc[[3]]]).sort_index()
    if kind == "unsorted":
        return bars.iloc[::-1]
    if kind == "naive":
        return bars.tz_localize(None)
    if kind == "other_tz":
        return bars.tz_convert("Europe/Stockholm")
    if kind == "plus4_tz":
        return bars.tz_convert("Etc/GMT-4")  # ligger på 4H-rutnätet men är inte UTC
    if kind == "not_datetime":
        return bars.reset_index(drop=True)
    if kind == "no_close":
        return bars.drop(columns="close")
    bad = bars.copy()
    bad.iloc[4, bad.columns.get_loc("close")] = {"nan": np.nan, "inf": np.inf, "zero": 0.0, "negative": -1.0}[kind]
    return bad


@pytest.mark.parametrize("kind,message", [
    ("misaligned", "4H-gräns"), ("minute", "4H-gräns"), ("duplicate", "Dubbletter"), ("unsorted", "sorterat"),
    ("naive", "UTC"), ("other_tz", "UTC"), ("plus4_tz", "UTC"), ("not_datetime", "DatetimeIndex"),
    ("no_close", "close"), ("nan", "ändliga"), ("inf", "ändliga"), ("zero", "ändliga"), ("negative", "ändliga")])
def test_invalid_index_or_prices_are_rejected(kind, message):
    with pytest.raises(ValueError, match=message):
        ms.signals(_bad(kind))


def test_input_is_not_modified():
    bars = bars_from_daily(returns_closes(cycling(65)))
    copy = bars.copy()
    ms.signals(bars)
    pd.testing.assert_frame_equal(bars, copy)


EMPTY = pd.DataFrame({"close": pd.Series(dtype=float)}, index=pd.DatetimeIndex([], tz="UTC"))


@pytest.mark.parametrize("make", [lambda: EMPTY, lambda: bars_from_daily(returns_closes(cycling(65))).iloc[:0]],
                         ids=["tom_ram", "tomt_prefix"])
def test_empty_input_gives_empty_signal_frame_with_stable_schema(make):
    bars = make()
    ms.validate_bars(bars)
    sig = ms.signals(bars)
    ref = ms.signals(bars_from_daily(returns_closes(cycling(65))))
    assert sig.empty and len(sig) == 0
    assert list(sig.columns) == ms.COLUMNS
    assert isinstance(sig.index, pd.DatetimeIndex) and str(sig.index.tz) == "UTC"
    assert sig.index.dtype == ref.index.dtype
    assert sig.dtypes.to_dict() == ref.dtypes.to_dict()
    assert str(sig["decision_time"].dt.tz) == "UTC" and str(sig["earliest_fill"].dt.tz) == "UTC"
    assert sig["available"].dtype == bool and sig["w_target"].dtype == float


def test_latest_decision_on_empty_result_says_no_decision_known():
    with pytest.raises(KeyError, match="Inget beslut känt"):
        ms.latest_decision(ms.signals(EMPTY), pd.Timestamp("2022-01-01", tz="UTC"))


def test_nonempty_incomplete_single_day_is_still_unavailable():
    bars = bars_from_daily([100.0]).iloc[:2]                 # 00- och 04-staplarna, dagen pågår
    sig = ms.signals(bars)
    assert len(sig) == 1
    row = sig.iloc[0]
    assert row["reason"] == ms.INCOMPLETE_DAY
    assert not row["available"] and math.isnan(row["w_target"]) and math.isnan(row["close"])
    with pytest.raises(KeyError, match="Inget beslut känt"):
        ms.latest_decision(sig, bars.index[-1] + ms.BAR)
