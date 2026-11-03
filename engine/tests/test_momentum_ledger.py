"""mom-ledger/1.0.0 (H-0017 leverans C1) mot syntetiska orakel. Ingen marknadshistorik.

Facit kommer från docs/momentum-a1-orakel.json (separat räknekod i scripts/) och handräknade uttryck, aldrig från
produktionslösaren.
"""
import dataclasses
import json
import math
import warnings
from pathlib import Path

import numpy as np
import pytest

from traderlab import momentum_ledger as L

ORACLE = json.loads((Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())
REL = 1e-12
c = 0.0016


def close(a, b):
    return a == pytest.approx(b, rel=REL, abs=1e-9)


def pos(C, q, avg, deposit):
    """Konto med givet innehav och konsekvent avstämning (realized = costs = 0)."""
    acct = L.Account(C=C, q=q, deposit=deposit, avg_price=avg)
    assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-9)
    return acct


def test_version_and_costs():
    assert L.VERSION == "mom-ledger/1.0.0"
    assert L.COST_NORMAL == pytest.approx(0.0016, rel=1e-15)
    assert L.COST_STRESS == pytest.approx(0.0040, rel=1e-15)


def test_O1_fee_w05_matches_oracle_and_hand_formula():
    o = ORACLE["O1_avgift_w05"]
    acct, f = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    hand_q = 0.5 * 100_000 / (100 * (1 + 0.5 * c))
    assert close(f.q_new, o["q"]) and close(f.q_new, hand_q)
    assert close(f.dq, o["q"]) and close(f.cost, o["cost"]) and close(acct.C, o["C"])
    assert close(f.E_trade, o["E_after"]) and close(f.weight_trade, 0.5)
    assert f.E_before == 100_000 and f.phase == "after_trade" and not f.risk_reduce_only_hold


def test_O2_target_one_after_cost_is_not_overexposed():
    o = ORACLE["O2_avgift_w1"]
    acct, f = L.fill_normal(L.Account.open(100_000), 1.0, 100, 100)
    assert close(f.q_new, 100_000 / 100.16) and close(f.q_new, o["q"])
    assert close(f.E_trade, o["E_after"]) and f.weight_trade <= 1 + REL
    assert abs(acct.C) < 1e-9                             # hela kapitalet i positionen, inget mer
    assert 1000 * 100 / (100_000 - c * 100 * 1000) > 1    # naiva 1 000 enheter vore överexponering


def test_O3_basis_counted_once():
    o = ORACLE["O3_basis"]
    acct, f = L.fill_normal(L.Account.open(100_000), 0.5, 100, 99.5)
    hand_q = 50_000 / (99.5 + 0.5 * (0.5 + 0.16))
    assert close(f.q_new, hand_q) and close(f.q_new, o["q"])
    assert close(f.cost, o["cost"]) and close(acct.C, o["C"]) and close(f.E_trade, o["E_after"])
    assert close(f.E_trade, 100_000 + f.dq * (99.5 - 100) - f.cost)
    assert close(f.weight_trade, 0.5)


def test_O4_partial_buy_then_partial_sell():
    o = ORACLE["O4_partial"]
    a1, _ = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    assert close(a1.equity(110), o["E_fore_kop"]) and close(a1.weight(110), o["vikt_fore_kop"])
    a2, buy = L.fill_normal(a1, 0.60, 110, 110)
    assert close(buy.q_new, o["kop"]["q"]) and close(buy.cost, o["kop"]["cost"]) and close(a2.C, o["kop"]["C"])
    assert close(buy.E_trade, o["kop"]["E_after"]) and close(buy.weight_trade, 0.60)
    assert buy.realized_delta == 0 and close(a2.avg_price, (a1.q * 100 + buy.dq * 110) / buy.q_new)
    a3, sell = L.fill_normal(a2, 0.40, 105, 105)
    assert close(a2.equity(105), o["E_fore_salj"])
    assert close(sell.q_new, o["salj"]["q"]) and close(sell.cost, o["salj"]["cost"]) and close(a3.C, o["salj"]["C"])
    assert close(sell.E_trade, o["salj"]["E_after"]) and close(sell.weight_trade, 0.40)
    sold = a2.q - a3.q
    assert close(sell.realized_delta, sold * (105 - a2.avg_price))   # bara sålda enheter
    assert a3.avg_price == a2.avg_price
    for acct in (a1, a2, a3):
        assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-9)


