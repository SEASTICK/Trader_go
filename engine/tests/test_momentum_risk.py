"""mom-risk/1.0.0 (H-0017 leverans C3) på syntetiska konton och signaler. Ingen marknadshistorik, ingen eventloop.

Facit från docs/momentum-a1-orakel.json och handräkning; gränsfall konstrueras med math.nextafter så att exakt
float-beteende utan epsilon prövas.
"""
import dataclasses
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from traderlab import momentum_funding as F
from traderlab import momentum_ledger as L
from traderlab import momentum_risk as R
from traderlab import momentum_signal as S

ORACLE = json.loads((Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())
T0 = pd.Timestamp("2022-01-01", tz="UTC")
H = R.BAR


def sig(T, s, cap):
    return R.SignalInput(day=T - pd.Timedelta(days=1), decision_time=T, available=True, s=s, cap=cap,
                         w_target=s * cap, version=S.VERSION)


def acct_w(w, E=100_000.0, M=100.0):
    """Konto med vikt w vid markpris M och kapital E (konsekvent avstämning)."""
    q = w * E / M
    return L.Account(C=E - q * M, q=q, deposit=E, avg_price=M if q else 0.0)


def state_at(T, peak=100_000.0, day_start=100_000.0, **kw):
    """Tillstånd mitt i körningen, redo för gränsen T."""
    return R.RiskState(initial=100_000.0, peak=peak, day_start=day_start, next_boundary=T, started=True,
                       last_decision_day=None, **kw)


def close_at(T, acct, M=100.0, **kw):
    return R.CloseInput(T - H, acct, M, **kw)


def first_step(s=1.0, cap=0.5):
    return R.step(R.RiskState.start(100_000, T0), T0, None, sig(T0, s, cap))


def test_version_and_thresholds():
    assert R.VERSION == "mom-risk/1.0.0"
    assert (R.BAND, R.DAY_STOP, R.PERMANENT_STOP) == (0.02, -0.02, -0.15)
    assert R.PRIORITY[:3] == (R.TERMINAL, R.PERMANENT, R.DAY) and R.PRIORITY[-1] == R.NORMAL


def test_first_boundary_decides_from_previous_day_and_keeps_start_capital():
    st, rec = first_step(2 / 3, 0.6)
    assert rec.daily_decision == R.NORMAL and rec.intent.kind == R.NORMAL and rec.intent.w == (2 / 3) * 0.6
    assert rec.intent.fill_time == T0 == rec.intent.decision_time and rec.source_bar is None
    assert rec.intent.mark_decision is None and rec.intent.E_decision == 100_000
    assert st.day_start == 100_000 and st.peak == 100_000 and st.next_boundary == T0 + H


# Handelsband: exakt float utan epsilon.

def _band_case(w_cur, s, cap):
    T = T0 + pd.Timedelta(days=3)
    acct = acct_w(w_cur)
    c = acct.q * 100.0 / acct.equity(100.0)
    _, rec = R.step(state_at(T), T, close_at(T, acct), sig(T, s, cap))
    return c, rec


def _first_true(f, x, direction):
    """Grannfloats (sann, falsk) kring gränsen för f nära x. direction pekar från det falska mot det sanna området."""
    away = -direction
    prev = x
    for _ in range(100_000):
        nxt = math.nextafter(prev, direction if not f(prev) else away)
        if f(nxt) != f(prev):
            return (nxt, prev) if f(nxt) else (prev, nxt)
        prev = nxt
    raise AssertionError("ingen gräns hittad")


def test_band_upwards_at_exact_float_boundary():
    c = acct_w(0.3).q * 100.0 / acct_w(0.3).equity(100.0)
    on, under = _first_true(lambda cap: abs(1.0 * cap - c) >= 0.02, c + 0.02, math.inf)
    assert abs(on - c) >= 0.02 > abs(under - c)
    _, rec_on = _band_case(0.3, 1.0, on)
    _, rec_under = _band_case(0.3, 1.0, under)
    _, rec_over = _band_case(0.3, 1.0, 0.33)
    assert rec_on.intent.kind == R.NORMAL and rec_over.intent.kind == R.NORMAL
    assert rec_under.daily_decision == R.HOLD and rec_under.intent is None
    print("band uppåt: c =", repr(c), "på", repr(on), "diff", repr(on - c), "under", repr(under), "diff", repr(under - c))


def test_band_downwards_at_exact_float_boundary():
    acct = acct_w(0.3)
    c = acct.q * 100.0 / acct.equity(100.0)
    target = lambda cap: (1 / 3) * cap                    # s = 1/3 så att cap >= w_current och inget capbrott
    on, under = _first_true(lambda cap: abs(target(cap) - c) >= 0.02, 3 * (c - 0.02), -math.inf)
    assert on >= c and under >= c
    _, rec_on = _band_case(0.3, 1 / 3, on)
    _, rec_under = _band_case(0.3, 1 / 3, under)
    _, rec_over = _band_case(0.3, 1 / 3, 0.75)
    assert rec_on.intent.kind == R.NORMAL and rec_on.intent.w == target(on)
    assert rec_under.daily_decision == R.HOLD and rec_over.intent.kind == R.NORMAL
    print("band nedåt: c =", repr(c), "mål", repr(target(on)), "diff", repr(c - target(on)), "under", repr(c - target(under)))


# Stopp: exakt float utan epsilon.

def _close_flat(T, E, state):
    return R.step(state, T, close_at(T, L.Account(C=E, q=0.0, deposit=100_000.0)), None)


def test_permanent_stop_at_exact_float_boundary():
    T = T0 + pd.Timedelta(days=2, hours=8)
    on, above = _first_true(lambda E: E / 100_000.0 - 1 <= -0.15, 85_000.0, -math.inf)
    st_on, rec_on = _close_flat(T, on, state_at(T, day_start=on))
    st_above, rec_above = _close_flat(T, above, state_at(T, day_start=above))
    assert rec_on.permanent_triggered and st_on.permanent and st_on.permanent_time == T
    assert not rec_above.permanent_triggered and not st_above.permanent
    print("permanent: på", repr(on), repr(on / 1e5 - 1), "ovanför", repr(above), repr(above / 1e5 - 1))


def test_day_stop_at_exact_float_boundary_uses_day_start():
    T = T0 + pd.Timedelta(days=2, hours=8)
    base = 101_000.0
    on, above = _first_true(lambda E: E / base - 1 <= -0.02, base * 0.98, -math.inf)
    st_on, rec_on = _close_flat(T, on, state_at(T, peak=110_000.0, day_start=base))
    st_above, rec_above = _close_flat(T, above, state_at(T, peak=110_000.0, day_start=base))
    assert rec_on.day_stop_triggered and st_on.lock_day == T0 + pd.Timedelta(days=2)
    assert rec_on.day_start_used == base and not rec_above.day_stop_triggered and st_above.lock_day is None
    print("dagsstopp: på", repr(on), repr(on / base - 1), "ovanför", repr(above), repr(above / base - 1))


def test_peak_updates_from_initial_and_includes_funding_through_account():
    T = T0 + H
    st, _ = first_step(1.0, 0.5)
    acct, _ = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    paid, _, rec_f = F.apply_funding(acct, F.FundingState("main", "A"), F.FundingEvent("f", T0 + pd.Timedelta(hours=1),
                                     0.001, 100.0, F.MARK_OPEN, T0), "funding_interior")
    st2, rec = R.step(st, T, close_at(T, paid, 110.0), None)
    assert rec.E_close == paid.equity(110.0) and rec.E_close == pytest.approx(acct.equity(110.0) - rec_f.payment)
    assert st2.peak == rec.E_close > 100_000                  # funding räknas en gång, via kontot
    st3, rec3 = R.step(st2, T + H, close_at(T + H, paid, 105.0), None)
    assert st3.peak == st2.peak and rec3.drawdown == pytest.approx(paid.equity(105.0) / st2.peak - 1)


# Dagsbeslut: prioritet.

@pytest.mark.parametrize("w_cur,s,cap,expected,w", [
    (0.505, 1.0, 0.5, R.CAP, 0.5),            # capbrott trots bandavstånd 0,005
    (0.01, 0.0, 0.5, R.FLAT, 0.0),            # platt signal trots bandavstånd 0,01
    (0.0, 0.0, 0.5, R.HOLD, None),            # platt signal utan position
    (0.0, 1.0, 0.01, R.HOLD, None),           # utan position: inget capbrott, bandavstånd 0,01
    (0.7, 0.0, 0.5, R.FLAT, 0.0),             # platt och capbrott samtidigt: platt först enligt §7
    (0.45, 2 / 3, 0.69, R.HOLD, None),        # mål 0,46: inom bandet, under cap
])
def test_daily_decision_priority(w_cur, s, cap, expected, w):
    c, rec = _band_case(w_cur, s, cap)
    assert rec.daily_decision == expected
    if w is None:
        assert rec.intent is None
    else:
        assert rec.intent.kind == expected and rec.intent.risk and rec.intent.w == w


def test_merge_priority_terminal_permanent_day_cap():
    T = T0 + pd.Timedelta(days=3)
    acct = acct_w(0.7, E=84_000.0)                           # dd -16 %, dag -16 %, capbrott vid cap 0,5
    st = state_at(T, peak=100_000.0, day_start=100_000.0)
    _, rec = R.step(st, T, close_at(T, acct), sig(T, 1.0, 0.5))
    assert rec.candidates == (R.PERMANENT, R.DAY) and rec.intent.kind == R.PERMANENT and rec.intent.w == 0
    assert (R.DAY, "strykt av permanent_stop") in rec.suppressed
    Tt = pd.Timestamp("2024-12-31 20:00", tz="UTC")
    _, rec_t = R.step(state_at(Tt, peak=100_000.0, day_start=100_000.0), Tt, close_at(Tt, acct), None, terminal=True)
    assert rec_t.intent.kind == R.TERMINAL and rec_t.candidates[0] == R.TERMINAL
    st2, rec2 = R.step(state_at(T, peak=100_000.0, day_start=90_000.0), T, close_at(T, acct_w(0.7, E=88_000.0)),
                       sig(T, 1.0, 0.5))
    assert rec2.intent.kind == R.DAY and (R.CAP, "strykt av day_stop") in rec2.suppressed


def test_terminal_ends_the_account():
    Tt = pd.Timestamp("2024-12-31 20:00", tz="UTC")
    st, _ = R.step(state_at(Tt), Tt, close_at(Tt, acct_w(0.3)), None, terminal=True)
    assert st.terminated
    with pytest.raises(R.RiskError, match="terminal"):
        R.step(st, Tt + H, close_at(Tt + H, acct_w(0.0)), sig(Tt + H, 1.0, 0.5))


# Dagsreset och lock_day.

def test_O6_day_stop_at_last_close_keeps_risk_exit_over_reset():
    o = ORACLE["O6_dagsreset"]
    T = T0 + pd.Timedelta(days=5)                            # D+1 00:00
    acct = L.Account(C=50_000.0, q=1000.0, deposit=100_000.0, avg_price=50.0)
    st, rec = R.step(state_at(T, day_start=100_000.0), T, close_at(T, acct, 47.9), sig(T, 1.0, 0.6))
    assert rec.E_close == o["E_close_D"] and rec.day_return == pytest.approx(o["dagsavkastning_D"])
    assert rec.day_stop_triggered and rec.candidates == (R.DAY, R.NORMAL)
    assert rec.intent.kind == R.DAY and (R.NORMAL, "strykt av day_stop") in rec.suppressed
    assert st.day_start == o["day_start_D1"] and st.lock_day == T - pd.Timedelta(days=1)
    assert rec.intent.mark_decision == 47.9 and rec.intent.w_current == pytest.approx(o["vikt_vid_beslut"])
    # Scenario A vid 00:00: funding på q före affären, sedan riskutträdet vid kontraktsöppning 47,55 och mark 47,5.
    a1, _, fr = F.apply_funding(acct, F.FundingState("main", "A"), F.FundingEvent("f", T, 0.0001, 47.5, F.MARK_OPEN, T),
                                "funding_A")
    a2, fill = R.fill_intent(a1, rec.intent, 47.55, 47.5)
    assert fr.payment == o["A"]["funding"] and fill.cost == pytest.approx(o["A"]["kostnad"])
    assert a2.equity(47.5) == pytest.approx(o["A"]["E_efter"]) and a2.q == 0
    # Gap och funding efter midnatt flyttar inte day_start bakåt.
    st2, rec2 = R.step(st, T + H, close_at(T + H, a2, 47.5), None)
    assert rec2.day_start_used == o["day_start_D1"]
    assert rec2.day_return == pytest.approx(o["A"]["dag_D1_hittills"]) and not rec2.day_stop_triggered


def test_day_stop_inside_day_blocks_same_day_and_lapses_next_day():
    D = T0 + pd.Timedelta(days=4)
    T = D + pd.Timedelta(hours=8)                            # close av 04-stapeln
    acct = acct_w(0.5, E=97_000.0)
    st, rec = R.step(state_at(T, day_start=100_000.0), T, close_at(T, acct), None)
    assert rec.intent.kind == R.DAY and st.lock_day == D
    flat = L.Account(C=97_000.0, q=0.0, deposit=100_000.0)
    for k in range(3):                                       # resten av dagen: inga nya avsikter
        st, rec = R.step(st, st.next_boundary, close_at(st.next_boundary, flat), None)
        assert rec.intent is None and st.lock_day == D
    Tm = D + pd.Timedelta(days=1)
    st, rec = R.step(st, Tm, close_at(Tm, flat), sig(Tm, 1.0, 0.5))
    assert rec.intent.kind == R.NORMAL and rec.intent.fill_time.floor("D") != st.lock_day
    assert st.day_start == 97_000.0


def test_normal_intent_on_lock_day_is_suppressed():
    # Kan bara inträffa om en normalavsikt skulle fyllas samma dag som låset; konstruerat direkt.
    Tm = T0 + pd.Timedelta(days=4)
    st = state_at(Tm, lock_day=Tm)
    _, rec = R.step(st, Tm, close_at(Tm, L.Account(C=100_000.0, q=0.0, deposit=100_000.0)), sig(Tm, 1.0, 0.5))
    assert rec.intent is None and (R.NORMAL, "fyllningsdagen är lock_day") in rec.suppressed


def test_permanent_stop_survives_every_reset():
    T = T0 + pd.Timedelta(days=2, hours=4)
    st, rec = R.step(state_at(T), T, close_at(T, acct_w(0.5, E=84_000.0)), None)
    assert st.permanent and rec.intent.kind == R.PERMANENT
    flat = L.Account(C=84_000.0, q=0.0, deposit=100_000.0)
    for _ in range(6 * 4):
        Tn = st.next_boundary
        st, rec = R.step(st, Tn, close_at(Tn, flat, 100.0), sig(Tn, 1.0, 1.0) if Tn == Tn.floor("D") else None)
        assert st.permanent and rec.intent is None
        if Tn == Tn.floor("D"):
            assert rec.daily_decision == R.HOLD


def test_only_midnight_has_daily_decisions():
    st, _ = first_step(1.0, 0.5)
    acct, _ = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    for k in range(1, 7):
        T = T0 + k * H
        midnight = T == T.floor("D")
        st, rec = R.step(st, T, close_at(T, acct, 100.0), sig(T, 1.0, 0.5) if midnight else None)
        assert (rec.daily_decision is not None) == midnight
    with pytest.raises(R.RiskError, match="Signal"):
        R.step(st, st.next_boundary, close_at(st.next_boundary, acct), sig(st.next_boundary, 1.0, 0.5))


# Komposition med C1: vikt fryses, inte enheter.

def test_risk_intent_never_increases_position_after_gap_O14():
    o = ORACLE["O14_reduce_only"]
    T = T0 + pd.Timedelta(days=6)
    acct = L.Account(C=800.0, q=2.0, deposit=1000.0, avg_price=100.0)
    st = R.RiskState(initial=1000.0, peak=1000.0, day_start=1000.0, next_boundary=T, started=True)
    _, rec = R.step(st, T, close_at(T, acct, 100.0), sig(T, 1.0, 0.195))
    assert rec.intent.kind == R.CAP and rec.intent.w == 0.195 and rec.intent.mark_decision == 100.0
    held, f_down = R.fill_intent(acct, rec.intent, 90, 90)
    assert f_down.risk_reduce_only_hold and held.q == 2 and f_down.cost == 0
    smaller, f_up = R.fill_intent(acct, rec.intent, 110, 110)
    assert f_up.q_new == pytest.approx(o["open_110"]["q"]) and f_up.weight_trade == pytest.approx(0.195)


def test_normal_intent_may_change_direction_after_gap_O15():
    o = ORACLE["O15_normal_efter_gap"]
    T = T0 + pd.Timedelta(days=6)
    acct = L.Account(C=800.0, q=2.0, deposit=1000.0, avg_price=100.0)
    st = R.RiskState(initial=1000.0, peak=1000.0, day_start=1000.0, next_boundary=T, started=True)
    _, rec = R.step(st, T, close_at(T, acct, 100.0), sig(T, 1 / 3, 0.45))
    assert rec.intent.kind == R.NORMAL and rec.intent.w == pytest.approx(0.15) and rec.intent.w_current == 0.2
    new, f = R.fill_intent(acct, rec.intent, 70, 70)          # säljbeslut blir köp efter gap ned
    assert f.dq > 0 and f.q_new == pytest.approx(o["fyllning"]["q"], rel=1e-12)


def test_no_old_normal_intent_returns_after_risk_fill():
    D = T0 + pd.Timedelta(days=5)
    acct = L.Account(C=50_000.0, q=1000.0, deposit=100_000.0, avg_price=50.0)
    st, rec = R.step(state_at(D, day_start=100_000.0), D, close_at(D, acct, 47.9), sig(D, 1.0, 0.6))
    flat, _ = R.fill_intent(acct, rec.intent, 47.55, 47.5)
    for _ in range(5):                                        # resten av D+1 utan dagsbeslut
        st, rec = R.step(st, st.next_boundary, close_at(st.next_boundary, flat, 47.5), None)
        assert rec.intent is None and rec.candidates == ()


# Tid, prefix och indata.

def _run(marks):
    st, rec0 = first_step(1.0, 0.5)
    acct, _ = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    out = [rec0]
    for k, m in enumerate(marks, start=1):
        T = T0 + k * H
        st, rec = R.step(st, T, close_at(T, acct, m), sig(T, 1.0, 0.5) if T == T.floor("D") else None)
        out.append(rec)
    return out


def test_prefix_and_future_changes_keep_earlier_records():
    marks = [100, 99, 98.5, 101, 97, 100.5, 102, 96, 95, 99.5, 100, 101]
    full = _run(marks)
    for k in (3, 6, 9):
        assert _run(marks[:k]) == full[:k + 1]
        changed = marks[:k] + [m * 0.7 for m in marks[k:]]
        assert _run(changed)[:k + 1] == full[:k + 1]


def test_inputs_are_not_modified():
    acct = acct_w(0.3)
    st = state_at(T0 + pd.Timedelta(days=3))
    s = sig(st.next_boundary, 1.0, 0.5)
    copies = (dataclasses.replace(acct), dataclasses.replace(st), dataclasses.replace(s))
    R.step(st, st.next_boundary, close_at(st.next_boundary, acct), s)
    assert (acct, st, s) == copies


def _bad_calls():
    T = T0 + pd.Timedelta(days=3)
    st, a = state_at(T), acct_w(0.3)
    good = dict(state=st, T=T, close=close_at(T, a), signal=sig(T, 1.0, 0.5))
    return T, st, a, good


@pytest.mark.parametrize("case", [
    "duplicate", "skip", "naive", "other_tz", "offgrid", "signal_offday", "signal_unavailable", "signal_mismatch",
    "signal_wrong_day", "missing_signal", "close_bar", "first_with_close", "later_without_close", "decided_twice",
    "negative_q", "nonpositive_E", "bad_state_type", "bad_terminal",
])
def test_invalid_calls_raise_without_change(case):
    T, st, a, good = _bad_calls()
    kw = dict(good)
    if case == "duplicate":
        st2, _ = R.step(**good)
        kw = dict(good, state=st2)
    elif case == "skip":
        kw["T"] = T + H
    elif case == "naive":
        kw["T"] = T.tz_localize(None)
    elif case == "other_tz":
        kw["T"] = T.tz_convert("Etc/GMT-4")
    elif case == "offgrid":
        kw["T"] = T + pd.Timedelta(hours=1)
    elif case == "signal_offday":
        kw = dict(good, state=state_at(T + H), T=T + H, close=close_at(T + H, a))
    elif case == "signal_unavailable":
        kw["signal"] = dataclasses.replace(good["signal"], available=False)
    elif case == "signal_mismatch":
        kw["signal"] = dataclasses.replace(good["signal"], w_target=0.4)
    elif case == "signal_wrong_day":
        kw["signal"] = sig(T + pd.Timedelta(days=1), 1.0, 0.5)
    elif case == "missing_signal":
        kw["signal"] = None
    elif case == "close_bar":
        kw["close"] = R.CloseInput(T - 2 * H, a, 100.0)
    elif case == "first_with_close":
        kw["state"] = R.RiskState.start(100_000, T)
    elif case == "later_without_close":
        kw["close"] = None
    elif case == "decided_twice":
        kw["state"] = dataclasses.replace(st, last_decision_day=T - pd.Timedelta(days=1))
    elif case == "negative_q":
        kw["close"] = close_at(T, L.Account(C=110_000.0, q=-100.0, deposit=100_000.0, avg_price=100.0))
    elif case == "nonpositive_E":
        kw["close"] = close_at(T, L.Account(C=-10_000.0, q=50.0, deposit=100_000.0, avg_price=2200.0))
    elif case == "bad_state_type":
        kw["state"] = "state"
    elif case == "bad_terminal":
        kw["terminal"] = 1
    before = kw["state"]
    with pytest.raises(L.LedgerError):
        R.step(**kw)
    assert kw["state"] == before


@pytest.mark.parametrize("field,value", [("mark_close", math.nan), ("mark_close", math.inf), ("mark_close", 0.0),
                                         ("mark_close", True), ("liquidated", 1)])
def test_invalid_close_inputs(field, value):
    kw = dict(bar_open=T0, account=acct_w(0.3), mark_close=100.0, liquidated=False) | {field: value}
    with pytest.raises(R.RiskError):
        R.CloseInput(**kw)


@pytest.mark.parametrize("kw", [dict(initial=math.nan), dict(peak=math.inf), dict(day_start=0.0), dict(peak=50_000.0),
                                dict(permanent=True), dict(lock_day="2022-01-01"), dict(next_boundary=T0 + pd.Timedelta(minutes=5))])
def test_invalid_states(kw):
    base = dict(initial=100_000.0, peak=100_000.0, day_start=100_000.0, next_boundary=T0)
    with pytest.raises(R.RiskError):
        R.RiskState(**(base | kw))


def test_overflow_in_close_is_controlled():
    T = T0 + H
    st, _ = first_step()
    with pytest.raises(L.LedgerError):
        R.step(st, T, close_at(T, L.Account(C=1e308, q=1e308, deposit=1.0), 10.0), None)


def test_documented_liquidation_is_absorbing_and_unexplained_zero_is_error():
    T = T0 + pd.Timedelta(days=2, hours=4)
    zero = L.Account(C=0.0, q=0.0, deposit=100_000.0)
    with pytest.raises(R.RiskError):
        R.step(state_at(T), T, close_at(T, zero), None)            # noll utan likvidationstillstånd
    st, rec = R.step(state_at(T), T, close_at(T, zero, liquidated=True), None)
    assert st.liquidated and rec.intent is None and rec.E_close is None
    for _ in range(6):
        Tn = st.next_boundary
        st, rec = R.step(st, Tn, close_at(Tn, zero, liquidated=True), None)
        assert rec.intent is None and st.liquidated
    with pytest.raises(R.RiskError):
        R.step(st, st.next_boundary, close_at(st.next_boundary, acct_w(0.2)), None)


def test_signal_from_b_row_is_accepted():
    closes = [100 * (1 + 0.01 * ((-1) ** i)) for i in range(62)]
    from test_momentum_signal import bars_from_daily
    frame = bars_from_daily(closes, start=T0 - pd.Timedelta(days=62))
    row = S.signals(frame).iloc[-1]
    s_in = R.SignalInput.from_row(row)
    T = row["decision_time"]
    assert T == T0
    st, rec = R.step(R.RiskState.start(100_000, T0), T0, None, s_in)
    assert rec.daily_decision in (R.NORMAL, R.HOLD)


def test_band_is_inclusive_at_exactly_two_percentage_points():
    # 0,04 och 0,02 skiljer sig exakt med float(0,02): 0,04 = 2 * 0,02 i binär form.
    assert 0.04 - 0.02 == 0.02
    _, rec_up = _band_case(0.02, 1.0, 0.04)
    assert rec_up.intent.kind == R.NORMAL                    # >= 0,02, inte > 0,02
    cap = 0.06
    while (1 / 3) * cap != 0.02:                             # s = 1/3 ger mål exakt 0,02 utan capbrott
        cap = math.nextafter(cap, math.inf if (1 / 3) * cap < 0.02 else -math.inf)
    assert 0.04 - (1 / 3) * cap == 0.02
    _, rec_down = _band_case(0.04, 1 / 3, cap)
    assert rec_down.intent.kind == R.NORMAL and rec_down.intent.w == 0.02


def test_stop_thresholds_cannot_be_hit_exactly_so_inclusivity_is_unobservable():
    # E/peak - 1 är exakt (Sterbenz) för kvoter i [0,5, 1] och ligger då på rutnätet 2^-53.
    # float(-0,15) och float(-0,02) ligger inte där, så likhet kan aldrig inträffa och <= och < ger samma beslut.
    for threshold in (-0.15, -0.02):
        assert (threshold * 2 ** 53) != int(threshold * 2 ** 53)
    for E, base in ((85_000.0, 100_000.0), (98_980.0, 101_000.0)):
        x = E
        for _ in range(200):
            r = x / base - 1
            assert r not in (-0.15, -0.02)
            x = math.nextafter(x, math.inf)


def test_time_order_check_alone_rejects_duplicate_and_skip():
    T = T0 + pd.Timedelta(days=3, hours=8)                   # ingen midnatt: inget dagsbeslut som också spärrar
    st = state_at(T)
    a = acct_w(0.3)
    st2, _ = R.step(st, T, close_at(T, a), None)
    with pytest.raises(R.RiskError, match="Fel tid"):
        R.step(st2, T, close_at(T, a), None)                 # samma gräns igen, med matchande close
    with pytest.raises(R.RiskError, match="Fel tid"):
        R.step(st, T + H, close_at(T + H, a), None)          # lucka, med matchande close


# Regressioner för Codex granskning av d77e353 (C3-01 och C3-02).

TERM = pd.Timestamp("2024-12-31 20:00", tz="UTC")
ZERO = L.Account(C=0.0, q=0.0, deposit=100_000.0)


def test_terminal_on_already_liquidated_account_gives_no_intent():
    st = state_at(TERM, liquidated=True, day_start=0.0)
    st2, rec = R.step(st, TERM, close_at(TERM, ZERO, liquidated=True), None, terminal=True)
    assert rec.intent is None and rec.candidates == () and st2.terminated and st2.liquidated
    with pytest.raises(R.RiskError, match="terminal"):
        R.step(st2, TERM + H, close_at(TERM + H, ZERO, liquidated=True), None)


def test_liquidation_first_reported_at_terminal_gives_no_intent():
    st2, rec = R.step(state_at(TERM), TERM, close_at(TERM, ZERO, liquidated=True), None, terminal=True)
    assert rec.intent is None and rec.candidates == () and st2.liquidated and st2.terminated


@pytest.mark.parametrize("with_signal", [False, True])
def test_liquidated_state_holds_over_midnight_until_terminal(with_signal):
    T = TERM - pd.Timedelta(days=1)                          # 2024-12-30 20:00
    st, rec = R.step(state_at(T), T, close_at(T, ZERO, liquidated=True), None)
    assert st.liquidated and rec.intent is None
    while True:
        Tn = st.next_boundary
        midnight = Tn == Tn.floor("D")
        signal = sig(Tn, 1.0, 0.5) if (midnight and with_signal) else None
        st, rec = R.step(st, Tn, close_at(Tn, ZERO, liquidated=True), signal, terminal=Tn == TERM)
        assert rec.intent is None and rec.candidates == () and st.liquidated and rec.daily_decision is None
        if Tn == TERM:
            break
    assert st.terminated


def test_live_terminal_still_closes_with_cost():
    acct = acct_w(0.4)
    st2, rec = R.step(state_at(TERM), TERM, close_at(TERM, acct), None, terminal=True)
    assert rec.intent.kind == R.TERMINAL and st2.terminated
    closed, fill = R.fill_intent(acct, rec.intent, 99.0, 99.0)
    assert closed.q == 0 and fill.cost == pytest.approx(L.COST_NORMAL * 99.0 * acct.q)


BAD_AVAILABLE = ["False", "True", 0, 1, None, math.nan, 1.0]
BAD_VERSION = ["mom-signal/999", "mom-signal/1.0", None, 1, b"mom-signal/1.0.0"]


@pytest.mark.parametrize("value", BAD_AVAILABLE)
def test_available_must_be_a_real_bool(value):
    with pytest.raises(R.RiskError, match="available"):
        dataclasses.replace(sig(T0, 1.0, 0.5), available=value)
    with pytest.raises(R.RiskError, match="available"):
        R.SignalInput(T0 - pd.Timedelta(days=1), T0, value, 1.0, 0.5, 0.5, S.VERSION)


@pytest.mark.parametrize("value", BAD_VERSION)
def test_signal_version_must_be_exactly_locked(value):
    with pytest.raises(R.RiskError, match="version"):
        dataclasses.replace(sig(T0, 1.0, 0.5), version=value)


def _b_row(**changes):
    from test_momentum_signal import bars_from_daily
    closes = [100 * (1 + 0.01 * ((-1) ** i)) for i in range(62)]
    row = S.signals(bars_from_daily(closes, start=T0 - pd.Timedelta(days=62))).iloc[-1].copy()
    for k, v in changes.items():
        if v is _DROP:
            row = row.drop(k)
        else:
            row[k] = v
    return row


_DROP = object()


@pytest.mark.parametrize("field,value", [("available", v) for v in ["False", "True", 0, 1, None, math.nan]]
                         + [("version", v) for v in ["mom-signal/999", None, 1]]
                         + [("available", _DROP), ("version", _DROP)])
def test_from_row_rejects_invalid_contract_fields(field, value):
    with pytest.raises(R.RiskError):
        R.SignalInput.from_row(_b_row(**{field: value}))


def test_valid_python_and_numpy_bools_and_real_b_rows_still_work():
    row = _b_row()
    assert isinstance(row["available"], (bool, np.bool_))
    s_in = R.SignalInput.from_row(row)
    assert s_in.available is True and s_in.version == S.VERSION
    for b in (True, np.bool_(True)):
        assert dataclasses.replace(sig(T0, 1.0, 0.5), available=b).available is True
    st, rec = R.step(R.RiskState.start(100_000, T0), T0, None, s_in)
    assert rec.daily_decision in (R.NORMAL, R.HOLD)


@pytest.mark.parametrize("false", [False, np.bool_(False)])
def test_real_false_is_still_unavailable_data(false):
    s_in = dataclasses.replace(sig(T0, 1.0, 0.5), available=false)
    assert s_in.available is False
    st = R.RiskState.start(100_000, T0)
    with pytest.raises(R.RiskError, match="OGILTIG_DATA"):
        R.step(st, T0, None, s_in)
    unavailable_b = R.SignalInput.from_row(_b_row(available=np.bool_(False), s=math.nan, cap=math.nan, w_target=math.nan))
    with pytest.raises(R.RiskError, match="OGILTIG_DATA"):
        R.step(st, T0, None, unavailable_b)


@pytest.mark.parametrize("field,value", [
    ("day", pd.Timestamp("2021-12-31")), ("day", pd.Timestamp("2021-12-31 01:00", tz="Europe/Stockholm")),
    ("day", "2021-12-31"), ("day", pd.Timestamp("2021-12-31 04:00", tz="UTC")),
    ("decision_time", pd.Timestamp("2022-01-01")), ("decision_time", T0.tz_convert("Etc/GMT-4")),
    ("decision_time", T0 + H), ("decision_time", "2022-01-01T00:00Z")])
def test_signal_times_follow_utc_day_contract(field, value):
    with pytest.raises(R.RiskError):
        dataclasses.replace(sig(T0, 1.0, 0.5), **{field: value})


def test_rejected_signals_leave_state_usable_and_unchanged():
    st = R.RiskState.start(100_000, T0)
    for bad in ("False", "mom-signal/999"):
        with pytest.raises(R.RiskError):
            R.SignalInput(T0 - pd.Timedelta(days=1), T0, bad if bad == "False" else True, 1.0, 0.5, 0.5,
                          S.VERSION if bad == "False" else bad)
    assert st == R.RiskState.start(100_000, T0)
    _, rec = R.step(st, T0, None, sig(T0, 1.0, 0.5))
    assert rec.intent.kind == R.NORMAL


# Regressioner för C4-06 (Codex granskning av 4241d0e): felmeddelanden är säkra för heltal som inte kan skrivas som text.

HUGE = 10 ** 5000


def _huge_risk_calls():
    good = sig(T0, 1.0, 0.5)
    st = state_at(T0 + pd.Timedelta(days=3))
    return {
        "start": lambda: R.RiskState.start(1000, HUGE),
        "initial": lambda: R.RiskState.start(HUGE, T0),
        "available": lambda: dataclasses.replace(good, available=HUGE),
        "version": lambda: dataclasses.replace(good, version=HUGE),
        "day": lambda: dataclasses.replace(good, day=HUGE),
        "decision_time": lambda: dataclasses.replace(good, decision_time=HUGE),
        "step_T": lambda: R.step(st, HUGE, close_at(st.next_boundary, acct_w(0.3)), None),
        "bar_open": lambda: R.CloseInput(HUGE, acct_w(0.3), 100.0),
        "mark_close": lambda: R.CloseInput(T0, acct_w(0.3), HUGE),
        "lock_day": lambda: dataclasses.replace(st, lock_day=HUGE),
    }


@pytest.mark.parametrize("field", list(_huge_risk_calls()))
def test_huge_integer_in_any_field_gives_readable_risk_error(field):
    with pytest.raises(R.RiskError) as err:
        _huge_risk_calls()[field]()
    assert str(err.value)
