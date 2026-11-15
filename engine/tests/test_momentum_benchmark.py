"""mom-bh/1.0.0 och eventlagrets buy_and_hold-väg (H-0026, tidigare H-0017, leverans D2). Endast syntetiska data.

Facit ur docs/momentum-a1-orakel.json och oberoende Decimal: inträde q = 100 000 / (P(1 + c)) vid platt start och w = 1
(§6), E_trade = q·M, därefter fasta enheter; belopp = q·M_ref·ränta. Fall som behöver ett tillstånd mitt i horisonten
använder eventlagrets privata fixturväg och är märkta FIXTUR; publika förlopp startar i EngineState.start.
"""
import dataclasses
import json
import math
from decimal import Decimal as D, getcontext
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from traderlab import momentum_benchmark as BH
from traderlab import momentum_control as K
from traderlab import momentum_event as V
from traderlab import momentum_funding as F
from traderlab import momentum_ledger as L
from traderlab import momentum_margin as M
from traderlab import momentum_risk as R

from test_momentum_control import make_sig, market

getcontext().prec = 60
ORACLE = json.loads((Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())
H = V.BAR
T0 = V.START
c = D(repr(L.COST_NORMAL))


def bh(order="A", mmr=0.05, key="buy_and_hold/L1"):
    return V.Scenario(key, order, mmr, policy=V.BUY_AND_HOLD)


def ev(eid, t, rate, Mref):
    return F.FundingEvent(eid, t, rate, Mref, F.MARK_OPEN, F.bar_open(t))


def close(a, b, rel=1e-12):
    return a == pytest.approx(float(b), rel=rel, abs=1e-9)


def run_bars(scenario, bars, events=None, signals=None):
    """Publikt förlopp från EngineState.start genom givna (T, P, O, H, L, C)."""
    st = V.EngineState.start(scenario)
    log = V.RunLog.begin(st)
    out = []
    for T, P, o, h, l, cl in bars:
        r = V.process_bar(st, V.Bar(T, P, o, h, l, cl), (events or {}).get(T, ()), (signals or {}).get(T))
        log, st = log.add(r), r.state
        out.append(r)
    return st, log, out


# O2 och basis.

def test_O2_full_weight_entry_after_cost():
    o = ORACLE["O2_avgift_w1"]
    st, _, res = run_bars(bh(), [(T0, 100.0, 100.0, 100.0, 100.0, 100.0)])
    a = st.account
    assert a.q == pytest.approx(o["q"], rel=1e-12) and a.costs == pytest.approx(o["cost"], rel=1e-12)
    assert a.equity(100.0) == pytest.approx(o["E_after"], rel=1e-12) and a.q != 1000
    assert a.C == pytest.approx(o["C"], abs=1e-9)                       # floatresten klipps inte bort
    trade = next(t for t in res[0].trace if t.phase == "after_trade")
    assert trade.reason == V.BH_RULE and trade.intent == R.NORMAL


@pytest.mark.parametrize("P", [101.0, 99.0])
def test_entry_with_basis_P_ne_M(P):
    st, _, res = run_bars(bh(), [(T0, P, 100.0, 100.0, 100.0, 100.0)])
    q = D(100_000) / (D(repr(P)) * (1 + c))
    assert close(st.account.q, q) and close(next(t for t in res[0].trace if t.phase == "after_trade").E, q * 100)


# Fasta enheter, ingen momentumrisk.

def _crash_path():
    """Dag 0 inträde vid 100. Därefter fall genom −2 %, −15 % och −20 % per close (ingen marginalträff: C ≈ 0),
    sedan kraftig uppgång."""
    prices = [100.0] * 6 + [97.9] * 6 + [84.9] * 6 + [79.9] * 6 + [60.0] * 6 + [150.0] * 6
    return [(T0 + k * H, p, p, p, p, p) for k, p in enumerate(prices)]


def test_fixed_units_no_cap_band_or_stops():
    bars = _crash_path()
    q_entry = D(100_000) / (D(100) * (1 + c))
    Tpay, Trecv = T0 + 8 * H + pd.Timedelta(minutes=30), T0 + 20 * H
    events = {Tpay.floor("4h"): [ev("pay", Tpay, 0.001, 97.9)], Trecv: [ev("recv", Trecv, -0.002, 79.9)]}
    st, log, res = run_bars(bh("B"), bars, events)
    qs = [r.state.account.q for r in res]
    assert all(q == qs[0] for q in qs) and close(qs[0], q_entry)
    assert sum(1 for r in res for t in r.trace if t.phase == "after_trade" and t.cost > 0) == 1
    assert all(r.step_record.daily_decision is None and not r.step_record.permanent_triggered
               and not r.step_record.day_stop_triggered for r in res)
    assert not st.risk_state.permanent and st.risk_state.lock_day is None
    # Funding bokförd men aldrig återinvesterad: q oförändrat, C rör sig med beloppen.
    paid = q_entry * D("97.9") * D("0.001")
    recv = q_entry * D("79.9") * D("-0.002")
    C = D(100_000) - q_entry * 100 * (1 + c) - paid - recv
    assert close(st.account.C, C) and close(st.account.funding_net, paid + recv)
    # Samma prisbana för ett momentumkonto (s = 1, cap = 1) utlöser stopp: buy_and_hold försvagar inte main.
    sigs = {T: make_sig(T - pd.Timedelta(days=1), (1, 1, 1), 1.0).to_input() for T, *_ in bars if T == T.floor("D")}
    stm, _, resm = run_bars(V.Scenario("mom7/L1", "B", 0.05), bars, events, sigs)
    stops = [i for i, r in enumerate(resm) if r.step_record.day_stop_triggered or r.step_record.permanent_triggered]
    assert stops and resm[stops[0]].state.account.q == 0                 # momentumkontot säljer ut vid stoppet


def test_weight_above_one_after_B_funding_is_not_rebalanced():
    st, _, res = run_bars(bh("B"), [(T0, 100.0, 100.0, 100.0, 100.0, 100.0), (T0 + H, 100.0, 100.0, 100.0, 100.0, 100.0)],
                          {T0: [ev("f", T0, 0.001, 100.0)]})
    post = next(t for t in res[0].trace if t.phase == "after_funding_B")
    assert post.q * 100 / post.E > 1 and res[1].state.account.q == res[0].state.account.q


def test_constant_close_market_is_accepted_but_momentum_still_requires_signal():
    idx = pd.date_range(K.WARMUP_START, V.TERMINAL, freq=H)
    contract = pd.DataFrame({"open": 100.0, "close": 100.0}, index=idx)
    mark = pd.DataFrame({"open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0}, index=K.TEST_BARS)
    m = K.Market(contract, mark)
    run = BH.run_buy_and_hold(m, "A", 0.05)
    assert len(run.log.day_ends) == 1096 and run.log.state.account.q == 0
    with pytest.raises(K.ControlError, match="otillgänglig"):
        K.run_component(m, "mom7", "A", 0.05)                       # D1:s signalkrav består


# O5/O16: funding vid exakta tider i A och B.

@pytest.mark.parametrize("order", ["A", "B"])
@pytest.mark.parametrize("rate", ["0.0001", "-0.0002", "0"])
def test_funding_times_entry_midnight_and_terminal(order, rate):
    r_ = D(rate)
    q = D(100_000) / (D(100) * (1 + c))
    Tm = T0 + 6 * H                                                    # första midnatt efter start
    evs = {T0: [ev("e0", T0, float(r_), 100.0), ev("p1", T0 + pd.Timedelta(milliseconds=1), float(r_), 100.0),
                ev("p30", T0 + pd.Timedelta(seconds=30), float(r_), 100.0)],
           Tm - H: [ev("m30", Tm - pd.Timedelta(seconds=30), float(r_), 100.0), ev("m1", Tm - pd.Timedelta(milliseconds=1), float(r_), 100.0)],
           Tm: [ev("t0", Tm, float(r_), 100.0), ev("t1", Tm + pd.Timedelta(milliseconds=1), float(r_), 100.0)]}
    bars = [(T0 + k * H, 100.0, 100.0, 100.0, 100.0, 100.0) for k in range(8)]
    st, log, res = run_bars(bh(order), bars, evs)
    fund = {t.event_id: t for r in res for t in r.trace if t.event_id}
    assert fund["e0"].phase == f"funding_{order}" and close(fund["e0"].funding, 0 if order == "A" else q * 100 * r_)
    for eid in ("p1", "p30", "m30", "m1", "t1"):
        assert fund[eid].phase == "funding_interior" and close(fund[eid].funding, q * 100 * r_)
    assert fund["t0"].phase == f"funding_{order}" and close(fund["t0"].funding, q * 100 * r_)   # hold: A = B
    assert fund["m1"].time.floor("D") == T0 and fund["t1"].time.floor("D") == Tm
    assert st.funding_state.processed == set(fund)


def test_pre_start_and_2025_funding_handled_before_economics():
    base = market()
    pre = F.FundingEvent("pre", T0 - pd.Timedelta(seconds=30), 0.0001, 100.0, F.MARK_OPEN, T0 - H)
    run = BH.run_buy_and_hold(market(funding=[pre]), "A", 0.05)
    assert run.ignored_pre_start == 1 and "pre" not in run.log.state.funding_state.processed
    with pytest.raises(K.ControlError, match="2025"):
        K.Market(base.contract, base.mark, (F.FundingEvent("late", V.END, 0.0001, 100.0, F.MARK_OPEN, V.END),))
    m = K.Market(base.contract, base.mark)
    m.mark.iloc[50, 0] *= 1.01
    with pytest.raises(K.ControlError, match="ändrats"):
        BH.run_buy_and_hold(m, "A", 0.05)


# O10 och full kalender, alla åtta etiketter, oberoende ledger.

def _funding_market():
    base = market(mark_shift=1.002)                                    # P ≠ M överallt
    picks = [T0 + 30 * H, T0 + 31 * H + pd.Timedelta(hours=1), T0 + 900 * H, T0 + 4000 * H + pd.Timedelta(minutes=5),
             V.TERMINAL, V.TERMINAL + pd.Timedelta(seconds=30)]
    rates = [0.0003, -0.0005, 0.0001, -0.0002, 0.0004, 0.0001]
    evs = [F.FundingEvent(f"f{i}", t, r, float(base.mark.at[t.floor("4h"), "open"]), F.MARK_OPEN, t.floor("4h"))
           for i, (t, r) in enumerate(zip(picks, rates))]
    return K.Market(base.contract, base.mark, tuple(evs)), dict(zip([e.event_id for e in evs], zip(picks, rates)))


@pytest.fixture(scope="module")
def eight():
    m, _ = _funding_market()
    return m, {(o, mmr, l): BH.run_buy_and_hold(m, o, mmr, l) for o in "AB" for mmr in M.MMRS for l in K.LEGACY_ORDERS}


def test_eight_labels_independent_ledger_every_close_and_terminal(eight):
    m, runs = eight
    _, fund = _funding_market()
    c_ = m.contract
    mk = m.mark
    assert len({(r.scenario.account_key, r.scenario.label) for r in runs.values()}) == 8      # skilda identiteter
    for (o, mmr, l), run in runs.items():
        log = run.log
        assert len(log.close_points) == 6577 and len(log.day_ends) == 1096 and run.scenario.label.startswith("buy_and_hold-")
        P0, M0 = D(repr(float(c_.at[T0, "open"]))), D(repr(float(mk.at[T0, "open"])))
        q = D(100_000) / (P0 * (1 + c))
        C = D(100_000) - q * P0 * (1 + c)
        by_bar = {}
        for eid, (t, r) in fund.items():
            by_bar.setdefault(t.floor("4h"), []).append((t, r))
        expected = {}
        for T in K.TEST_BARS:
            Mref = D(repr(float(mk.at[T, "open"])))
            for t, r in sorted(by_bar.get(T, [])):
                if T == V.TERMINAL and (o == "B" or t > T):
                    continue                                           # terminal: B och senare event möter q = 0
                C -= q * Mref * D(repr(r))
            if T == V.TERMINAL:
                C += q * D(repr(float(c_.at[T, "open"]))) * (1 - c)
                expected[T] = C
            else:
                expected[T] = C + q * D(repr(float(mk.at[T, "close"])))
        for src, known, E in log.close_points[1:]:
            assert close(E, expected[src], rel=1e-11)
        assert close(log.day_ends[-1][1], expected[V.TERMINAL], rel=1e-11)
        q_live = [t.q for t in log.trace if t.phase == "after_trade"]
        assert q_live[0] == q_live[0] and close(q_live[0], q) and q_live[-1] == 0


def test_L1_L2_traces_identical_and_A_B_differ_only_by_entry_and_terminal(eight):
    _, runs = eight
    norm = lambda r: [(t.phase, t.time, t.C, t.q, t.E, t.funding, t.cost, t.event_id) for t in r.log.trace]
    for o in "AB":
        for mmr in M.MMRS:
            assert norm(runs[(o, mmr, "L1")]) == norm(runs[(o, mmr, "L2")])
    assert runs[("A", 0.05, "L1")].log.day_ends != runs[("B", 0.05, "L1")].log.day_ends


def test_O10_local_terminal_fixture():
    o = ORACLE["O10_horisont"]
    s = bh("B")
    acct = L.Account(C=60_000.0, q=400.0, deposit=100_000.0, realized=-2_000.0, avg_price=95.0)
    rs = R.RiskState(initial=100_000.0, peak=100_000.0, day_start=100_000.0, next_boundary=V.TERMINAL, started=True)
    st = V.EngineState._fixture(s, acct, rs, F.FundingState(s.account_key, s.label), M.MarginState(s.account_key, s.label, 0.05),
                                V.TERMINAL, 95.0)                     # FIXTUR
    r = V.process_bar(st, V.Bar(V.TERMINAL, 95.1, 95.0, 95.1, 95.0, 95.1))
    trade = next(t for t in r.trace if t.phase == "after_trade")
    assert close(trade.cost, o["terminal_kostnad"]) and close(r.terminal_point[1], o["terminal_E"]) and r.state.account.q == 0


# O11/O18: likvidation i buy_and_hold.

def _threshold(mmr, paid=D(500)):
    q = D(100_000) / (D(100) * (1 + c))
    C = D(100_000) - q * 100 * (1 + c) - paid
    return q, C, -C / (q * (1 - D(repr(mmr))))


def test_O11_threshold_after_paid_funding():
    _, _, m05 = _threshold(0.05)
    assert float(m05) == pytest.approx(0.5271578947368453, rel=1e-9)


@pytest.mark.parametrize("mmr", M.MMRS)
def test_public_gap_liquidation_at_float_boundary(mmr):
    q, C, m_star = _threshold(mmr)
    rate = float(D(500) / (q * 100))
    base = [(T0, 100.0, 100.0, 100.0, 100.0, 100.0)]
    evs = {T0 + H: [ev("pay", T0 + H + pd.Timedelta(minutes=10), rate, 100.0)]}
    st0, _, _ = run_bars(bh("A", mmr), base + [(T0 + H, 100.0, 100.0, 100.0, 100.0, 100.0)], evs)
    a = st0.account
    hit = lambda mk: a.C + a.q * mk <= mmr * abs(a.q) * mk               # samma floatvillkor som marginalprövningen
    lo, hi = float(m_star) * 0.9, float(m_star) * 1.1
    while math.nextafter(lo, hi) != hi:
        mid = (lo + hi) / 2
        if mid in (lo, hi):
            break
        lo, hi = (lo, mid) if hit(mid) else (mid, hi)
    for mk, expect in ((lo, False), (hi, True), (math.nextafter(lo, 0.0), False)):
        r = V.process_bar(st0, V.Bar(T0 + 2 * H, mk, mk, mk, mk, mk))
        assert r.state.margin_state.liquidated == (expect or hit(mk)) == hit(mk)
    deep = V.process_bar(st0, V.Bar(T0 + 2 * H, 0.4, 0.4, 0.4, 0.4, 0.4))
    assert deep.state.margin_state.record.E_before < 0 and deep.state.account.C == deep.state.account.q == 0


def test_mmr_scenarios_differ_and_intrabar_unresolved_then_absorbing():
    q, C, _ = _threshold(0.05)
    rate = float(D(500) / (q * 100))
    bars = [(T0, 100.0, 100.0, 100.0, 100.0, 100.0), (T0 + H, 100.0, 100.0, 100.0, 100.0, 100.0)]
    evs = {T0 + H: [ev("pay", T0 + H + pd.Timedelta(minutes=10), rate, 100.0)]}
    res = {}
    for mmr in M.MMRS:
        st, _, _ = run_bars(bh("A", mmr), bars, evs)
        res[mmr] = V.process_bar(st, V.Bar(T0 + 2 * H, 0.515, 0.515, 0.515, 0.515, 0.515)).state.margin_state.liquidated
    assert res[0.05] and not res[0.005]
    st, _, _ = run_bars(bh("B", 0.05), bars, evs)
    T = T0 + 2 * H
    mixed = [ev("p", T + pd.Timedelta(minutes=5), 0.02, 50.0), ev("r", T + pd.Timedelta(minutes=50), -0.02, 50.0)]
    r = V.process_bar(st, V.Bar(T, 50.0, 50.0, 51.0, 0.6, 0.6), mixed)
    assert r.state.margin_state.record.phase == M.INTRABAR and {u[0] for u in r.unresolved} == {"p", "r"}
    a = r.state.account
    assert a.funding_net == st.account.funding_net and a.C == a.q == 0 and a.reconciliation_gap() == pytest.approx(0, abs=1e-6)
    s2 = r.state
    for k in range(1, 8):
        Tk = T + k * H
        rr = V.process_bar(s2, V.Bar(Tk, 80.0, 80.0, 90.0, 70.0, 80.0), [ev(f"z{k}", Tk + pd.Timedelta(hours=1), -0.05, 80.0)])
        assert rr.absorbed == 1 and rr.state.account == a and rr.step_record.intent is None
        assert rr.state.risk_state.liquidated                            # kontoregeln vet om likvidationen
        s2 = rr.state


def test_liquidated_buy_and_hold_gets_no_terminal_intent():
    s = bh("A")
    acct = L.Account(C=-600_000.0, q=10_000.0, deposit=100_000.0, realized=300_000.0, avg_price=100.0)
    rs = R.RiskState(initial=100_000.0, peak=101_000.0, day_start=101_000.0, next_boundary=V.TERMINAL - 2 * H, started=True)
    st = V.EngineState._fixture(s, acct, rs, F.FundingState(s.account_key, s.label), M.MarginState(s.account_key, s.label, 0.05),
                                V.TERMINAL - 2 * H, 70.0)              # FIXTUR
    r = V.process_bar(st, V.Bar(V.TERMINAL - 2 * H, 55.0, 55.0, 60.0, 50.0, 58.0))
    assert r.state.margin_state.liquidated
    st = r.state
    for T in (V.TERMINAL - H, V.TERMINAL):
        rr = V.process_bar(st, V.Bar(T, 60.0, 60.0, 60.0, 60.0, 60.0))
        assert rr.step_record.intent is None and rr.state.risk_state.liquidated and rr.state.account.C == 0
        st = rr.state
    assert st.terminated and rr.terminal_point == (V.TERMINAL, 0.0)


# Isolering, policy och fel.

def test_momentum_label_and_path_unchanged():
    assert V.Scenario("main", "A", 0.05).label == "A-mmr0.05-c0.0016"
    assert bh().label == "buy_and_hold-A-mmr0.05-c0.0016"
    m = market()
    before = K.run_component(m, "mom7", "A", 0.05).log.day_ends
    BH.run_buy_and_hold(m, "A", 0.05)
    assert K.run_component(m, "mom7", "A", 0.05).log.day_ends == before


def test_policy_binding_and_errors():
    st = V.EngineState.start(bh())
    with pytest.raises(V.EventError, match="ingen signal"):
        V.process_bar(st, V.Bar(T0, 100.0, 100.0, 100.0, 100.0, 100.0), (), make_sig(T0 - pd.Timedelta(days=1), (1, 1, 1), 1.0).to_input())
    with pytest.raises(V.EventError, match="skapas bara|hör inte"):
        dataclasses.replace(st, scenario=V.Scenario("buy_and_hold/L1", "A", 0.05))      # policybyte: etiketten binder policyn
    for bad in ("hold", "", None, True):
        with pytest.raises(V.EventError):
            V.Scenario("x", "A", 0.05, policy=bad)
    r = V.process_bar(V.EngineState.start(bh(key="annat")), V.Bar(T0, 100.0, 100.0, 100.0, 100.0, 100.0))
    with pytest.raises(V.EventError, match="följer inte"):
        V.RunLog.begin(st).add(r)
    with pytest.raises(K.ControlError):
        BH.run_buy_and_hold(market(), "A", 0.05, "L3")
    with pytest.raises(K.ControlError):
        BH.run_buy_and_hold("inte en marknad", "A", 0.05)


def test_prefix_later_prices_do_not_change_earlier_points():
    a = BH.run_buy_and_hold(market(), "A", 0.05)
    m2 = market()
    contract, mark = m2.contract.copy(), m2.mark.copy()
    cut = pd.Timestamp("2023-06-01", tz="UTC")
    contract.loc[cut:, ["open", "close"]] *= 1.3
    mark.loc[cut:, :] *= 1.3
    b = BH.run_buy_and_hold(K.Market(contract, mark), "A", 0.05)
    assert [cp for cp in a.log.close_points if cp[1] <= cut] == [cp for cp in b.log.close_points if cp[1] <= cut]
