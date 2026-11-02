"""Urvalsregel och walk-forward för H-0013 på syntetisk data. Ingen riktig data, inget slutprov."""
import json

import numpy as np
import pandas as pd
import pytest

from traderlab import adaptive, backtest, fas1, fas2, regime
from traderlab.costs import ZERO
from traderlab.strategies.rules import SPECS
from traderlab.synthetic import make_bars

EMA, BB, FLAT = "ema_adx_trend", "bb_rsi_reversion", adaptive.FLAT
UTC = lambda t: pd.Timestamp(t, tz="UTC")
N_DEV = int((UTC("2025-01-01") - UTC("2020-01-01")) / pd.Timedelta(hours=4))
ALL_BB = adaptive.Playbook.of({l: BB for l in regime.LABELS})


def funding_for(bars, rate=0.0001):
    return pd.Series(rate, index=pd.date_range(bars.index[0], bars.index[-1], freq="8h"))


@pytest.fixture(scope="module")
def dev():
    bars = make_bars(N_DEV, interval="4h", seed=1, vol=0.015)
    return bars, funding_for(bars)


@pytest.fixture(scope="module")
def wf(dev):
    return fas2.walk_forward(*dev)


@pytest.fixture(scope="module")
def wf_bb(dev):
    """Walk-forward där urvalet alltid ger bb_rsi_reversion, så att fönstren har affärer att räkna."""
    orig = fas2.select
    fas2.select = lambda by_candidate: ALL_BB
    try:
        return fas2.walk_forward(*dev)
    finally:
        fas2.select = orig


# Urvalsregeln

def cand(trades=25, t=1.0, sharpe=1.0, days=100):
    return {"days": days, "trades": trades, "sharpe": sharpe, "t": t}


def stats_for(ema, bb):
    return {EMA: {l: ema for l in regime.LABELS}, BB: {l: bb for l in regime.LABELS}}


@pytest.mark.parametrize("trades, expected", [(19, FLAT), (20, BB), (21, BB)])
def test_at_least_20_trades_entered_in_the_regime(trades, expected):
    book = fas2.select(stats_for(cand(trades=5, sharpe=9.0), cand(trades=trades)))
    assert set(dict(book.choices).values()) == {expected}


@pytest.mark.parametrize("t, expected", [(0.0, FLAT), (-0.5, FLAT), (None, FLAT), (1e-9, BB)])
def test_t_must_be_positive(t, expected):
    book = fas2.select(stats_for(cand(t=-1.0), cand(t=t)))
    assert set(dict(book.choices).values()) == {expected}


def test_highest_sharpe_wins_and_exact_tie_goes_to_ema():
    assert set(dict(fas2.select(stats_for(cand(sharpe=0.5), cand(sharpe=0.7))).choices).values()) == {BB}
    assert set(dict(fas2.select(stats_for(cand(sharpe=0.9), cand(sharpe=0.7))).choices).values()) == {EMA}
    assert set(dict(fas2.select(stats_for(cand(sharpe=0.7), cand(sharpe=0.7))).choices).values()) == {EMA}


def test_a_higher_sharpe_that_is_not_eligible_never_wins():
    book = fas2.select(stats_for(cand(trades=19, sharpe=5.0), cand(sharpe=0.1)))
    assert set(dict(book.choices).values()) == {BB}


def test_no_eligible_candidate_gives_flat_per_regime():
    by = stats_for(cand(trades=0, t=None, sharpe=0.0), cand(trades=0, t=None, sharpe=0.0))
    by[BB][regime.LABELS[2]] = cand(sharpe=0.3)
    book = fas2.select(by)
    assert dict(book.choices) == {regime.LABELS[0]: FLAT, regime.LABELS[1]: FLAT, regime.LABELS[2]: BB,
                                  regime.LABELS[3]: FLAT}


def test_regime_stats_count_days_and_trades_per_regime(dev):
    bars, funding = dev
    tb, tf = bars[bars.index < UTC("2023-01-01")], funding[funding.index < UTC("2023-01-01")]
    eff = regime.daily(tb)
    s = fas2.regime_stats(tb, tf, BB, effective=eff)
    sig = adaptive.signals(tb, ALL_BB, effective=eff)
    res = backtest.run(tb, sig.target, fas2.COSTS, funding=tf, stop_distance=sig.stop_distance)
    assert sum(v["trades"] for v in s.values()) == len(res.trades) > 0
    days = regime.per_bar(tb, eff).groupby(tb.index.floor("D")).first()
    for label, v in s.items():
        assert v["days"] == int((days == label).sum())


