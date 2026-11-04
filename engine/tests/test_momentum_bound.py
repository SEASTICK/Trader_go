"""mom-bound/1.0.0 (H-0017 leverans C6) på syntetiska staplar, event och signalrader. Ingen marknadshistorik.

Facit från docs/momentum-a1-orakel.json (O7) och handräkning/Decimal, aldrig från boundfunktionen. Träffstaplar följer
C6-01-tillägget (docs/momentum-C6-01-edwins-beslut.md: H1, I1, G1, P1). Mitt-i-horisonten-tillstånd byggs med eventlagrets
privata fixturväg; ett fixturtillstånd kan inte börja en BoundLog, så punkter för sådana staplar prövas med bar_points och
en fristående peakfold i testet.
"""
import dataclasses
import json
from decimal import Decimal as D, getcontext
from pathlib import Path

import pandas as pd
import pytest

from traderlab import momentum_bound as B
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
T_MID = pd.Timestamp("2023-04-10 08:00", tz="UTC")       # ingen midnatt: ingen avsikt


def close(a, b):
    return a == pytest.approx(float(b), rel=1e-12, abs=1e-9)


def sc(order="A", mmr=0.05, cost=L.COST_NORMAL, key="main"):
    return V.Scenario(key, order, mmr, cost)


def sig(T, s, cap):
    return R.SignalInput(T - pd.Timedelta(days=1), T, True, s, cap, s * cap, S.VERSION)


def ev(eid, t, rate, Mref):
    return F.FundingEvent(eid, t, rate, Mref, F.MARK_OPEN, F.bar_open(t))


def fixture(scenario, acct, T, prev_mark, *, peak=100_000.0, day_start=100_000.0):
    rs = R.RiskState(initial=100_000.0, peak=peak, day_start=day_start, next_boundary=T, started=True)
    return V.EngineState._fixture(scenario, acct, rs, F.FundingState(scenario.account_key, scenario.label),
                                  M.MarginState(scenario.account_key, scenario.label, scenario.mmr), T, prev_mark)


def fold(points, peak, minimum=0.0):
    """Fristående peak-/drawdownfold i Decimal (testets facit, inte modulens)."""
    peak, minimum, dds = D(repr(peak)), D(repr(minimum)), []
    for p in points:
        E = D(repr(p["E"]))
        peak = max(peak, E)
        dds.append(E / peak - 1)
        minimum = min(minimum, dds[-1])
    return peak, minimum, dds


def phases(points):
    return [p["phase"] if isinstance(p, dict) else p.phase for p in points]


# O7: lokalt orakel och ett verkligt sekventiellt förlopp.

def test_O7_local_points_and_bound_against_oracle():
    o = ORACLE["O7_intrastapel_main"]
    acct = L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0)
    st = fixture(sc(), acct, T_MID, 100.0, peak=105_000.0, day_start=100_000.0)
    r = V.process_bar(st, V.Bar(T_MID, 100.0, 100.0, 112.0, 95.0, 101.0))
    pts = B.bar_points(r)
    assert phases(pts) == ["open", "trade", "post", "high", "low", "close"]
    E = {p["phase"]: p["E"] for p in pts}
    assert (E["open"], E["high"], E["low"], E["close"]) == (o["E_open"], o["E_high"], o["E_low"], o["E_close"])
    peak, minimum, _ = fold(pts, 105_000.0)
    assert peak == o["bound_peak"] and float(minimum) == pytest.approx(o["bound_dd"], rel=1e-14)
    assert E["low"] / E["high"] - 1.0 == o["bound_dd"]                  # samma float-uträkning som oraklet
    assert float(D(o["E_close"]) / D(105_000) - 1) == pytest.approx(o["close_dd"], rel=1e-15)   # separat close-DD
    assert r.step_record.intent is None and r.state.risk_state.peak == 105_000.0     # bounden matar inte close-peak


