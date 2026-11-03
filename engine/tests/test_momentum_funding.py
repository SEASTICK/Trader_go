"""Fundingbokföring för H-0017 (leverans C2) på syntetiska konton och event. Ingen marknadshistorik.

Facit från docs/momentum-a1-orakel.json och Decimal-räkning, aldrig från produktionskoden. A/B komponeras här av C1-
fyllningar och fundingfunktionen i den låsta ordningen; detta är inte en eventloop.
"""
import dataclasses
import json
import math
from decimal import Decimal as D, getcontext
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from traderlab import momentum_funding as F
from traderlab import momentum_ledger as L

getcontext().prec = 50
ORACLE = json.loads((Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())
T = pd.Timestamp("2022-01-02 00:00", tz="UTC")
R = 0.0001


def close(a, b):
    return a == pytest.approx(b, rel=1e-12, abs=1e-9)


def ev(eid, t, rate=R, M=100.0, source=F.MARK_OPEN):
    ref = F.bar_open(t) if source == F.MARK_OPEN else F.bar_open(t) + F.BAR
    return F.FundingEvent(eid, t, rate, M, source, ref)


def st(key="main", scenario="A"):
    return F.FundingState(key, scenario)


def pos(C, q, avg, deposit):
    acct = L.Account(C=C, q=q, deposit=deposit, avg_price=avg)
    assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-9)
    return acct


def test_versions_and_c1_identity_unchanged_without_funding():
    assert F.VERSION == "mom-funding/1.0.0" and L.VERSION == "mom-ledger/1.0.0"
    old = L.Account(C=800, q=2, deposit=1000, avg_price=100)            # konstruktion utan funding_net
    assert old.funding_net == 0 and old.reconciliation_gap() == 0
    acct, f = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    assert acct.funding_net == 0 and close(f.E_trade, ORACLE["O1_avgift_w05"]["E_after"])


def test_O5_entry_and_exit_with_simultaneous_funding_in_A_and_B():
    o = ORACLE["O5_funding_samma_grans"]
    start = L.Account.open(100_000)
    # Inträde. A: funding på q före affären (0), sedan fyllning.
    a1, _, ra = F.apply_funding(start, st(scenario="A"), ev("f1", T), "funding_A")
    a2, fill_a = L.fill_normal(a1, 0.5, 100, 100)
    assert ra.payment == 0 and close(fill_a.E_trade, o["inträde_A"]["E"])
    # B: fyllning, sedan funding på q efter affären.
    b1, fill_b = L.fill_normal(start, 0.5, 100, 100)
    b2, _, rb = F.apply_funding(b1, st(scenario="B"), ev("f1", T), "funding_B")
    assert close(rb.payment, o["inträde_B"]["funding"]) and close(rb.E_after, o["inträde_B"]["E"])
    # Utgång från O1-läget.
    held = a2
    x1, _, rxa = F.apply_funding(held, st(scenario="A"), ev("f2", T + pd.Timedelta(hours=8)), "funding_A")
    x2, _ = L.fill_normal(x1, 0.0, 100, 100)
    assert close(rxa.payment, o["utgång_A"]["funding"]) and close(x2.equity(100), o["utgång_A"]["E"])
    y1, _ = L.fill_normal(held, 0.0, 100, 100)
    y2, _, rxb = F.apply_funding(y1, st(scenario="B"), ev("f2", T + pd.Timedelta(hours=8)), "funding_B")
    assert rxb.payment == 0 and close(y2.equity(100), o["utgång_B"]["E"])
    for acct in (a2, b2, x2, y2):
        assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-9)


def test_O5b_E_trade_and_E_post_are_separate_phases():
    o = ORACLE["O5b_kapitalfaser_B"]
    acct, fill = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    post, _, rec = F.apply_funding(acct, st(scenario="B"), ev("f1", T), "funding_B")
    assert close(fill.E_trade, o["E_trade"]) and close(fill.weight_trade, o["vikt_after_trade"])
    assert close(rec.E_before, fill.E_trade) and close(rec.E_after, o["E_post"])
    assert close(post.weight(100), o["vikt_after_funding_B"])
    assert fill.phase == "after_trade" and rec.phase == "funding_B"
    # Funding är varken kostnad eller realiserat.
    assert post.costs == acct.costs and post.realized == acct.realized and close(post.funding_net, o["funding"])


