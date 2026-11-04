"""mom-control/1.0.0, D1-rättning: adapterkontrakt (D1-01), låst underlag (D1-02) och de obligatoriska komponentintegrerade
proven (D1-03). Endast syntetiska data, inga verkliga körningar.

Facit räknas oberoende i Decimal med §6:s självfinansieringsidentitet (köp: q = w(E0 + q0·j)/(M + w·j), j = P(1+c) − M;
sälj: q = w(E0 − q0·k)/(M − w·k), k = M − P + cP) och belopp = q·M_ref·ränta. Fall som behöver ett tillstånd mitt i
horisonten använder eventlagrets privata fixturväg och är märkta FIXTUR; de bevisar inte publik proveniens, som i stället
visas av de publika förloppen från EngineState.start och run_component.
"""
import math
from decimal import Decimal as D, getcontext

import numpy as np
import pandas as pd
import pytest

from traderlab import momentum_control as K
from traderlab import momentum_event as V
from traderlab import momentum_funding as F
from traderlab import momentum_ledger as L
from traderlab import momentum_margin as M
from traderlab import momentum_risk as R
from traderlab import momentum_signal as S

from test_momentum_control import make_sig, market, vol_for

getcontext().prec = 60
H = V.BAR
T0 = V.START
c = D(repr(L.COST_NORMAL))


def ev(eid, t, rate, Mref):
    return F.FundingEvent(eid, t, rate, Mref, F.MARK_OPEN, F.bar_open(t))


def fixture(order, acct, T, prev_mark, *, peak=100_000.0, day_start=100_000.0, mmr=0.05, key="mom7/L1", **rs_kw):
    """FIXTUR: tillstånd mitt i horisonten via eventlagrets privata väg."""
    s = V.Scenario(key, order, mmr)
    rs = R.RiskState(initial=100_000.0, peak=peak, day_start=day_start, next_boundary=T, started=True, **rs_kw)
    return V.EngineState._fixture(s, acct, rs, F.FundingState(key, s.label), M.MarginState(key, s.label, mmr), T, prev_mark)


def buy_q(E0, q0, w, P, Mk):
    j = P * (1 + c) - Mk
    return w * (E0 + q0 * j) / (Mk + w * j)


def sell_q(E0, q0, w, P, Mk):
    k = Mk - P + c * P
    return w * (E0 - q0 * k) / (Mk - w * k)


def close(a, b):
    return a == pytest.approx(float(b), rel=1e-12, abs=1e-9)


# D1-01: adapterkontraktet.

@pytest.fixture(scope="module")
def table():
    return S.signals(market().contract[["close"]])


def _row_signal(table, day, comp="mom7", **change):
    row = table.loc[day].copy()
    for k, v in change.items():
        row[k] = v
    t = table.copy()
    t = t.astype({"available": object}) if "available" in change else t
    t.loc[day] = row
    return K.component_signals(t, comp)[day]


@pytest.mark.parametrize("change", [dict(s=0.123), dict(available="False"), dict(earliest_fill="late"),
                                    dict(decision_time="same"), dict(s14=0.25), dict(vol=float("nan")),
                                    dict(cap=0.5), dict(version="mom-signal/0.9")],
                         ids=["s_main", "available_str", "earliest_fill", "decision_time", "s14", "vol_nan", "cap", "version"])
def test_adapter_rejects_inconsistent_source_rows(table, change):
    day = pd.Timestamp("2023-05-10", tz="UTC")
    if change.get("earliest_fill") == "late":
        change = dict(earliest_fill=day + pd.Timedelta(days=2))
    if change.get("decision_time") == "same":
        change = dict(decision_time=day)
    with pytest.raises(K.ControlError) as err:
        _row_signal(table, day, **change)
    assert str(err.value)


def test_adapter_keeps_earliest_fill_and_source_fields(table):
    day = pd.Timestamp("2023-05-10", tz="UTC")
    cs = K.component_signals(table, "mom14")[day]
    row = table.loc[day]
    assert cs.earliest_fill == row["earliest_fill"] == cs.decision_time == day + pd.Timedelta(days=1)
    assert (cs.s_main, cs.s7, cs.s14, cs.s28, cs.vol, cs.cap) == (row["s"], row["s7"], row["s14"], row["s28"], row["vol"], row["cap"])


