"""mom-event/1.0.0 (H-0017 leverans C5) på syntetiska staplar, event och signalrader. Ingen marknadshistorik.

Facit från docs/momentum-a1-orakel.json och handräkning/Decimal, aldrig från eventfunktionen. Tillstånd nära en viss
tid byggs med den privata fixturvägen EngineState._fixture och dokumenterade invarianter (valideras vid konstruktion);
det är ingen ny strategistart och ingen publik återställning.
"""
import copy
import dataclasses
import json
import math
from decimal import Decimal as D, getcontext
from pathlib import Path

import pandas as pd
import pytest

from traderlab import momentum_event as V
from traderlab import momentum_funding as F
from traderlab import momentum_ledger as L
from traderlab import momentum_margin as M
from traderlab import momentum_risk as R
from traderlab import momentum_signal as S

getcontext().prec = 60
ORACLE = json.loads((Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())
H = V.BAR
T0 = V.START
c = 0.0016


def close(a, b):
    return a == pytest.approx(b, rel=1e-12, abs=1e-9)


def sc(order="A", mmr=0.05, cost=L.COST_NORMAL, key="main"):
    return V.Scenario(key, order, mmr, cost)


def sig(T, s, cap):
    return R.SignalInput(T - pd.Timedelta(days=1), T, True, s, cap, s * cap, S.VERSION)


def bar(T, P=100.0, mo=None, mh=None, ml=None, mc=None):
    mo = P if mo is None else mo
    mc = mo if mc is None else mc
    mh = max(mo, mc) if mh is None else mh
    ml = min(mo, mc) if ml is None else ml
    return V.Bar(T, P, mo, mh, ml, mc)


def ev(eid, t, rate, Mref):
    return F.FundingEvent(eid, t, rate, Mref, F.MARK_OPEN, F.bar_open(t))


def restore(scenario, acct, T, prev_mark, *, peak=100_000.0, day_start=100_000.0, initial=100_000.0,
            liquidated=False, permanent=False, last_decision_day=None):
    """Tillstånd mitt i horisonten, redo för stapeln T (dokumenterad testinvariant, inte ny start)."""
    rs = R.RiskState(initial=initial, peak=peak, day_start=0.0 if liquidated else day_start, next_boundary=T,
                     started=True, permanent=permanent, permanent_time=T - H if permanent else None,
                     last_decision_day=last_decision_day, liquidated=liquidated)
    ms = M.MarginState(scenario.account_key, scenario.label, scenario.mmr)
    if liquidated:
        rec_acct = L.Account(C=-1.0, q=1.0, deposit=0.0, avg_price=1.0)   # syntetiskt underlag för tillståndet
        chk = M.check(rec_acct, ms, M.GAP, 1.0, M.MARK_OPEN, T - H)
        _, ms, _ = M.liquidate(rec_acct, ms, chk)
    return V.EngineState._fixture(scenario, acct, rs, F.FundingState(scenario.account_key, scenario.label), ms, T,
                                  prev_mark)


def phases(result):
    return [t.phase for t in result.trace]


def test_versions_and_horizon_constants():
    assert V.VERSION == "mom-event/1.0.0" and V.PROTOCOL == "momentum-protokoll/1.0.0"
    assert (V.START, V.TERMINAL, V.END) == (pd.Timestamp("2022-01-01", tz="UTC"),
                                           pd.Timestamp("2024-12-31 20:00", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC"))
    assert V.EngineState.start(sc()).account == L.Account.open(100_000)


# O5 och O5b: verklig komposition av inträde och utgång i A och B.

def _run_constant(state, start_T, n, events_by_T=None, signals=None):
    results = []
    for k in range(n):
        T = start_T + k * H
        r = V.process_bar(state, bar(T), (events_by_T or {}).get(T, ()), (signals or {}).get(T))
        results.append(r)
        state = r.state
    return state, results


@pytest.mark.parametrize("order", ["A", "B"])
def test_O5_entry_and_exit_with_simultaneous_funding(order):
    o, o5b = ORACLE["O5_funding_samma_grans"], ORACLE["O5b_kapitalfaser_B"]
    T1 = T0 + pd.Timedelta(days=1)
    events = {T0: [ev("f0", T0, 0.0001, 100.0)], T1: [ev("f1", T1, 0.0001, 100.0)]}
    signals = {T0: sig(T0, 1.0, 0.5), T1: sig(T1, 0.0, 0.5)}
    state, res = _run_constant(V.EngineState.start(sc(order)), T0, 7, events, signals)
    first, exit_bar = res[0], res[6]
    entry_trade = next(t for t in first.trace if t.phase == "after_trade")
    assert close(entry_trade.E, o5b["E_trade"]) and close(entry_trade.q * 100 / entry_trade.E, 0.5)
    if order == "A":
        assert phases(first) == ["decision", "gap", "funding_A", "after_trade", "margin_basis"]
        assert next(t for t in first.trace if t.phase == "funding_A").funding == 0
        assert close(state.account.equity(100), o["utgång_A"]["E"])
        assert next(t for t in exit_bar.trace if t.phase == "funding_A").funding == pytest.approx(o["utgång_A"]["funding"])
    else:
        assert phases(first) == ["decision", "gap", "after_trade", "funding_B", "after_funding_B", "margin_basis"]
        post = next(t for t in first.trace if t.phase == "after_funding_B")
        assert close(post.E, o5b["E_post"]) and close(post.q * 100 / post.E, o5b["vikt_after_funding_B"])
        exit_funding = next(t for t in exit_bar.trace if t.phase == "funding_B").funding
        assert exit_funding == 0
        # Oberoende: O1-kontot minus inträdets B-funding, sedan stängning till P = 100 med kostnad.
        q = D(repr(o5b["q"]))
        E_hand = D(100_000) - q * D(100) * D("0.0016") - q * D(100) * D("0.0001") - q * D(100) * D("0.0016")
        assert close(state.account.equity(100), float(E_hand))
    assert state.account.q == 0 and state.funding_state.processed == {"f0", "f1"}
    assert state.account.reconciliation_gap() == pytest.approx(0, abs=1e-8)


def test_simultaneous_event_on_flat_account_is_booked_once():
    st = V.EngineState.start(sc("A"))
    r = V.process_bar(st, bar(T0), [ev("z", T0, 0.0001, 100.0)], sig(T0, 0.0, 0.5))
    assert "z" in r.state.funding_state.processed and r.state.account.C == 100_000
    with pytest.raises(F.FundingError, match="redan bokfört"):
        F.apply_funding(r.state.account, r.state.funding_state, ev("z", T0, 0.0001, 100.0), "funding_B")


# O6: dagsstopp vid 20-stapeln, reset och riskutträde på nya sidan.

@pytest.mark.parametrize("order", ["A", "B"])
def test_O6_day_stop_at_last_close_reset_and_exit(order):
    o = ORACLE["O6_dagsreset"]
    T = pd.Timestamp("2023-03-11", tz="UTC")
    acct = L.Account(C=50_000.0, q=1000.0, deposit=100_000.0, avg_price=50.0)
    st = restore(sc(order), acct, T, 47.9, day_start=100_000.0)
    r = V.process_bar(st, bar(T, P=47.55, mo=47.5), [ev("f", T, 0.0001, 47.5)], sig(T, 1.0, 0.6))
    assert r.day_end == (T - pd.Timedelta(days=1), o["E_close_D"], False)
    assert r.step_record.intent.kind == R.DAY and (R.NORMAL, "strykt av day_stop") in r.step_record.suppressed
    assert r.state.risk_state.day_start == o["day_start_D1"] == 97_900.0
    exp = o["A"] if order == "A" else o["B"]
    assert close(r.state.account.equity(47.5), exp["E_efter"]) and r.state.account.q == 0
    fills = [t for t in r.trace if t.phase == "after_trade"]
    assert len(fills) == 1 and close(fills[0].cost, exp["kostnad"])
    # Resten av dagen: ingen normalavsikt återkommer; day_start flyttas inte av gap/funding efter midnatt.
    state = r.state
    for k in range(1, 6):
        rr = V.process_bar(state, bar(T + k * H, P=47.5))
        assert rr.step_record.intent is None and rr.step_record.day_start_used == 97_900.0
        state = rr.state
    assert close(rr.step_record.day_start_used * (1 + o["A"]["dag_D1_hittills"]), o["A"]["E_efter"]) if order == "A" else True


def test_permanent_stop_survives_resets_over_several_days():
    T = pd.Timestamp("2023-06-02", tz="UTC")
    acct = L.Account(C=-40_000.0, q=1000.0, deposit=100_000.0, avg_price=140.0)  # E(124) = 84 000
    st = restore(sc(), acct, T, 124.0, peak=100_000.0, day_start=86_000.0)
    r = V.process_bar(st, bar(T, P=124.0), (), sig(T, 1.0, 1.0))
    assert r.step_record.permanent_triggered and r.step_record.intent.kind == R.PERMANENT and r.state.account.q == 0
    state = r.state
    for k in range(1, 6 * 3 + 1):
        Tk = T + k * H
        rr = V.process_bar(state, bar(Tk, P=130.0), (), sig(Tk, 1.0, 1.0) if Tk == Tk.floor("D") else None)
        assert rr.state.risk_state.permanent and rr.step_record.intent is None and rr.state.account.q == 0
        state = rr.state


# O10 och horisont.

@pytest.mark.parametrize("order", ["A", "B"])
def test_O10_terminal_close_and_no_further_steps(order):
    o = ORACLE["O10_horisont"]
    acct = L.Account(C=60_000.0, q=400.0, deposit=100_000.0, realized=-2_000.0, avg_price=95.0)
    st = restore(sc(order), acct, V.TERMINAL, 95.0, peak=110_000.0, day_start=98_000.0)
    events = [ev("t0", V.TERMINAL, 0.0001, 95.0), ev("t1", V.TERMINAL + pd.Timedelta(seconds=30), 0.0001, 95.0)]
    r = V.process_bar(st, bar(V.TERMINAL, P=95.1, mo=95.0), events)
    assert r.step_record.intent.kind == R.TERMINAL and r.state.terminated and r.state.account.q == 0
    term = next(t for t in r.trace if t.phase == "after_trade")
    assert close(term.cost, o["terminal_kostnad"])
    gap = next(t for t in r.trace if t.phase == "gap")
    assert close(gap.E, o["E_fore_terminal"])
    A_pay = 400 * 95.0 * 0.0001 if order == "A" else 0.0
    assert close(r.terminal_point[1], o["terminal_E"] - A_pay)
    interior = next(t for t in r.trace if t.phase == "funding_interior")
    assert interior.funding == 0 and interior.q == 0                       # efter terminal: ingen ekonomisk effekt
    if order == "B":
        assert next(t for t in r.trace if t.phase == "funding_B").funding == 0
    with pytest.raises(V.EventError, match="Terminal"):
        V.process_bar(r.state, bar(V.TERMINAL + H))


def test_no_funding_or_bars_before_start_or_from_2025():
    st = V.EngineState.start(sc())
    with pytest.raises(V.EventError):
        V.process_bar(st, bar(T0), [ev("pre", T0 - pd.Timedelta(seconds=30), 0.0001, 100.0)], sig(T0, 1.0, 0.5))
    with pytest.raises(V.EventError):
        V.process_bar(st, bar(T0 - H), (), None)
    with pytest.raises(V.EventError):
        V.Bar(V.END, 100.0, 100.0, 100.0, 100.0, 100.0) and V.process_bar(
            restore(sc(), L.Account.open(100_000), V.END, 100.0), bar(V.END))


def test_full_synthetic_horizon_has_1096_days_and_no_2025_decision():
    state = V.EngineState.start(sc("A"))
    log = V.RunLog.begin(state)
    T = T0
    n = 0
    while True:
        midnight = T == T.floor("D")
        r = V.process_bar(state, bar(T, P=100.0 + 0.01 * (n % 7)), (), sig(T, 1.0, 0.5) if midnight else None)
        log, state, n = log.add(r), r.state, n + 1
        if r.state.terminated:
            break
        T += H
    assert n == 1096 * 6
    assert len(log.day_ends) == 1096 and log.day_base == (T0 - pd.Timedelta(days=1), 100_000.0)
    assert log.day_ends[0][0] == T0 and log.day_ends[-1][0] == pd.Timestamp("2024-12-31", tz="UTC")
    assert log.close_points[0] == (None, T0, 100_000.0) and len(log.close_points) == 1 + (1096 * 6 - 1) + 1
    assert log.close_points[-2][0] == pd.Timestamp("2024-12-31 16:00", tz="UTC")
    assert log.close_points[-1][0] == V.TERMINAL and log.close_points[-1][2] == log.day_ends[-1][1]
    assert all(cp[1] <= V.END for cp in log.close_points) and state.account.q == 0


def test_first_decision_uses_warmup_signal_and_no_position_before_start():
    r = V.process_bar(V.EngineState.start(sc()), bar(T0), (), sig(T0, 2 / 3, 0.6))
    assert r.close_point is None and r.day_end is None
    assert r.step_record.intent.kind == R.NORMAL and r.step_record.intent.w == (2 / 3) * 0.6
    assert phases(r)[:2] == ["decision", "gap"] and next(t for t in r.trace if t.phase == "gap").q == 0


# O14/O15: integrerade gapfall och båda kostnadsnivåerna.

@pytest.mark.parametrize("cost", [L.COST_NORMAL, L.COST_STRESS])
def test_O14_risk_hold_and_reduction_after_gap(cost):
    o = ORACLE["O14_reduce_only"]
    T = pd.Timestamp("2023-09-05", tz="UTC")
    # O14 skalat 100 gånger till låst startkapital 100 000; storlekslösaren är homogen i (E, q_old).
    acct = L.Account(C=80_000.0, q=200.0, deposit=100_000.0, avg_price=100.0)
    st = restore(sc(cost=cost), acct, T, 100.0)
    down = V.process_bar(st, bar(T, P=90.0), (), sig(T, 1.0, 0.195))
    hold = next(t for t in down.trace if t.phase == "after_trade")
    assert hold.reason == "risk_reduce_only_hold" and hold.cost == 0 and down.state.account.q == 200
    up = V.process_bar(st, bar(T, P=110.0), (), sig(T, 1.0, 0.195))
    q_up = up.state.account.q
    E = D(80_000) + D(200) * D(110)
    k = D(110) * D(repr(cost))                                       # säljgren: k = M - P + cP med P = M
    exp_q = D("0.195") * (E - 200 * k) / (D(110) - D("0.195") * k)
    assert abs(D(repr(q_up)) - exp_q) <= exp_q * D("1e-13")
    if cost == L.COST_NORMAL:
        assert q_up == pytest.approx(100 * o["open_110"]["q"], rel=1e-12)


@pytest.mark.parametrize("cost", [L.COST_NORMAL, L.COST_STRESS])
def test_O15_normal_changes_direction_after_gap(cost):
    o = ORACLE["O15_normal_efter_gap"]
    T = pd.Timestamp("2023-09-05", tz="UTC")
    # O15 skalat 100 gånger till låst startkapital 100 000 (homogent i E och q_old).
    acct = L.Account(C=80_000.0, q=200.0, deposit=100_000.0, avg_price=100.0)
    st = restore(sc(cost=cost), acct, T, 100.0)
    r = V.process_bar(st, bar(T, P=70.0), (), sig(T, 1 / 3, 0.45))
    assert r.step_record.intent.kind == R.NORMAL and r.state.account.q > 200
    w = (1 / 3) * 0.45
    E = D(80_000) + D(200) * D(70)
    exp_q = D(repr(w)) * (E + D(70) * D(repr(cost)) * 200) / (D(70) * (1 + D(repr(w)) * D(repr(cost))))
    assert abs(D(repr(r.state.account.q)) - exp_q) <= exp_q * D("1e-13")
    if cost == L.COST_NORMAL:
        assert r.state.account.q == pytest.approx(100 * o["fyllning"]["q"], rel=1e-12)


def test_basis_counted_once_in_composition():
    o = ORACLE["O3_basis"]
    r = V.process_bar(V.EngineState.start(sc()), bar(T0, P=100.0, mo=99.5), (), sig(T0, 1.0, 0.5))
    assert close(r.state.account.q, o["q"]) and close(r.state.account.equity(99.5), o["E_after"])


# O16: exakta tider vid gräns, midnatt, första öppning och terminal.

@pytest.mark.parametrize("order", ["A", "B"])
def test_O16_exact_boundary_and_plus_minus_times(order):
    T = pd.Timestamp("2023-02-01", tz="UTC")
    st = restore(sc(order), L.Account.open(100_000), T - H, 100.0)
    prev = V.process_bar(st, bar(T - H), [ev("m30", T - pd.Timedelta(seconds=30), 0.0001, 100.0),
                                          ev("m1", T - pd.Timedelta(milliseconds=1), 0.0001, 100.0)])
    assert prev.interior_booked == 2 and all(t.q == 0 and t.funding == 0 for t in prev.trace if t.phase == "funding_interior")
    assert all(t.time.floor("D") == T - pd.Timedelta(days=1) for t in prev.trace if t.phase == "funding_interior")
    events = [ev("e0", T, 0.0001, 100.0), ev("p1", T + pd.Timedelta(milliseconds=1), 0.0001, 100.0),
              ev("p30", T + pd.Timedelta(seconds=30), 0.0001, 100.0)]
    r = V.process_bar(prev.state, bar(T), events, sig(T, 1.0, 0.5))
    q_new = r.state.account.q
    sim = next(t for t in r.trace if t.phase in ("funding_A", "funding_B"))
    assert sim.phase == f"funding_{order}" and sim.funding == (0.0 if order == "A" else pytest.approx(q_new * 100 * 0.0001))
    interior = [t for t in r.trace if t.phase == "funding_interior"]
    assert [t.event_id for t in interior] == ["p1", "p30"] and all(t.q == q_new for t in interior)
    assert all(t.funding == pytest.approx(q_new * 100 * 0.0001) for t in interior)
    assert r.simultaneous == 1 and r.interior_booked == 2


def test_exit_at_open_then_interior_event_sees_zero_and_entry_sees_new_q():
    T = pd.Timestamp("2023-02-01", tz="UTC")
    acct = L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0)
    st = restore(sc(), acct, T, 100.0)
    r = V.process_bar(st, bar(T), [ev("x", T + pd.Timedelta(seconds=30), 0.0001, 100.0)], sig(T, 0.0, 0.5))
    assert r.state.account.q == 0 and next(t for t in r.trace if t.phase == "funding_interior").funding == 0


def test_event_in_wrong_bar_is_rejected():
    st = V.EngineState.start(sc())
    with pytest.raises(V.EventError, match="ligger inte i stapeln"):
        V.process_bar(st, bar(T0), [ev("late", T0 + H, 0.0001, 100.0)], sig(T0, 1.0, 0.5))


# O11 och O18: gap- och intrastapellikvidation, absorberande nollkonto.

def _risky(order="A", mmr=0.05, T=pd.Timestamp("2023-04-10", tz="UTC")):
    """E(70) = 100 000 med peak och dagskapital 101 000: inget dags- eller permanent stopp vid closen."""
    acct = L.Account(C=-600_000.0, q=10_000.0, deposit=100_000.0, realized=300_000.0, avg_price=100.0)
    return restore(sc(order, mmr), acct, T, 70.0, peak=101_000.0, day_start=101_000.0), T


def test_gap_liquidation_before_fill_strikes_intent_and_absorbs():
    st, T = _risky("B")
    r = V.process_bar(st, bar(T, P=55.0, mo=55.0, mh=60.0, ml=50.0, mc=58.0), [ev("b", T, 0.0001, 55.0)],
                      sig(T, 1.0, 1.0))
    liq = next(t for t in r.trace if t.phase == "liquidation")
    assert "struken" in liq.reason and "after_trade" not in phases(r) and "funding_B" not in phases(r)
    assert r.state.account.C == 0 and r.state.account.q == 0 and r.state.margin_state.liquidated
    rec = r.state.margin_state.record
    assert rec.E_before == -50_000.0 and rec.capital_reset == 50_000.0 and rec.phase == M.GAP
    assert r.absorbed == 1 and r.state.funding_state.processed == frozenset()     # B-eventet absorberat
    state = r.state
    for k in range(1, 8):                                            # över midnatt: inga avsikter, ingen funding
        Tk = T + k * H
        rr = V.process_bar(state, bar(Tk, P=60.0), [ev(f"a{k}", Tk + pd.Timedelta(hours=1), -0.01, 60.0)],
                           sig(Tk, 1.0, 1.0) if Tk == Tk.floor("D") else None)
        assert rr.step_record.intent is None and rr.absorbed == 1 and rr.state.account.C == 0
        assert rr.close_point[2] == 0.0
        state = rr.state
    assert state.risk_state.liquidated and state.account.liquidation_adjustment == rec.adjustment_delta


@pytest.mark.parametrize("mmr", M.MMRS)
def test_gap_check_uses_both_rates(mmr):
    st, T = _risky("A", mmr)
    r = V.process_bar(st, bar(T, P=62.0, mo=62.0, mh=63.0, ml=61.9, mc=62.5), (), sig(T, 1.0, 1.0))
    hit = (D(-600_000) + D(10_000) * D(62)) <= D(repr(mmr)) * D(10_000) * D(62)
    assert r.state.margin_state.liquidated == hit
    if not hit:
        assert "after_trade" in phases(r)


FUNDING_PHASES = set(V.BOOKED) | {V.ABSORBED, V.UNRESOLVED}


def _event_categories(result):
    return [(t.event_id, t.phase) for t in result.trace if t.phase in FUNDING_PHASES]


# C5-01 (Edwins beslut 2026-11-04): vid intrastapelträff bokförs ingen mellanhändelse; alla redovisas som olösta.
@pytest.mark.parametrize("mmr,hit", [(0.05, True), (0.005, False)])
@pytest.mark.parametrize("credit_first", [False, True])
@pytest.mark.parametrize("order", ["A", "B"])
@pytest.mark.parametrize("with_sim", [False, True])
def test_intrabar_hit_books_no_interior_funding_and_keeps_basis_separate(mmr, hit, credit_first, order, with_sim):
    st, T = _risky(order, mmr, pd.Timestamp("2023-04-10 08:00", tz="UTC"))   # ingen midnatt: ingen avsikt
    rates = {"pay": "0.02", "pay2": "0.005", "recv": "-0.02", "recv2": "-0.01", "zero": "0"}
    offsets = [30, 60, 90, 120, 150]                                 # minuter in i stapeln
    names = ["recv", "recv2", "zero", "pay", "pay2"] if credit_first else ["pay", "pay2", "zero", "recv", "recv2"]
    events = [ev(n, T + pd.Timedelta(minutes=m), float(rates[n]), 64.0) for n, m in zip(names, offsets)]
    if with_sim:
        events = [ev("sim", T, 0.0001, 64.0)] + events
    r = V.process_bar(st, bar(T, P=64.0, mo=64.0, mh=66.0, ml=63.5, mc=65.0), events)
    # Oberoende Decimal-facit.
    q, Mref, low = D(10_000), D(64), D("63.5")
    sim = q * Mref * D("0.0001") if with_sim else D(0)
    amount = {n: q * Mref * D(v) for n, v in rates.items()}
    C_open = D(-600_000) - sim                                         # samtidig funding bokförd i A före, B efter
    C_basis = C_open - sum(v for v in amount.values() if v > 0)      # efter betald, före mottagen
    E_low, MM = C_basis + q * low, D(repr(mmr)) * q * low
    assert (E_low <= MM) == hit
    assert r.margin_basis is not None and close(r.margin_basis[0], float(C_basis))
    assert close(r.margin_basis[1], float(E_low)) and close(r.margin_basis[2], float(MM)) and r.margin_basis[3] == 63.5
    cats = _event_categories(r)
    assert sorted(i for i, _ in cats) == sorted(e.event_id for e in events)          # varje event exakt en gång
    acct = r.state.account
    sim_cat = [("sim", f"funding_{order}")] if with_sim else []
    if hit:
        assert cats == sim_cat + [(n, V.UNRESOLVED) for n in names]
        assert [u[0] for u in r.unresolved] == names and [u[1] for u in r.unresolved] == [e.time for e in events[-5:]]
        for eid, _, amt, in_basis in r.unresolved:
            assert close(amt, float(amount[eid])) and in_basis == (amount[eid] > 0)
        assert r.interior_booked == 0 and r.absorbed == 0
        assert r.state.funding_state.processed == ({"sim"} if with_sim else frozenset())
        assert close(acct.funding_net, float(sim)) and acct.C == 0 and acct.q == 0 and acct.avg_price == 0
        assert close(acct.liquidation_adjustment, float(-C_open - q * D(100)))                   # hela kontot efter öppningen
        assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-8)
        rec = r.state.margin_state.record
        assert rec.phase == M.INTRABAR and close(rec.E_before, float(E_low)) and close(rec.C_old, float(C_basis))
        liq = next(t for t in r.trace if t.phase == "liquidation")
        assert liq.time == V.UNKNOWN_TIME and liq.source == "mark_low"
        assert all(t.time == e.time for t, e in zip([t for t in r.trace if t.phase == V.UNRESOLVED], events[-5:]))
        # Absorberande noll i följande staplar: inga nya fundingposter, ingen återupplivning.
        state = r.state
        for k in range(1, 5):
            Tk = T + k * H
            rr = V.process_bar(state, bar(Tk, P=70.0), [ev(f"n{k}", Tk + pd.Timedelta(hours=1), -0.05, 70.0)],
                               sig(Tk, 1.0, 1.0) if Tk == Tk.floor("D") else None)
            assert rr.state.account == acct and rr.close_point[2] == 0.0 and _event_categories(rr) == [(f"n{k}", V.ABSORBED)]
            state = rr.state
    else:
        assert cats == sim_cat + [(n, "funding_interior") for n in names] and r.unresolved == ()
        assert r.interior_booked == 5 and r.state.funding_state.processed == {e.event_id for e in events}
        assert close(acct.funding_net, float(sim + sum(amount.values())))
        assert close(acct.C, float(C_open - sum(amount.values())))
        Cs = [t.C for t in r.trace if t.phase == "funding_interior"]
        exp, run = [], C_open
        for n in names:
            run -= amount[n]
            exp.append(float(run))
        assert all(close(a, b) for a, b in zip(Cs, exp))                  # kronologiskt, en post i taget


def test_gap_liquidation_lists_each_absorbed_event_once():
    st, T = _risky("B")
    events = [ev("b", T, 0.0001, 55.0), ev("i1", T + pd.Timedelta(hours=1), 0.01, 55.0),
              ev("i2", T + pd.Timedelta(hours=2), -0.01, 55.0)]
    r = V.process_bar(st, bar(T, P=55.0, mo=55.0, mh=60.0, ml=50.0, mc=58.0), events, sig(T, 1.0, 1.0))
    assert _event_categories(r) == [("b", V.ABSORBED), ("i1", V.ABSORBED), ("i2", V.ABSORBED)]
    assert r.absorbed == 3 and r.unresolved == () and r.margin_basis is None


def test_liquidated_account_through_midnight_and_terminal_has_no_intent():
    zero = L.Account(C=0.0, q=0.0, deposit=100_000.0, liquidation_adjustment=-100_000.0)
    st = restore(sc(), zero, V.TERMINAL - 2 * H, 50.0, liquidated=True)
    for T in (V.TERMINAL - 2 * H, V.TERMINAL - H, V.TERMINAL):
        r = V.process_bar(st, bar(T, P=50.0), [ev(f"l{T.hour}", T + pd.Timedelta(hours=1), 0.01, 50.0)])
        assert r.step_record.intent is None and r.state.account == zero and r.absorbed == 1
        st = r.state
    assert st.terminated and r.terminal_point == (V.TERMINAL, 0.0)


# Isolering, prefix och signaler.

def test_four_scenarios_are_isolated_with_same_event_ids():
    events = {T0: [ev("f0", T0, 0.0001, 100.0)], T0 + H: [ev("f1", T0 + H + pd.Timedelta(hours=1), 0.0002, 100.0)]}
    finals = {}
    for order in "AB":
        for mmr in M.MMRS:
            state, _ = _run_constant(V.EngineState.start(sc(order, mmr)), T0, 2, events, {T0: sig(T0, 1.0, 0.5)})
            assert state.funding_state.processed == {"f0", "f1"}
            assert state.funding_state.scenario == state.margin_state.scenario == sc(order, mmr).label
            finals[(order, mmr)] = state.account.C
    assert finals[("A", 0.05)] == finals[("A", 0.005)] and finals[("B", 0.05)] == finals[("B", 0.005)]
    assert finals[("A", 0.05)] != finals[("B", 0.05)]


def test_mismatched_states_are_rejected():
    s = sc()
    good = V.EngineState.start(s)
    with pytest.raises(V.EventError, match="hör inte"):
        dataclasses.replace(good, funding_state=F.FundingState("other", s.label))
    with pytest.raises(V.EventError, match="hör inte|sats"):
        dataclasses.replace(good, margin_state=M.MarginState("main", s.label, 0.005))
    with pytest.raises(V.EventError):
        dataclasses.replace(good, next_bar=T0 + H)
    with pytest.raises(V.EventError, match="likviderat"):
        restore(s, L.Account(C=5.0, deposit=5.0), T0 + H, 100.0, liquidated=True)


# C5-02: tillståndet kan inte sättas ihop av främmande delar eller avvika från startläget.

@pytest.mark.parametrize("acct", [L.Account.open(200_000), L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0),
                                  L.Account(C=0.0)], ids=["kapital_200k", "position_fore_start", "nollkonto"])
