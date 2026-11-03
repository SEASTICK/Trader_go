#!/usr/bin/env python3
"""Review immutable signal versions before/after the empty-input fix; synthetic only."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import types

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REV = '3294e8f992818e9f988077eafb2e6ef110be86f0'
OLD = 'bfdb33b8c083ec65af2da8eecabc30de1f1a1b3f'
TARGET = Path(__file__).with_name('verification.json')


def source(rev):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                    rev + ':engine/traderlab/momentum_signal.py'], text=True)


def module(text):
    out = types.ModuleType('locked_signal_review')
    exec(compile(text, 'locked_signal_review', 'exec'), out.__dict__)
    return out


def calculation_prefix(node):
    prefix = []
    for part in node.body:
        if isinstance(part, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('out', 'col') for t in part.targets):
            break
        prefix.append(ast.dump(part, include_attributes=False))
    return prefix


def run():
    old_text, new_text = source(OLD), source(REV)
    old, new = module(old_text), module(new_text)
    old_functions = {n.name: n for n in ast.parse(old_text).body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: n for n in ast.parse(new_text).body if isinstance(n, ast.FunctionDef)}
    for name in ('validate_bars', 'daily_closes', 'latest_decision'):
        assert ast.dump(old_functions[name], include_attributes=False) == ast.dump(new_functions[name], include_attributes=False)
    assert calculation_prefix(old_functions['signals']) == calculation_prefix(new_functions['signals'])

    prices = [100.]
    for i in range(150):
        prices.append(prices[-1] * (1 + .001 * (i % 7 - 3) + .0002 * (i % 3)))
    idx = pd.date_range('2021-01-01', periods=len(prices) * 6, freq='4h', tz='UTC')
    bars = pd.DataFrame({'close': [p if h == 5 else p * (1 + .01 * h)
                                  for p in prices for h in range(6)]}, index=idx)
    cases = [bars.iloc[:n] for n in (1, 2, 5, 6, 7, 59, 60, 360, 365, 366, 367, 481, 905, 906)]
    cases += [bars.drop(idx[80 * 6 + 2]), bars[~(idx.floor('D') == idx[80 * 6])], bars.assign(close=100.)]
    for case in cases:
        pd.testing.assert_frame_equal(new.signals(case), old.signals(case))
    ref = new.signals(bars)
    schema = {name: str(dtype) for name, dtype in ref.dtypes.items()}
    for empty in (bars.iloc[:0], pd.DataFrame({'close': pd.Series(dtype=float)}, index=pd.DatetimeIndex([], tz='UTC'))):
        new.validate_bars(empty)
        got = new.signals(empty)
        assert got.empty and list(got) == new.COLUMNS
        assert got.dtypes.to_dict() == ref.dtypes.to_dict()
        assert isinstance(got.index, pd.DatetimeIndex) and str(got.index.tz) == 'UTC'
        for column in ('decision_time', 'earliest_fill'):
            assert str(got[column].dt.tz) == 'UTC'
        try:
            new.latest_decision(got, pd.Timestamp('2022-01-01', tz='UTC'))
        except KeyError as exc:
            assert 'Inget beslut känt' in str(exc)
        else:
            raise AssertionError('Expected documented lookup error')
        try:
            old.signals(empty)
        except KeyError:
            pass
        else:
            raise AssertionError('Old empty-input defect did not reproduce')
    incomplete = new.signals(bars.iloc[:2])
    assert len(incomplete) == 1 and not incomplete.iloc[0]['available']
    assert incomplete.iloc[0]['reason'] == 'incomplete_day' and pd.isna(incomplete.iloc[0]['w_target'])
    return {'reviewed_revision': REV, 'previous_signal_revision': OLD, 'synthetic_only': True,
            'source_sha256': {'before': hashlib.sha256(old_text.encode()).hexdigest(),
                              'after': hashlib.sha256(new_text.encode()).hexdigest()},
            'unchanged_calculation_ast': True, 'identical_nonempty_cases': len(cases),
            'typed_empty_cases': 2, 'schema': schema, 'documented_empty_lookup_error': True,
            'nonempty_incomplete_day_preserved': True, 'old_defect_reproduced': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: 3294e8f empty schema fixed; unchanged calculations and 17 nonempty outputs')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
