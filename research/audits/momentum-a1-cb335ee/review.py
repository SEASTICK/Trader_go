#!/usr/bin/env python3
"""Synthetic counterexamples to A1 cb335ee; no strategy/data imports or market files.

The Decimal cases solve the equal-price cash ledger independently of A1's solver.
The Sharpe example disproves monotonicity, not an observed strategy outcome.
"""
import argparse
from decimal import Decimal, getcontext
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import statistics

getcontext().prec = 40
D = Decimal
TARGET = Path(__file__).with_name('verification.json')


def run():
    fee = D('.0016')
    # Buy from cash: q*p = w*(initial - fee*q*p).
    initial, p, w = D(100000), D(100), D('.5')
    q = w * initial / (p * (1 + w * fee))
    post_trade = initial - fee * q * p
    paid = q * p * D('.0001')
    final = post_trade - paid
    assert abs(q * p / post_trade - w) < D("1e-35")
    assert q * p / final > w + D('1e-12')

    # Prior close C=800, q=2, M=100 => weight .20; target/cap .195.
    # Next open M=P=90: weight is already below target. Solving for frozen
    # target including the purchase fee requires ADDING units.
    cash, old_q, open_p, target = D(800), D(2), D(90), D('.195')
    equity = cash + old_q * open_p
    new_q = target * (equity + fee * open_p * old_q) / (open_p * (1 + target * fee))
    assert old_q * D(100) / (cash + old_q * D(100)) > target
    assert old_q * open_p / equity < target
    assert new_q > old_q

    boundary = datetime(2022, 1, 2, tzinfo=timezone.utc)
    event = boundary + timedelta(seconds=30)
    assert abs((event - boundary).total_seconds()) < 60
    assert event > boundary  # §8.3 nevertheless books it at boundary in §8.1.

    original = [.010, .011, .009, .100]
    financially_worse = [.010, .011, .009, .010]
    sharpe = lambda r: statistics.mean(r) / statistics.stdev(r) * math.sqrt(365)
    assert all(a <= b for a, b in zip(financially_worse, original))
    assert sum(financially_worse) < sum(original)
    assert sharpe(financially_worse) > sharpe(original)
    return {
        'reviewed_revision': 'cb335eec6b70002affc41b632b5931457e6a53fc',
        'synthetic_only': True,
        'scenario_B_phases': {
            'q': str(q), 'equity_before_funding': str(post_trade),
            'funding_paid': str(paid), 'equity_after_funding': str(final),
            'weight_before_funding': str(w), 'weight_after_funding': str(q * p / final)},
        'risk_intent_after_gap': {
            'old_units': str(old_q), 'target_weight': str(target),
            'opening_weight': str(old_q * open_p / equity),
            'solver_units': str(new_q), 'increase': str(new_q - old_q)},
        'funding_snap': {'actual_event': event.isoformat(), 'booked_boundary': boundary.isoformat(),
                         'moved_back_seconds': 30},
        'nonmonotone_sharpe': {
            'original_returns': original, 'financially_worse_returns': financially_worse,
            'original_annual_sharpe': sharpe(original),
            'financially_worse_annual_sharpe': sharpe(financially_worse)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result, 'Saved reproduction differs'
        print('PASS: four synthetic counterexamples; no market history read')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
        print(TARGET)