# Fönster, uppvärmning och platt start

def test_six_windows_with_exact_boundaries(wf):
    assert fas2.TEST_STARTS == fas1.TEST_STARTS and fas2.HOLDOUT_START == fas1.HOLDOUT_START == "2025-01-01"
    ends = fas2.TEST_STARTS[1:] + ["2025-01-01"]
    assert [w["train"] for w in wf.windows] == [["2020-01-01", a] for a in fas2.TEST_STARTS]
    assert [w["test"] for w in wf.windows] == [[a, b] for a, b in zip(fas2.TEST_STARTS, ends)]
    assert wf.final["train"] == ["2020-01-01", "2025-01-01"]


@pytest.mark.parametrize("k", range(6))
def test_window_starts_flat_and_counts_only_trades_entered_inside(dev, k):
    bars, funding = dev
    a = UTC(fas2.TEST_STARTS[k])
    b = UTC((fas2.TEST_STARTS + ["2025-01-01"])[k + 1])
    res, info = fas2.evaluate_window(bars, funding, ALL_BB, a, b)
    assert res.bar_returns.index.min() == a and res.bar_returns.index.max() < b
    assert res.position.iloc[0] == 0.0, "flat at the first bar of the window"
    assert all(a + pd.Timedelta(hours=4) <= t.entry_time < b for t in res.trades)
    assert all(t.exit_time is not None and t.exit_time < b for t in res.trades), "closed inside the window"
    assert res.position.iloc[-1] == 0.0
    assert info["trades"] == len(res.trades) == sum(v["trades"] for v in info["per_regime"].values())


@pytest.mark.parametrize("k", range(6))
def test_every_window_trade_starts_on_a_new_entry_signal(dev, k):
    """Även vid fönstrets start: en kandidatsignal som redan pågick tas inte över."""
    bars, funding = dev
    a = UTC(fas2.TEST_STARTS[k])
    b = UTC((fas2.TEST_STARTS + ["2025-01-01"])[k + 1])
    raw = SPECS[BB].signals(bars[bars.index < b]).target
    res, _ = fas2.evaluate_window(bars, funding, ALL_BB, a, b)
    step = pd.Timedelta(hours=4)
    for t in res.trades:
        side = 1.0 if t.side == "Long" else -1.0
        decided = t.entry_time - step
        assert decided >= a, "the decision is taken after the playbook started"
        assert raw[decided] == side and raw[decided - step] != side


def test_a_position_still_open_is_closed_at_the_second_to_last_open_with_costs(dev, monkeypatch):
    bars, funding = dev
    a, b = UTC("2024-07-01"), UTC("2025-01-01")
    days = pd.date_range("2020-01-01", "2024-12-31", freq="D", tz="UTC")
    monkeypatch.setattr(fas2.regime, "daily", lambda hist, interval="4h": pd.Series("upp/låg vol", index=days, dtype=object))

    def always_long_after_start(hist):
        sig = (hist.index > a).astype(float)
        return {EMA: (sig, np.full(len(hist), np.nan)), BB: (sig, np.full(len(hist), np.nan))}
    monkeypatch.setattr(adaptive, "candidate_signals", always_long_after_start)
    res, info = fas2.evaluate_window(bars, funding, ALL_BB, a, b)
    assert len(res.trades) == 1
    last = res.trades[0]
    hist = bars[bars.index < b]
    assert last.exit_time == hist.index[-2] and last.exit_reason == "signal"
    notional = last.size * last.equity_at_entry
    rate = fas2.COSTS.per_side
    assert last.costs == pytest.approx(rate * notional * (1 + last.exit_price / last.entry_price))
    assert res.position.iloc[-1] == 0.0 and info["local_costs"] == pytest.approx(last.costs)