@pytest.mark.parametrize("kw", [dict(adapter_version="x"), dict(source_version="mom-signal/0.9"), dict(day="naiv"),
                                dict(cap=10 ** 5000), dict(vol=True), dict(available=1), dict(component="mom21")],
                         ids=["adapter_version", "source_version", "naiv_dag", "huge", "bool_vol", "available_int", "komponent"])
def test_direct_construction_is_validated(kw):
    good = make_sig(pd.Timestamp("2022-03-01", tz="UTC"), (1, 0, 1), 0.4)
    fields = {f: getattr(good, f) for f in good.__dataclass_fields__}
    if kw.get("day") == "naiv":
        kw = dict(day=pd.Timestamp("2022-03-01"))
    with pytest.raises(K.ControlError) as err:
        K.ComponentSignal(**(fields | kw))
    assert str(err.value)


def test_decisions_in_run_keep_earliest_fill():
    run = K.run_component(market(), "mom7", "A", 0.05)
    assert all(cs.earliest_fill == cs.decision_time for cs in run.decisions)


# D1-02: låst underlag.

def test_market_owns_a_copy_and_detects_later_mutation():
    m0 = market()
    raw_c, raw_m = m0.contract.copy(), m0.mark.copy()
    m = K.Market(raw_c, raw_m)
    raw_c.loc[V.END] = raw_c.iloc[-1]                                  # anroparens tabell ändras efteråt
    raw_m.iloc[100, 0] = 1.0
    assert m.verified() is m and m.contract.index.max() == V.TERMINAL
    m.contract.loc[V.END] = m.contract.iloc[-1]                        # även intern ändring upptäcks
    with pytest.raises(K.ControlError, match="ändrats"):
        K.run_component(m, "mom7", "A", 0.05)
    m2 = K.Market(m0.contract, m0.mark)
    m2.mark.iloc[200, 2] = m2.mark.iloc[200, 2] * 0.5
    with pytest.raises(K.ControlError, match="ändrats"):
        K.run_controls(m2, "A", 0.05)


# D1-03: O5/O5b/O16 genom komponentkompositionen, publik start.

def _o5_sequence(order):
    """mom7: inträde vid första öppningen (cap 0,5), minskning nästa midnatt (cap 0,3, P = 100,5 ≠ M = 100),
    utgång dagen efter (s = 0). Fundingevent exakt vid T, T ± 1 ms och T ± 30 s."""
    r1, r2 = D("0.0001"), D("0.0002")
    T1, T2 = T0 + pd.Timedelta(days=1), T0 + pd.Timedelta(days=2)
    sigs = {T0: make_sig(T0 - pd.Timedelta(days=1), (1, 0, 0), 0.5), T1: make_sig(T0, (1, 1, 0), 0.3),
            T2: make_sig(T1, (0, 1, 1), 0.3)}
    events = {T0: [ev("e0", T0, float(r1), 100.0), ev("p1", T0 + pd.Timedelta(milliseconds=1), float(r1), 100.0),
                   ev("p30", T0 + pd.Timedelta(seconds=30), float(r1), 100.0)],
              T1 - H: [ev("m30", T1 - pd.Timedelta(seconds=30), float(r2), 100.0),
                       ev("m1", T1 - pd.Timedelta(milliseconds=1), float(r2), 100.0)],
              T1: [ev("e1", T1, float(r2), 100.0), ev("q1", T1 + pd.Timedelta(milliseconds=1), float(r2), 100.0),
                   ev("q30", T1 + pd.Timedelta(seconds=30), float(r2), 100.0)],
              T2: [ev("e2", T2, float(r1), 100.0), ev("x30", T2 + pd.Timedelta(seconds=30), float(r1), 100.0)]}
    st = V.EngineState.start(V.Scenario("mom7/L1", order, 0.05))
    res = {}
    T = T0
    while T <= T2:
        P = 100.5 if T == T1 else 100.0
        r = V.process_bar(st, V.Bar(T, P, 100.0, 100.0, 100.0, 100.0), events.get(T, ()),
                          sigs[T].to_input() if T in sigs else None)
        res[T], st = r, r.state
        T += H
    return res, (T1, T2), (r1, r2)