def test_unstarted_state_must_be_exact_start(acct):
    good = V.EngineState.start(sc())
    with pytest.raises(V.EventError):
        dataclasses.replace(good, account=acct)
    with pytest.raises(V.EventError):
        V.EngineState(scenario=sc(), account=acct, risk_state=good.risk_state, funding_state=good.funding_state,
                      margin_state=good.margin_state, next_bar=T0)


@pytest.mark.parametrize("acct", [L.Account.open(200_000), L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0),
                                  L.Account(C=0.0), L.Account(C=100_000.0, deposit=100_000.0, realized=5.0, costs=5.0)],
                         ids=["kapital_200k", "position_fore_start", "nollkonto", "rord_bokforing"])
def test_start_invariant_itself_rejects_non_start_accounts(acct):
    # Invariantlagret bakom grinden (start/process_bar): även en intern väg kan inte skapa ett avvikande startläge.
    good = V.EngineState.start(sc())
    with V._issuing(), pytest.raises(V.EventError, match="startläget"):
        V.EngineState(scenario=sc(), account=acct, risk_state=good.risk_state, funding_state=good.funding_state,
                      margin_state=good.margin_state, next_bar=T0)


def test_direct_construction_and_replace_are_rejected_even_when_valid():
    good = V.EngineState.start(sc())
    with pytest.raises(V.EventError, match="skapas bara"):
        V.EngineState(scenario=good.scenario, account=good.account, risk_state=good.risk_state,
                      funding_state=good.funding_state, margin_state=good.margin_state, next_bar=T0)
    with pytest.raises(V.EventError, match="skapas bara"):
        dataclasses.replace(good)
    r = V.process_bar(good, bar(T0), (), sig(T0, 1.0, 0.5))
    with pytest.raises(V.EventError, match="skapas bara"):
        dataclasses.replace(r, absorbed=0)
    assert copy.deepcopy(good) == good                                   # oförändrad kopia av samma tillstånd


