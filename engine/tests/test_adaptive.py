"""Strategiväljaren för Fas 2 (H-0013) på syntetisk data: kontrakt, riktning, byten, tidpunkter och ingen framtidsdata."""
import numpy as np
import pandas as pd
import pytest

from traderlab import adaptive, backtest, regime
from traderlab.costs import ZERO
from traderlab.strategies.rules import SPECS
from traderlab.synthetic import from_closes, make_bars

EMA, BB, FLAT = "ema_adx_trend", "bb_rsi_reversion", adaptive.FLAT
UP_HI, UP_LO, DN_HI, DN_LO = regime.LABELS
BPD = 6  # 4h-staplar per dag


def book(**kw):
    """Spelbok med EMA i alla lägen, utom de som anges (nycklar uh, ul, dh, dl)."""
    keys = {"uh": UP_HI, "ul": UP_LO, "dh": DN_HI, "dl": DN_LO}
    choices = {label: EMA for label in regime.LABELS}
    choices.update({keys[k]: v for k, v in kw.items()})
    return adaptive.Playbook.of(choices)


def bars_for(days):
    return from_closes([100.0 + (i % 7) for i in range(days * BPD)], start="2021-01-01")


def eff(labels):
    """Gällande dagsläge, med första värdet för 2020-12-31 (det läge som gäller staplarna 1 januari)."""
    return pd.Series(labels, index=pd.date_range("2020-12-31", periods=len(labels), freq="D", tz="UTC"), dtype=object)


@pytest.fixture
def fake(monkeypatch):
    """Ersätter kandidaternas signaler med handskrivna, så att väljarens regler kan prövas exakt."""
    state = {}

    def install(ema=None, bb=None, stop=5.0):
        def candidate_signals(bars):
            n = len(bars)
            pad = lambda s: np.array((list(s) + [s[-1]] * n)[:n] if s else [0.0] * n, dtype=float)
            return {EMA: (pad(ema or []), np.full(n, stop)), BB: (pad(bb or []), np.full(n, stop))}
        monkeypatch.setattr(adaptive, "candidate_signals", candidate_signals)
        state["on"] = True
    return install


def run(days, labels, schedule, **kw):
    return adaptive.signals(bars_for(days), schedule, effective=eff(labels), **kw)


# Kontraktet

def test_contract_round_trip_and_stable_ids():
    pb = book(ul=BB, dh=FLAT)
    data = pb.to_dict()
    assert data["contract"] == adaptive.CONTRACT_VERSION == "h0013-adaptive/1.0.0"
    assert data["candidates"] == {EMA: "1.0.0", BB: "1.0.0", FLAT: None}
    assert adaptive.Playbook.from_dict(data) == pb and adaptive.Playbook.from_dict(data).id == pb.id
    books = adaptive.all_playbooks()
    assert len(books) == 81 and len({b.id for b in books}) == 81


@pytest.mark.parametrize("change, match", [
    ({"contract": "h0013-adaptive/2.0.0"}, "kontraktsversion"),
    ({"candidates": {EMA: "1.1.0"}}, "låst version"),
])
def test_contract_rejects_other_versions(change, match):
    with pytest.raises(ValueError, match=match):
        adaptive.Playbook.from_dict({**book().to_dict(), **change})


def test_playbook_needs_exactly_the_four_regimes_and_known_candidates():
    with pytest.raises(ValueError, match="exakt ett val"):
        adaptive.Playbook.of({UP_HI: EMA})
    with pytest.raises(ValueError, match="exakt ett val"):
        adaptive.Playbook.of({**{l: EMA for l in regime.LABELS}, regime.UNKNOWN: EMA})
    with pytest.raises(ValueError, match="Okända kandidater"):
        adaptive.Playbook.of({**{l: EMA for l in regime.LABELS}, UP_HI: "donchian_breakout"})


def test_schedule_must_be_utc_and_increasing(fake):
    fake()
    with pytest.raises(ValueError, match="UTC"):
        run(3, [UP_HI] * 4, [(pd.Timestamp("2021-01-02"), book())])
    with pytest.raises(ValueError, match="stigande"):
        run(3, [UP_HI] * 4, [(pd.Timestamp("2021-01-02", tz="UTC"), book()), (pd.Timestamp("2021-01-02", tz="UTC"), book())])


# Kandidater och riktning

@pytest.mark.parametrize("label", list(regime.LABELS) + [regime.UNKNOWN])
@pytest.mark.parametrize("name", [EMA, BB, FLAT])
@pytest.mark.parametrize("side", [1.0, -1.0])
def test_every_regime_candidate_and_side(fake, label, name, side):
    # Kandidaten är platt i två staplar efter bytet och går sedan in. Bara tillåten riktning blir en position.
    fake(ema=[0, 0, 0, side] if name == EMA else [0], bb=[0, 0, 0, side] if name == BB else [0])
    choices = {l: FLAT for l in regime.LABELS}
    if label in choices:
        choices[label] = name
    sig = run(2, [label] * 3, adaptive.Playbook.of(choices))
    allowed = {UP_HI: 1, UP_LO: 1, DN_HI: -1, DN_LO: -1}.get(label, 0)
    expected = side if (name != FLAT and side == allowed) else 0.0
    assert sig.target.iloc[0] == 0.0
    assert (sig.target.iloc[3:] == expected).all()
    assert (sig.candidate == (FLAT if label == regime.UNKNOWN else name)).all()