def test_no_trade_takes_no_cost_and_changes_nothing():
    a1, _ = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    a2, f = L.fill_normal(a1, a1.weight(100), 100, 100)
    assert f.dq == 0 and f.cost == 0 and a2 == a1


def test_full_close_with_zero_weight():
    a1, _ = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    for fill in (L.fill_normal, L.fill_risk):
        a2, f = fill(a1, 0.0, 97, 96.5)
        assert f.q_new == 0 and a2.q == 0 and a2.avg_price == 0
        assert close(f.cost, c * 97 * a1.q)
        assert close(f.realized_delta, a1.q * (97 - 100))
        assert close(a2.C, a1.C + a1.q * 97 - c * 97 * a1.q) and close(f.E_trade, a2.C)
        assert not f.risk_reduce_only_hold


@pytest.mark.parametrize("w0,w1", [(1.0, -1.0), (-1.0, 1.0)])
def test_reversal_is_one_trade_with_one_cost(w0, w1):
    a1, f1 = L.fill_normal(L.Account.open(100_000), w0, 100, 100)
    a2, f2 = L.fill_normal(a1, w1, 104, 104)
    assert np.sign(a2.q) == np.sign(w1) and close(f2.weight_trade, w1)
    assert close(f2.dq, a2.q - a1.q) and close(abs(f2.dq), abs(a1.q) + abs(a2.q))
    assert close(f2.cost, c * 104 * abs(f2.dq))
    assert close(f2.realized_delta, a1.q * (104 - 100))           # hela gamla positionen, en gång
    assert a2.avg_price == 104
    assert close(a2.C, a1.C - f2.dq * 104 - f2.cost)
    assert a2.reconciliation_gap() == pytest.approx(0, abs=1e-9)
    assert close(a2.costs, f1.cost + f2.cost)


def test_short_legacy_weight_minus_one_matches_oracle():
    o = ORACLE["O11_likvidation"]["legacy_short_w-1"]
    acct, f = L.fill_normal(L.Account.open(100_000), -1.0, 100, 100)
    assert close(f.q_new, o["q"]) and close(acct.C, o["C"]) and close(f.E_trade, o["E_after"])
    assert close(f.weight_trade, -1.0)


def test_O14_risk_is_reduce_only_after_gap():
    o = ORACLE["O14_reduce_only"]
    acct = pos(800, 2, 100, 1000)
    assert close(acct.weight(100), 0.20)
    same, down = L.fill_risk(acct, 0.195, 90, 90)
    assert down.risk_reduce_only_hold and close(down.q_star, o["open_90"]["q_star"])
    assert down.q_new == 2 and down.dq == 0 and down.cost == 0 and same == acct
    assert close(down.E_trade, o["open_90"]["E_trade"])
    smaller, up = L.fill_risk(acct, 0.195, 110, 110)
    assert not up.risk_reduce_only_hold and close(up.q_new, o["open_110"]["q"]) and up.q_new < 2
    assert close(up.cost, o["open_110"]["cost"]) and close(up.weight_trade, 0.195)


def test_O15_normal_intent_may_change_direction_after_gap():
    o = ORACLE["O15_normal_efter_gap"]
    acct = pos(800, 2, 100, 1000)
    new, f = L.fill_normal(acct, 0.15, 70, 70)
    assert f.dq > 0 and close(f.q_new, o["fyllning"]["q"]) and close(f.cost, o["fyllning"]["cost"])
    assert close(f.weight_trade, 0.15) and not f.risk_reduce_only_hold