def test_foreign_risk_lock_cannot_be_swapped_in():
    T = pd.Timestamp("2023-05-02", tz="UTC")
    locked = restore(sc("A", key="locked"), L.Account.open(100_000), T, 100.0, permanent=True)
    other = restore(sc("B", key="other"), L.Account.open(100_000), T, 100.0)
    with pytest.raises(V.EventError, match="skapas bara"):
        dataclasses.replace(locked, risk_state=other.risk_state)
    r = V.process_bar(locked, bar(T), (), sig(T, 1.0, 0.5))           # riktiga låset gäller: ingen köp
    assert r.state.account.q == 0 and r.step_record.intent is None


def _rs(T, **kw):
    base = dict(initial=100_000.0, peak=100_000.0, day_start=100_000.0, next_boundary=T, started=True)
    return R.RiskState(**(base | kw))


@pytest.mark.parametrize("case", ["insattning", "ej_avstamt", "nollkonto_levande", "negativt_levande", "permanent_med_q",
                                  "lock_med_q", "likviderad_med_C", "ostartat_risk", "terminal", "vid_start",
                                  "efter_terminal", "prev_noll", "fel_nyckel", "kapitalbas_200k", "funding_utan_historik",
                                  "naiv_tid"])
def test_fixture_invariants_reject_inconsistent_states(case):
    T = pd.Timestamp("2023-05-02 08:00", tz="UTC")
    s = sc()
    acct, rs, fs = L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0), _rs(T), F.FundingState("main", s.label)
    ms, nb, pm = M.MarginState("main", s.label, s.mmr), T, 100.0
    if case == "insattning":
        acct = L.Account(C=50_000.0, q=500.0, deposit=90_000.0, realized=10_000.0, avg_price=100.0)
    elif case == "ej_avstamt":
        acct = L.Account(C=50_001.0, q=500.0, deposit=100_000.0, avg_price=100.0)
    elif case == "nollkonto_levande":
        acct = L.Account(C=0.0, deposit=100_000.0, realized=-100_000.0)
    elif case == "negativt_levande":
        pm = 90.0
        acct = L.Account(C=-50_000.0, q=500.0, deposit=100_000.0, avg_price=300.0)
    elif case == "permanent_med_q":
        rs = _rs(T, permanent=True, permanent_time=T - H)
    elif case == "lock_med_q":
        rs = _rs(T, lock_day=T.floor("D"))
    elif case == "likviderad_med_C":
        rec_acct = L.Account(C=-1.0, q=1.0, deposit=0.0, avg_price=1.0)
        _, ms, _ = M.liquidate(rec_acct, ms, M.check(rec_acct, ms, M.GAP, 1.0, M.MARK_OPEN, T - H))
        acct = L.Account(C=5.0, deposit=100_000.0, realized=-99_995.0)
    elif case == "ostartat_risk":
        rs = R.RiskState.start(100_000.0, T)
    elif case == "terminal":
        rs = _rs(T, terminated=True)
    elif case == "vid_start":
        nb = T0
        rs = _rs(T0)
    elif case == "efter_terminal":
        nb = V.TERMINAL + H
    elif case == "prev_noll":
        pm = 0.0
    elif case == "fel_nyckel":
        fs = F.FundingState("annan", s.label)
    elif case == "kapitalbas_200k":
        acct = L.Account(C=150_000.0, q=500.0, deposit=200_000.0, avg_price=100.0)
        rs = _rs(T, initial=200_000.0, peak=200_000.0, day_start=200_000.0)
    elif case == "funding_utan_historik":
        acct = L.Account(C=49_999.0, q=500.0, deposit=100_000.0, avg_price=100.0, funding_net=1.0)
    elif case == "naiv_tid":
        nb = pd.Timestamp("2023-05-02 08:00")
    snapshot = (acct, rs, fs, ms)
    with pytest.raises(V.EventError) as err:
        V.EngineState._fixture(s, acct, rs, fs, ms, nb, pm)
    assert str(err.value) and (acct, rs, fs, ms) == snapshot