def test_warmup_uses_history_from_2020_but_no_data_after_the_window(dev):
    bars, funding = dev
    a, b = UTC("2022-07-01"), UTC("2023-01-01")
    shocked = bars.copy()
    after = shocked.index >= b
    shocked.loc[after, ["open", "high", "low", "close"]] *= 3.0
    r1, i1 = fas2.evaluate_window(bars, funding, ALL_BB, a, b)
    r2, i2 = fas2.evaluate_window(shocked, funding, ALL_BB, a, b)
    pd.testing.assert_series_equal(r1.bar_returns, r2.bar_returns)
    assert i1 == i2


# Ingen framtidsdata i urvalet

@pytest.mark.parametrize("k", range(6))
def test_changed_test_or_future_data_never_changes_an_earlier_choice(dev, wf, k):
    bars, funding = dev
    a = UTC(fas2.TEST_STARTS[k])
    shocked = bars.copy()
    rng = np.random.default_rng(k)
    later = shocked.index >= a
    shocked.loc[later, ["open", "high", "low", "close"]] *= rng.uniform(0.5, 2.0, (later.sum(), 1))
    f2 = funding.copy()
    f2[f2.index >= a] = 0.01
    retrained = fas2.train(shocked, f2, a)
    keys = ("train", "playbook", "playbook_id", "candidates")
    assert {key: retrained[key] for key in keys} == {key: wf.windows[k][key] for key in keys}


def test_training_reads_nothing_at_or_after_the_window(dev, monkeypatch):
    bars, funding = dev
    a = UTC("2023-07-01")
    seen = []
    orig = fas2.regime_stats

    def spy(b, f, name, costs=fas2.COSTS, effective=None):
        seen.append((b.index.max(), f.index.max(), effective.index.max()))
        return orig(b, f, name, costs, effective)
    monkeypatch.setattr(fas2, "regime_stats", spy)
    fas2.train(bars, funding, a)
    assert seen and all(x < a and y < a and z < a for x, y, z in seen)


# Ihopsättning, kostnader och finansieringsränta

def test_stitched_curve_has_no_overlap_and_matches_the_windows(dev, wf_bb):
    bars, funding = dev
    r = wf_bb.returns
    assert r.index.is_unique and r.index.is_monotonic_increasing
    edges = [UTC(t) for t in fas2.TEST_STARTS] + [UTC("2025-01-01")]
    parts = []
    for w, a, b in zip(wf_bb.windows, edges[:-1], edges[1:]):
        res, info = fas2.evaluate_window(bars, funding, ALL_BB, a, b)
        pd.testing.assert_series_equal(r[(r.index >= a) & (r.index < b)], res.bar_returns, check_freq=False)
        assert info["local_costs"] == w["local_costs"] and info["local_funding"] == w["local_funding"]
        assert w["costs"] == pytest.approx(w["local_costs"] * w["capital_start"])
        parts.append(res)
    assert len(wf_bb.trades) == sum(len(p.trades) for p in parts) > 0
    pd.testing.assert_series_equal(wf_bb.equity, (1 + r).cumprod(), check_freq=False)


def test_costs_and_funding_are_counted_once(wf_bb):
    assert wf_bb.total_costs == pytest.approx(sum(t.costs for t in wf_bb.trades))
    assert wf_bb.total_funding == pytest.approx(sum(t.funding for t in wf_bb.trades))
    assert wf_bb.total_costs == pytest.approx(sum(w["costs"] for w in wf_bb.windows))
    assert wf_bb.total_funding == pytest.approx(sum(w["funding"] for w in wf_bb.windows))
    assert wf_bb.total_costs > 0 and wf_bb.total_funding != 0


def test_zero_costs_and_funding_change_only_the_charges(dev):
    bars, funding = dev
    a, b = UTC("2024-01-01"), UTC("2024-07-01")
    with_costs, _ = fas2.evaluate_window(bars, funding, ALL_BB, a, b)
    free, _ = fas2.evaluate_window(bars, funding * 0, ALL_BB, a, b, costs=ZERO)
    assert [t.entry_time for t in with_costs.trades] == [t.entry_time for t in free.trades]
    assert free.total_costs == 0 and free.total_funding == 0
    gross = sum(t.gross_pnl for t in with_costs.trades)
    assert gross == pytest.approx(sum(t.gross_pnl for t in free.trades), rel=0.2)


# Sparat underlag, versionsmärkning och reproducerbarhet

