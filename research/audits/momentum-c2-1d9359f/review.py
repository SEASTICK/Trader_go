#!/usr/bin/env python3
"""Synthetic C2 Decimal verification and API-defect reproduction at locked 1d9359f.

Loads the matching ledger and funding sources from Git into isolated in-memory
modules. No market archives, production mutations, external calls or research jobs.
"""
import argparse
import dataclasses
from decimal import Decimal as D, localcontext
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import types

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REV = '1d9359fe71259a9099ac7443993a48dfa8c1423f'
TARGET = Path(__file__).with_name('verification.json')
sys.path.insert(0, str(ROOT / 'engine'))
import traderlab


def source(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', REV + ':' + path], text=True)


def load(name, text):
    out = types.ModuleType('traderlab.' + name)
    out.__package__ = 'traderlab'
    sys.modules[out.__name__] = out
    exec(compile(text, out.__name__, 'exec'), out.__dict__)
    return out


def run():
    ledger_source = source('engine/traderlab/momentum_ledger.py')
    funding_source = source('engine/traderlab/momentum_funding.py')
    L = load('_review_c2_ledger', ledger_source)
    F = load('_review_c2_funding', funding_source.replace('from .momentum_ledger import ', 'from ._review_c2_ledger import '))
    spec = importlib.util.spec_from_file_location('prior_c1_decimal', ROOT / 'research/audits/momentum-c1-6eba8d6/review.py')
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    prior.normal_cases(L)
    rng = random.Random(1717)
    T = pd.Timestamp('2022-01-01', tz='UTC')
    with localcontext() as ctx:
        ctx.prec = 50
        for i in range(200):
            q = 0. if i % 11 == 0 else rng.uniform(-500, 500)
            m = rng.uniform(80, 200)
            rate = 0. if i % 13 == 0 else rng.uniform(-.001, .001)
            account = L.Account(C=100000 - q * m, q=q, deposit=100000, avg_price=m)
            t = T + pd.Timedelta(hours=4 * i) + pd.Timedelta(seconds=30 if i % 2 else 0)
            event = F.FundingEvent(str(i), t, rate, m, 'mark_open', F.bar_open(t))
            for stress in (False, True):
                state = F.FundingState('a', str(stress))
                before = dataclasses.replace(account)
                new, state2, record = F.apply_funding(account, state, event,
                    'funding_interior' if i % 2 else 'funding_A', F.FundingConfig(stress=stress))
                payment = D(str(q)) * D(str(m)) * D(str(rate))
                if stress and payment > 0:
                    payment *= 2
                assert math.isclose(record.payment, float(payment), rel_tol=1e-12, abs_tol=1e-10)
                assert math.isclose(new.C, float(D(str(account.C)) - payment), rel_tol=1e-12, abs_tol=1e-8)
                assert new.q == account.q and new.costs == account.costs and new.realized == account.realized
                assert math.isclose(new.funding_net, float(payment), rel_tol=1e-12, abs_tol=1e-10)
                assert abs(new.reconciliation_gap()) < 1e-7
                assert state.processed == frozenset() and account == before
                try:
                    F.apply_funding(new, state2, event, record.phase, F.FundingConfig(stress=stress))
                except F.FundingError:
                    pass
                else:
                    raise AssertionError('Duplicate in valid state accepted')

    base = L.Account(C=50000, q=500, deposit=100000, avg_price=100)
    phase_defects = []
    for t, phase in ((T + pd.Timedelta(seconds=30), 'funding_A'),
                     (T + pd.Timedelta(seconds=30), 'funding_B'), (T, 'funding_interior')):
        event = F.FundingEvent('phase', t, .0001, 100, 'mark_open', F.bar_open(t))
        _, _, record = F.apply_funding(base, F.FundingState('main', 'A'), event, phase)
        phase_defects.append({'time': record.time.isoformat(), 'accepted_phase': record.phase, 'payment': record.payment})
    event = F.FundingEvent('f1', T, .0001, 100, 'mark_open', T)
    once, _, r1 = F.apply_funding(base, F.FundingState('main', 'A'), event, 'funding_A')
    malformed = F.FundingState('main', 'A', processed='f1')
    twice, _, r2 = F.apply_funding(once, malformed, event, 'funding_A')
    assert r1.payment == r2.payment == 5 and twice.C == 49990 and twice.funding_net == 10
    try:
        F.FundingEvent('bad', T, .0001, 100, [], T)
    except Exception as exc:
        source_error = type(exc).__name__
    else:
        raise AssertionError('Expected unhashable-source failure')
    assert source_error == 'TypeError'
    return {'reviewed_revision': REV, 'synthetic_only': True,
            'source_sha256': {'ledger': hashlib.sha256(ledger_source.encode()).hexdigest(),
                              'funding': hashlib.sha256(funding_source.encode()).hexdigest()},
            'decimal_funding_stress_cases': 400, 'previous_C1_decimal_cases': 250,
            'correct_state_duplicate_rejection_verified': True,
            'C2_01_phase_time_mismatch_accepted': phase_defects,
            'C2_02_malformed_state': {'string_input': 'f1', 'normalized': sorted(malformed.processed),
                'cash_after_one': once.C, 'cash_after_duplicate': twice.C, 'funding_net_after_duplicate': twice.funding_net},
            'invalid_price_source_error': source_error}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: C2 400 Decimal cases, C1 compatibility and two funding API gaps reproduced at 1d9359f')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
