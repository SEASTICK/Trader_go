#!/usr/bin/env python3
"""Locked C4-06 review. Git sources only; synthetic inputs, no network/archives.
--check recomputes and compares the complete verification artifact.
"""
import argparse
import ast
import dataclasses as dc
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import types
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REV = '9174b9c4f1543cefa6793a33d4eb7b853e0a368d'
BASE = '6530ca27f06e1c7816b61678f014b26dcf6a5fa5'
OLD = '4241d0e164db6a7c20250f31fef2695d86e885bb'
TARGET = Path(__file__).with_name('verification.json')
sys.path.insert(0, str(ROOT / 'engine'))
import traderlab


def source(path, rev=REV):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', rev+':'+path], text=True)


def load(name, code):
    m = types.ModuleType('traderlab.'+name)
    m.__package__ = 'traderlab'
    sys.modules[m.__name__] = m
    exec(compile(code, m.__name__, 'exec'), m.__dict__)
    return m


def modules(rev, tag):
    names = {n: '_c406_'+tag+'_'+n for n in ('ledger', 'signal', 'funding', 'risk')}
    out = []
    for n, name in names.items():
        code = source('engine/traderlab/momentum_'+n+'.py', rev)
        for dep, replacement in names.items():
            code = code.replace('from .momentum_'+dep+' import ', 'from .'+replacement+' import ')
            code = code.replace('from . import momentum_'+dep+' as ', 'from . import '+replacement+' as ')
        out.append(load(name, code))
    return out


def normalized(code, new):
    tree = ast.parse(code)
    if new:
        imports = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == 'momentum_ledger']
        assert len(imports) == 1
        assert imports[0].names[-1].name == '_show'
        imports[0].names.pop()
        count = 0
        # Only allow _show(expr) in formatted values within raise messages.
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                for f in ast.walk(node):
                    if isinstance(f, ast.FormattedValue) and isinstance(f.value, ast.Call) and isinstance(f.value.func, ast.Name) and f.value.func.id == '_show':
                        assert f.conversion == -1 and len(f.value.args) == 1 and not f.value.keywords
                        f.value = f.value.args[0]
                        f.conversion = ord('r')
                        count += 1
        assert count in (9, 4)
    return ast.dump(tree, include_attributes=False)


def error_cases(L, S, F, R, value):
    t = pd.Timestamp('2022-01-02', tz='UTC')
    a = L.Account(C=50000, q=500, avg_price=100, deposit=100000)
    fs = F.FundingState('main', 'A')
    ev = F.FundingEvent('x', t, .0001, 100, F.MARK_OPEN, t)
    sig = R.SignalInput(t-pd.Timedelta(days=1), t, True, 1., .5, .5, S.VERSION)
    rs = R.RiskState.start(100000, t)
    saved = [dc.asdict(x) for x in (a, fs, ev, sig, rs)]
    cases = {}
    for field in ('event_id', 'time', 'M_ref_time', 'M_ref_source', 'rate', 'M_ref'):
        cases['funding.'+field] = (lambda f=field: dc.replace(ev, **{f:value}), F.FundingError)
    for field in ('stress', 'price_model'):
        cases['funding.'+field] = (lambda f=field: F.FundingConfig(**{f:value}), F.FundingError)
    for field in ('account_key', 'scenario', 'processed'):
        cases['funding.'+field] = (lambda f=field: dc.replace(fs, **{f:[value] if f=='processed' else value}), F.FundingError)
    cases['funding.phase'] = (lambda: F.apply_funding(a, fs, ev, value), F.FundingError)
    cases['risk.start'] = (lambda: R.RiskState.start(100000, value), R.RiskError)
    cases['risk.initial'] = (lambda: R.RiskState.start(value, t), R.RiskError)
    for field in ('available', 'version', 'day', 'decision_time'):
        cases['risk.'+field] = (lambda f=field: dc.replace(sig, **{f:value}), R.RiskError)
    cases['risk.step_T'] = (lambda: R.step(rs, value, signal=sig), R.RiskError)
    cases['risk.bar_open'] = (lambda: R.CloseInput(value, a, 100), R.RiskError)
    cases['risk.mark_close'] = (lambda: R.CloseInput(t, a, value), R.RiskError)
    cases['risk.lock_day'] = (lambda: dc.replace(rs, lock_day=value), R.RiskError)
    result = {}
    for name, (call, expected) in cases.items():
        try:
            call()
        except expected as exc:
            assert str(exc) and f'{exc}' and repr(exc)
            result[name] = expected.__name__
        except ValueError:
            result[name] = 'ValueError'
        else:
            raise AssertionError(name+' accepted')
        assert saved == [dc.asdict(x) for x in (a, fs, ev, sig, rs)]
    return result


