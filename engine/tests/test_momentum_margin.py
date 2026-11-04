"""mom-margin/1.0.0 (H-0017 leverans C4) på syntetiska konton och prispunkter. Ingen marknadshistorik, ingen eventloop.

Facit från docs/momentum-a1-orakel.json (O11, O18) och fristående Decimal-räkning, aldrig från produktionskoden.
"""
import dataclasses
import json
import math
from decimal import Decimal as D, getcontext
from pathlib import Path

import pandas as pd
import pytest

from traderlab import momentum_funding as F
from traderlab import momentum_ledger as L
from traderlab import momentum_margin as M
from traderlab import momentum_risk as R

getcontext().prec = 60
ORACLE = json.loads((Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())
BAR = pd.Timestamp("2023-05-10 08:00", tz="UTC")


def st(mmr=0.05, key="main", scenario="A"):
    return M.MarginState(key, scenario, mmr)


def decimal_hit(C, q, m, mmr):
    """Fristående: C + q*m <= mmr*|q|*m i 60 siffror."""
    C, q, m, mmr = (D(repr(float(x))) for x in (C, q, m, mmr))
    return C + q * m <= mmr * abs(q) * m


def short_legacy():
    acct, _ = L.fill_normal(L.Account.open(100_000), -1.0, 100, 100)
    return acct


def long_w1():
    acct, _ = L.fill_normal(L.Account.open(100_000), 1.0, 100, 100)
    return acct


def test_version_and_rates():
    assert M.VERSION == "mom-margin/1.0.0" and M.MMRS == (0.05, 0.005)


def test_O11_short_thresholds_and_direct_condition():
    o = ORACLE["O11_likvidation"]["legacy_short_w-1"]
    acct = short_legacy()
    assert acct.q == pytest.approx(o["q"], rel=1e-12) and acct.C == pytest.approx(o["C"], rel=1e-12)
    for mmr, key in ((0.05, "mark_mmr_0_05"), (0.005, "mark_mmr_0_005")):
        t = M.threshold(acct, mmr)
        assert t == pytest.approx(o[key], rel=1e-12)
        exact = D(repr(acct.C)) / (abs(D(repr(acct.q))) * (1 + D(repr(mmr))))
        assert abs(D(repr(t)) - exact) <= exact * D("1e-15")
        assert M.check(acct, st(mmr), M.GAP, t * 1.001, M.MARK_OPEN, BAR).hit
        assert not M.check(acct, st(mmr), M.GAP, t * 0.999, M.MARK_OPEN, BAR).hit
    assert round(o["mark_mmr_0_05"], 2) == 190.48 and round(o["mark_mmr_0_005"], 2) == 199.0


def test_O11_long_w1_can_be_liquidated_after_paid_funding():
    o = ORACLE["O11_likvidation"]["main_long_w1"]
    acct = long_w1()
    assert abs(acct.C) < 1e-9 and abs(o["C"]) < 1e-9
    paid = dataclasses.replace(acct, C=acct.C - 500.0, funding_net=500.0)
    t = M.threshold(paid, 0.05)
    assert t == pytest.approx(o["efter_betald_funding_500"], rel=1e-9)
    assert M.check(paid, st(), M.GAP, 0.52, M.MARK_OPEN, BAR).hit
    assert not M.check(paid, st(), M.GAP, 0.60, M.MARK_OPEN, BAR).hit


def _boundary(acct, mmr, start, direction):
    """Grannfloats (träff, ej träff) för direktvillkoret nära start."""
    f = lambda m: acct.C + acct.q * m <= mmr * abs(acct.q) * m
    x = start
    for _ in range(100_000):
        y = math.nextafter(x, direction if not f(x) else -direction)
        if f(y) != f(x):
            return (y, x) if f(y) else (x, y)
        x = y
    raise AssertionError("ingen gräns")


@pytest.mark.parametrize("mmr", M.MMRS)
@pytest.mark.parametrize("side", ["long", "short"])
@pytest.mark.parametrize("scale", [1.0, 37.5])
def test_direct_condition_at_exact_float_boundary(mmr, side, scale):
    if side == "long":
        acct = L.Account(C=-60_000.0 * scale, q=1000.0 * scale, deposit=40_000.0 * scale, avg_price=100.0)
        direction = -math.inf                                 # träff mot lägre pris
    else:
        acct = L.Account(C=180_000.0 * scale, q=-1000.0 * scale, deposit=80_000.0 * scale, avg_price=100.0)
        direction = math.inf                                  # träff mot högre pris
    t = M.threshold(acct, mmr)
    on, off = _boundary(acct, mmr, t, direction)
    hit_on = M.check(acct, st(mmr), M.GAP, on, M.MARK_OPEN, BAR)
    hit_off = M.check(acct, st(mmr), M.GAP, off, M.MARK_OPEN, BAR)
    assert hit_on.hit and not hit_off.hit
    assert hit_on.E <= hit_on.MM and hit_off.E > hit_off.MM
    # Beslutet följer faktisk float-aritmetik. Exakt reell aritmetik kan skilja sig någon ulp vid själva gränsen,
    # men ska stämma en bit därifrån, och float-gränsen ska ligga mycket nära den exakta gränsen.
    exact = (-D(repr(acct.C)) / (D(repr(acct.q)) * (1 - D(repr(mmr)))) if acct.q > 0
             else D(repr(acct.C)) / (-D(repr(acct.q)) * (1 + D(repr(mmr)))))
    assert abs(D(repr(on)) - exact) <= exact * D("1e-14")
    inside, outside = (on * (1 - 1e-9), off * (1 + 1e-9)) if acct.q > 0 else (on * (1 + 1e-9), off * (1 - 1e-9))
    assert decimal_hit(acct.C, acct.q, inside, mmr) and M.check(acct, st(mmr), M.GAP, inside, M.MARK_OPEN, BAR).hit
    assert not decimal_hit(acct.C, acct.q, outside, mmr)
    assert not M.check(acct, st(mmr), M.GAP, outside, M.MARK_OPEN, BAR).hit
    assert hit_on.threshold == t and hit_on.q == acct.q and hit_on.mmr == mmr


def test_gap_with_negative_equity_is_logged_unclipped_and_reset_is_positive():
    acct = L.Account(C=-90_000.0, q=1000.0, deposit=10_000.0, avg_price=100.0)
    assert acct.reconciliation_gap() == 0
    chk = M.check(acct, st(), M.GAP, 85.0, M.MARK_OPEN, BAR)
    assert chk.hit and chk.E == -5_000.0 and chk.MM == 0.05 * 1000 * 85
    after, state, rec = M.liquidate(acct, st(), chk)
    assert rec.E_before == -5_000.0 and rec.capital_reset == 5_000.0          # nollgolv, ingen marknadsvinst
    assert rec.mark_to_market == 1000 * (85 - 100) == -15_000.0
    assert rec.adjustment_delta == 90_000.0 - 100_000.0 == rec.mark_to_market + rec.capital_reset
    assert (after.C, after.q, after.avg_price) == (0.0, 0.0, 0.0) and after.liquidation_adjustment == -10_000.0
    assert after.reconciliation_gap() == 0 and state.liquidated and state.record is rec


def test_intrabar_uses_low_for_long_and_high_for_short():
    long_acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    c = M.check_bar(long_acct, st(), BAR, 70.0, 75.0, 62.0, 70.0)
    assert c.price_source == M.MARK_LOW and c.m == 62.0 and c.phase == M.INTRABAR and c.hit
    assert not M.check_bar(long_acct, st(), BAR, 70.0, 75.0, 64.0, 70.0).hit
    short_acct = L.Account(C=180_000.0, q=-1000.0, deposit=80_000.0, avg_price=100.0)
    c = M.check_bar(short_acct, st(), BAR, 150.0, 175.0, 140.0, 160.0)
    assert c.price_source == M.MARK_HIGH and c.m == 175.0 and c.hit
    assert not M.check_bar(short_acct, st(), BAR, 150.0, 170.0, 140.0, 160.0).hit
    assert c.bar_open == BAR and not hasattr(c, "time")      # ingen påhittad händelsetid


def test_wrong_extreme_or_phase_is_rejected():
    long_acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    with pytest.raises(M.MarginError, match="mark_low"):
        M.check(long_acct, st(), M.INTRABAR, 75.0, M.MARK_HIGH, BAR)
    with pytest.raises(M.MarginError, match="mark_open"):
        M.check(long_acct, st(), M.GAP, 75.0, M.MARK_LOW, BAR)
    with pytest.raises(M.MarginError, match="fas"):
        M.check(long_acct, st(), "after_trade", 75.0, M.MARK_OPEN, BAR)


def test_no_hit_and_flat_account_with_positive_capital():
    assert not M.check(L.Account.open(100_000), st(), M.GAP, 50.0, M.MARK_OPEN, BAR).hit
    assert M.threshold(L.Account.open(100_000), 0.05) is None
    healthy, _ = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    assert not M.check(healthy, st(), M.GAP, 1.0, M.MARK_OPEN, BAR).hit       # C > 0: kan aldrig likvideras som long
    with pytest.raises(M.MarginError, match="platt"):
        M.check(L.Account.open(100_000), st(), M.INTRABAR, 50.0, M.MARK_LOW, BAR)


def test_unexplained_flat_zero_or_negative_account_is_invalid():
    for C in (0.0, -10.0):
        with pytest.raises(M.MarginError, match="oförklarat"):
            M.check(L.Account(C=C, q=0.0, deposit=0.0 if C == 0 else 1.0, realized=0.0 if C == 0 else -11.0),
                    st(), M.GAP, 100.0, M.MARK_OPEN, BAR)


@pytest.mark.parametrize("kw,match", [
    (dict(m=math.nan), "m måste"), (dict(m=math.inf), "m måste"), (dict(m=0.0), "Markpriset"), (dict(m=-1.0), "Markpriset"),
    (dict(m=True), "m måste"), (dict(bar_open=pd.Timestamp("2023-05-10 08:00")), "UTC"),
    (dict(bar_open=pd.Timestamp("2023-05-10 09:00", tz="UTC")), "4H"), (dict(bar_open="2023-05-10"), "UTC"),
    (dict(price_source="mark_mid"), "mark_open")])
def test_invalid_check_inputs(kw, match):
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    args = dict(acct=acct, state=st(), phase=M.GAP, m=70.0, price_source=M.MARK_OPEN, bar_open=BAR) | kw
    with pytest.raises(M.MarginError, match=match):
        M.check(**args)


@pytest.mark.parametrize("mmr", [0.01, 0.05000001, "0.05", None, True, math.nan])
def test_only_registered_rates(mmr):
    with pytest.raises(M.MarginError):
        M.MarginState("main", "A", mmr)


def test_invalid_ohlc_and_overflow():
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    for o, h, l, c in ((70, 69, 62, 70), (70, 75, 71, 70), (70, 75, 62, 76), (70, 75, 0, 70), (70, math.inf, 62, 70)):
        with pytest.raises(M.MarginError):
            M.check_bar(acct, st(), BAR, o, h, l, c)
    with pytest.raises(L.LedgerError):
        M.check(L.Account(C=1.0, q=1e300, deposit=1.0), st(), M.GAP, 1e10, M.MARK_OPEN, BAR)


def test_liquidation_adjustment_field_is_validated_and_defaults_to_zero():
    assert L.Account.open(1000).liquidation_adjustment == 0
    for v in (math.nan, math.inf, True, "1"):
        with pytest.raises(L.LedgerError):
            L.Account(C=1.0, liquidation_adjustment=v)
        with pytest.raises(L.LedgerError):
            dataclasses.replace(L.Account.open(1000), liquidation_adjustment=v)
    acct = L.Account(C=990.0, deposit=1000.0, liquidation_adjustment=-10.0)
    assert acct.reconciliation_gap() == 0 and L.Account(C=990.0, deposit=1000.0).reconciliation_gap() == -10.0


def test_liquidation_after_partials_costs_and_funding_keeps_history_and_reconciles():
    acct, _ = L.fill_normal(L.Account.open(100_000), 1.0, 100, 100)
    acct, _ = L.fill_normal(acct, 0.8, 104, 103.5)
    acct, _ = L.fill_normal(acct, 1.0, 98, 98.2)
    acct, _, fr = F.apply_funding(acct, F.FundingState("main", "A"),
                                  F.FundingEvent("f", BAR, 0.01, 98.0, F.MARK_OPEN, BAR), "funding_A")
    assert acct.funding_net > 0 and acct.costs > 0 and acct.realized != 0 and acct.C < 0
    before = acct
    t = M.threshold(acct, 0.05)
    chk = M.check(acct, st(), M.INTRABAR, t * 0.99, M.MARK_LOW, BAR)
    after, state, rec = M.liquidate(acct, st(), chk)
    assert before.reconciliation_gap() == pytest.approx(0, abs=1e-8)
    assert after.reconciliation_gap() == pytest.approx(0, abs=1e-8)
    for f in ("deposit", "realized", "costs", "funding_net"):
        assert getattr(after, f) == getattr(before, f)
    exp_delta = -D(repr(before.C)) - D(repr(before.q)) * D(repr(before.avg_price))
    assert abs(D(repr(rec.adjustment_delta)) - exp_delta) <= abs(exp_delta) * D("1e-14")
    assert rec.mark_to_market + rec.capital_reset == pytest.approx(rec.adjustment_delta, rel=1e-12)
    assert after.liquidation_adjustment == rec.adjustment_delta and rec.account_before == before


@pytest.mark.parametrize("k", [0.01, 1.0, 250.0])
def test_scale_invariance_of_liquidation(k):
    base = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    scaled = L.Account(C=-60_000.0 * k, q=1000.0 * k, deposit=40_000.0 * k, avg_price=100.0)
    _, _, r1 = M.liquidate(base, st(), M.check(base, st(), M.GAP, 62.0, M.MARK_OPEN, BAR))
    _, _, rk = M.liquidate(scaled, st(), M.check(scaled, st(), M.GAP, 62.0, M.MARK_OPEN, BAR))
    assert rk.adjustment_delta == pytest.approx(k * r1.adjustment_delta, rel=1e-12)
    assert rk.capital_reset == pytest.approx(k * r1.capital_reset, rel=1e-12) and r1.capital_reset < 0


def test_stale_check_wrong_rate_no_hit_and_double_liquidation_are_rejected():
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    chk = M.check(acct, st(), M.GAP, 62.0, M.MARK_OPEN, BAR)
    changed = dataclasses.replace(acct, C=acct.C + 1.0, deposit=acct.deposit + 1.0)
    with pytest.raises(M.MarginError, match="gammalt"):
        M.liquidate(changed, st(), chk)
    with pytest.raises(M.MarginError, match="underhållssats"):
        M.liquidate(acct, st(0.005), chk)
    with pytest.raises(M.MarginError, match="Ingen träff"):
        M.liquidate(acct, st(), M.check(acct, st(), M.GAP, 70.0, M.MARK_OPEN, BAR))
    after, state, rec = M.liquidate(acct, st(), chk)
    with pytest.raises(M.MarginError, match="redan likviderat"):
        M.liquidate(acct, state, chk)
    with pytest.raises(M.MarginError, match="redan likviderat"):
        M.check(after, state, M.GAP, 50.0, M.MARK_OPEN, BAR)
    assert state.record is rec and after.liquidation_adjustment == rec.adjustment_delta    # bokförd en gång


def _open_sequence(acct, funding_state, state, *, P, M_open, rate, w, t):
    """§8.1 i ordning: gappunkt, scenario A-funding, marginalprövning vid mark_open, fyllning bara utan träff."""
    acct, funding_state, fr = F.apply_funding(acct, funding_state, F.FundingEvent("open", t, rate, M_open, F.MARK_OPEN, t),
                                              "funding_A")
    chk = M.check(acct, state, M.GAP, M_open, M.MARK_OPEN, t)
    if chk.hit:
        acct, state, rec = M.liquidate(acct, state, chk)
        return acct, state, None, chk
    acct, fill = L.fill_normal(acct, w, P, M_open)
    return acct, state, fill, chk


@pytest.mark.parametrize("mmr", M.MMRS)
def test_composition_margin_before_fill_and_after_A_funding(mmr):
    t = pd.Timestamp("2023-05-11 00:00", tz="UTC")
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    # Utan funding: E vid 62,9 är 2 900; med betald funding 1000*62,9*0,03 = 1 887 faller E under MM vid 5 %.
    a, s, fill, chk = _open_sequence(acct, F.FundingState("main", "A"), st(mmr), P=63.0, M_open=62.9, rate=0.03, w=0.0, t=t)
    E_expected = -60_000.0 - 1000 * 62.9 * 0.03 + 1000 * 62.9
    assert chk.E == pytest.approx(E_expected)
    assert chk.hit == decimal_hit(-60_000.0 - 1000 * 62.9 * 0.03, 1000.0, 62.9, mmr)
    if chk.hit:
        assert fill is None and s.liquidated and a.q == 0 and a.costs == acct.costs         # ingen fill, ingen avgift
    else:
        assert fill is not None and a.q == 0 and not s.liquidated


def test_intrabar_check_uses_C_after_paid_and_before_received_funding():
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    t_pay, t_recv = BAR + pd.Timedelta(minutes=30), BAR + pd.Timedelta(hours=2)
    fs = F.FundingState("main", "A")
    paid, fs, _ = F.apply_funding(acct, fs, F.FundingEvent("pay", t_pay, 0.02, 64.0, F.MARK_OPEN, BAR), "funding_interior")
    chk = M.check_bar(paid, st(), BAR, 64.0, 66.0, 63.5, 65.0)     # efter betald, före mottagen
    assert chk.hit and chk.E == pytest.approx(-60_000.0 - 1000 * 64.0 * 0.02 + 1000 * 63.5)
    recv_first, fs2, _ = F.apply_funding(paid, fs, F.FundingEvent("recv", t_recv, -0.02, 64.0, F.MARK_OPEN, BAR),
                                         "funding_interior")
    assert not M.check_bar(recv_first, st(), BAR, 64.0, 66.0, 63.5, 65.0).hit   # mottagen först skulle dölja träffen
    after, state, _ = M.liquidate(paid, st(), chk)
    # En senare kredit på det likviderade nollkontot återupplivar inget: q = 0 ger belopp 0.
    revived, _, rec = F.apply_funding(after, fs, F.FundingEvent("recv", t_recv, -0.02, 64.0, F.MARK_OPEN, BAR),
                                      "funding_interior")
    assert rec.payment == 0 and revived.C == 0 and revived.q == 0 and state.liquidated


def test_zero_account_follows_C3_liquidation_path_including_terminal():
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    zero, state, _ = M.liquidate(acct, st(), M.check(acct, st(), M.GAP, 62.0, M.MARK_OPEN, BAR))
    T = pd.Timestamp("2024-12-31 16:00", tz="UTC")
    rs = R.RiskState(initial=100_000.0, peak=100_000.0, day_start=100_000.0, next_boundary=T, started=True)
    rs, rec = R.step(rs, T, R.CloseInput(T - R.BAR, zero, 62.0, liquidated=True), None)
    assert rs.liquidated and rec.intent is None
    rs, rec = R.step(rs, T + R.BAR, R.CloseInput(T, zero, 62.0, liquidated=True), None, terminal=True)
    assert rec.intent is None and rs.terminated and rs.liquidated


def test_O18_liquidated_subaccount_stays_zero_while_survivor_continues():
    o = ORACLE["O18_likvidation"]["blandning_ett_delkonto_likviderat"]
    dying = L.Account(C=-30_000.0, q=1000.0, deposit=20_000.0, avg_price=50.0)
    survivor = L.Account.open(50_000)
    zero, state, _ = M.liquidate(dying, st(key="sub1"), M.check(dying, st(key="sub1"), M.GAP, 31.0, M.MARK_OPEN, BAR))
    assert zero.equity(31.0) == 0 and state.liquidated
    survivor, _ = L.fill_normal(survivor, 0.5, 100, 100)              # överlevaren handlar vidare, separat konto
    mix = zero.equity(104.0) + survivor.equity(104.0)
    assert mix == survivor.equity(104.0) > 50_000 and zero.equity(104.0) == 0
    assert o["kedjad_stammer"] and o["E_end"][-1] == 52_000          # oraklets blandning: överlevaren fortsätter
    with pytest.raises(M.MarginError):
        M.check(zero, state, M.GAP, 40.0, M.MARK_OPEN, BAR)


def test_previous_modules_unchanged_with_default_adjustment():
    acct, f = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    assert acct.liquidation_adjustment == 0 and f.E_trade == pytest.approx(ORACLE["O1_avgift_w05"]["E_after"], rel=1e-12)
    assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("C,q", [(-95_000.0, 1000.0), (105_000.0, -1000.0)])
def test_exact_equality_E_equals_MM_is_a_hit(C, q):
    acct = L.Account(C=C, q=q, deposit=5_000.0, avg_price=100.0)
    chk = M.check(acct, st(0.05), M.GAP, 100.0, M.MARK_OPEN, BAR)
    assert chk.E == chk.MM == 5_000.0 and chk.hit                     # villkoret är inkluderande: E <= MM
    assert decimal_hit(C, q, 100.0, 0.05) is True                     # reellt är MM 5 000,000000000000277 >= E


# Regressioner för Codex granskning av 0773f76 (C4-01 och C4-02).

@pytest.mark.parametrize("mmr,q,exact", [(0.05, -1.75e308, "0.54421768707482993197"),
                                         (0.005, -1.795e308, "0.55433140703169389820")])
def test_short_threshold_denominator_overflow_is_controlled(mmr, q, exact):
    acct = L.Account(C=1e308, q=q, deposit=1e308)
    copy = dataclasses.replace(acct)
    assert math.isinf(abs(q) * (1 + mmr))                              # nämnaren överflödar trots ändliga fält
    assert D(repr(1e308)) / (abs(D(repr(q))) * (1 + D(repr(mmr)))) == pytest.approx(D(exact), rel=D("1e-18"))
    with pytest.raises(L.LedgerError, match="nämnare"):
        M.threshold(acct, mmr)
    with pytest.raises(L.LedgerError, match="nämnare"):
        M.check(acct, st(mmr), M.GAP, 0.5, M.MARK_OPEN, BAR)
    assert acct == copy


def test_ordinary_and_zero_thresholds_still_work():
    assert M.threshold(L.Account(C=0.0, q=10.0, deposit=1000.0, avg_price=100.0), 0.05) == 0
    assert M.threshold(L.Account.open(100), 0.005) is None
    assert M.threshold(short_legacy(), 0.05) == pytest.approx(ORACLE["O11_likvidation"]["legacy_short_w-1"]["mark_mmr_0_05"],
                                                             rel=1e-12)
    assert M.threshold(L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0), 0.005) == pytest.approx(
        60_000 / (1000 * 0.995), rel=1e-12)


