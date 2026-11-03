"""Read archived H-0013 training statistics only; no market data or strategy execution."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'research/results/H-0013-20261103T143504962276Z-completed.json'
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'f752202e7c6413265d0dc404f546720d835d569af2251704134a41b44d561ee1'
data = json.loads(raw)
assert data['holdout_loaded'] is False and data['decision'] == 'REJECT'
wf = data['result']['walk_forward']
counts = Counter()
windows = []
for window in wf['windows']:
    eligible = []
    for candidate, regimes in window['candidates'].items():
        for label, stats in regimes.items():
            few = stats['trades'] < 20
            bad_t = stats['t'] is None or stats['t'] <= 0
            reason = 'both_fail' if few and bad_t else 'trade_count_only' if few else 't_only' if bad_t else 'eligible'
            counts[reason] += 1
            if not few and not bad_t:
                eligible.append({'candidate': candidate, 'regime': label, **stats})
    # Independently verify recorded choices using the locked selection rule.
    for label, selected in window['playbook']['choices'].items():
        candidates = [(c, window['candidates'][c][label]) for c in ['ema_adx_trend', 'bb_rsi_reversion']]
        valid = [(c, s) for c, s in candidates if s['trades'] >= 20 and s['t'] is not None and s['t'] > 0]
        expected = max(valid, key=lambda pair: pair[1]['sharpe'])[0] if valid else 'platt'
        assert selected == expected
    windows.append({'test': window['test'], 'eligible': eligible, 'executed_trades': window['trades'],
                    'local_return': window['local_return']})
assert len(windows) == 6 and sum(counts.values()) == 48
print(json.dumps({'source': str(SOURCE.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'scope': 'existing archived result only; no new backtest or holdout access',
                  'candidate_regime_assessments': dict(counts), 'windows': windows,
                  'final_training_candidates': wf['final']['candidates'],
                  'final_choices': wf['final']['playbook']['choices']}, ensure_ascii=False, indent=2))
