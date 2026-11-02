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


def test_supplied_labels_are_not_carried_over_a_missing_day():
    effective = pd.Series(["upp/låg vol", "ned/låg vol"], index=pd.DatetimeIndex(["2021-01-01", "2021-01-03"], tz="UTC"))
    idx = pd.DatetimeIndex(["2021-01-02 04:00", "2021-01-03 04:00", "2021-01-04 04:00"], tz="UTC")
    got = regime.per_bar(pd.DataFrame(index=idx), effective)
    assert list(got) == ["upp/låg vol", regime.UNKNOWN, "ned/låg vol"]


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


# Validering av tidsserien

def test_series_shifted_30_minutes_is_rejected(bars):
    shifted = bars.set_axis(bars.index + pd.Timedelta(minutes=30))
    with pytest.raises(ValueError, match="rutnätet"):
        regime.raw_daily(shifted)
    with pytest.raises(ValueError, match="rutnätet"):
        regime.per_bar(shifted)


def test_irregular_timestamp_is_rejected(bars):
    extra = bars.iloc[[10]].set_axis([bars.index[10] + pd.Timedelta(hours=2)])
    irregular = pd.concat([bars, extra]).sort_index()
    with pytest.raises(ValueError, match="rutnätet"):
        regime.raw_daily(irregular)


def test_wrong_or_unknown_interval_is_rejected(bars):
    with pytest.raises(ValueError, match="rutnätet"):
        regime.raw_daily(bars, interval="1d")
    with pytest.raises(ValueError, match="stöds inte"):
        regime.raw_daily(bars, interval="3h")


def test_duplicates_and_unsorted_are_rejected(bars):
    with pytest.raises(ValueError, match="dubbletter"):
        regime.raw_daily(pd.concat([bars.iloc[:10], bars.iloc[9:20]]))
    with pytest.raises(ValueError, match="sorterade"):
        regime.raw_daily(bars.iloc[::-1])


def test_supplied_daily_labels_must_be_utc_midnights():
    idx = pd.DatetimeIndex(["2021-01-02 00:00"], tz="UTC")
    with pytest.raises(ValueError, match="00:00"):
        regime.per_bar(pd.DataFrame(index=idx), _raw(["upp/låg vol"], start="2021-01-01 04:00"))
    with pytest.raises(ValueError, match="dubbletter"):
        regime.with_hysteresis(pd.Series(["upp/låg vol"] * 2, index=pd.DatetimeIndex(["2021-01-01"] * 2, tz="UTC")))


# Luckor mitt i serien

GAP_DAY = 250


@pytest.fixture(scope="module")
def long_bars():
    return make_bars(700 * BARS_PER_DAY, interval="4h", seed=11, vol=0.02)


def _day(bars, n):
    return bars.index[0].floor("D") + n * regime.DAY


def _drop(bars, mask):
    return bars[~mask]


@pytest.mark.parametrize("kind", ["missing", "incomplete_last_bar", "incomplete_first_bar"])
def test_gap_day_is_unknown_and_windows_restart(long_bars, kind):
    day = long_bars.index.floor("D")
    gap = _day(long_bars, GAP_DAY)
    if kind == "missing":
        holed = _drop(long_bars, day == gap)
    elif kind == "incomplete_last_bar":
        holed = _drop(long_bars, long_bars.index == gap + pd.Timedelta(hours=20))
    else:  # utan 00:00-stapeln: dagens sista stapel finns, men dagen är ändå inte stängd
        holed = _drop(long_bars, long_bars.index == gap)
    assert gap not in regime.daily_closes(holed).index
    raw = regime.raw_daily(holed)
    assert len(raw) == 700, "every calendar day is present, also the gap"
    assert raw[gap] == regime.UNKNOWN
    # 200-dagarsmedlet räknas först när 200 hela dagar efter luckan finns.
    assert (raw[gap: gap + 199 * regime.DAY] == regime.UNKNOWN).all()
    assert raw[gap + 200 * regime.DAY] != regime.UNKNOWN
    full = regime.raw_daily(long_bars)
    pd.testing.assert_series_equal(raw[:gap - regime.DAY], full[:gap - regime.DAY])
    labels = regime.per_bar(holed)
    assert (labels[labels.index.floor("D") == gap + regime.DAY] == regime.UNKNOWN).all()


def test_confirmation_restarts_after_a_gap(long_bars):
    holed = _drop(long_bars, long_bars.index.floor("D") == _day(long_bars, GAP_DAY))
    raw, eff = regime.raw_daily(holed), regime.daily(holed)
    back = _day(long_bars, GAP_DAY + 200)  # första kända dagen efter luckan
    assert eff[back - regime.DAY] == regime.UNKNOWN
    # Utan ett omedelbart läge måste även dagarna efter luckan bekräftas på nytt i tre dagar.
    assert eff[back] == (raw[back] if raw[back] in regime.IMMEDIATE else regime.UNKNOWN)
    pd.testing.assert_series_equal(eff[back:], regime.with_hysteresis(raw[back - regime.DAY:]).iloc[1:])


@pytest.mark.parametrize("cut_day", [GAP_DAY, GAP_DAY + 1, GAP_DAY + 201, 650])
def test_future_bars_never_change_earlier_labels_across_a_gap(long_bars, cut_day):
    holed = _drop(long_bars, long_bars.index.floor("D") == _day(long_bars, GAP_DAY))
    cut = holed.index.searchsorted(_day(long_bars, cut_day))
    pd.testing.assert_series_equal(regime.per_bar(holed.iloc[:cut]), regime.per_bar(holed).iloc[:cut])


def test_missing_calendar_day_breaks_the_three_day_count():
    """Granskningens exempel: samma läge 1, 3 och 4 januari är bara två dagar i rad."""
    idx = pd.DatetimeIndex(["2021-01-01", "2021-01-03", "2021-01-04"], tz="UTC")
    got = regime.with_hysteresis(pd.Series(["upp/låg vol"] * 3, index=idx))
    assert list(got.index.day) == [1, 2, 3, 4]
    assert list(got) == [regime.UNKNOWN] * 4
    idx5 = idx.append(pd.DatetimeIndex(["2021-01-05"], tz="UTC"))
    got5 = regime.with_hysteresis(pd.Series(["upp/låg vol"] * 4, index=idx5))
    assert got5.iloc[-1] == "upp/låg vol"


def test_missing_day_switches_away_from_down_high_vol_at_once():
    idx = pd.DatetimeIndex(["2021-01-01", "2021-01-03"], tz="UTC")
    got = regime.with_hysteresis(pd.Series(["ned/hög vol", "ned/hög vol"], index=idx))
    assert list(got) == ["ned/hög vol", regime.UNKNOWN, "ned/hög vol"]


def test_day_closure_ignores_later_timestamps(bars):
    """Om en dag är stängd avgörs av dagens egna staplar, inte av om datan fortsätter."""
    end = 300 * BARS_PER_DAY
    exact = regime.daily_closes(bars.iloc[:end])
    with_next = regime.daily_closes(bars.iloc[: end + 1])
    with_much_more = regime.daily_closes(bars)
    pd.testing.assert_series_equal(exact, with_next)
    pd.testing.assert_series_equal(exact, with_much_more.iloc[:300])
    five_bars = bars.iloc[: end - 1]  # dag 300 saknar sin sista stapel
    assert len(regime.daily_closes(five_bars)) == 299


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