def test_O16_exact_and_plus_minus_30_seconds_keep_time_and_day():
    o = ORACLE["O16_fundingtider"]
    before, after = L.Account.open(100_000), pos(50_000, 500, 100, 100_000)
    cases = {"samtidig_exakt_T": T, "plus_30s": T + pd.Timedelta(seconds=30), "minus_30s": T - pd.Timedelta(seconds=30)}
    for name, t in cases.items():
        exp = o[name]
        assert t.isoformat() == exp["tid"] and t.date().isoformat() == exp["dag"]
        if t == T:
            _, _, ra = F.apply_funding(before, st(scenario="A"), ev(name, t), "funding_A")
            _, _, rb = F.apply_funding(after, st(scenario="B"), ev(name, t), "funding_B")
            assert (ra.payment, rb.payment) == (exp["betalt_A"], exp["betalt_B"])
        else:
            acct = after if t > T else before      # anroparen ger positionen som gäller vid t
            _, _, r = F.apply_funding(acct, st(), ev(name, t), "funding_interior")
            assert r.payment == exp["betalt_A"] == exp["betalt_B"] and r.time == t
    assert F.bar_open(T - pd.Timedelta(seconds=30)) == pd.Timestamp("2022-01-01 20:00", tz="UTC")
    assert F.bar_open(T + pd.Timedelta(seconds=30)) == T == F.bar_open(T)


def test_O17_closed_position_pays_nothing_and_new_entry_uses_new_position():
    o = ORACLE["O17_legacy_ordning"]
    stopped, _ = L.fill_normal(L.Account(C=10_000, q=900, deposit=100_000, avg_price=100), 0.0, 94, 94)
    assert close(stopped.equity(94), o["gapstop_plus_30s"]["E_efter_gapstop"]) and stopped.q == 0
    _, _, r = F.apply_funding(stopped, st(), ev("g", T + pd.Timedelta(seconds=30), M=94.0), "funding_interior")
    assert r.payment == o["gapstop_plus_30s"]["L2"] == 0
    entered, _ = L.fill_normal(L.Account.open(100_000), 1.0, 100, 100)
    _, _, r = F.apply_funding(entered, st(), ev("h", T + pd.Timedelta(hours=2)), "funding_interior")
    assert close(r.q, o["inträde_vid_oppning_stop_inom_stapel"]["q_open"])
    assert close(r.payment, o["inträde_vid_oppning_stop_inom_stapel"]["L2_funding"])


@pytest.mark.parametrize("q", [3.0, -3.0, 0.0])
@pytest.mark.parametrize("rate", [0.0002, -0.0002, 0.0])
def test_long_short_flat_with_positive_negative_zero_rate(q, rate):
    acct = L.Account(C=1000 - q * 100, q=q, deposit=1000, avg_price=100 if q else 0)
    new, _, r = F.apply_funding(acct, st(), ev("e", T, rate=rate, M=101.0), "funding_A")
    exp = D(q) * D("101") * D(repr(rate))
    assert math.isclose(r.payment, float(exp), rel_tol=1e-15, abs_tol=0)
    assert close(new.C, acct.C - float(exp)) and close(new.funding_net, float(exp))
    assert close(r.E_after - r.E_before, -float(exp)) and new.q == acct.q
    assert new.reconciliation_gap() == pytest.approx(0, abs=1e-9)


def test_multiple_events_accumulate_and_dedupe():
    acct, state = pos(-2000, 30, 100, 1000), st()
    total = D(0)
    for i, (rate, M) in enumerate([(0.0001, 100.0), (-0.00005, 102.5), (0.0003, 99.0)]):
        acct, state, r = F.apply_funding(acct, state, ev(f"e{i}", T + pd.Timedelta(hours=8 * i), rate, M), "funding_A")
        total += D(30) * D(repr(M)) * D(repr(rate))
    assert close(acct.funding_net, float(total)) and close(acct.C, -2000 - float(total))
    assert state.processed == {"e0", "e1", "e2"}
    before_acct, before_state = acct, state
    with pytest.raises(F.FundingError, match="redan bokfört"):
        F.apply_funding(acct, state, ev("e1", T + pd.Timedelta(hours=8)), "funding_A")
    assert acct == before_acct and state == before_state