@pytest.mark.parametrize("mmr", [0.05 + 0j, 0.005 + 0j, "0.05", None, b"0.05", [0.05]])
def test_rate_type_is_validated_before_membership(mmr):
    with pytest.raises(M.MarginError, match="Underhållssatsen"):
        M.MarginState("main", "A", mmr)
    with pytest.raises(M.MarginError, match="Underhållssatsen"):
        dataclasses.replace(st(), mmr=mmr)
    with pytest.raises(M.MarginError, match="Underhållssatsen"):
        M.threshold(L.Account.open(100), mmr)


def test_valid_numpy_rates_still_work():
    import numpy as np
    s = M.MarginState("main", "A", np.float64(0.05))
    assert s.mmr == 0.05 and type(s.mmr) is float
    assert M.threshold(short_legacy(), np.float64(0.005)) == pytest.approx(
        ORACLE["O11_likvidation"]["legacy_short_w-1"]["mark_mmr_0_005"], rel=1e-12)


@pytest.mark.parametrize("bad", [None, "konto", 7, {"q": 1.0}])
def test_public_entry_points_reject_non_accounts(bad):
    with pytest.raises(M.MarginError, match="ledger-Account|Fel typ"):
        M.threshold(bad, 0.05)
    with pytest.raises(M.MarginError, match="ledger-Account|Fel typ"):
        M.check_bar(bad, st(), BAR, 100, 110, 90, 100)
    with pytest.raises(M.MarginError, match="ledger-Account|Fel typ"):
        M.check(bad, st(), M.GAP, 100.0, M.MARK_OPEN, BAR)
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    chk = M.check(acct, st(), M.GAP, 62.0, M.MARK_OPEN, BAR)
    with pytest.raises(M.MarginError, match="ledger-Account|Fel typ"):
        M.liquidate(bad, st(), chk)
    with pytest.raises(M.MarginError, match="Fel typ"):
        M.check_bar(acct, "tillstånd", BAR, 100, 110, 90, 100)


