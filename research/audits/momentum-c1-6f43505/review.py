#!/usr/bin/env python3
"""C1 fix verification on locked Git source; only synthetic accounts/prices."""
import argparse
import dataclasses
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import warnings

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REV = '6f4350569f52527d9a156333240b735530e423a6'
OLD = '6eba8d61cca0df03c3aa6c352a26834011479094'
TARGET = Path(__file__).with_name('verification.json')


def source(rev):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                    rev + ':engine/traderlab/momentum_ledger.py'], text=True)


def run():
    # Reuse the preserved independent Decimal reference, not production sizing.
    spec = importlib.util.spec_from_file_location('prior_c1_review', ROOT / 'research/audits/momentum-c1-6eba8d6/review.py')
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    old_source, new_source = source(OLD), source(REV)
    old, new = prior.module(old_source), prior.module(new_source)
    prior.normal_cases(new)
    rng = random.Random(1701)
    for i in range(250):
        E, M, old_w = rng.uniform(1000, 100000), rng.uniform(25, 200), rng.uniform(-.95, .95)
        q, C = old_w * E / M, E * (1 - old_w)
        avg = M * rng.uniform(.8, 1.2)
        args = dict(C=C, q=q, deposit=C + q * avg, avg_price=avg)
        P, w, c = M * rng.uniform(.97, 1.03), rng.uniform(-1, 1), (.0016, .004)[i % 2]
        for name in ('fill_normal', 'fill_risk'):
            a, f = getattr(old, name)(old.Account(**args), w, P, M, c)
            b, g = getattr(new, name)(new.Account(**args), w, P, M, c)
            assert vars(a) == vars(b) and vars(f) == vars(g)

    valid = new.Account(C=800, q=2, deposit=1000, avg_price=100)
    rejected = 0
    for field in ('C', 'q', 'deposit', 'avg_price', 'realized', 'costs'):
        for value in (math.nan, math.inf, -math.inf, True, '1'):
            for make in (lambda: new.Account(**(dict(C=800, q=2, deposit=1000, avg_price=100) | {field: value})),
                         lambda: dataclasses.replace(valid, **{field: value})):
                try:
                    make()
                except new.LedgerError:
                    rejected += 1
                else:
                    raise AssertionError('Invalid Account accepted')
    assert rejected == 60
    for fill in (new.fill_normal, new.fill_risk):
        before = dataclasses.replace(valid)
        try:
            fill(valid, 0, 1e308, 100)
        except new.LedgerError:
            pass
        else:
            raise AssertionError('Overflow accepted')
        assert valid == before
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        for kind in (float, int, np.float64, np.int64):
            try:
                new.solve_units(*(kind(x) for x in (1000, 0, 200, 100, -1)))
            except new.LedgerError:
                pass
            else:
                raise AssertionError('Undefined first division accepted')
        try:
            new.solve_units(1e308, 0., 1e-300, 1e-300, 1.)
        except new.LedgerError:
            pass
        else:
            raise AssertionError('Nonfinite q0 accepted')
    return {'reviewed_revision': REV, 'previous_revision': OLD, 'synthetic_only': True,
            'source_sha256': {'before': hashlib.sha256(old_source.encode()).hexdigest(),
                              'after': hashlib.sha256(new_source.encode()).hexdigest()},
            'decimal_reference_cases': 250, 'identical_before_after_normal_risk_pairs': 500,
            'rejected_invalid_constructions_and_replacements': rejected,
            'original_overflow_rejected_both_fill_paths': True,
            'first_division_rejected_for_python_and_numpy': True,
            'nonfinite_q0_rejected': True, 'input_account_unchanged_on_error': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: C1 fixes, 250 Decimal cases, 500 identical before/after fills and numeric guards')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
