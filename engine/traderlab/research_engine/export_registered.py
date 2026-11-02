"""Explicit adapter for registered Phase 1 results. No data fetching or backtests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..registry import latest_decisions

HYPOTHESES = {'H-0009': 'ema_adx_trend', 'H-0010': 'donchian_breakout',
              'H-0011': 'bb_rsi_reversion', 'H-0012': 'squeeze_breakout'}
CRITERIA = {'t_at_least_required', 'stressed_costs_positive',
            'sharpe_above_buy_and_hold', 'stability_at_least_half'}
OUTPUT = Path('app/data/registered-results.json')


def export_registered(repo: Path) -> list[dict]:
    decisions = latest_decisions((repo / 'research/registry.md').read_text())
    exported = []
    for hypothesis, strategy in HYPOTHESES.items():
        files = sorted((repo / 'research/results').glob(hypothesis + '-*.json'))
        if not files:
            raise ValueError(f'{hypothesis}: resultat saknas; exporten avbruten')
        path = files[-1]
        raw = path.read_bytes()
        r = json.loads(raw)
        if (r.get('hypothesis_id') != hypothesis or r.get('strategy') != strategy
                or r.get('phase') != 'fas1' or r.get('simulated') is not False
                or set(r.get('criteria', {})) != CRITERIA
                or not all(type(v) is bool for v in r['criteria'].values())
                or r.get('meets_all_criteria') != all(r['criteria'].values())):
            raise ValueError(f'{hypothesis}: ogiltigt registrerat resultat')
        decision = decisions.get(hypothesis)
        if decision not in ('REJECT', 'MORE_RESEARCH', 'READY_FOR_PAPER'):
            raise ValueError(f'{hypothesis}: registrerat beslut saknas')
        curve = r['curves']
        if not curve['t'] or len({len(curve[k]) for k in ('t', 'equity', 'drawdown')}) != 1:
            raise ValueError(f'{hypothesis}: ogiltig kurva')
        end = r['out_of_sample'][1]
        if any(t[:10] < r['out_of_sample'][0] or t[:10] >= end for t in curve['t']):
            raise ValueError(f'{hypothesis}: kurva utanför registrerad testperiod')
        audit = None
        for candidate in sorted((repo / 'research/audits').glob('reproduction-*/' + strategy + '.json'), reverse=True):
            a = json.loads(candidate.read_text())
            if (a.get('kind') == 'technical_reproduction' and a.get('hypothesis_id') == hypothesis
                    and a.get('stats') == r['stats'] and a.get('curves') == curve
                    and a.get('final_params') == r['final_params'] and a.get('reproducible_equity') is True):
                audit = {'result_file': candidate.relative_to(repo).as_posix(),
                         'dataset_sha256': a['dataset_sha256'], 'code_commit': a['code_commit'],
                         'bootstrap_sharpe_ci': a['bootstrap_sharpe_ci'],
                         'without_best_year_sharpe': a['without_best_year_sharpe'],
                         'excluded_best_year': a['excluded_best_year']}
                break
        exported.append({'contract_version': 1, 'source': 'HISTORIK', 'kind': 'registered',
                         'hypothesis_id': hypothesis, 'strategy': strategy, 'version': r['strategy_version'],
                         'decision': decision, 'run_at': r['run_at'], 'period': r['out_of_sample'],
                         'market': r['market'], 'interval': r['interval'],
                         'stats': r['stats'], 'curves': curve, 'baseline_stats': r['baseline_buy_and_hold'],
                         'criteria': r['criteria'], 'windows': r['windows'], 'params': r['final_params'],
                         'stability': r['stability'], 'stressed_total_return': r['stressed_total_return'],
                         't_daily_nw': r['t_daily_nw'], 't_required': r['t_required'],
                         'trials_total': r['trials_total'], 'attempts': r['attempts'],
                         'costs_bps_per_side': r['costs_bps_per_side'], 'trades': r['trades'],
                         'registry_commit': r['registry_commit'],
                         'result_file': path.relative_to(repo).as_posix(),
                         'result_sha256': hashlib.sha256(raw).hexdigest(), 'audit': audit,
                         'warnings': ['Historiskt använd utvecklingsperiod; inget nytt oberoende slutprov.',
                                      'Slutprovet från 2025 körs inte i denna vy.',
                                      'Historiska testresultat är ingen prognos eller ett tillstånd till livehandel.',
                                      'Separat mark-price- och likvidationsvalidering återstår.']})
    # Validate completely before replacing the previous export.
    encoded = json.dumps(exported, ensure_ascii=False, indent=1, allow_nan=False) + '\n'
    target = repo / OUTPUT
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.json.tmp')
    temporary.write_text(encoded)
    temporary.replace(target)
    return exported