def test_each_window_saves_playbook_periods_candidate_stats_days_and_trades(wf):
    for w in wf.windows:
        assert adaptive.Playbook.from_dict(w["playbook"]).id == w["playbook_id"]
        assert set(w["candidates"]) == {EMA, BB}
        for name in (EMA, BB):
            assert set(w["candidates"][name]) == set(regime.LABELS)
            assert set(w["candidates"][name][regime.LABELS[0]]) == {"days", "trades", "sharpe", "t"}
        assert set(w["per_regime"]) == set(regime.LABELS) | {regime.UNKNOWN}
        days = (UTC(w["test"][1]) - UTC(w["test"][0])).days
        assert sum(v["days"] for v in w["per_regime"].values()) == days


def test_final_playbook_is_versioned_and_chosen_on_the_whole_development_period(dev, wf):
    f = wf.final
    assert f["contract"] == adaptive.CONTRACT_VERSION == f["playbook"]["contract"]
    assert adaptive.Playbook.from_dict(f["playbook"]).id == f["playbook_id"]
    assert fas2.train(*dev, "2025-01-01")["playbook_id"] == f["playbook_id"]
    assert wf.config["version"] == fas2.WALK_FORWARD_VERSION and wf.config["min_trades"] == 20
    assert wf.config["candidates"] == {EMA: "1.0.0", BB: "1.0.0", FLAT: None}


def test_same_data_and_configuration_give_the_same_result(dev, wf):
    again = fas2.walk_forward(*dev)
    assert json.dumps(again.to_dict(), sort_keys=True) == json.dumps(wf.to_dict(), sort_keys=True)
    pd.testing.assert_series_equal(again.returns, wf.returns)


# Slutprovet

def test_holdout_bars_are_rejected_before_anything_is_computed(dev, monkeypatch):
    bars, funding = dev
    extra = make_bars(3, interval="4h", seed=9, start="2025-01-01")
    monkeypatch.setattr(fas2, "train", lambda *a, **k: pytest.fail("trained on holdout"))
    with pytest.raises(ValueError, match="slutprovet"):
        fas2.walk_forward(pd.concat([bars, extra]), funding)
    late = pd.concat([funding, pd.Series(0.0001, index=[UTC("2025-01-01 00:00")])])
    with pytest.raises(ValueError, match="slutprovet"):
        fas2.walk_forward(bars, late)
    early = make_bars(3, interval="4h", seed=9, start="2019-12-31 12:00")
    with pytest.raises(ValueError, match="före"):
        fas2.walk_forward(pd.concat([early, bars]), funding)


def test_loader_bounds_archive_reads_before_the_holdout(monkeypatch, dev):
    bars, funding = dev
    calls = []

    def load(market, symbol, interval, data_dir, *, start, end):
        calls.append(("bars", market, interval, start, end))
        return bars

    def load_funding(symbol, data_dir, *, start, end):
        calls.append(("funding", symbol, start, end))
        return funding
    monkeypatch.setattr(fas2.binance, "load", load)
    monkeypatch.setattr(fas2.binance, "load_funding", load_funding)
    fas2.load_development("unused")
    assert [c[-1] for c in calls] == [UTC("2025-01-01")] * 2
    assert [c[-2] for c in calls] == [UTC("2020-01-01")] * 2
    assert calls[0][1:3] == ("um", "4h")


def test_real_archive_reader_never_opens_holdout_files(tmp_path):
    folder = tmp_path / "raw" / "binance" / "um" / "BTCUSDT" / "4h"
    folder.mkdir(parents=True)
    for month in ("2024-12", "2025-01"):
        (folder / f"BTCUSDT-4h-{month}.zip").write_bytes(b"not a zip")
    picked = fas2.binance._bounded_files(sorted(folder.glob("*.zip")), UTC("2020-01-01"), UTC("2025-01-01"))
    assert [p.name for p in picked] == ["BTCUSDT-4h-2024-12.zip"]


# Slutprovsskydd i varje publik ingång

@pytest.fixture
def no_compute(monkeypatch):
    """Varje beräkning efter kontrollen ska vara oanropad när indata avvisas."""
    def fail(*a, **k):
        raise AssertionError("beräkningen anropades trots förbjudna indata")
    for target, name in ((fas2.regime, "daily"), (fas2.regime, "per_bar"), (fas2.adaptive, "signals"),
                         (fas2.backtest, "run"), (fas2.stats, "daily_returns")):
        monkeypatch.setattr(target, name, fail)


