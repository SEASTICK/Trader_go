#!/usr/bin/env python3
"""A1-r2 arithmetic review, synthetic only. No engine or market-data imports.

Checks selected corrected oracle outcomes independently and reproduces two
remaining specification gaps. This is not a test of an implemented event engine.
"""
import argparse
from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = Path(__file__).with_name('verification.json')
D = Decimal


def run():
    # Read only synthetic, committed specification fixtures.
    oracle = json.loads((ROOT / 'docs/momentum-a1-orakel.json').read_text())
    risk = oracle['O14_reduce_only']
    assert risk['open_90']['q'] == 2 and risk['open_90']['cost'] == 0
    assert risk['open_90']['risk_reduce_only_hold'] is True
    assert risk['open_110']['q'] < 2 and risk['open_110']['risk_reduce_only_hold'] is False
    b = oracle['O5b_kapitalfaser_B']
    assert b['vikt_after_trade'] == .5 and b['vikt_after_funding_B'] > .5
    times = oracle['O16_fundingtider']
    assert times['plus_30s']['betalt_A'] == times['plus_30s']['betalt_B'] == 5
    assert times['minus_30s']['betalt_A'] == times['minus_30s']['betalt_B'] == 0

    # O8's gap example. Existing long stops at the opening, BEFORE +30s funding.
    cash, units, price, stop = D(10000), D(900), D(94), D(95)
    fee, rate = D('.0016'), D('.0001')
    assert price <= stop
    after_stop_equity = cash + units * price - fee * units * price
    held_at_plus_30s = D(0)
    chronological_payment = held_at_plus_30s * price * rate
    literal_L2_payment = units * price * rate
    assert chronological_payment == 0 and literal_L2_payment == D('8.46')

    # The prescribed liquidation sets E to zero permanently, so §4's ratio
    # is undefined on subsequent days. Do not silently coerce it to zero here.
    equity = [D(100000), D(0), D(0), D(0)]
    returns = []
    with localcontext() as ctx:
        ctx.traps[InvalidOperation] = True
        for before, after in zip(equity, equity[1:]):
            try:
                returns.append(str(after / before - 1))
            except InvalidOperation:
                returns.append('undefined_0_over_0')
    assert returns == ['-1', 'undefined_0_over_0', 'undefined_0_over_0']
    return {
        'reviewed_revision': '979fb30f483b856d9210be3591101cd0fb3b3b98',
        'synthetic_only': True,
        'corrected_oracle_outcomes_checked': ['O14 gap directions', 'O5b phases', 'O16 +/-30s'],
        'gap_stop_before_funding': {
            'stop_at': '2022-01-02T00:00:00+00:00',
            'funding_at': '2022-01-02T00:00:30+00:00',
            'cash_after_gap_stop': str(after_stop_equity),
            'q_at_funding': str(held_at_plus_30s),
            'actual_payment_both_legacy_orders': str(chronological_payment),
            'literal_L2_payment': str(literal_L2_payment),
            'if_funding_exactly_at_opening': {'A_payment': str(literal_L2_payment), 'B_payment': '0'}},
        'liquidation_following_days': {
            'equity': [str(v) for v in equity], 'returns_under_unqualified_ratio': returns,
            'needs_explicit_absorbing_zero_convention': True},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result
        print('PASS: corrected synthetic oracle outcomes and two remaining contract gaps')
    else:
        TARGET.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        print(TARGET)