# Regressioner för Codex omgranskning av c312dfa (C4-03).

@pytest.mark.parametrize("big", [10 ** 400, -(10 ** 400)])
def test_huge_integer_rate_is_margin_error(big):
    state = st()
    acct = L.Account.open(1000)
    with pytest.raises(M.MarginError, match="Underhållssatsen"):
        M.MarginState("main", "A", big)
    with pytest.raises(M.MarginError, match="Underhållssatsen"):
        dataclasses.replace(state, mmr=big)
    with pytest.raises(M.MarginError, match="Underhållssatsen"):
        M.threshold(acct, big)
    assert state == st() and acct == L.Account.open(1000)


def test_huge_integer_price_is_margin_error():
    acct = L.Account(C=-60_000.0, q=1000.0, deposit=40_000.0, avg_price=100.0)
    with pytest.raises(M.MarginError, match="ändligt flyttal"):
        M.check(acct, st(), M.GAP, 10 ** 400, M.MARK_OPEN, BAR)
    with pytest.raises(M.MarginError, match="ändligt flyttal"):
        M.check_bar(acct, st(), BAR, 100, 10 ** 400, 90, 100)


def test_ordinary_integer_and_float_rates_unchanged():
    assert M.MarginState("main", "A", 0.05).mmr == 0.05 and M.MarginState("main", "A", 0.005).mmr == 0.005
    with pytest.raises(M.MarginError, match="Underhållssatsen"):
        M.MarginState("main", "A", 1)                                # vanligt heltal: giltigt tal men ingen registrerad sats