def test_unknown_is_always_flat_even_if_the_book_would_trade(fake):
    fake(ema=[0, 1] + [1] * 20)
    sig = run(2, [regime.UNKNOWN] * 3, book())
    assert (sig.target == 0).all() and (sig.candidate == FLAT).all()


def test_signal_against_the_trend_is_flat_and_opposite_to_allowed_is_a_new_entry(fake):
    fake(ema=[0, -1, -1, -1, 1, 1, 0, 1])
    sig = run(2, [UP_LO] * 3, book())
    assert list(sig.target.iloc[:8]) == [0, 0, 0, 0, 1, 1, 0, 1]


def test_exit_when_the_candidate_exits_or_flips(fake):
    fake(ema=[0, 0, -1, -1, 0, 0, -1, 1, 1])
    sig = run(2, [DN_HI] * 3, book())
    assert list(sig.target.iloc[:9]) == [0, 0, -1, -1, 0, 0, -1, 0, 0]


# Byten

def test_regime_switch_closes_at_next_open_and_old_trade_is_not_resumed(fake):
    # Long i upp/låg vol dag 1. Läget för dag 2 är upp/hög vol (samma kandidat, samma riktning).
    fake(ema=[0, 1] + [1] * 20 + [0, 1, 1, 1])
    sig = run(5, [UP_LO, UP_HI, UP_HI, UP_HI, UP_HI, UP_HI], book())
    last_bar_day1 = BPD - 1  # 20:00 den 1 januari: beslutet gäller 00:00 den 2 januari, nytt läge
    assert sig.target.iloc[1:last_bar_day1].eq(1).all()
    assert sig.switch.iloc[last_bar_day1] and sig.regime.iloc[last_bar_day1] == UP_HI
    assert sig.regime.iloc[last_bar_day1 - 1] == UP_LO
    assert (sig.target.iloc[last_bar_day1:22] == 0).all(), "signal still long, but the old trade is not resumed"
    assert sig.target.iloc[23] == 1, "a new entry signal (0 -> 1) opens a new trade"


def test_entry_signal_on_the_switch_bar_itself_waits_for_a_new_one(fake):
    s = BPD - 1
    fake(ema=[0] * s + [1] * 10 + [0, 1])
    sig = run(3, [DN_LO, UP_LO, UP_LO, UP_LO], book())
    assert sig.switch.iloc[s]
    assert (sig.target.iloc[: s + 11] == 0).all()
    assert sig.target.iloc[s + 11] == 1


def test_new_playbook_with_another_candidate_at_a_window_boundary_closes(fake):
    fake(ema=[0, 1] + [1] * 40, bb=[0, 1] + [1] * 40)
    boundary = pd.Timestamp("2021-01-03 00:00", tz="UTC")
    sig = run(5, [UP_HI] * 6, [(pd.Timestamp("2021-01-01", tz="UTC"), book()), (boundary, book(uh=BB))])
    k = 2 * BPD - 1  # 20:00 den 2 januari, beslutet gäller stapeln vid gränsen
    assert sig.target.iloc[1:k].eq(1).all() and sig.candidate.iloc[k - 1] == EMA
    assert sig.switch.iloc[k] and sig.candidate.iloc[k] == BB
    assert (sig.target.iloc[k:] == 0).all(), "bb's old long is not taken over at the boundary"


def test_new_playbook_with_the_same_candidate_keeps_the_position(fake):
    fake(ema=[0, 1] + [1] * 40)
    boundary = pd.Timestamp("2021-01-03 00:00", tz="UTC")
    sig = run(5, [UP_HI] * 6, [(pd.Timestamp("2021-01-01", tz="UTC"), book()), (boundary, book(dl=BB))])
    assert not sig.switch.any()
    assert sig.target.iloc[1:].eq(1).all()
    assert sig.playbook.iloc[0] != sig.playbook.iloc[-1]


def test_bars_before_the_first_playbook_are_flat(fake):
    fake(ema=[0, 1] + [1] * 40)
    sig = run(3, [UP_HI] * 4, [(pd.Timestamp("2021-01-02 00:00", tz="UTC"), book())])
    assert (sig.playbook.iloc[: BPD - 1] == adaptive.NO_PLAYBOOK).all()
    assert (sig.target == 0).all(), "candidate was already long when the playbook started"


# Tidpunkter i backtestet: beslut på stängd stapel, fyllning vid nästa öppning, ATR-stop vid inträdet