def test_sequential_run_from_start_matches_independent_decimal():
    st = V.EngineState.start(sc())
    log = B.BoundLog.begin(st)
    r = V.process_bar(st, V.Bar(T0, 100.0, 100.0, 112.0, 95.0, 101.0), (), sig(T0, 1.0, 0.5))
    log = log.add(r)
    c, w = D(repr(L.COST_NORMAL)), D("0.5")
    q = w * D(100_000) / (D(100) + w * c * D(100))                  # q·M = w·E_trade, E_trade = 100 000 − c·q·P
    C = D(100_000) - q * D(100) - c * q * D(100)
    exp = [D(100_000), D(100_000), C + q * 100, C + q * 100, C + q * 112, C + q * 95, C + q * 101]
    assert phases(log.points) == ["start", "open", "trade", "post", "high", "low", "close"]
    assert all(close(p.E, e) for p, e in zip(log.points, exp))
    peak, minimum, dds = fold([{"E": float(e)} for e in exp], 100_000.0)
    assert close(log.peak, peak) and close(log.max_dd_bound, minimum) and log.max_dd_bound_mag == -log.max_dd_bound
    assert all(close(p.drawdown, d) for p, d in zip(log.points, dds))
    assert log.points[0].time == T0 and log.points[0].bar_open is None            # start före första kostnaden
    assert log.points[4].time == V.UNKNOWN_TIME and log.points[5].time == V.UNKNOWN_TIME
    assert log.max_dd_close == 0.0 and log.run.close_points == ((None, T0, 100_000.0),)


# Fundingbas för high/low utan träff (§10.2) och B:s skilda E_trade/E_post.

@pytest.mark.parametrize("order", ["A", "B"])
@pytest.mark.parametrize("credit_first", [False, True])
@pytest.mark.parametrize("with_sim", [False, True])
def test_interior_funding_bases_without_hit(order, credit_first, with_sim):
    acct = L.Account(C=50_000.0, q=500.0, deposit=100_000.0, avg_price=100.0)
    st = fixture(sc(order), acct, T_MID, 100.0)
    rates = {"pay": "0.001", "pay2": "0.0005", "recv": "-0.002", "recv2": "-0.0004", "zero": "0"}
    names = ["recv", "recv2", "zero", "pay", "pay2"] if credit_first else ["pay", "pay2", "zero", "recv", "recv2"]
    events = [ev(n, T_MID + pd.Timedelta(minutes=20 * (k + 1)), float(rates[n]), 100.0) for k, n in enumerate(names)]
    if with_sim:
        events = [ev("sim", T_MID, 0.0003, 100.0)] + events
    r = V.process_bar(st, V.Bar(T_MID, 100.0, 100.0, 104.0, 97.0, 101.0), events)
    q = D(500)
    p = {n: q * 100 * D(v) for n, v in rates.items()}
    sim = q * 100 * D("0.0003") if with_sim else D(0)
    C_post = D(50_000) - sim
    C_high = C_post - sum(min(x, 0) for x in p.values())
    C_low = C_post - sum(max(x, 0) for x in p.values())
    pts = {x["phase"]: x for x in B.bar_points(r)}
    gap_E = D(50_000) + q * 100                                       # före A-funding
    assert close(pts["open"]["E"], gap_E) and close(pts["post"]["C"], C_post)
    assert close(pts["trade"]["C"], D(50_000) - (sim if order == "A" else 0))     # B: samtidig efter E_trade
    assert close(pts["high"]["C"], C_high) and close(pts["high"]["E"], C_high + q * 104)
    assert close(pts["low"]["C"], C_low) and close(pts["low"]["E"], C_low + q * 97)
    assert close(pts["high"]["hypothetical_funding"], sum(min(x, 0) for x in p.values()))
    assert close(pts["low"]["hypothetical_funding"], sum(max(x, 0) for x in p.values()))
    assert close(pts["close"]["C"], C_post - sum(p.values())) and close(pts["close"]["E"], C_post - sum(p.values()) + q * 101)
    assert close(r.state.account.funding_net, sim + sum(p.values()))           # ledgern: varje post en gång
    assert [t.event_id for t in r.trace if t.phase == "funding_interior"] == names


def test_B_trade_and_post_differ_on_entry_with_simultaneous_funding():
    st = V.EngineState.start(sc("B"))
    r = V.process_bar(st, V.Bar(T0, 100.0, 100.0, 101.0, 99.0, 100.0), [ev("f0", T0, 0.0001, 100.0)], sig(T0, 1.0, 0.5))
    pts = {x["phase"]: x for x in B.bar_points(r)}
    assert pts["trade"]["E"] > pts["post"]["E"] and close(pts["trade"]["E"] - pts["post"]["E"], pts["post"]["q"] * 100 * 0.0001)
    assert pts["high"]["q"] == pts["post"]["q"] > 0                       # high/low på q efter öppningen


def test_partial_sale_uses_q_after_open_for_extremes():
    acct = L.Account(C=0.0, q=1000.0, deposit=100_000.0, avg_price=100.0)
    T = pd.Timestamp("2023-04-11", tz="UTC")
    st = fixture(sc(), acct, T, 100.0)
    r = V.process_bar(st, V.Bar(T, 100.0, 100.0, 110.0, 90.0, 100.0), (), sig(T, 1.0, 0.5))
    pts = {x["phase"]: x for x in B.bar_points(r)}
    q_open = r.state.account.q
    assert 0 < q_open < 1000 and pts["open"]["q"] == 1000 and pts["high"]["q"] == pts["low"]["q"] == q_open
    assert close(pts["high"]["E"], D(repr(pts["post"]["C"])) + D(repr(q_open)) * 110)