@pytest.mark.parametrize("order", ["A", "B"])
def test_O5_O16_component_entry_decrease_exit(order):
    res, (T1, T2), (r1, r2) = _o5_sequence(order)
    Mk = D(100)
    # Inträde vid första öppningen: E0 = 100 000, q0 = 0.
    q_a = buy_q(D(100_000), D(0), D("0.5"), Mk, Mk)
    first = res[T0]
    ph = [t.phase for t in first.trace if t.phase not in ("margin_basis",)]
    exp_ph = ["decision", "gap", "funding_A", "after_trade", "funding_interior", "funding_interior"] if order == "A" else \
             ["decision", "gap", "after_trade", "funding_B", "after_funding_B", "funding_interior", "funding_interior"]
    assert ph == exp_ph
    trade = next(t for t in first.trace if t.phase == "after_trade")
    E_trade = D(100_000) - c * q_a * Mk
    assert close(trade.q, q_a) and close(trade.E, E_trade) and close(trade.q * 100 / trade.E, D("0.5"))
    sim = next(t for t in first.trace if t.phase in ("funding_A", "funding_B"))
    assert close(sim.funding, 0 if order == "A" else q_a * Mk * r1)           # A på q_old = 0, B på q_new
    if order == "B":
        post = next(t for t in first.trace if t.phase == "after_funding_B")
        assert close(post.E, E_trade - q_a * Mk * r1)
    inter = [t for t in first.trace if t.phase == "funding_interior"]
    assert [t.event_id for t in inter] == ["p1", "p30"] and all(close(t.funding, q_a * Mk * r1) for t in inter)
    # Dag 0:s 20-stapel: mellanevent 23:59:30 och 23:59:59,999 på q_a, dag 0.
    late = [t for t in res[T1 - H].trace if t.phase == "funding_interior"]
    assert [t.event_id for t in late] == ["m30", "m1"] and all(close(t.funding, q_a * Mk * r2) for t in late)
    assert all(t.time.floor("D") == T0 for t in late)
    # Minskning vid T1 med P = 100,5 ≠ M = 100.
    st_before = res[T1].prev_state.account
    E0 = D(repr(st_before.C)) + D(repr(st_before.q)) * Mk
    C_after_A = D(repr(st_before.C)) - (D(repr(st_before.q)) * Mk * r2 if order == "A" else 0)
    E0_trade_base = C_after_A + D(repr(st_before.q)) * Mk
    q_b = sell_q(E0_trade_base, D(repr(st_before.q)), D("0.3"), D("100.5"), Mk)
    dec = next(t for t in res[T1].trace if t.phase == "after_trade")
    assert close(dec.q, q_b) and close(dec.q * 100 / dec.E, D("0.3")) and dec.intent == R.CAP     # w 0,5 > cap 0,3
    sim1 = next(t for t in res[T1].trace if t.phase in ("funding_A", "funding_B"))
    assert close(sim1.funding, (D(repr(st_before.q)) if order == "A" else q_b) * Mk * r2)
    assert [t.event_id for t in res[T1].trace if t.phase == "funding_interior"] == ["q1", "q30"]
    assert all(close(t.funding, q_b * Mk * r2) for t in res[T1].trace if t.phase == "funding_interior")
    gap1 = next(t for t in res[T1].trace if t.phase == "gap")
    assert close(gap1.E, E0)                                                   # gap före A-funding på q_old
    # Utgång vid T2: s7 = 0.
    ex = next(t for t in res[T2].trace if t.phase == "after_trade")
    assert ex.q == 0 and res[T2].step_record.intent.kind == R.FLAT
    sim2 = next(t for t in res[T2].trace if t.phase in ("funding_A", "funding_B"))
    assert close(sim2.funding, q_b * Mk * r1 if order == "A" else 0)
    assert next(t for t in res[T2].trace if t.phase == "funding_interior").funding == 0


@pytest.mark.parametrize("order", ["A", "B"])
def test_terminal_funding_order_in_full_component_run(order):
    base = market()
    Tm = V.TERMINAL
    m0 = float(base.mark.at[Tm, "open"])
    events = [ev("t0", Tm, 0.0001, m0), ev("t30", Tm + pd.Timedelta(seconds=30), 0.0001, m0)]
    run = K.run_component(market(funding=events), "mom7", order, 0.05)
    term = [t for t in run.log.trace if t.bar_open == Tm]
    q_old = next(t for t in term if t.phase == "gap").q
    sim = next(t for t in term if t.phase in ("funding_A", "funding_B"))
    assert sim.phase == f"funding_{order}" and close(sim.funding, D(repr(q_old)) * D(repr(m0)) * D("0.0001") if order == "A" else 0)
    assert next(t for t in term if t.phase == "funding_interior").funding == 0 and run.log.state.account.q == 0
    assert sum(t.phase == "after_trade" for t in term) == 1


