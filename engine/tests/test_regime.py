"""Marknadsläget för Fas 2 (H-0013) på syntetisk data: uppvärmning, dagsgränser, hysteres och ingen framtidsdata."""
import numpy as np
import pandas as pd
import pytest

from traderlab import metrics, regime
from traderlab.synthetic import from_closes, make_bars

DAYS = 400
BARS_PER_DAY = 6


@pytest.fixture(scope="module")
def bars():
    return make_bars(DAYS * BARS_PER_DAY, interval="4h", seed=7, vol=0.02)


def _raw(labels, start="2021-01-01"):
    return pd.Series(labels, index=pd.date_range(start, periods=len(labels), freq="D", tz="UTC"))


# Uppvärmning

def test_unknown_until_200_day_mean_and_volatility_median_exist(bars):
    raw = regime.raw_daily(bars)
    assert len(raw) == DAYS
    # 200-dagarsmedlet finns från dag 200 (index 199). Medianen behöver 60 volatilitetsvärden, alltså dag 90.
    assert (raw.iloc[:199] == regime.UNKNOWN).all()
    assert (raw.iloc[199:] != regime.UNKNOWN).all()
    assert set(raw.iloc[199:]) <= set(regime.LABELS)


def test_short_history_is_only_unknown():
    short = make_bars(150 * BARS_PER_DAY, interval="4h", seed=1)
    assert (regime.per_bar(short) == regime.UNKNOWN).all()
    assert regime.current(short) == regime.UNKNOWN


def test_raw_labels_match_metrics_regimes(bars):
    """Samma beräkning som Fas 1:s regimrapport (metrics.regimes), före hysteres."""
    ours = regime.per_bar(bars, regime.raw_daily(bars))
    theirs = metrics.regimes(bars).fillna(regime.UNKNOWN)
    pd.testing.assert_series_equal(ours, theirs, check_names=False)


# Dagsgränser

def test_each_bar_uses_the_previous_closed_day(bars):
    effective = regime.daily(bars)
    labels = regime.per_bar(bars)
    for day in effective.index[1:]:
        today = labels[labels.index.floor("D") == day]
        assert len(today) == BARS_PER_DAY
        assert (today == effective[day - regime.DAY]).all()
    assert (labels[labels.index.floor("D") == effective.index[0]] == regime.UNKNOWN).all()


def test_midnight_bar_switches_to_yesterday_and_evening_bar_does_not():
    effective = _raw(["upp/låg vol", "ned/hög vol", "upp/hög vol"])
    idx = pd.DatetimeIndex(["2021-01-02 00:00", "2021-01-02 20:00", "2021-01-03 00:00", "2021-01-04 04:00"], tz="UTC")
    got = regime.per_bar(pd.DataFrame(index=idx), effective)
    assert list(got) == ["upp/låg vol", "upp/låg vol", "ned/hög vol", "upp/hög vol"]


def test_a_started_day_is_not_closed(bars):
    partial = bars.iloc[: 300 * BARS_PER_DAY + 2]  # två staplar in på dag 301
    closes = regime.daily_closes(partial)
    assert len(closes) == 300
    assert closes.index[-1] == bars.index[0].floor("D") + 299 * regime.DAY
    assert regime.current(partial) == regime.daily(bars.iloc[: 300 * BARS_PER_DAY]).iloc[-1]


def test_current_is_the_label_for_the_next_bar(bars):
    nxt = pd.DataFrame(index=[bars.index[-1] + pd.Timedelta(hours=4)])
    assert regime.current(bars) == regime.per_bar(nxt, regime.daily(bars)).iloc[0]


def test_requires_utc_index(bars):
    naive = bars.tz_convert(None)
    with pytest.raises(ValueError, match="UTC"):
        regime.raw_daily(naive)
    with pytest.raises(ValueError, match="UTC"):
        regime.raw_daily(bars.tz_convert("Europe/Stockholm"))


# Hysteres