def test_same_event_in_separate_accounts_and_scenarios():
    acct = pos(50_000, 500, 100, 100_000)
    e = ev("shared", T)
    states = [st("main", "A"), st("main", "B"), st("mom7", "A")]
    results = [F.apply_funding(acct, s, e, "funding_A") for s in states]
    assert all(close(r[2].payment, 5.0) for r in results)
    assert {(r[2].account_key, r[2].scenario) for r in results} == {("main", "A"), ("main", "B"), ("mom7", "A")}


def test_zero_amount_on_flat_account_is_processed_and_cannot_be_charged_later():
    flat, state = L.Account.open(1000), st()
    flat2, state2, r = F.apply_funding(flat, state, ev("z", T), "funding_A")
    assert r.payment == 0 and "z" in state2.processed and flat2.C == flat.C
    long_, _ = L.fill_normal(flat2, 0.5, 100, 100)
    with pytest.raises(F.FundingError):
        F.apply_funding(long_, state2, ev("z", T), "funding_B")


@pytest.mark.parametrize("q,rate,doubled", [(3.0, 0.0002, True), (3.0, -0.0002, False),
                                             (-3.0, 0.0002, False), (-3.0, -0.0002, True)])
def test_stress_doubles_only_actual_payments(q, rate, doubled):
    acct = L.Account(C=1000 - q * 100, q=q, deposit=1000, avg_price=100)
    _, _, n = F.apply_funding(acct, st(scenario="norm"), ev("s", T, rate=rate), "funding_A")
    _, _, s = F.apply_funding(acct, st(scenario="stress"), ev("s", T, rate=rate), "funding_A",
                              F.FundingConfig(stress=True))
    assert n.payment == n.payment_base == s.payment_base
    assert s.payment == (2 * n.payment if doubled else n.payment)
    assert (n.payment > 0) == doubled                      # tecknet på betalningen avgör, inte räntans
    assert n.config == "mark_open" and s.config == "mark_open+stress"


def test_funding_then_partial_reversal_hold_and_close_reconcile_with_decimal():
    acct, state = L.Account.open(100_000), st()
    ledger_C = D(100_000)
    steps = [("fill", 0.5, 100.0, 100.0), ("fund", 0.0001, 100.0), ("fill", 0.3, 103.0, 102.5),
             ("fund", -0.0002, 102.5), ("fill", -0.4, 99.0, 99.2), ("fund", 0.0003, 99.2),
             ("risk", -0.6, 98.0, 98.0), ("fill", 0.0, 97.0, 97.1)]
    for i, step in enumerate(steps):
        if step[0] == "fund":
            q_before = D(acct.q)
            t = T + pd.Timedelta(hours=4 * i, minutes=30)           # mellanhändelse efter stapelns fyllning
            acct, state, r = F.apply_funding(acct, state, ev(f"e{i}", t, step[1], step[2]), "funding_interior")
            pay = q_before * D(repr(step[2])) * D(repr(step[1]))
            ledger_C -= pay
            assert math.isclose(r.C_before - r.C_after, float(pay), rel_tol=1e-12, abs_tol=1e-9)
        else:
            fill = L.fill_risk if step[0] == "risk" else L.fill_normal
            q_old = D(acct.q)
            acct, f = fill(acct, step[1], step[2], step[3])
            dq = D(f.q_new) - q_old
            ledger_C -= dq * D(repr(step[2])) + D(repr(L.COST_NORMAL)) * D(repr(step[2])) * abs(dq)
        assert math.isclose(acct.C, float(ledger_C), rel_tol=1e-12, abs_tol=1e-6)
        assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-8)
    assert acct.q == 0 and acct.funding_net != 0 and acct.costs > 0
    assert close(acct.C, acct.deposit + acct.realized - acct.costs - acct.funding_net)