def test_fill_at_next_open_stop_at_entry_and_close_at_switch(fake):
    closes = [100.0 + i for i in range(4 * BPD)]
    bars = from_closes(closes, start="2021-01-01")
    fake(ema=[0, 0, 1] + [1] * 30, stop=3.0)
    labels = eff([UP_LO, DN_LO, DN_LO, DN_LO, DN_LO])
    sig = adaptive.signals(bars, book(), effective=labels)
    res = backtest.run(bars, sig.target, ZERO, stop_distance=sig.stop_distance)
    first = res.trades[0]
    assert first.entry_time == bars.index[3] and first.entry_price == bars["open"].iloc[3]
    assert first.stop_price == pytest.approx(bars["open"].iloc[3] - 3.0)
    # Läget för 2 januari är ned/låg vol: stängs vid öppningen 00:00 den 2 januari, ingen short av gammal signal.
    assert first.exit_time == pd.Timestamp("2021-01-02 00:00", tz="UTC") and first.exit_reason == "signal"
    assert len(res.trades) == 1


def test_stop_exit_is_not_reopened_until_a_new_entry_signal(fake):
    opens = [100, 100, 100, 100, 90, 95, 96, 97, 98, 99, 100, 101] + [102] * 6
    bars = pd.DataFrame({"open": opens, "high": [o + 1 for o in opens], "low": [o - 1 for o in opens],
                         "close": opens, "volume": 1.0},
                        index=pd.date_range("2021-01-01", periods=len(opens), freq="4h", tz="UTC")).astype(float)
    fake(ema=[0, 0, 1, 1, 1, 1, 1, 0, 1] + [1] * 20, stop=5.0)
    sig = adaptive.signals(bars, book(), effective=eff([UP_LO] * 5))
    res = backtest.run(bars, sig.target, ZERO, stop_distance=sig.stop_distance)
    assert res.trades[0].entry_time == bars.index[3] and res.trades[0].exit_reason == "stop"
    assert res.trades[0].exit_time == bars.index[4]
    assert res.trades[1].entry_time == bars.index[9], "re-entered only after the new 0 -> 1 signal"


# Ingen framtidsdata, och oförändrade delar

@pytest.fixture(scope="module")
def real():
    return make_bars(500 * BPD, interval="4h", seed=5, vol=0.02)


@pytest.mark.parametrize("cut_day", [210, 260.5, 333, 420.83, 499])
def test_future_bars_never_change_earlier_decisions(real, cut_day):
    cut = int(cut_day * BPD)
    pb = book(ul=BB, dh=FLAT)
    full, prefix = adaptive.signals(real, pb), adaptive.signals(real.iloc[:cut], pb)
    for field in ("target", "stop_distance", "regime", "candidate", "switch"):
        pd.testing.assert_series_equal(getattr(prefix, field), getattr(full, field).iloc[:cut])


def test_positions_follow_the_trend_and_unknown_is_flat_on_real_regimes(real):
    sig = adaptive.signals(real, book())
    assert (sig.target[sig.regime.str.startswith("upp/")] >= 0).all()
    assert (sig.target[sig.regime.str.startswith("ned/")] <= 0).all()
    assert (sig.target[sig.regime == regime.UNKNOWN] == 0).all()
    assert (sig.target != 0).any()
    # Läget för beslutet är exakt läget för nästa stapel enligt regimmodulen.
    nxt = pd.DataFrame(index=real.index + pd.Timedelta(hours=4))
    pd.testing.assert_series_equal(sig.regime, regime.per_bar(nxt, regime.daily(real)).set_axis(real.index),
                                   check_names=False)


def test_candidates_are_the_unchanged_frozen_strategies(real):
    assert {k: SPECS[k].version for k in (EMA, BB)} == {EMA: "1.0.0", BB: "1.0.0"}
    assert SPECS[EMA].defaults == {"fast": 50, "slow": 200, "adx_n": 14, "adx_min": 20.0, "atr_n": 14, "stop_atr": 3.0}
    assert SPECS[BB].defaults == {"bb_n": 20, "bb_k": 2.0, "rsi_n": 14, "rsi_low": 30.0, "atr_n": 14, "stop_atr": 2.0}
    cand = adaptive.candidate_signals(real)
    for name in (EMA, BB):
        own = SPECS[name].signals(real)
        np.testing.assert_array_equal(cand[name][0], own.target.to_numpy(float))
        np.testing.assert_array_equal(cand[name][1], own.stop_distance.to_numpy(float))
    sig = adaptive.signals(real, book())
    assert dict(sig.candidate_runs) == {EMA: SPECS[EMA].run_id({}), BB: SPECS[BB].run_id({})}


def test_flat_playbook_never_trades(real):
    sig = adaptive.signals(real, adaptive.Playbook.of({l: FLAT for l in regime.LABELS}))
    assert (sig.target == 0).all() and sig.stop_distance.isna().all()