def test_new_regime_needs_three_days_in_a_row():
    raw = _raw(["upp/låg vol"] * 3 + ["upp/hög vol"] * 2 + ["upp/låg vol"] + ["upp/hög vol"] * 3)
    got = regime.with_hysteresis(raw)
    assert list(got) == [regime.UNKNOWN, regime.UNKNOWN, "upp/låg vol",
                         "upp/låg vol", "upp/låg vol", "upp/låg vol",
                         "upp/låg vol", "upp/låg vol", "upp/hög vol"]


def test_down_high_vol_and_unknown_apply_at_once():
    raw = _raw(["upp/låg vol"] * 3 + ["ned/hög vol"] + ["upp/låg vol"] * 3 + [regime.UNKNOWN] + ["ned/låg vol"] * 3)
    got = list(regime.with_hysteresis(raw))
    assert got[3] == "ned/hög vol"
    assert got[4:6] == ["ned/hög vol"] * 2, "leaving down/high vol also needs three days"
    assert got[6] == "upp/låg vol"
    assert got[7] == regime.UNKNOWN
    assert got[8:10] == [regime.UNKNOWN] * 2
    assert got[10] == "ned/låg vol"


def test_two_day_blips_never_change_the_regime():
    pattern = ["ned/låg vol", "ned/låg vol", "upp/låg vol", "upp/låg vol"] * 10
    got = regime.with_hysteresis(_raw(pattern))
    assert set(got) == {regime.UNKNOWN}


def test_hysteresis_reduces_switches_on_real_shaped_series(bars):
    raw = regime.raw_daily(bars)
    eff = regime.with_hysteresis(raw)
    switches = lambda s: int((s != s.shift()).sum())
    assert switches(eff) <= switches(raw)
    known = eff != regime.UNKNOWN
    assert set(eff[known]) <= set(regime.LABELS)


# Ingen framtidsdata

@pytest.mark.parametrize("cut_day", [150, 205, 260, 333, 399])
def test_future_bars_never_change_earlier_labels(bars, cut_day):
    cut = cut_day * BARS_PER_DAY
    full = regime.per_bar(bars).iloc[:cut]
    prefix = regime.per_bar(bars.iloc[:cut])
    pd.testing.assert_series_equal(prefix, full)
    pd.testing.assert_series_equal(regime.daily(bars.iloc[:cut]), regime.daily(bars).iloc[:cut_day])


def test_changing_future_prices_leaves_earlier_labels_and_same_day_bars_unchanged(bars):
    day = 260
    cut = day * BARS_PER_DAY  # första stapeln på dag 261
    shocked = bars.copy()
    rng = np.random.default_rng(3)
    shocked.iloc[cut:, :4] = shocked.iloc[cut:, :4].to_numpy() * rng.uniform(0.3, 3.0, (len(bars) - cut, 1))
    a, b = regime.per_bar(bars), regime.per_bar(shocked)
    # Staplarna på den chockade dagen använder fortfarande gårdagens läge.
    pd.testing.assert_series_equal(a.iloc[: cut + BARS_PER_DAY], b.iloc[: cut + BARS_PER_DAY])


def test_a_known_trend_flip_shows_up_one_day_late():
    # 260 dagar stigande pris, sedan ett ras som ger ned/hög vol direkt (ingen väntan på tre dagar).
    closes = []
    price = 100.0
    rng = np.random.default_rng(0)
    for d in range(300):
        step = 1.002 + rng.normal(0, 0.002) if d < 260 else 0.85
        for _ in range(BARS_PER_DAY):
            price *= step ** (1 / BARS_PER_DAY)
            closes.append(price)
    bars = from_closes(closes)
    eff = regime.daily(bars)
    first_crash_day = eff.index[260]
    flips = eff[eff == "ned/hög vol"]
    assert not flips.empty and flips.index[0] >= first_crash_day
    labels = regime.per_bar(bars)
    first_bar = labels[labels == "ned/hög vol"].index[0]
    assert first_bar.floor("D") == flips.index[0] + regime.DAY
