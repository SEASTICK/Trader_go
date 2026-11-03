#!/usr/bin/env python3
"""Independent arithmetic review of A1-r3 synthetic specification fixtures.

No market history, strategy engine, trading job or registration is used. Existing
stats functions are checked on synthetic 1096-day absorbing-loss series only.
"""
import argparse
from decimal import Decimal as D, localcontext
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'engine'))
from traderlab import stats

TARGET = Path(__file__).with_name('verification.json')
REVISION = 'a25db812c1ea60932de7bf8fbcaf33a009859b46'


def near(actual, expected):
    assert math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-10), (actual, expected)


def run():
    fixtures = json.loads((ROOT / 'docs/momentum-a1-orakel.json').read_text())
    legacy = fixtures['O17_legacy_ordning']
    with localcontext() as ctx:
        ctx.prec = 40
        c, p, q = D('.0016'), D(94), D(900)
        gap_cash = D(10000) + q * p - c * p * q
        pay_A = q * p * D('.0001')
        near(legacy['gapstop_plus_30s']['E_efter_gapstop'], gap_cash)
        assert legacy['gapstop_plus_30s']['q_vid_handelse'] == 0
        assert legacy['gapstop_plus_30s']['L1'] == legacy['gapstop_plus_30s']['L2'] == 0
        near(legacy['gapstop_exakt_vid_oppning']['A'], pay_A)
        assert legacy['gapstop_exakt_vid_oppning']['B'] == 0
        near(legacy['gapstop_exakt_vid_oppning']['E_A'], gap_cash - pay_A)
        near(legacy['gapstop_exakt_vid_oppning']['E_B'], gap_cash)
        # Independent equal-price entry from cash, not A1's sizing helper.
        new_q = D(100000) / (D(100) * (1 + c))
        entry_C = D(100000) - new_q * D(100) * (1 + c)
        stop_C = entry_C + new_q * D(97) * (1 - c)
        entry_pay = new_q * D(100) * D('.0001')
        entry = legacy['inträde_vid_oppning_stop_inom_stapel']
        near(entry['q_open'], new_q)
        assert entry['L1_funding'] == 0
        near(entry['L2_funding'], entry_pay)
        near(entry['E_L1'], stop_C)
        near(entry['E_L2'], stop_C - entry_pay)

    loss = fixtures['O18_likvidation']
    expected = {
        'mitt_i_perioden': [.01, -1., 0., 0.],
        'terminaldag': [-.01, -1.],
        'delkonto_likviderat': [.02, -1., 0.],
        'blandning_ett_delkonto_likviderat': [.015, 51000/101500-1, 52000/51000-1],
    }
    for name, returns in expected.items():
        case = loss[name]
        assert case['langd'] == len(returns) == len(case['E_end']) - 1
        for actual, wanted in zip(case['r'], returns):
            near(actual, wanted)
        near(math.prod(1 + r for r in returns) - 1, case['E_end'][-1] / case['E_end'][0] - 1)
        assert all(math.isfinite(r) for r in case['r'])
        near(case['sharpe'], stats.sharpe(returns))
        near(case['nw_t'], stats.newey_west_t(returns))
    assert loss['oforklarad_nolla_ger_ogiltig'] is True
    # This decision field is a specified fixture, not a verified engine decision.
    assert loss['main_beslut'] == {'likvidationsflagga': True, 'C6': False, 'giltig': True, 'beslut': 'REJECT'}

    # Full horizon, liquidation on first/interior/terminal day. Expected series
    # are constructed directly; no division by a zero balance is attempted.
    full = []
    for liquidation_day in (1, 500, 1096):
        returns = [0.] * 1096
        returns[liquidation_day - 1] = -1.
        equity = [100000] * liquidation_day + [0] * (1097 - liquidation_day)
        assert len(equity) == 1097 and len(returns) == 1096
        assert math.prod(1 + r for r in returns) == equity[-1] / equity[0] == 0
        sharpe, t = stats.sharpe(returns), stats.newey_west_t(returns, lags=6)
        assert math.isfinite(sharpe) and math.isfinite(t)
        full.append({'liquidation_day': liquidation_day, 'days': len(returns),
                     'net_return': -1., 'sharpe': sharpe, 'nw_t_lags6': t})

    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
              ('docs/momentum-protokoll-A1.md', 'docs/momentum-a1-orakel.json', 'scripts/momentum-a1-oracles.py')}
    return {'reviewed_revision': REVISION, 'synthetic_only': True,
            'source_sha256': hashes,
            'R2_01': {'gap_stop_later_funding_both_L': 0., 'at_open_A': float(pay_A),
                      'at_open_B': 0., 'new_entry_L2_funding': float(entry_pay)},
            'R2_02': {'fixture_series_verified': list(expected), 'full_horizon_cases': full,
                      'mix_net_return': -.48, 'engine_decision_tested': False}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = run()
    if args.check:
        assert json.loads(TARGET.read_text()) == result, 'Sources or independent results changed'
        print('PASS: A1-r3 independent synthetic arithmetic, source hashes and full-horizon finite statistics')
    else:
        TARGET.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
        print(TARGET)