def test_mark_close_is_only_a_labelled_diagnostic_and_must_match_event():
    acct = pos(50_000, 500, 100, 100_000)
    e = ev("d", T + pd.Timedelta(hours=1), source=F.MARK_CLOSE)
    assert e.M_ref_time == T + F.BAR
    _, _, r = F.apply_funding(acct, st(), e, "funding_interior", F.FundingConfig(price_model=F.MARK_CLOSE))
    assert r.config == "mark_close" and r.M_ref_source == F.MARK_CLOSE
    with pytest.raises(F.FundingError, match="matchar inte"):
        F.apply_funding(acct, st(), e, "funding_interior")            # huvudmodellen kräver mark_open


@pytest.mark.parametrize("kwargs,match", [
    (dict(time=pd.Timestamp("2022-01-02")), "UTC"),
    (dict(time=pd.Timestamp("2022-01-02", tz="Europe/Stockholm")), "UTC"),
    (dict(time="2022-01-02T00:00Z"), "UTC"),
    (dict(time=T + pd.Timedelta(microseconds=1)), "millisekund"),
    (dict(rate=math.nan), "rate"), (dict(rate=math.inf), "rate"), (dict(rate=True), "rate"),
    (dict(M_ref=0.0), "M_ref"), (dict(M_ref=-1.0), "M_ref"), (dict(M_ref=math.inf), "M_ref"),
    (dict(event_id=""), "event_id"), (dict(event_id=7), "event_id"),
    (dict(M_ref_source="mark_mid"), "källa"),
    (dict(M_ref_time=T - F.BAR), "M_ref_time"),
])
def test_invalid_events_are_rejected(kwargs, match):
    base = dict(event_id="x", time=T, rate=R, M_ref=100.0, M_ref_source=F.MARK_OPEN, M_ref_time=T)
    with pytest.raises(F.FundingError, match=match):
        F.FundingEvent(**(base | kwargs))


def test_millisecond_times_are_kept_exactly():
    t = T + pd.Timedelta(milliseconds=4)
    e = ev("ms", t)
    _, _, r = F.apply_funding(pos(50_000, 500, 100, 100_000), st(), e, "funding_interior")
    assert r.time == t and r.M_ref_time == T


def test_overflow_and_bad_phase_leave_account_and_state_unchanged():
    acct, state = L.Account(C=1.0, q=1e300, deposit=1.0), st()
    before = (dataclasses.replace(acct), state)
    with pytest.raises(L.LedgerError):
        F.apply_funding(acct, state, ev("o", T, rate=1e10, M=1e10), "funding_A")
    with pytest.raises(F.FundingError, match="fas"):
        F.apply_funding(acct, state, ev("o", T), "after_trade")
    assert (acct, state) == before



def test_numpy_and_python_numbers_give_same_booking():
    acct = pos(50_000, 500, 100, 100_000)
    _, _, a = F.apply_funding(acct, st(), F.FundingEvent("n", T, 0.0001, 100.5, F.MARK_OPEN, T), "funding_A")
    _, _, b = F.apply_funding(acct, st(), F.FundingEvent("n", T, np.float64(0.0001), np.int64(100) + 0.5,
                                                         F.MARK_OPEN, T), "funding_A")
    assert a.payment == b.payment and type(b.payment) is float


def test_trace_record_fields():
    acct = pos(50_000, 500, 100, 100_000)
    _, _, r = F.apply_funding(acct, st("main", "A"), ev("t", T), "funding_A")
    d = r.as_dict()
    assert {"event_id", "time", "q", "rate", "M_ref", "M_ref_source", "M_ref_time", "payment", "payment_base",
            "C_before", "C_after", "E_before", "E_after", "phase", "account_key", "scenario", "config"} <= set(d)
    assert d["version"] == F.VERSION and close(d["E_before"] - d["E_after"], d["payment"])


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "1"])
def test_funding_net_field_is_validated_like_other_fields(value):
    with pytest.raises(L.LedgerError):
        L.Account(C=800, q=2, deposit=1000, avg_price=100, funding_net=value)
    with pytest.raises(L.LedgerError):
        dataclasses.replace(L.Account(C=800, q=2, deposit=1000, avg_price=100), funding_net=value)


