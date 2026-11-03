#!/usr/bin/env python3
"""Synthetic C2 Decimal verification and API regression checks at locked fcf5cb4.

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
REV = 'fcf5cb4a42f76b6151a8fe66f0c87f9617e95430'
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
    old_source = subprocess.check_output(['git', '-C', str(ROOT), 'show',
        '1d9359f:engine/traderlab/momentum_funding.py'], text=True)
    old = load('_review_c2_old_funding', old_source.replace('from .momentum_ledger import ', 'from ._review_c2_ledger import '))
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
                old_result = old.apply_funding(account, old.FundingState('a', str(stress)),
                    old.FundingEvent(str(i), t, rate, m, 'mark_open', old.bar_open(t)),
                    record.phase, old.FundingConfig(stress=stress))
                for actual, previous in zip((new, state2, record), old_result):
                    assert dataclasses.asdict(actual) == dataclasses.asdict(previous)
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
    phase_cases = 0
    for offset in (0, -1, 1, -30000, 30000):
        t = T + pd.Timedelta(milliseconds=offset)
        event = F.FundingEvent('phase', t, .0001, 100, 'mark_open', F.bar_open(t))
        for phase in F.PHASES:
            state = F.FundingState('main', 'A')
            expected = (offset == 0) == (phase != 'funding_interior')
            try:
                new, _, record = F.apply_funding(base, state, event, phase)
            except F.FundingError:
                assert not expected
            else:
                assert expected and record.payment == 5 and new.C == 49995
            assert base.C == 50000 and state.processed == frozenset()
            phase_cases += 1
    def reject(call):
        try:
            call()
        except F.FundingError:
            return
        raise AssertionError('Expected FundingError')
    state = F.FundingState('main', 'A')
    bad_values = ['f1', b'f1', None, 7, {'f1': True}, True,
                  [None], [''], [b'f1'], [1], [False]]
    for ids in bad_values:
        reject(lambda: F.FundingState('main', 'A', ids))
        reject(lambda: dataclasses.replace(state, processed=ids))
    event = F.FundingEvent('f1', T, .0001, 100, 'mark_open', T)
    once, booked, _ = F.apply_funding(base, state, event, 'funding_A')
    for collection in (set, frozenset, list, tuple):
        restored = F.FundingState('main', 'A', collection(['f1']))
        assert restored.processed == frozenset({'f1'})
        reject(lambda: F.apply_funding(once, restored, event, 'funding_A'))
    separate, _, _ = F.apply_funding(base, F.FundingState('other', 'B'), event, 'funding_B')
    assert once.C == separate.C == 49995 and booked.processed == frozenset({'f1'})
    for bad_source in ([], (), {}, 1, None):
        reject(lambda: F.FundingEvent('bad', T, .0001, 100, bad_source, T))
    return {'reviewed_revision': REV, 'synthetic_only': True,
            'source_sha256': {'ledger': hashlib.sha256(ledger_source.encode()).hexdigest(),
                              'funding': hashlib.sha256(funding_source.encode()).hexdigest()},
            'decimal_funding_stress_cases': 400, 'previous_C1_decimal_cases': 250,
            'valid_before_after_identical_cases': 400,
            'phase_matrix_cases': phase_cases, 'invalid_state_constructor_replace_checks': len(bad_values)*2,
            'restored_whole_id_duplicate_rejections': 4, 'separate_scenario_verified': True,
            'invalid_price_source_checks': 5}



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: C2 fixes, 400 unchanged Decimal cases and 250 C1 cases verified at fcf5cb4')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