def holdout_bars():
    return make_bars(12, interval="4h", seed=9, start="2025-01-01")  # 2025-01-01 och 2025-01-02, som i granskningen


@pytest.fixture(scope="module")
def short_dev():
    bars = make_bars(400 * 6, interval="4h", seed=3, vol=0.015)
    return bars, funding_for(bars)


def entries(bars, funding, effective=None, start="2023-01-01", end="2023-07-01"):
    return {
        "check_development": lambda: fas2.check_development(bars, funding, start, end, effective),
        "regime_stats": lambda: fas2.regime_stats(bars, funding, BB, effective=effective),
        "train": lambda: fas2.train(bars, funding, end),
        "evaluate_window": lambda: fas2.evaluate_window(bars, funding, ALL_BB, start, end),
        "walk_forward": lambda: fas2.walk_forward(bars, funding),
    }


@pytest.mark.parametrize("entry", ["check_development", "regime_stats", "train", "evaluate_window", "walk_forward"])
@pytest.mark.parametrize("case", ["holdout_bars", "holdout_funding", "early_bars", "early_funding", "naive_index"])
def test_every_entry_rejects_forbidden_data_before_computing(short_dev, no_compute, entry, case):
    bars, funding = short_dev
    if case == "holdout_bars":
        bars = pd.concat([bars, holdout_bars()])
    elif case == "holdout_funding":
        funding = pd.concat([funding, funding_for(holdout_bars())])
    elif case == "early_bars":
        bars = pd.concat([make_bars(6, interval="4h", seed=9, start="2019-12-31"), bars])
    elif case == "early_funding":
        funding = pd.concat([pd.Series(0.0001, index=[UTC("2019-12-31 16:00")]), funding])
    else:
        bars = bars.tz_convert(None)
    with pytest.raises(ValueError, match="slutprovet|före|UTC"):
        entries(bars, funding)[entry]()


def test_supplied_daily_labels_from_the_holdout_are_rejected(short_dev, no_compute):
    bars, funding = short_dev
    labels = pd.Series("upp/låg vol", index=pd.date_range("2020-01-01", "2025-01-01", freq="D", tz="UTC"), dtype=object)
    with pytest.raises(ValueError, match="Dagslägena når slutprovet"):
        fas2.regime_stats(bars, funding, BB, effective=labels)


@pytest.mark.parametrize("call, match", [
    (lambda b, f: fas2.train(b, f, "2025-01-03"), "utanför"),           # granskningens prov
    (lambda b, f: fas2.train(b, f, "2020-01-01"), "före slutet"),
    (lambda b, f: fas2.train(b, f, "2019-06-01"), "utanför"),
    (lambda b, f: fas2.evaluate_window(b, f, ALL_BB, "2025-01-01", "2025-01-03"), "utanför"),  # granskningens prov
    (lambda b, f: fas2.evaluate_window(b, f, ALL_BB, "2024-12-01", "2025-01-02"), "utanför"),
    (lambda b, f: fas2.evaluate_window(b, f, ALL_BB, "2019-12-01", "2020-06-01"), "utanför"),
    (lambda b, f: fas2.evaluate_window(b, f, ALL_BB, "2023-07-01", "2023-01-01"), "före slutet"),
    (lambda b, f: fas2.evaluate_window(b, f, ALL_BB, "2023-01-01", "2023-01-01"), "före slutet"),
])
def test_forbidden_periods_are_rejected_before_computing(short_dev, no_compute, call, match):
    with pytest.raises(ValueError, match=match):
        call(*short_dev)


def test_holdout_data_passed_with_an_allowed_period_is_still_rejected(short_dev, no_compute):
    bars, funding = short_dev
    with pytest.raises(ValueError, match="slutprovet"):
        fas2.evaluate_window(pd.concat([bars, holdout_bars()]), funding, ALL_BB, "2021-01-01", "2021-02-01")
    with pytest.raises(ValueError, match="slutprovet"):
        fas2.train(pd.concat([bars, holdout_bars()]), funding, "2021-01-01")


# Gemensam kapitalbas