def test_no_public_restore_path_around_risk_lock():
    # C5-02 (granskning av 3f46aa5): ett konto som fått permanent stopp genom vanliga motorsteg kan inte förenas med
    # ett annat kontos olåsta riskstate via någon publik väg.
    assert not hasattr(V.EngineState, "restore")
    def run(key, s):
        st = V.EngineState.start(sc(key=key))
        marks = [100.0, 300.0, 300.0, 300.0, 300.0, 220.0]
        for k, m in enumerate(marks):
            T = T0 + k * H
            r = V.process_bar(st, bar(T, P=m, mo=m if k else 100.0), (), sig(T, s, 0.5) if T == T.floor("D") else None)
            st = r.state
        return V.process_bar(st, bar(T0 + 6 * H, P=220.0), (), sig(T0 + 6 * H, s, 0.5)).state
    locked, free = run("locked", 1.0), run("free", 0.0)
    assert locked.risk_state.permanent and locked.account.q == 0 and not free.risk_state.permanent
    with pytest.raises(V.EventError, match="skapas bara"):
        dataclasses.replace(locked, risk_state=free.risk_state)
    nxt = V.process_bar(locked, bar(locked.next_bar, P=220.0), (), None)
    assert nxt.state.account.q == 0                                      # riktiga låset gäller