def test_risk_never_buys_from_flat_or_flips_sign():
    flat = L.Account.open(1000)
    same, f = L.fill_risk(flat, 0.5, 100, 100)
    assert f.risk_reduce_only_hold and same == flat and f.cost == 0
    long_, _ = L.fill_normal(flat, 0.5, 100, 100)
    same, f = L.fill_risk(long_, -0.5, 100, 100)
    assert f.risk_reduce_only_hold and same.q == long_.q


def test_scaling_capital_scales_amounts_and_keeps_relative_measures():
    k = 7.25
    a, fa = L.fill_normal(pos(800, 2, 100, 1000), 0.6, 105, 104.5)
    b, fb = L.fill_normal(pos(800 * k, 2 * k, 100, 1000 * k), 0.6, 105, 104.5)
    for x, y in ((fa.q_new, fb.q_new), (fa.cost, fb.cost), (fa.E_trade, fb.E_trade), (a.C, b.C)):
        assert close(y, k * x)
    assert close(fa.weight_trade, fb.weight_trade)


def test_trace_record_exposes_after_trade_phase_without_funding():
    acct, f = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100)
    d = f.as_dict()
    assert d["phase"] == "after_trade" and d["version"] == L.VERSION
    assert {"E_before", "E_trade", "q_old", "q_new", "dq", "cost", "P", "M", "c", "kind"} <= set(d)
    assert d["E_trade"] == acct.equity(100)                # ingen funding inbakad


def test_cost_stress_uses_same_solver():
    acct, f = L.fill_normal(L.Account.open(100_000), 0.5, 100, 100, L.COST_STRESS)
    assert close(f.q_new, 50_000 / (100 * (1 + 0.5 * 0.004))) and close(f.weight_trade, 0.5)


@pytest.mark.parametrize("kwargs", [
    dict(E=math.nan), dict(E=math.inf), dict(E=0.0), dict(E=-5.0), dict(E=True),
    dict(P=0.0), dict(P=-1.0), dict(P=math.nan), dict(M=0.0), dict(M=math.inf),
    dict(w=1.5), dict(w=-1.01), dict(w=math.nan), dict(c=-0.001), dict(c=math.nan), dict(q_old=math.nan)])
def test_invalid_solver_inputs_raise(kwargs):
    args = dict(E=1000.0, q_old=0.0, P=100.0, M=100.0, w=0.5, c=c) | kwargs
    with pytest.raises(L.LedgerError):
        L.solve_units(**args)


@pytest.mark.parametrize("args,why", [
    ((1000.0, 0.0, 100.0, 10.0, -1.0), "båda vakterna"),
    ((1000.0, -5.0, 500.0, 1.0, -1.0), "bara nämnaren <= 0, grenen ser konsekvent ut"),
    ((1000.0, 5.0, 1.0, 500.0, -1.0), "nämnaren > 0 men lösningen motsäger säljgrenen"),
])
def test_inconsistent_solution_raises_instead_of_clipping(args, why):
    # Extrem syntetisk basis P/M; varje vakt måste fånga sitt fall ensam.
    with pytest.raises(L.LedgerError):
        L.solve_units(*args)


@pytest.mark.parametrize("capital", [0.0, -1.0, math.nan])
def test_invalid_capital_raises(capital):
    with pytest.raises(L.LedgerError):
        L.Account.open(capital)


def test_numpy_scalars_are_accepted_and_no_nan_leaks():
    acct, f = L.fill_normal(L.Account.open(np.float64(1000)), np.float64(0.5), np.int64(100), np.float64(100))
    assert all(math.isfinite(v) for v in (f.q_new, f.cost, f.E_trade, acct.C))


def test_long_sequence_reconciles():
    acct = L.Account.open(50_000)
    for w, p, m in [(0.3, 100, 100), (0.8, 103, 102.5), (0.2, 99, 99.4), (-0.6, 97, 97), (-1.0, 95, 95.2),
                    (0.4, 101, 100.7), (0.0, 108, 108)]:
        acct, f = L.fill_normal(acct, w, p, m)
        assert close(f.weight_trade, w) if w else acct.q == 0
        assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-8)
    assert acct.q == 0 and close(acct.C, acct.deposit + acct.realized - acct.costs)