def test_reconciliation_includes_funding_net():
    acct = L.Account(C=795.0, q=2, deposit=1000, avg_price=100, funding_net=5.0)
    assert acct.reconciliation_gap() == 0
    assert L.Account(C=795.0, q=2, deposit=1000, avg_price=100).reconciliation_gap() == -5.0


# Regressioner för Codex granskning av 1d9359f (C2-01, C2-02 och feltyp för källan).

PHASE_TIMES = {
    "exakt_gräns": (T, {"funding_A", "funding_B"}),
    "plus_1ms": (T + pd.Timedelta(milliseconds=1), {"funding_interior"}),
    "minus_1ms": (T - pd.Timedelta(milliseconds=1), {"funding_interior"}),
    "plus_30s": (T + pd.Timedelta(seconds=30), {"funding_interior"}),
    "minus_30s": (T - pd.Timedelta(seconds=30), {"funding_interior"}),
}


@pytest.mark.parametrize("case", PHASE_TIMES)
@pytest.mark.parametrize("phase", F.PHASES)
def test_phase_must_match_exact_event_time(case, phase):
    t, allowed = PHASE_TIMES[case]
    acct, state = pos(50_000, 500, 100, 100_000), st()
    if phase in allowed:
        new, state2, r = F.apply_funding(acct, state, ev("p", t), phase)
        assert r.phase == phase and close(r.payment, 5.0) and r.time == t
    else:
        before = (dataclasses.replace(acct), state)
        with pytest.raises(F.FundingError, match="4H-gräns|mellanhändelse"):
            F.apply_funding(acct, state, ev("p", t), phase)
        assert (acct, state) == before


@pytest.mark.parametrize("bad", ["f1", b"f1", None, 7, {"f1": 1}, iter(["f1"])])
def test_processed_must_be_an_explicit_collection(bad):
    with pytest.raises(F.FundingError, match="processed"):
        F.FundingState("main", "A", processed=bad)
    with pytest.raises(F.FundingError, match="processed"):
        dataclasses.replace(st(), processed=bad)


@pytest.mark.parametrize("element", [7, True, None, "", b"f1", 1.5])
def test_processed_elements_must_be_nonempty_strings(element):
    with pytest.raises(F.FundingError, match="event-id"):
        F.FundingState("main", "A", processed={"f1", element} if element is not None else ["f1", None])
    with pytest.raises(F.FundingError, match="event-id"):
        dataclasses.replace(st(), processed=["f1", element])


@pytest.mark.parametrize("ids", [set(), frozenset(), [], (), {"f1", "event-2024"}, ["f1", "event-2024"],
                                 ("f1", "event-2024"), frozenset({"f1", "event-2024"})])
def test_valid_collections_keep_whole_ids(ids):
    state = F.FundingState("main", "A", processed=ids)
    assert state.processed == frozenset(ids) and all(isinstance(i, str) for i in state.processed)
    assert "f" not in state.processed and "1" not in state.processed


def test_restored_processed_id_rejects_second_booking_without_change():
    acct = pos(50_000, 500, 100, 100_000)
    once, _, r = F.apply_funding(acct, st(), ev("f1", T), "funding_A")
    assert once.C == 49_995 and once.funding_net == 5
    restored = F.FundingState("main", "A", processed=["f1"])        # t.ex. återläst från en lista
    with pytest.raises(F.FundingError, match="redan bokfört"):
        F.apply_funding(once, restored, ev("f1", T), "funding_A")
    with pytest.raises(F.FundingError, match="processed"):
        F.FundingState("main", "A", processed="f1")                 # Codex reproduktion avvisas nu
    other, _, r2 = F.apply_funding(once, F.FundingState("main", "B", processed=[]), ev("f1", T), "funding_B")
    assert close(r2.payment, 5.0) and other.funding_net == 10       # separat scenario fungerar som tidigare


@pytest.mark.parametrize("source", [["mark_open"], ("mark_open",), {"mark_open": 1}, 3, None])
def test_non_string_price_source_is_funding_error(source):
    with pytest.raises(F.FundingError, match="Källan"):
        F.FundingEvent("x", T, R, 100.0, source, T)