def test_valid_restores_near_terminal_and_mid_horizon_are_independent():
    a = restore(sc("A"), L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0), V.TERMINAL, 100.0)
    b = restore(sc("B"), L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0),
                pd.Timestamp("2023-05-02 08:00", tz="UTC"), 100.0)
    ra = V.process_bar(a, bar(V.TERMINAL))
    rb = V.process_bar(b, bar(b.next_bar))
    assert ra.state.terminated and ra.state.account.q == 0 and rb.state.account.q == 500 and not rb.state.terminated


# C5-03: loggen tar bara emot nästa resultat i samma förlopp.

def _first_results():
    st = V.EngineState.start(sc())
    r0 = V.process_bar(st, bar(T0), (), sig(T0, 1.0, 0.5))
    r1 = V.process_bar(r0.state, bar(T0 + H))
    return st, r0, r1


def test_runlog_rejects_duplicates_gaps_backsteps_and_foreign_results():
    st, r0, r1 = _first_results()
    log = V.RunLog.begin(st).add(r0)
    with pytest.raises(V.EventError, match="följer inte"):
        log.add(r0)                                                    # dubblett
    with pytest.raises(V.EventError, match="följer inte"):
        V.RunLog.begin(st).add(r1)                                     # lucka
    log2 = log.add(r1)
    with pytest.raises(V.EventError, match="följer inte"):
        log2.add(r0)                                                   # bakåtsteg
    foreign = V.process_bar(V.EngineState.start(sc("B", key="foreign")), bar(T0), (), sig(T0, 1.0, 0.5))
    with pytest.raises(V.EventError, match="följer inte"):
        V.RunLog.begin(st).add(foreign)
    other_prices = V.process_bar(r0.state, bar(T0 + H, P=101.0))      # annat andra steg från samma r0
    assert log.add(other_prices).state == other_prices.state           # giltigt som nästa steg efter r0
    with pytest.raises(V.EventError, match="följer inte"):
        log2.add(other_prices)
    assert len(log2.close_points) == 2 and log2.day_ends == ()          # start + close för T0-stapeln