# Regressioner för Codex granskning av 6eba8d6 (C1-01 och C1-02).

FIELDS = ("C", "q", "deposit", "avg_price", "realized", "costs")


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "1"])
def test_account_fields_must_be_finite_numbers(field, value):
    ok = dict(C=800.0, q=2.0, deposit=1000.0, avg_price=100.0)
    with pytest.raises(L.LedgerError):
        L.Account(**(ok | {field: value}))
    with pytest.raises(L.LedgerError):
        dataclasses.replace(L.Account(**ok), **{field: value})


def test_valid_negative_cash_short_and_losses_are_kept():
    acct = L.Account(C=-450.0, q=8.0, deposit=1000.0, avg_price=150.0, realized=-200.0, costs=50.0)
    assert acct.reconciliation_gap() == pytest.approx(0, abs=1e-9) and acct.equity(150) == 750
    short = L.Account(C=1900.0, q=-6.0, deposit=1000.0, avg_price=150.0)
    assert short.weight(150) == pytest.approx(-900 / 1000)
    new, f = L.fill_normal(acct, 0.5, 150, 150)
    assert math.isfinite(new.realized) and new.realized < 0 and new.reconciliation_gap() == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("fill", [L.fill_normal, L.fill_risk])
def test_overflow_from_finite_arguments_raises_and_leaves_account(fill):
    acct = pos(800, 2, 100, 1000)
    before = dataclasses.replace(acct)
    with pytest.raises(L.LedgerError):
        fill(acct, 0.0, 1e308, 100)            # stängning: realiserat och C överflödar
    assert acct == before


@pytest.mark.parametrize("fill,w", [(L.fill_normal, 0.2), (L.fill_risk, 0.5)])
def test_no_trade_and_hold_paths_also_check_overflow(fill, w):
    acct = pos(800, 2, 100, 1000)
    with pytest.raises(L.LedgerError):
        fill(acct, w, 1e308, 1e308)            # E före affär = 800 + 2e308 = inf


def test_public_values_never_return_nonfinite():
    big = L.Account(C=1e308, q=0.0, deposit=-1e308)
    with pytest.raises(L.LedgerError):
        big.reconciliation_gap()
    with pytest.raises(L.LedgerError):
        L.Account(C=1e308, q=1e308).equity(10)
    with pytest.raises(L.LedgerError):
        L.Account(C=1e308, q=1e308).weight(10)


@pytest.mark.parametrize("args", [
    (1000, 0, 200.0, 100, -1),
    (1000.0, 0.0, np.float64(200), 100.0, -1.0),
    (np.int64(1000), np.int64(0), np.int64(200), np.int64(100), np.int64(-1)),
    (np.float64(1000), 0, 200, np.float64(100), np.float64(-1)),
])
def test_zero_first_denominator_is_ledger_error_for_all_scalar_types(args):
    with warnings.catch_warnings():
        warnings.simplefilter("error")         # ingen numpy-varning eller inf får välja gren
        with pytest.raises(L.LedgerError, match="kostnadsfria nämnaren"):
            L.solve_units(*args)
        acct = L.Account(C=args[0], q=args[1], deposit=args[0])
        with pytest.raises(L.LedgerError):
            L.fill_normal(acct, args[4], args[2], args[3])


def test_nonfinite_intermediate_from_finite_arguments_raises():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(L.LedgerError, match="q0"):
            L.solve_units(1e308, 0.0, 1e-300, 1e-300, 1.0)


def test_numpy_scalars_give_same_result_as_python_floats():
    a = L.solve_units(1000.0, 2.0, 101.0, 100.5, 0.3)
    b = L.solve_units(np.float64(1000), np.int64(2), np.float64(101), np.float64(100.5), np.float64(0.3))
    assert a == b and type(b) is float