# D1-03: band och stopp, exakta gränser (FIXTUR) och publikt flerdygnsförlopp.

def _boundary(f, lo, hi):
    """Minsta float x i [lo, hi] med f(x) sant, f monoton; returnerar (sista falska, första sanna)."""
    while math.nextafter(lo, hi) != hi:
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            break
        if f(mid):
            hi = mid
        else:
            lo = mid
    return lo, hi


def test_band_exact_float_boundary_and_cap_breach_inside_band():
    T = pd.Timestamp("2023-05-02", tz="UTC")
    acct = L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0)       # w = 0,5 exakt
    lo, hi = _boundary(lambda cap: abs(cap - 0.5) >= R.BAND, 0.5, 0.6)
    for cap, trade in ((lo, False), (hi, True)):
        cap_ok = min(1.0, 0.1 / vol_for(cap))
        st = fixture("A", acct, T, 100.0)
        r = V.process_bar(st, V.Bar(T, 100.0, 100.0, 100.0, 100.0, 100.0), (), make_sig(T - pd.Timedelta(days=1), (1, 0, 0), cap_ok).to_input())
        assert (r.step_record.intent is not None) == trade and (cap_ok - 0.5 >= 0.02) == trade
    st = fixture("A", acct, T, 100.0)
    r = V.process_bar(st, V.Bar(T, 100.0, 100.0, 100.0, 100.0, 100.0), (), make_sig(T - pd.Timedelta(days=1), (1, 0, 0), 0.49).to_input())
    assert r.step_record.intent.kind == R.CAP and r.state.account.q < 500                  # capbrott inom band


def test_day_and_permanent_stop_exact_float_boundaries():
    T = pd.Timestamp("2023-05-02", tz="UTC")
    acct = L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0)       # E = 100 000
    sig = make_sig(T - pd.Timedelta(days=1), (1, 0, 0), 0.5).to_input()
    lo, hi = _boundary(lambda ds: 100_000.0 / ds - 1.0 <= R.DAY_STOP, 100_000.0, 110_000.0)
    for ds, stop in ((lo, False), (hi, True)):
        r = V.process_bar(fixture("A", acct, T, 100.0, peak=ds, day_start=ds), V.Bar(T, 100.0, 100.0, 100.0, 100.0, 100.0), (), sig)
        assert (r.step_record.intent is not None and r.step_record.intent.kind == R.DAY) == stop
    acct2 = L.Account(C=40_000.0, q=500.0, deposit=100_000.0, avg_price=120.0)      # E = 90 000
    lo, hi = _boundary(lambda pk: 90_000.0 / pk - 1.0 <= -0.15, 100_000.0, 110_000.0)
    for pk, stop in ((lo, False), (hi, True)):
        r = V.process_bar(fixture("A", acct2, T, 100.0, peak=pk, day_start=90_000.0), V.Bar(T, 100.0, 100.0, 100.0, 100.0, 100.0), (),
                          make_sig(T - pd.Timedelta(days=1), (1, 0, 0), 0.45).to_input())
        assert r.step_record.permanent_triggered == stop


def test_public_component_run_permanent_stop_holds_over_days_and_other_account_unaffected():
    """Publikt: mom7 köper vid start, priset faller > 15 % över dagar; ingen ny köp efter permanent stopp.
    mom14 (platt signal) på samma priser får inga lås."""
    states = {k: V.EngineState.start(V.Scenario(f"{k}/L1", "A", 0.05)) for k in ("mom7", "mom14")}
    subs = {"mom7": (1, 0, 0), "mom14": (1, 0, 0)}
    prices = [100.0] * 6 + [84.0] * 30                                    # > 15 % i en stapel: permanent före dag
    triggered = None
    for i, p in enumerate(prices):
        T = T0 + i * H
        for k in states:
            sig = make_sig(T - pd.Timedelta(days=1), subs[k], 1.0, k).to_input() if T == T.floor("D") else None
            r = V.process_bar(states[k], V.Bar(T, p, p, p, p, p), (), sig)
            states[k] = r.state
            if k == "mom7" and r.step_record.permanent_triggered:
                triggered = T
    s7, s14 = states["mom7"], states["mom14"]
    assert triggered is not None and s7.risk_state.permanent and s7.account.q == 0
    assert not s14.risk_state.permanent and s14.risk_state.lock_day is None and s14.account.q == 0
    assert s14.risk_state.peak == 100_000.0 and s7.risk_state.peak > s14.risk_state.peak - 1   # egna peaks