def test_runlog_begins_only_at_start_and_stops_at_terminal():
    restored = restore(sc(), L.Account.open(100_000), V.TERMINAL - H, 100.0)
    with pytest.raises(V.EventError, match="startläget"):
        V.RunLog.begin(restored)
    with pytest.raises(V.EventError, match="skapas bara"):
        V.RunLog(state=V.EngineState.start(sc()))
    with pytest.raises(V.EventError, match="skapas bara"):
        dataclasses.replace(V.RunLog.begin(V.EngineState.start(sc())), close_points=())


def test_runlog_after_terminal_is_closed():
    state = V.EngineState.start(sc("A"))
    log = V.RunLog.begin(state)
    T, last = T0, None
    while True:
        r = V.process_bar(state, bar(T), (), sig(T, 1.0, 0.5) if T == T.floor("D") else None)
        log, state, last = log.add(r), r.state, r
        if state.terminated:
            break
        T += H
    assert log.terminated and len(log.day_ends) == 1096 and len(log.close_points) == 6577
    with pytest.raises(V.EventError, match="avslutad"):
        log.add(last)


def _prefix_run(highs):
    state = V.EngineState.start(sc())
    out = []
    for k, h in enumerate(highs):
        T = T0 + k * H
        b = V.Bar(T, 100.0 + k, 100.0 + k, max(h, 100.0 + k + 1), 99.0 + k, 100.0 + k + 1)
        r = V.process_bar(state, b, (), sig(T, 1.0, 0.5) if T == T.floor("D") else None)
        out.append((r.step_record, r.close_point, r.day_end))
        state = r.state
    return out