def rerun_reference(path, old_revision):
    # Reuse independent historical reference formulas without changing old audit files.
    code = source(path)
    m = types.ModuleType('_c406_reference_'+old_revision)
    m.__file__ = str(ROOT / path)
    exec(compile(code, m.__file__, 'exec'), m.__dict__)
    m.REV = REV
    original = m.subprocess.check_output
    def locked(args, **kw):
        args = [OLD+x[len(old_revision):] if isinstance(x, str) and x.startswith(old_revision+':') else x for x in args]
        result = original(args, **kw)
        if old_revision == 'd77e353' and any(isinstance(x, str) and x.endswith(':engine/traderlab/momentum_risk.py') for x in args):
            result = result.replace('from .momentum_signal import VERSION as SIGNAL_VERSION',
                                    'from ._review_c3_signal import VERSION as SIGNAL_VERSION')
        return result
    # Scoped subprocess facade prevents altering global subprocess or other audits.
    m.subprocess = types.SimpleNamespace(check_output=locked)
    return m.run()


def run():
    assert sys.get_int_max_str_digits() == 4300
    changed = subprocess.check_output(['git','-C',str(ROOT),'diff','--name-only',BASE,REV], text=True).splitlines()
    assert changed == sorted(['docs/momentum-C4-06-rattning.md','docs/momentum-checklista.md','docs/momentum-status.json',
        'engine/tests/test_momentum_funding.py','engine/tests/test_momentum_risk.py',
        'engine/traderlab/momentum_funding.py','engine/traderlab/momentum_risk.py'])
    for n in ('funding','risk'):
        p = 'engine/traderlab/momentum_'+n+'.py'
        assert normalized(source(p), True) == normalized(source(p, BASE), False)
        reverted = source(p).replace(', _show\n', '\n')
        reverted = re.sub(r'\{_show\(([^()]+)\)\}', r'{\1!r}', reverted)
        assert reverted == source(p, BASE)
        assert source(p, BASE) == source(p, OLD)
    # Exact changed-file allowlist also proves every other tracked file unchanged.
    current = modules(REV, 'new')
    baseline = modules(BASE, 'base')
    new = error_cases(*current, 10**5000)
    old = error_cases(*baseline, 10**5000)
    assert all(v != 'ValueError' for v in new.values())
    assert sum(v == 'ValueError' for v in old.values()) == 17
    original_eight = ['funding.event_id','funding.time','funding.M_ref_source','funding.stress',
                      'risk.start','risk.available','risk.version','risk.day']
    assert all(old[k] == 'ValueError' for k in original_eight)
    negative = error_cases(*current, -(10**5000))
    assert negative == new
    c2 = rerun_reference('research/audits/momentum-c2-fcf5cb4/review.py', '1d9359f')
    c3 = rerun_reference('research/audits/momentum-c3-8c19618/review.py', 'd77e353')
    assert c2['valid_before_after_identical_cases'] == c3['valid_before_after_identical_cases'] == 400
    paths = ['engine/traderlab/momentum_'+n+'.py' for n in ('ledger','signal','funding','risk','margin')]
    paths += ['research/h0017-protokoll.md','research/registry.md',
              'research/audits/momentum-c2-fcf5cb4/review.py','research/audits/momentum-c3-8c19618/review.py']
    assert sys.get_int_max_str_digits() == 4300
    return dict(reviewed_revision=REV, diff_base=BASE, comparison_revision=OLD, synthetic_only=True,
        changed_from_base=changed, only_error_formatting_and_import_changed=True,
        base_errors=old, fixed_errors=new, negative_integer_errors=negative,
        original_eight_reproduced=True, unchanged_inputs=True,
        c2_reference=c2, c3_reference=c3,
        source_sha256={r: {p: hashlib.sha256(source(p, r).encode()).hexdigest() for p in paths} for r in (REV, BASE, OLD)})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: C4-06; 44 controlled errors, 17 base leaks, 400 funding and 400 risk comparisons')
    else:
        TARGET.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        print(TARGET)