def test_O6_component_day_stop_with_normal_intent_and_reset():
    o = __import__("json").loads((__import__("pathlib").Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())["O6_dagsreset"]
    T = pd.Timestamp("2023-03-11", tz="UTC")
    acct = L.Account(C=50_000.0, q=1000.0, deposit=100_000.0, avg_price=50.0)
    for order in "AB":
        st = fixture(order, acct, T, 47.9)                                          # FIXTUR
        r = V.process_bar(st, V.Bar(T, 47.55, 47.5, 47.55, 47.5, 47.55), [ev("f", T, 0.0001, 47.5)],
                          make_sig(T - pd.Timedelta(days=1), (1, 1, 1), 0.6).to_input())
        assert r.step_record.intent.kind == R.DAY and (R.NORMAL, "strykt av day_stop") in r.step_record.suppressed
        assert r.state.risk_state.day_start == o["day_start_D1"] and r.state.account.q == 0
        exp = o["A"] if order == "A" else o["B"]
        assert close(r.state.account.equity(47.5), exp["E_efter"])


@pytest.mark.parametrize("cost", [L.COST_NORMAL, L.COST_STRESS])
def test_O14_component_reduce_only_hold_after_gap(cost):
    T = pd.Timestamp("2023-09-05", tz="UTC")
    acct = L.Account(C=80_000.0, q=200.0, deposit=100_000.0, avg_price=100.0)       # O14 ×100 (homogent)
    s = V.Scenario("mom7/L1", "A", 0.05, cost)
    rs = R.RiskState(initial=100_000.0, peak=100_000.0, day_start=100_000.0, next_boundary=T, started=True)
    st = V.EngineState._fixture(s, acct, rs, F.FundingState(s.account_key, s.label), M.MarginState(s.account_key, s.label, 0.05), T, 100.0)
    sig = make_sig(T - pd.Timedelta(days=1), (1, 0, 0), 0.195).to_input()
    down = V.process_bar(st, V.Bar(T, 90.0, 90.0, 90.0, 90.0, 90.0), (), sig)
    hold = next(t for t in down.trace if t.phase == "after_trade")
    assert hold.reason == "risk_reduce_only_hold" and hold.cost == 0 and down.state.account.q == 200


def test_normal_intent_switches_buy_to_sell_after_gap():
    """O15-analog för komponent (O15 självt har s = 1/3): köpbeslut vid close, gap upp gör fyllningen till sälj."""
    T = pd.Timestamp("2023-09-05", tz="UTC")
    acct = L.Account(C=55_000.0, q=450.0, deposit=100_000.0, avg_price=100.0)       # w = 0,45 vid 100
    st = fixture("A", acct, T, 100.0)                                               # FIXTUR
    r = V.process_bar(st, V.Bar(T, 130.0, 130.0, 130.0, 130.0, 130.0), (), make_sig(T - pd.Timedelta(days=1), (1, 0, 0), 0.5).to_input())
    E0 = D(55_000) + D(450) * D(130)
    exp = sell_q(E0, D(450), D("0.5"), D(130), D(130))
    assert r.step_record.intent.kind == R.NORMAL and r.state.account.q < 450 and close(r.state.account.q, exp)


# D1-03: likvidation i komponentkontot (FIXTUR) och absorberande noll till terminal.

def _risky(order, mmr, T):
    acct = L.Account(C=-600_000.0, q=10_000.0, deposit=100_000.0, realized=300_000.0, avg_price=100.0)
    return fixture(order, acct, T, 70.0, peak=101_000.0, day_start=101_000.0, mmr=mmr)


@pytest.mark.parametrize("mmr", M.MMRS)
@pytest.mark.parametrize("order", ["A", "B"])
def test_component_gap_and_intrabar_liquidation(order, mmr):
    T = pd.Timestamp("2023-04-10", tz="UTC")
    g = V.process_bar(_risky(order, mmr, T), V.Bar(T, 55.0, 55.0, 60.0, 50.0, 58.0), [ev("s", T, 0.001, 55.0),
                      ev("i", T + pd.Timedelta(hours=1), -0.01, 55.0)], make_sig(T - pd.Timedelta(days=1), (1, 0, 0), 1.0).to_input())
    rec = g.state.margin_state.record
    sim = D(10_000) * 55 * D("0.001") if order == "A" else D(0)
    assert rec.phase == M.GAP and close(rec.E_before, D(-600_000) + D(10_000) * 55 - sim) and rec.E_before < 0
    assert "after_trade" not in [t.phase for t in g.trace] and g.absorbed == (2 if order == "B" else 1)
    assert g.state.account.reconciliation_gap() == pytest.approx(0, abs=1e-8)
    Ti = T + 2 * H
    pay, rec_ = ev("pay", Ti + pd.Timedelta(minutes=30), 0.02, 64.0), ev("rcv", Ti + pd.Timedelta(hours=2), -0.02, 64.0)
    i = V.process_bar(_risky(order, mmr, Ti), V.Bar(Ti, 64.0, 64.0, 66.0, 58.0, 60.0), [pay, rec_])
    assert i.state.margin_state.liquidated and {u[0] for u in i.unresolved} == {"pay", "rcv"}
    a = i.state.account
    assert a.funding_net == 0 and close(a.liquidation_adjustment, D(600_000) - D(10_000) * 100) and a.C == a.q == 0


def test_absorbing_zero_from_liquidation_through_midnight_to_terminal():
    T = pd.Timestamp("2024-12-30 16:00", tz="UTC")
    st = _risky("A", 0.05, T)
    r = V.process_bar(st, V.Bar(T, 55.0, 55.0, 60.0, 50.0, 58.0))
    adj = r.state.account.liquidation_adjustment
    st, Tk = r.state, T + H
    while True:
        sig = make_sig(Tk - pd.Timedelta(days=1), (1, 1, 1), 1.0).to_input() if Tk == Tk.floor("D") else None
        rr = V.process_bar(st, V.Bar(Tk, 80.0, 80.0, 90.0, 70.0, 80.0), [ev(f"z{Tk.hour}", Tk + pd.Timedelta(hours=1), -0.05, 80.0)], sig)
        assert rr.step_record.intent is None and rr.state.account.C == 0 and rr.state.account.liquidation_adjustment == adj
        assert rr.absorbed == 1 and (rr.close_point is None or rr.close_point[2] == 0.0)
        st = rr.state
        if st.terminated:
            assert rr.terminal_point == (V.TERMINAL, 0.0)
            break
        Tk += H


# D1-03: alla åtta scenarioetiketter och L1/L2-spår.

def _normalized(run):
    return [(t.phase, t.time, t.C, t.q, t.E, t.funding, t.cost, t.event_id) for t in run.log.trace]


@pytest.fixture(scope="module")
def eight():
    m = market(funding=[F.FundingEvent("f", T0 + pd.Timedelta(hours=1), 0.0003, float(market().mark.at[T0, "open"]),
                                       F.MARK_OPEN, T0)])
    return {(o, mmr, l): K.run_component(m, "mom7", o, mmr, l) for o in "AB" for mmr in M.MMRS for l in K.LEGACY_ORDERS}


def test_all_eight_scenario_labels_and_identical_L1_L2_traces(eight):
    keys = {(r.scenario.account_key, r.scenario.label) for r in eight.values()}
    assert len(keys) == 8
    for o in "AB":
        for mmr in M.MMRS:
            a, b = eight[(o, mmr, "L1")], eight[(o, mmr, "L2")]
            assert _normalized(a) == _normalized(b) and a.log.day_ends == b.log.day_ends
            assert a.scenario.account_key != b.scenario.account_key


# D1-03: övriga negativa prov.

def test_more_invalid_markets():
    m = market()
    dup = m.mark.copy()
    dup = pd.concat([dup.iloc[:10], dup.iloc[9:10], dup.iloc[10:]])
    with pytest.raises(K.ControlError):
        K.Market(m.contract, dup)
    huge = m.mark.copy().astype(object)
    huge.iloc[3, 1] = 10 ** 5000
    with pytest.raises(K.ControlError):
        K.Market(m.contract, huge)
    with pytest.raises(K.ControlError):
        K.Market(m.contract, m.mark, funding="inte en lista")