def test_future_prices_and_high_low_do_not_change_earlier_decisions():
    base = _prefix_run([110.0] * 9)
    assert _prefix_run([110.0] * 5 + [500.0] * 4)[:5] == base[:5]
    altered = _prefix_run([300.0] * 9)                               # high påverkar bara marginal, inte beslut
    assert [x[0] for x in altered] == [x[0] for x in base]


def test_unavailable_or_wrong_day_signal_is_rejected_not_flat():
    st = V.EngineState.start(sc())
    with pytest.raises(V.EventError, match="OGILTIG_DATA"):
        V.process_bar(st, bar(T0), (), dataclasses.replace(sig(T0, 1.0, 0.5), available=False))
    with pytest.raises(V.EventError):
        V.process_bar(st, bar(T0), (), sig(T0 + pd.Timedelta(days=1), 1.0, 0.5))
    with pytest.raises(V.EventError):
        V.process_bar(st, bar(T0), (), None)


# Felprov.

def test_order_errors_skip_duplicate_backwards():
    st = V.EngineState.start(sc())
    r = V.process_bar(st, bar(T0), (), sig(T0, 1.0, 0.5))
    for T in (T0, T0 + 2 * H, T0 - H):
        with pytest.raises(V.EventError):
            V.process_bar(r.state, bar(T) if T >= T0 else V.Bar(T, 1.0, 1.0, 1.0, 1.0, 1.0))
    assert V.process_bar(r.state, bar(T0 + H)).state.next_bar == T0 + 2 * H


