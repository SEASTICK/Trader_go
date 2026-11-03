#!/usr/bin/env python3
"""C1 independent Decimal checks and guard-defect reproductions, synthetic only.

Loads the immutable ledger source at 6eba8d6 in memory. It does not test later
fixes, read market history, mutate production code, or run any research job.
"""
import argparse
from decimal import Decimal as D, localcontext
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import types
import warnings

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REV = '6eba8d61cca0df03c3aa6c352a26834011479094'
TARGET = Path(__file__).with_name('verification.json')
COUNTER = itertools.count()


def module(source):
    name = 'locked_ledger_review_' + str(next(COUNTER))
    out = types.ModuleType(name)
    sys.modules[name] = out  # dataclasses resolves postponed annotations via the module.
    exec(compile(source, name, 'exec'), out.__dict__)
    return out


def normal_cases(ledger):
    rng = random.Random(1701)
    with localcontext() as ctx:
        ctx.prec = 50
        for i in range(250):
            E, M = rng.uniform(1000, 100000), rng.uniform(25, 200)
            old_w = rng.uniform(-.95, .95)
            q, C = old_w * E / M, E * (1 - old_w)
            avg = M * rng.uniform(.8, 1.2)
            account = ledger.Account(C=C, q=q, deposit=C + q * avg, avg_price=avg)
            P, w, c = M * rng.uniform(.97, 1.03), rng.uniform(-1, 1), (.0016, .004)[i % 2]
            dC, dq, dP, dM, dw, dc = (D(str(v)) for v in (C, q, P, M, w, c))
            # Independent reference: enumerate BOTH buy/sell candidates from the
            # cash ledger, rather than using production's cost-free branch choice.
            roots = []
            for sign in (D(1), D(-1)):
                den = dM - dw * (dM - dP - dc * dP * sign)
                if den <= 0:
                    continue
                x = dw * (dC + dq * dP * (1 + dc * sign)) / den
                equity = dC - (x - dq) * dP - dc * dP * abs(x - dq) + x * dM
                if sign * (x - dq) >= 0 and x * dw >= 0 and equity > 0:
                    roots.append((x, equity))
            assert len(roots) == 1
            target, expected_equity = roots[0]
            new, fill = ledger.fill_normal(account, w, P, M, c)
            assert math.isclose(fill.q_new, float(target), rel_tol=1e-11, abs_tol=1e-9)
            assert math.isclose(fill.E_trade, float(expected_equity), rel_tol=1e-11, abs_tol=1e-8)
            assert math.isclose(fill.weight_trade, w, rel_tol=1e-11, abs_tol=1e-12)
            assert abs(new.reconciliation_gap()) < 1e-7
            risk, risk_fill = ledger.fill_risk(account, w, P, M, c)
            assert abs(risk.q) <= abs(account.q) and risk.q * account.q >= 0
            if risk_fill.risk_reduce_only_hold:
                assert risk == account and risk_fill.dq == risk_fill.cost == 0


def run():
    source = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                     REV + ':engine/traderlab/momentum_ledger.py'], text=True)
    ledger = module(source)
    normal_cases(ledger)
    caught = []
    for name, old, new in (
        ('double_cost', 'cost = c * P * abs(dq)', 'cost = 2 * c * P * abs(dq)'),
        ('ignore_basis', 'k = M - P - c * P if buy else M - P + c * P', 'k = -c * P if buy else c * P'),
        ('risk_increase', 'hold = abs(q_star) > abs(acct.q) or q_star * acct.q < 0', 'hold = False'),
    ):
        assert old in source
        try:
            normal_cases(module(source.replace(old, new)))
        except AssertionError:
            caught.append(name)
        else:
            raise AssertionError('Mutation escaped: ' + name)

    poisoned = ledger.Account(C=800, q=2, deposit=1000, avg_price=math.nan)
    poisoned_after, poisoned_fill = ledger.fill_normal(poisoned, .1, 100, 100)
    assert math.isfinite(poisoned_fill.E_trade)
    assert math.isnan(poisoned_after.realized) and math.isnan(poisoned_fill.realized_delta)
    valid = ledger.Account(C=800, q=2, deposit=1000, avg_price=100)
    overflow_after, overflow_fill = ledger.fill_normal(valid, 0, 1e308, 100)
    assert math.isinf(overflow_after.C) and math.isinf(overflow_fill.E_trade)

    native_error = None
    try:
        ledger.solve_units(1000, 0, 200., 100, -1)
    except Exception as exc:
        native_error = type(exc).__name__
    assert native_error == 'ZeroDivisionError'
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter('always')
        numpy_result = ledger.solve_units(1000, 0, np.float64(200), 100, -1)
    assert math.isclose(numpy_result, -3125, rel_tol=1e-11)
    assert any('divide by zero' in str(w.message) for w in recorded)
    return {
        'reviewed_revision': REV, 'synthetic_only': True,
        'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'decimal_reference_cases': 250, 'precision': 50,
        'normal_and_risk_checked': True, 'caught_in_memory_mutations': caught,
        'C1_01_nonfinite_ledger': {
            'nan_account_metadata_accepted': True, 'finite_equity_with_nan_realized_delta': True,
            'finite_inputs_return_infinite_equity': True},
        'C1_02_initial_denominator_zero': {
            'inputs': {'E': 1000, 'q_old': 0, 'P': 200, 'M': 100, 'w': -1},
            'native_float_error': native_error, 'numpy_float64_returns': float(numpy_result),
            'numpy_division_warning': True},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: 250 Decimal cases, three mutations and two C1 guard defects reproduced at 6eba8d6')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
