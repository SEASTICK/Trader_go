#!/usr/bin/env python3
"""Synthetic review of the immutable B source at bfdb33b, not later fixes.

Loads that committed pure module in memory; no source mutations or market history.
Records independently calculated decisions, timing, gap recovery, mutation probes
and the empty-input defect. Run with the project's engine/.venv/bin/python.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import types

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REV = 'bfdb33b8c083ec65af2da8eecabc30de1f1a1b3f'
TARGET = Path(__file__).with_name('verification.json')


def module(source):
    out = types.ModuleType('synthetic_review_signal')
    exec(compile(source, 'committed_momentum_signal', 'exec'), out.__dict__)
    return out


def run():
    source = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                     REV + ':engine/traderlab/momentum_signal.py'], text=True)
    signal = module(source)
    prices = [100.]
    for i in range(150):
        prices.append(prices[-1] * (1 + .001 * (i % 7 - 3) + .0002 * (i % 3)))
    index = pd.date_range('2021-01-01', periods=len(prices) * 6, freq='4h', tz='UTC')
    bars = pd.DataFrame({'close': [p if k == 5 else p * (1 + .01 * k)
                                   for p in prices for k in range(6)]}, index=index)

    def formulas(m):
        got = m.signals(bars)
        for i in range(60, len(prices)):
            row = got.iloc[i]
            returns = [prices[j] / prices[j - 1] - 1 for j in range(i - 59, i + 1)]
            vol = statistics.stdev(returns) * math.sqrt(365)
            strength = sum(prices[i] > prices[i - h] for h in (7, 14, 28)) / 3
            assert row['available'] and row['decision_time'] == index[i * 6] + pd.Timedelta(days=1)
            assert math.isclose(row['vol'], vol, rel_tol=1e-12)
            assert row['s'] == strength
            assert math.isclose(row['w_target'], strength * min(1, .1 / vol), rel_tol=1e-12, abs_tol=1e-15)

    def gap(m):
        day = index[80 * 6]
        got = m.signals(bars.drop(day + pd.Timedelta(hours=8)))
        assert got.loc[day, 'reason'] == 'incomplete_day'
        assert not got.iloc[80:141]['available'].any()
        assert got.iloc[141]['available']

    formulas(signal)
    gap(signal)
    base = signal.signals(bars)
    cuts = (366, 367, 481, 504, 707, 905)
    for cut in cuts:
        part = bars.iloc[:cut]
        at = part.index[-1] + pd.Timedelta(hours=4)
        got = signal.signals(part)
        known = got[got['decision_time'] <= at]
        pd.testing.assert_frame_equal(known, base.loc[known.index])
    future = bars.copy()
    future.loc[index[100 * 6]:, 'close'] *= 4
    pd.testing.assert_frame_equal(signal.signals(future).iloc[:100], base.iloc[:100])

    caught = []
    for name, old, new, probe in (
        ('decision_time', 'daily.index + pd.Timedelta(days=1)', 'daily.index + pd.Timedelta(hours=20)', formulas),
        ('ddof', 'np.std(rets, ddof=1)', 'np.std(rets, ddof=0)', formulas),
        ('incomplete_day', 'last.reindex(days).where(complete)', 'last.reindex(days)', gap),
    ):
        assert old in source
        mutant = module(source.replace(old, new))
        try:
            probe(mutant)
        except AssertionError:
            caught.append(name)
        else:
            raise AssertionError('Mutation not caught: ' + name)

    empty = pd.DataFrame({'close': pd.Series(dtype=float)}, index=pd.DatetimeIndex([], tz='UTC'))
    signal.validate_bars(empty)
    assert signal.daily_closes(empty).shape == (0, 2)
    try:
        signal.signals(empty)
    except KeyError as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    else:
        raise AssertionError('Expected defect no longer reproduced in the locked revision')
    return {'reviewed_revision': REV, 'synthetic_only': True,
            'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
            'independent_daily_decisions': 91, 'prefix_cuts': list(cuts),
            'future_perturbation_passed': True, 'gap_recovery_day_offset': 61,
            'caught_in_memory_mutations': caught,
            'B_P2_empty_input': {'validation_accepted': True, 'daily_shape': [0, 2], 'signals_error': error}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: bfdb33b synthetic formulas/timing, three mutations and empty-input defect reproduced')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