@pytest.mark.parametrize("make,match", [
    (lambda: [ev("a", T0 + pd.Timedelta(hours=2), 0.0001, 100.0), ev("b", T0 + pd.Timedelta(hours=1), 0.0001, 100.0)], "sorterade"),
    (lambda: [ev("a", T0 + pd.Timedelta(hours=1), 0.0001, 100.0), ev("a", T0 + pd.Timedelta(hours=2), 0.0001, 100.0)], "Dubblerat"),
    (lambda: [ev("a", T0 + pd.Timedelta(hours=1), 0.0001, 101.0)], "M_ref"),
    (lambda: ["inte ett event"], "Fel typ"),
    (lambda: "inte en lista", "lista"),
])
def test_invalid_event_lists(make, match):
    with pytest.raises(V.EventError, match=match):
        V.process_bar(V.EngineState.start(sc()), bar(T0), make(), sig(T0, 1.0, 0.5))


@pytest.mark.parametrize("kw", [dict(mark_low=101.0), dict(mark_high=99.0), dict(contract_open=0.0),
                                dict(mark_open=math.nan), dict(mark_close=math.inf), dict(mark_low=True),
                                dict(mark_high=10 ** 400), dict(mark_open=10 ** 5000), dict(synthetic=False),
                                dict(open_time=pd.Timestamp("2022-01-01 01:00", tz="UTC")),
                                dict(open_time=pd.Timestamp("2022-01-01")), dict(open_time=10 ** 5000)],
                         ids=lambda kw: next(iter(kw)) + ("_huge" if any(isinstance(v, int) and not isinstance(v, bool)
                                                                       and abs(v) > 10 ** 300 for v in kw.values()) else ""))
def test_invalid_bars(kw):
    base = dict(open_time=T0, contract_open=100.0, mark_open=100.0, mark_high=101.0, mark_low=99.0, mark_close=100.0)
    with pytest.raises(L.LedgerError) as err:
        V.Bar(**(base | kw))
    assert str(err.value)


@pytest.mark.parametrize("kw", [dict(order="C"), dict(order=1), dict(mmr=0.01), dict(mmr=10 ** 5000), dict(cost=0.002),
                                dict(cost=math.nan), dict(account_key=""), dict(account_key=10 ** 5000)],
                         ids=["order", "order_int", "mmr", "mmr_huge", "cost", "cost_nan", "key", "key_huge"])
def test_invalid_scenarios(kw):
    base = dict(account_key="main", order="A", mmr=0.05, cost=L.COST_NORMAL)
    with pytest.raises(V.EventError) as err:
        V.Scenario(**(base | kw))
    assert str(err.value)


def test_inputs_are_not_modified():
    st = V.EngineState.start(sc())
    b, events, s = bar(T0), [ev("f0", T0, 0.0001, 100.0)], sig(T0, 1.0, 0.5)
    copies = (copy.deepcopy(st), dataclasses.replace(b), list(events), dataclasses.replace(s))
    V.process_bar(st, b, events, s)
    assert (st, b, events, s) == copies


def test_trace_provenance_fields():
    r = V.process_bar(V.EngineState.start(sc("B")), bar(T0), [ev("f0", T0, 0.0001, 100.0)], sig(T0, 1.0, 0.5))
    fb = next(t for t in r.trace if t.phase == "funding_B")
    assert fb.event_id == "f0" and fb.source == "mark_open" and fb.time == T0 and fb.mmr == 0.05
    assert fb.scenario == sc("B").label and fb.account_key == "main" and V.VERSION in fb.versions
    trade = next(t for t in r.trace if t.phase == "after_trade")
    assert trade.P == 100.0 and trade.intent == R.NORMAL and trade.intent_decision_time == T0 and trade.cost > 0


def _low_run(lows):
    state = V.EngineState.start(sc())
    out = []
    for k, low in enumerate(lows):
        T = T0 + k * H
        b = V.Bar(T, 100.0 + k, 100.0 + k, 102.0 + k, min(low, 99.0 + k), 100.5 + k)
        r = V.process_bar(state, b, (), sig(T, 1.0, 0.5) if T == T.floor("D") else None)
        out.append((r.step_record, r.close_point, r.day_end))
        state = r.state
    return out


def test_mark_low_never_changes_close_values_or_decisions():
    # Kontot har C > 0 och kan inte likvideras, så low får bara påverka marginalprövningen.
    base = _low_run([99.0] * 9)
    assert _low_run([60.0] * 9) == base
    assert [cp for _, cp, _ in base[1:]] == [(T0 + k * H, T0 + (k + 1) * H, cp[2]) for k, (_, cp, _) in enumerate(base[1:])]