# Ingen återkoppling till handel.

def _run(lows, highs, n=13):
    st = V.EngineState.start(sc())
    log = B.BoundLog.begin(st)
    for k in range(n):
        T = T0 + k * H
        m = 100.0 + (k % 3)
        r = V.process_bar(st, V.Bar(T, m, m, max(highs[k], m), min(lows[k], m), m), (),
                          sig(T, 1.0, 0.5) if T == T.floor("D") else None)
        log, st = log.add(r), r.state
    return log


def test_extremes_change_only_the_bound():
    a = _run([99.0] * 13, [103.0] * 13)
    b = _run([60.0] * 13, [180.0] * 13)                               # high över peak, low > 20 % ned, ingen träff
    assert a.run.close_points == b.run.close_points and a.run.day_ends == b.run.day_ends
    assert a.run.state.account == b.run.state.account and a.run.state.risk_state == b.run.state.risk_state
    assert [t for t in a.run.trace if t.phase != "margin_basis"] == [t for t in b.run.trace if t.phase != "margin_basis"]
    assert b.max_dd_bound_mag > 0.20 and a.max_dd_bound_mag < 0.20 and b.peak > a.peak
    assert not b.run.state.risk_state.permanent and b.run.state.risk_state.lock_day is None


def test_running_peak_and_minimum_over_midnights_match_independent_fold():
    log = _run([90.0, 99.0, 70.0] * 5, [150.0, 103.0, 101.0] * 5, n=15)      # passerar två midnätter
    _, minimum, dds = fold([{"E": p.E} for p in log.points], 100_000.0)
    assert all(close(p.drawdown, d) for p, d in zip(log.points, dds)) and close(log.max_dd_bound, minimum)
    peaks = []
    peak = D(100_000)
    for p in log.points:
        peak = max(peak, D(repr(p.E)))
        peaks.append(peak)
    assert all(close(p.peak, pk) for p, pk in zip(log.points, peaks)) and peaks[-1] > 100_000   # ingen reset per dag


def test_later_bars_never_change_earlier_points():
    a, b = _run([99.0] * 13, [103.0] * 13), _run([99.0] * 12 + [50.0], [103.0] * 12 + [300.0])
    k = len(a.points) - 6
    assert a.points[:k] == b.points[:k]


def test_O6_day_reset_unchanged_with_bound():
    o = ORACLE["O6_dagsreset"]
    T = pd.Timestamp("2023-03-11", tz="UTC")
    acct = L.Account(C=50_000.0, q=1000.0, deposit=100_000.0, avg_price=50.0)
    st = fixture(sc(), acct, T, 47.9)
    r = V.process_bar(st, V.Bar(T, 47.55, 47.5, 60.0, 47.5, 47.55), [ev("f", T, 0.0001, 47.5)], sig(T, 1.0, 0.6))
    assert r.state.risk_state.day_start == o["day_start_D1"] and r.state.account.q == 0
    pts = B.bar_points(r)
    assert phases(pts) == ["open", "trade", "post", "high", "low", "close"] and pts[3]["q"] == 0   # inga gamla extremer


# Start, terminal och platt konto.

@pytest.mark.parametrize("order", ["A", "B"])
def test_terminal_points_once_without_old_exposure(order):
    o = ORACLE["O10_horisont"]
    acct = L.Account(C=60_000.0, q=400.0, deposit=100_000.0, realized=-2_000.0, avg_price=95.0)
    st = fixture(sc(order), acct, V.TERMINAL, 95.0, peak=110_000.0, day_start=98_000.0)
    events = [ev("t0", V.TERMINAL, 0.0001, 95.0), ev("t1", V.TERMINAL + pd.Timedelta(seconds=30), 0.0001, 95.0)]
    r = V.process_bar(st, V.Bar(V.TERMINAL, 95.1, 95.0, 120.0, 50.0, 95.1), events)
    pts = B.bar_points(r)
    assert phases(pts) == ["open", "trade", "post", "terminal"]
    assert close(pts[0]["E"], D(60_000) + D(400) * D(95)) and close(pts[-1]["E"], r.terminal_point[1])
    assert all(p["q"] == 0 for p in pts[1:])
    assert close(pts[0]["E"], o["E_fore_terminal"]) and close(pts[1]["E"] - pts[0]["E"], 0) is False
    sim_term = D(400) * D(95) * D("0.0001") if order == "A" else D(0)
    assert close(pts[-1]["E"], D(repr(o["terminal_E"])) - sim_term)          # O10: B 97 979,136, A 97 975,336
    sim_A = D(400) * D(95) * D("0.0001") if order == "A" else D(0)
    k = D(400) * D("95.1") * D(repr(L.COST_NORMAL))                   # stängningskostnad vid P = 95,1
    assert close(pts[1]["E"], D(60_000) - sim_A + D(400) * D("95.1") - k)
    assert close(pts[1]["C"] - pts[2]["C"], 0) and close(pts[2]["E"], pts[3]["E"])


