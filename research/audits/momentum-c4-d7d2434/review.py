#!/usr/bin/env python3
"""Independent C4 review. Git-locked sources; synthetic values only, no network/data archives.
--check reproduces reference checks and controlled rejection of the historical defects.
"""
import argparse
import dataclasses as dc
from decimal import Decimal as D, localcontext
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import types
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REV = 'd7d2434dd7dbecc70f2267165a02e61296859346'
BASE = '35486b885da1cc249b7df97d5c68b9d17f67f53e'
LEDGER_BASE = 'db65a54bf96fa018c42506a2ee27886433dde71e'
TARGET = Path(__file__).with_name('verification.json')
sys.path.insert(0, str(ROOT / 'engine'))
import traderlab


def source(path, rev=REV):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', rev + ':' + path], text=True)


def load(name, code):
    mod = types.ModuleType('traderlab.' + name)
    mod.__package__ = 'traderlab'
    sys.modules[mod.__name__] = mod
    exec(compile(code, mod.__name__, 'exec'), mod.__dict__)
    return mod


def near(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-8), (a, b)


def reconciled(a):
    assert abs(a.reconciliation_gap()) <= 1e-12 * max(1., abs(a.deposit), abs(a.realized), abs(a.C), abs(a.q*a.avg_price))


def run():
    paths = ['engine/traderlab/momentum_' + n + '.py' for n in ('ledger', 'funding', 'signal', 'risk', 'margin')]
    paths += ['research/h0017-protokoll.md', 'research/registry.md', 'docs/momentum-a1-orakel.json',
              'docs/claude-uppdrag-momentum-C4.md', 'engine/tests/test_momentum_margin.py']
    sources = {p: source(p) for p in paths}
    L = load('_c4_ledger', sources[paths[0]])
    F = load('_c4_funding', sources[paths[1]].replace('from .momentum_ledger import ', 'from ._c4_ledger import '))
    load('_c4_signal', sources[paths[2]])
    R = load('_c4_risk', sources[paths[3]].replace('from .momentum_signal import ', 'from ._c4_signal import ')
             .replace('from . import momentum_ledger as ledger', 'from . import _c4_ledger as ledger')
             .replace('from .momentum_ledger import ', 'from ._c4_ledger import '))
    mc = sources[paths[4]].replace('from .momentum_ledger import ', 'from ._c4_ledger import ')
    M = load('_c4_margin', mc)
    old = load('_c4_base_ledger', source(paths[0], LEDGER_BASE))
    T = pd.Timestamp('2023-05-10 08:00', tz='UTC')
    def state(rate=.05): return M.MarginState('main', 'A/L1', rate)
    def reject(call, exc=L.LedgerError):
        try: call()
        except exc: return
        raise AssertionError('Expected controlled error')
    def liquidation(a, s, c):
        z, zs, rec = M.liquidate(a, s, c)
        assert (z.C, z.q, z.avg_price) == (0., 0., 0.) and zs.liquidated
        for field in ('deposit', 'realized', 'costs', 'funding_net'):
            assert getattr(z, field) == getattr(a, field)
        reconciled(z)
        near(rec.adjustment_delta, -D(str(a.C)) - D(str(a.q)) * D(str(a.avg_price)))
        near(rec.mark_to_market + rec.capital_reset, rec.adjustment_delta)
        near(z.liquidation_adjustment - a.liquidation_adjustment, rec.adjustment_delta)
        reject(lambda: M.liquidate(z, zs, c))
        reject(lambda: M.check(z, zs, M.GAP, c.m, M.MARK_OPEN, T))
        assert rec.account_before == a and rec.account_after == z
        return z, zs, rec

    rng = random.Random(170704)
    reference_cases = liquidations = 0
    with localcontext() as ctx:
        ctx.prec = 70
        for _ in range(150):
            scale = 10 ** rng.uniform(-3, 5)
            q = rng.choice((-1, 1)) * rng.uniform(10, 2000) * scale
            avg = rng.uniform(50, 250)
            C = (-.6 if q > 0 else 1.8) * abs(q) * avg
            realized, costs, funding, adjustment = (v * scale for v in (700, 160, 500, -20))
            deposit = C + q * avg - realized + costs + funding - adjustment
            a = L.Account(C=C, q=q, deposit=deposit, avg_price=avg, realized=realized,
                          costs=costs, funding_net=funding, liquidation_adjustment=adjustment)
            reconciled(a)
            for rate in (.05, .005):
                ddC, ddq, rr = D(str(C)), D(str(q)), D(str(rate))
                threshold = -ddC / (ddq * (1 - rr)) if q > 0 else ddC / (-ddq * (1 + rr))
                near(M.threshold(a, rate), threshold)
                for factor in ('0.9999999', '1.0000001'):
                    m = float(threshold * D(factor))
                    expected = ddC + ddq * D(str(m)) <= rr * abs(ddq) * D(str(m))
                    s = state(rate)
                    c = M.check(a, s, M.GAP, m, M.MARK_OPEN, T)
                    assert c.hit == expected
                    assert c.hit == (C + q * m <= rate * abs(q) * m)
                    near(c.E, ddC + ddq * D(str(m)))
                    if c.hit:
                        liquidation(a, s, c)
                        liquidations += 1
                    reference_cases += 1

    # Exact equality and adjacent float prices, independent direct-condition decision.
    boundary_cases = 0
    for rate in (.05, .005):
        for q in (-1000., 1000.):
            C = rate * 1000 * 100 - q * 100
            a = L.Account(C=C, q=q, avg_price=100, deposit=rate * 100000)
            c = M.check(a, state(rate), M.GAP, 100., M.MARK_OPEN, T)
            assert c.E == c.MM and c.hit
            for m in (math.nextafter(100., 0.), 100., math.nextafter(100., math.inf)):
                c = M.check(a, state(rate), M.GAP, m, M.MARK_OPEN, T)
                assert c.hit == (C + q * m <= rate * abs(q) * m)
                boundary_cases += 1

    # Negative E must remain visible; reset is positive, adjustment still total loss.
    a = L.Account(C=-90000, q=1000, deposit=10000, avg_price=100)
    c = M.check(a, state(), M.GAP, 85, M.MARK_OPEN, T)
    z, zs, rec = liquidation(a, state(), c)
    assert c.E == -5000 and rec.capital_reset == 5000 and rec.mark_to_market == -15000
    assert z.liquidation_adjustment == -10000
    # Stale account and wrong scenario rate rejected before returning an update.
    reject(lambda: M.liquidate(dc.replace(a, C=a.C+1), state(), c))
    reject(lambda: M.liquidate(a, state(.005), c))
    assert a.C == -90000

    # Actual partial trades and funding before liquidation retain every historical field.
    partial_cases = 0
    for rate in (.05, .005):
        partial = L.Account.open(100000)
        for w, price, mark in ((1., 100, 100), (.8, 104, 103.5), (1., 98, 98.2)):
            partial, _ = L.fill_normal(partial, w, price, mark)
        partial, _, _ = F.apply_funding(partial, F.FundingState('main', 'A'),
            F.FundingEvent('partial-funding', T, .01, 98, F.MARK_OPEN, T), 'funding_A')
        assert partial.costs > 0 and partial.realized != 0 and partial.funding_net > 0
        m = M.threshold(partial, rate) * .99
        cpartial = M.check(partial, state(rate), M.INTRABAR, m, M.MARK_LOW, T)
        assert cpartial.hit
        liquidation(partial, state(rate), cpartial)
        partial_cases += 1

    # O11 sizing uses an independent closed-form Decimal reference.
    o11 = json.loads(sources['docs/momentum-a1-orakel.json'])['O11_likvidation']
    for w in (-1., 1.):
        a, _ = L.fill_normal(L.Account.open(100000), w, 100, 100)
        near(a.q, D(str(w)) * D(100000) / D('100.16'))
        if w < 0:
            for rate, key in ((.05, 'mark_mmr_0_05'), (.005, 'mark_mmr_0_005')):
                near(M.threshold(a, rate), o11['legacy_short_w-1'][key])
        else:
            a = dc.replace(a, C=a.C-500, funding_net=500)
            assert M.check(a, state(), M.GAP, .52, M.MARK_OPEN, T).hit
            assert not M.check(a, state(), M.GAP, .60, M.MARK_OPEN, T).hit

    # A and B opening composition: gap valuation, A funding, check, fill, B funding.
    compositions = []
    for ordering in ('A', 'B'):
        for rate in (.05, .005):
            a = L.Account(C=-60000, q=1000, deposit=40000, avg_price=100)
            fs = F.FundingState('main', ordering)
            event = F.FundingEvent('open', T, .055, 63.5, F.MARK_OPEN, T)
            gap_E = a.C + a.q * 63.5
            if ordering == 'A':
                a, fs, _ = F.apply_funding(a, fs, event, 'funding_A')
                expected_E = gap_E - 1000 * 63.5 * .055
            else: expected_E = gap_E
            c = M.check(a, state(rate), M.GAP, 63.5, M.MARK_OPEN, T)
            near(c.E, expected_E)
            fill = None
            if c.hit:
                a, ms, _ = liquidation(a, state(rate), c)
                assert a.costs == 0
            else:
                a, fill = L.fill_normal(a, 0, 63, 63.5)
                if ordering == 'B':
                    a, fs, fr = F.apply_funding(a, fs, event, 'funding_B')
                    assert fr.payment == 0
            assert c.hit == (ordering == 'A')
            assert (fill is None) == c.hit
            compositions.append({'ordering': ordering, 'mmr': rate, 'hit': c.hit, 'fill': fill is not None})

    # Interior debit before credit, both rates, long and short adverse extremes.
    adverse_cases = 0
    for rate in (.05, .005):
        for q, C, price, high, low, debit_rate in ((1000, -60000, 64, 66, 63.5, .06),
                                                  (-1000, 180000, 179, 179.5, 175, -.01)):
            a = L.Account(C=C, q=q, deposit=C+q*100, avg_price=100)
            fs = F.FundingState('main', 'A')
            pay = F.FundingEvent('pay', T+pd.Timedelta(minutes=30), debit_rate, price, F.MARK_OPEN, T)
            credit = F.FundingEvent('credit', T+pd.Timedelta(hours=2), -debit_rate, price, F.MARK_OPEN, T)
            a, fs, _ = F.apply_funding(a, fs, pay, 'funding_interior')
            reject(lambda: F.apply_funding(a, fs, pay, 'funding_interior'))
            c = M.check_bar(a, state(rate), T, price, high, low, price)
            assert c.m == (low if q > 0 else high) and c.hit
            assert c.price_source == (M.MARK_LOW if q > 0 else M.MARK_HIGH)
            assert not hasattr(c, 'time')
            a, ms, _ = liquidation(a, state(rate), c)
            # Future orchestration must skip credit entirely; no extra funding record.
            calls = []
            if not ms.liquidated:
                a, fs, _ = F.apply_funding(a, fs, credit, 'funding_interior'); calls.append('credit')
            assert calls == [] and a.equity(price) == 0
            adverse_cases += 1

    # C3 keeps the liquidated account absorbed through midnight and terminal.
    TT = pd.Timestamp('2024-12-30 20:00', tz='UTC')
    rs = R.RiskState(100000, 100000, 100000, TT, started=True)
    risk_steps = 0
    while TT <= pd.Timestamp('2024-12-31 20:00', tz='UTC'):
        rs, record = R.step(rs, TT, R.CloseInput(TT-R.BAR, z, 85, liquidated=True),
                            terminal=TT == pd.Timestamp('2024-12-31 20:00', tz='UTC'))
        assert record.intent is None and record.candidates == () and rs.liquidated
        risk_steps += 1
        TT += R.BAR
    assert rs.terminated
    survivor, _ = L.fill_normal(L.Account.open(50000), .5, 100, 100)
    assert z.equity(110) + survivor.equity(110) == survivor.equity(110) > 50000

    # Ledger change compatibility, compare all old account and fill fields.
    compatibility = 0
    for _ in range(100):
        capital = rng.uniform(10000, 1000000)
        new, prev = L.Account.open(capital), old.Account.open(capital)
        for w in (rng.uniform(-1, 1), rng.uniform(-1, 1)):
            price = rng.uniform(90, 110)
            new, nf = L.fill_normal(new, w, price, 100)
            prev, pf = old.fill_normal(prev, w, price, 100)
            nd = dc.asdict(new)
            assert nd.pop('liquidation_adjustment') == 0
            assert nd == dc.asdict(prev) and dc.asdict(nf) == dc.asdict(pf)
            compatibility += 1

    invalid = 0
    for value in (float('nan'), float('inf'), -float('inf'), True, '1', None):
        reject(lambda: dc.replace(L.Account.open(1000), liquidation_adjustment=value)); invalid += 1
        reject(lambda: M.check(L.Account.open(1000), state(), M.GAP, value, M.MARK_OPEN, T)); invalid += 1
    for value in (0, -1):
        reject(lambda: M.check(L.Account.open(1000), state(), M.GAP, value, M.MARK_OPEN, T)); invalid += 1
    for rate in (.01, float('nan'), float('inf'), True, '0.05', None):
        reject(lambda: state(rate)); invalid += 1
    reject(lambda: M.check(L.Account(C=0), state(), M.GAP, 100, M.MARK_OPEN, T)); invalid += 1
    reject(lambda: M.check(L.Account(C=1, q=1e300), state(), M.GAP, 1e10, M.MARK_OPEN, T)); invalid += 1
    reject(lambda: M.check_bar(L.Account.open(1000), state(), T, 100, 90, 80, 100)); invalid += 1

    a = L.Account(C=-60000, q=1000, deposit=40000, avg_price=100)
    for phase, source_name, stamp in (
        (M.GAP, M.MARK_LOW, T), (M.INTRABAR, M.MARK_HIGH, T),
        ('unknown', M.MARK_OPEN, T), (M.GAP, M.MARK_OPEN, T.tz_localize(None)),
        (M.GAP, M.MARK_OPEN, T+pd.Timedelta(seconds=1)),
        (M.GAP, M.MARK_OPEN, '2023-05-10 08:00')):
        reject(lambda: M.check(a, state(), phase, 62, source_name, stamp)); invalid += 1
    assert M.threshold(L.Account.open(1000), .05) is None
    assert not M.check(L.Account.open(1000), state(), M.GAP, 100, M.MARK_OPEN, T).hit

    # Reproduce the exact earlier cases, now requiring controlled errors.
    def controlled(call, exc):
        try: call()
        except exc as error:
            return {'exception': type(error).__name__, 'message': str(error)}
        raise AssertionError('Expected controlled rejection')

    overflow_examples = []
    for rate, q in ((.05, -1.75e308), (.005, -1.795e308)):
        a = L.Account(C=1e308, q=q, deposit=1e308)
        s = state(rate)
        before = dc.asdict(a), dc.asdict(s)
        with localcontext() as ctx:
            ctx.prec = 70
            expected = D('1e308') / (abs(D(str(q))) * (1 + D(str(rate))))
        assert math.isinf(abs(q) * (1 + rate))
        E, MM = a.C + a.q * .5, rate * abs(a.q) * .5
        assert math.isfinite(E) and math.isfinite(MM) and E > MM
        direct = controlled(lambda: M.threshold(a, rate), L.LedgerError)
        check = controlled(lambda: M.check(a, s, M.GAP, .5, M.MARK_OPEN, T), L.LedgerError)
        assert before == (dc.asdict(a), dc.asdict(s))
        overflow_examples.append({'mmr': rate, 'q': q, 'decimal_threshold': str(expected),
                                  'E': E, 'MM': MM, 'threshold_error': direct, 'check_error': check})

    leaks = {}
    for name, call in (
        ('complex_mmr', lambda: state(.05+0j)),
        ('check_bar_invalid_account', lambda: M.check_bar(None, state(), T, 100, 110, 90, 100)),
        ('threshold_invalid_account', lambda: M.threshold(None, .05))):
        leaks[name] = controlled(call, M.MarginError)

    # Expanded independent type matrix, including replace and every public entry.
    type_checks = 0
    a, s = L.Account.open(1000), state()
    before = dc.asdict(a), dc.asdict(s)
    for rate in (.05+0j, .005+0j, '0.05', None, b'0.05', [.05], {}, True):
        for call in (lambda: state(rate), lambda: dc.replace(s, mmr=rate),
                     lambda: M.threshold(a, rate)):
            controlled(call, M.MarginError); type_checks += 1
    valid = L.Account(C=105000, q=-1000, avg_price=100, deposit=5000)
    hit = M.check(valid, s, M.GAP, 110, M.MARK_OPEN, T)
    for bad in (None, 'account', 7, {'q': 1}, object()):
        for call in (lambda: M.threshold(bad, .05),
                     lambda: M.check(bad, s, M.GAP, 100, M.MARK_OPEN, T),
                     lambda: M.check_bar(bad, s, T, 100, 110, 90, 100),
                     lambda: M.liquidate(bad, s, hit)):
            controlled(call, M.MarginError); type_checks += 1
    assert before == (dc.asdict(a), dc.asdict(s))
    import numpy as np
    for rate in (.05, .005, np.float64(.05), np.float64(.005)):
        assert type(state(rate).mmr) is float
        near(M.threshold(valid, rate), D(105000)/(D(1000)*(1+D(str(rate)))))
    assert M.threshold(L.Account(C=0, q=10), .05) == 0
    assert M.threshold(L.Account.open(100), .005) is None

    # C4-03: exact former reproductions now require controlled rejection.
    # Compare the same inputs against the exact diff base, also via replace.
    base_margin = load('_c4_base_margin', source(paths[4], BASE).replace(
        'from .momentum_ledger import ', 'from ._c4_ledger import '))
    large_integer_regression = {}
    for label, module, error_type in (('base', base_margin, OverflowError),
                                      ('reviewed', M, M.MarginError)):
        st = module.MarginState('main', 'A/L1', .05)
        snapshot = dc.asdict(a), dc.asdict(st)
        outcomes = {}
        for name, call in (
            ('construction', lambda: module.MarginState('main', 'A/L1', 10**400)),
            ('replace', lambda: dc.replace(st, mmr=10**400)),
            ('threshold', lambda: module.threshold(a, 10**400))):
            outcomes[name] = controlled(call, error_type)
        assert snapshot == (dc.asdict(a), dc.asdict(st))
        large_integer_regression[label] = outcomes

    # Additional adversarial cases: controlled price rejection and two remaining leaks.
    large_price_errors = []
    for big in (10**400, -(10**400)):
        for call in (lambda: M.check(a, s, M.GAP, big, M.MARK_OPEN, T),
                     lambda: M.check_bar(a, s, T, 100, big, 90, 100)):
            large_price_errors.append(controlled(call, M.MarginError))
    # CPython's standard digit limit must be active; never modify it to hide a defect.
    assert sys.get_int_max_str_digits() == 4300
    formatting_leaks = {}
    for name, call in (
        ('construction', lambda: state(10**5000)),
        ('replace', lambda: dc.replace(s, mmr=10**5000)),
        ('threshold', lambda: M.threshold(a, 10**5000))):
        try:
            call()
        except M.MarginError:
            raise AssertionError('C4-04 no longer reproduced')
        except ValueError as error:
            formatting_leaks[name] = {'exception': type(error).__name__, 'message': str(error)}
        else:
            raise AssertionError('Missing rejection')
    ledger_leaks = {}
    for name, call in (
        ('construction', lambda: L.Account(C=10**400)),
        ('replace', lambda: dc.replace(a, C=10**400)),
        ('open', lambda: L.Account.open(10**400)),
        ('equity', lambda: a.equity(10**400))):
        ledger_leaks[name] = controlled(call, OverflowError)
    assert before == (dc.asdict(a), dc.asdict(s))

    # Independent in-memory mutations: do not modify implementation or test files.
    mutations = {}
    for name, before, after, probe in (
        ('strict_condition', 'E <= MM', 'E < MM', 'equality'),
        ('reversed_condition', 'E <= MM', 'E >= MM', 'equality_off'),
        ('short_wrong_extreme', 'INTRABAR, h, MARK_HIGH', 'INTRABAR, l, MARK_HIGH', 'short'),
        ('lost_adjustment', 'acct.liquidation_adjustment + delta', 'acct.liquidation_adjustment', 'adjustment')):
        assert before in mc
        mutant = load('_c4_mutant_'+name, mc.replace(before, after))
        try:
            s = mutant.MarginState('main', 'A', .05)
            a = L.Account(C=105000, q=-1000, avg_price=100, deposit=5000)
            if probe == 'equality':
                assert mutant.check(a, s, mutant.GAP, 100, mutant.MARK_OPEN, T).hit
            elif probe == 'equality_off':
                assert not mutant.check(a, s, mutant.GAP, 90, mutant.MARK_OPEN, T).hit
            elif probe == 'short':
                assert mutant.check_bar(a, s, T, 90, 110, 80, 90).m == 110
            else:
                c = mutant.check(a, s, mutant.GAP, 110, mutant.MARK_OPEN, T)
                zero, _, _ = mutant.liquidate(a, s, c)
                reconciled(zero)
        except AssertionError: mutations[name] = 'caught'
        else: raise AssertionError('Mutation survived: '+name)

    unchanged = paths[:4] + ['research/h0017-protokoll.md', 'research/registry.md']
    for path in unchanged: assert sources[path] == source(path, BASE)
    allowed = {'engine/traderlab/momentum_margin.py', 'engine/tests/test_momentum_margin.py',
               'docs/momentum-margin-C4.md', 'docs/momentum-status.json', 'docs/momentum-checklista.md'}
    changed = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only', BASE, REV], text=True).splitlines()
    assert set(changed) == allowed
    # The exhaustive diff allowlist also protects every historical audit/result/protocol.
    return {'changed_from_base': changed, 'additional_controlled_type_checks': type_checks,
            'ledger_compatibility_base': LEDGER_BASE, 'reviewed_revision': REV, 'diff_base': BASE, 'synthetic_only': True,
            'decimal_reference_checks': reference_cases, 'liquidation_identity_cases': liquidations, 'actual_partial_funding_liquidations': partial_cases,
            'float_boundary_checks': boundary_cases, 'opening_compositions': compositions,
            'interior_adverse_compositions': adverse_cases, 'C3_absorbed_steps': risk_steps,
            'ledger_identical_before_after_fills': compatibility, 'controlled_invalid_checks': invalid,
            'negative_equity_reset': {'E_before': rec.E_before, 'capital_reset': rec.capital_reset},
            'C4-04': formatting_leaks, 'C4-05': ledger_leaks, 'large_price_controlled_errors': large_price_errors,
            'C4-01': overflow_examples, 'C4-02': leaks, 'C4-03': large_integer_regression, 'in_memory_mutations': mutations,
            'unchanged_from_base': unchanged,
            'source_sha256': {p: hashlib.sha256(v.encode()).hexdigest() for p, v in sources.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: C4 locked reference, compatibility, compositions and C4-01/C4-02 controlled rejection; C4-03 controlled; C4-04/C4-05 reproduced (not approval)')
    else:
        TARGET.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        print(TARGET)