def fake_window(local_return, cost, fund):
    """Ett fönster med känt utfall på lokalt startkapital 1,0: en affär vars nettoresultat är hela avkastningen."""
    def evaluate(bars, funding, book, start, end, costs=fas2.COSTS):
        a = fas2._ts(start)
        idx = pd.DatetimeIndex([a, a + pd.Timedelta(hours=4)])
        eq = pd.Series([1.0, 1.0 + local_return], index=idx)
        trade = backtest.Trade(entry_time=idx[0], entry_price=100.0, side="Long", size=1.0, equity_at_entry=1.0,
                               exit_time=idx[1], exit_price=100.0 * (1 + local_return), gross_pnl=local_return + cost + fund,
                               costs=cost, funding=fund, exit_reason="signal")
        res = backtest.BacktestResult(equity=eq, position=pd.Series(0.0, index=idx), trades=[trade],
                                      total_costs=cost, total_funding=fund)
        return res, {"test": [str(a.date()), str(fas2._ts(end).date())], "per_regime": {}, "trades": 1,
                     "local_return": local_return, "local_costs": cost, "local_funding": fund}
    return evaluate


@pytest.fixture
def stitched(monkeypatch, short_dev):
    trained = {"train": ["2020-01-01", "x"], "playbook": ALL_BB.to_dict(), "playbook_id": ALL_BB.id, "candidates": {}}
    monkeypatch.setattr(fas2, "train", lambda *a, **k: dict(trained))

    def run(returns, cost=0.01, fund=0.02):
        it = iter(returns)
        monkeypatch.setattr(fas2, "evaluate_window", lambda *a, **k: fake_window(next(it), cost, fund)(*a, **k))
        return fas2.walk_forward(*short_dev)
    return run


def test_review_example_six_windows_doubling(stitched):
    wf = stitched([1.0] * 6)
    assert wf.equity.iloc[-1] == pytest.approx(64.0)
    assert wf.total_costs == pytest.approx(0.63)
    assert wf.total_funding == pytest.approx(1.26)
    assert sum(t.net_pnl for t in wf.trades) == pytest.approx(63.0)


@pytest.mark.parametrize("returns", [[1.0, -0.5, 0.2, 0.0, 0.1, -0.3], [-0.2, -0.2, 0.5, 0.5, -0.4, 0.05]])
def test_amounts_follow_the_capital_at_each_window_start(stitched, returns):
    wf = stitched(returns, cost=0.003, fund=-0.001)
    capital = np.cumprod([1.0] + [1 + r for r in returns])
    assert [w["capital_start"] for w in wf.windows] == pytest.approx(list(capital[:-1]))
    assert [w["capital_end"] for w in wf.windows] == pytest.approx(list(capital[1:]))
    assert wf.equity.iloc[-1] == pytest.approx(capital[-1])
    assert sum(t.net_pnl for t in wf.trades) == pytest.approx(capital[-1] - 1)
    assert wf.total_costs == pytest.approx(0.003 * capital[:-1].sum())
    assert wf.total_funding == pytest.approx(-0.001 * capital[:-1].sum())
    for t, c in zip(wf.trades, capital[:-1]):
        assert t.equity_at_entry == pytest.approx(c) and t.entry_price == 100.0 and t.size == 1.0
    assert [w["local_costs"] for w in wf.windows] == [0.003] * 6
    assert "capital_base" in wf.config


def test_real_non_flat_walk_forward_reconciles_trades_with_the_curve(wf_bb):
    local = [w["local_return"] for w in wf_bb.windows]
    assert len(set(round(r, 9) for r in local)) > 1, "windows have different capital development"
    assert sum(t.net_pnl for t in wf_bb.trades) == pytest.approx(wf_bb.equity.iloc[-1] - 1)
    for w in wf_bb.windows:
        inside = wf_bb.returns[(wf_bb.returns.index >= UTC(w["test"][0])) & (wf_bb.returns.index < UTC(w["test"][1]))]
        assert (1 + inside).prod() == pytest.approx(1 + w["local_return"])
    starts = [w["capital_start"] for w in wf_bb.windows]
    assert starts[0] == 1.0 and starts[1:] == pytest.approx([w["capital_end"] for w in wf_bb.windows[:-1]])