def test_full_flat_horizon_counts_and_zero_drawdown():
    st = V.EngineState.start(sc())
    log = B.BoundLog.begin(st)
    T = T0
    while True:
        r = V.process_bar(st, V.Bar(T, 100.0, 100.0, 130.0, 70.0, 100.0), (), sig(T, 0.0, 0.5) if T == T.floor("D") else None)
        log, st = log.add(r), r.state
        if st.terminated:
            break
        T += H
    assert len(log.run.close_points) == 6577 and len(log.run.day_ends) == 1096
    assert len(log.points) == 1 + 6575 * 6 + 4 and log.max_dd_bound == 0.0 and log.peak == 100_000.0
    assert log.points[-1].phase == "terminal" and sum(p.phase == "terminal" for p in log.points) == 1
    with pytest.raises(V.EventError, match="avslutad"):
        log.add(r)


# Likvidation enligt C6-01 (H1, I1, G1, P1).

def _risky(order="A", mmr=0.05, T=T_MID, C=-600_000.0, q=10_000.0):
    acct = L.Account(C=C, q=q, deposit=100_000.0, realized=C + q * 100.0 - 100_000.0, avg_price=100.0)
    return fixture(sc(order, mmr), acct, T, 70.0, peak=101_000.0, day_start=101_000.0)


@pytest.mark.parametrize("low,exp_low", [(63.5, 22_200), (58.0, -32_800)])
@pytest.mark.parametrize("credit_first", [False, True])
def test_intrabar_hit_points_follow_C6_01(low, exp_low, credit_first):
    st = _risky()
    t1, t2 = T_MID + pd.Timedelta(minutes=30), T_MID + pd.Timedelta(hours=2)
    if credit_first:
        t1, t2 = t2, t1
    events = sorted([ev("pay", t1, 0.02, 64.0), ev("recv", t2, -0.02, 64.0)], key=lambda e: e.time)
    r = V.process_bar(st, V.Bar(T_MID, 64.0, 64.0, 66.0, low, max(low, 60.0)), events)
    assert r.state.margin_state.liquidated and {u[0] for u in r.unresolved} == {"pay", "recv"}
    pts = B.bar_points(r)
    assert phases(pts) == ["open", "trade", "post", "high", "low", "liquidation"]
    assert [p["E"] for p in pts] == [40_000.0, 40_000.0, 40_000.0, 72_800.0, float(exp_low), 0.0]
    assert pts[3]["C"] == -587_200.0 and pts[4]["C"] == -612_800.0 and pts[3]["q"] == pts[4]["q"] == 10_000
    assert pts[4]["E"] == r.margin_basis[1] and pts[5]["time"] == V.UNKNOWN_TIME
    peak, minimum, _ = fold(pts, 101_000.0)
    assert peak == 101_000 and minimum == (D(exp_low) / D(101_000) - 1 if exp_low < 0 else D(-1))
    # Ledgern enligt C5-01 är orörd av bounden.
    a = r.state.account
    assert a.funding_net == 0 and a.C == 0 and a.q == 0 and r.interior_booked == 0


def test_intrabar_hit_after_high_raises_peak_case_4():
    st = fixture(sc(), L.Account(C=-300_000.0, q=4_000.0, deposit=100_000.0, avg_price=100.0), T_MID, 100.0)
    events = [ev("pay", T_MID + pd.Timedelta(minutes=30), 0.01, 100.0), ev("recv", T_MID + pd.Timedelta(hours=1), -0.01, 100.0)]
    r = V.process_bar(st, V.Bar(T_MID, 100.0, 100.0, 110.0, 70.0, 75.0), events)
    pts = B.bar_points(r)
    assert [p["E"] for p in pts] == [100_000.0, 100_000.0, 100_000.0, 144_000.0, -24_000.0, 0.0]
    peak, minimum, dds = fold(pts, 100_000.0, -0.05)
    assert peak == 144_000 and minimum == D(-7) / D(6) and dds[-1] == -1


@pytest.mark.parametrize("order", ["A", "B"])
def test_gap_hit_points_follow_G1(order):
    st = _risky(order)
    r = V.process_bar(st, V.Bar(T_MID, 55.0, 55.0, 60.0, 50.0, 58.0), [ev("s", T_MID, 0.001, 55.0),
                                                                     ev("i", T_MID + H / 2, -0.01, 55.0)])
    pts = B.bar_points(r)
    gap = D(-600_000) + D(10_000) * 55                                 # −50 000 före A-funding
    if order == "A":
        assert phases(pts) == ["open", "gap_check", "liquidation"]
        assert close(pts[1]["E"], gap - D(10_000) * 55 * D("0.001")) and pts[1]["E"] == r.state.margin_state.record.E_before
    else:
        assert phases(pts) == ["open", "liquidation"]
    assert close(pts[0]["E"], gap) and pts[-1]["E"] == 0.0
    _, minimum, _ = fold(pts, 101_000.0)
    assert minimum == min(D(repr(p["E"])) / D(101_000) - 1 for p in pts)
    assert minimum < -1                                                # oklippt negativt (G1)


def test_liquidated_account_gives_absorbing_zero_points_and_keeps_peak():
    st = _risky()
    r = V.process_bar(st, V.Bar(T_MID, 55.0, 55.0, 60.0, 50.0, 58.0))
    state = r.state
    for k in range(1, 6):
        rr = V.process_bar(state, V.Bar(T_MID + k * H, 80.0, 80.0, 200.0, 79.0, 80.0))
        assert [(p["phase"], p["E"]) for p in B.bar_points(rr)] == [("absorbed", 0.0)]
        state = rr.state


def test_gap_check_absent_without_A_funding():
    r = V.process_bar(_risky("A"), V.Bar(T_MID, 55.0, 55.0, 60.0, 50.0, 58.0))
    assert phases(B.bar_points(r)) == ["open", "liquidation"]


# Rena måttgränser kring 20 % (ingen beslutsmotor).

@pytest.mark.parametrize("low", [80.01, 80.0, 79.99])
def test_twenty_percent_measure_boundary(low):
    acct = L.Account(C=0.0, q=1000.0, deposit=100_000.0, avg_price=100.0)
    st = fixture(sc(), acct, T_MID, 100.0)
    pts = B.bar_points(V.process_bar(st, V.Bar(T_MID, 100.0, 100.0, 100.0, low, 100.0)))
    lowp = next(p for p in pts if p["phase"] == "low")
    assert lowp["E"] == low * 1000 and (lowp["E"] / 100_000.0 - 1.0) == (low * 1000) / 100_000.0 - 1.0
    mag = -(lowp["E"] / 100_000.0 - 1.0)
    assert (mag <= 0.20) == (low >= 80.0)


# Kedja och fel.

def test_chain_and_construction_guards():
    st = V.EngineState.start(sc())
    r0 = V.process_bar(st, V.Bar(T0, 100.0, 100.0, 101.0, 99.0, 100.0), (), sig(T0, 1.0, 0.5))
    r1 = V.process_bar(r0.state, V.Bar(T0 + H, 100.0, 100.0, 101.0, 99.0, 100.0))
    log = B.BoundLog.begin(st).add(r0)
    snapshot = log
    for bad in (r0, ):
        with pytest.raises(V.EventError, match="följer inte"):
            log.add(bad)
    with pytest.raises(V.EventError, match="följer inte"):
        B.BoundLog.begin(st).add(r1)
    foreign = V.process_bar(V.EngineState.start(sc("B", key="x")), V.Bar(T0, 100.0, 100.0, 101.0, 99.0, 100.0), (),
                            sig(T0, 1.0, 0.5))
    with pytest.raises(V.EventError, match="följer inte"):
        log.add(foreign)
    assert log == snapshot
    with pytest.raises(B.BoundError, match="skapas bara"):
        dataclasses.replace(log, max_dd_bound=0.0)
    with pytest.raises(B.BoundError, match="skapas bara"):
        B.BoundLog(run=log.run)
    with pytest.raises(V.EventError, match="startläget"):
        B.BoundLog.begin(fixture(sc(), L.Account.open(100_000), T_MID, 100.0))
    with pytest.raises(B.BoundError):
        B.bar_points("inte ett resultat")
    assert r0.bar.mark_high == 101.0 and r0.bar.open_time == T0          # eventlagret bär stapeln (C6)
