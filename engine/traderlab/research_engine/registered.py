"""Reproduce frozen registered windows; never optimize or change registry decisions."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
from .. import backtest, fas1, metrics, quality
from ..data import binance
from ..strategies.rules import SPECS
from .runner import clean

DATASET='6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c'

def run_job(job, data_dir: Path, output: Path):
    repo=Path(__file__).resolve().parents[3]
    registered=json.loads((repo/'app/data/registered-results.json').read_text())
    proof=next((r for r in registered if r['hypothesis_id']==job.get('hypothesis_id')),None)
    if (not proof or job.get('kind')!='registered' or job.get('strategy')!=proof['strategy']
            or job.get('version')!=proof['version'] or job.get('market')!='um' or job.get('symbol')!='BTCUSDT'
            or job.get('interval')!='4h' or job.get('params')!={'reproduction':'frozen_windows_v1'}
            or pd.Timestamp(job['period_start'])!=pd.Timestamp('2020-01-01',tz='UTC')
            or pd.Timestamp(job['period_end'])!=pd.Timestamp('2025-01-01',tz='UTC')
            or job.get('capital')!=100000 or job.get('costs')!={'fee_bps':10,'spread_bps':2,'slippage_bps':5}
            or proof.get('decision')!='REJECT' or (proof.get('audit') or {}).get('dataset_sha256')!=DATASET):
        raise ValueError('Begäran matchar inte det frysta registrerade protokollet')
    original=repo/proof['result_file']
    if hashlib.sha256(original.read_bytes()).hexdigest()!=proof['result_sha256']:
        raise ValueError('Originalresultatets kontrollsumma matchar inte')
    frozen=json.loads((repo/'data/audits/fas1-20261102'/('frozen-'+DATASET+'.json')).read_text())
    # Only the 120 exact development archives are allowed; no network fallback.
    for i,item in enumerate(frozen['files']):
        folder='fundingRate' if 'fundingRate' in item['name'] else '4h'
        path=data_dir/'raw/binance/um/BTCUSDT'/folder/item['name']
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['sha256']: raise ValueError('Fryst data har ändrats')
        binance.verify_checksum(raw,path.with_suffix('.zip.CHECKSUM').read_bytes())
        output.with_suffix('.progress').write_text(str(.1+.2*i/120))
    start=pd.Timestamp('2020-01-01',tz='UTC');end=pd.Timestamp('2025-01-01',tz='UTC')
    bars=binance.load('um','BTCUSDT','4h',data_dir,start=start,end=end)
    funding=binance.load_funding('BTCUSDT',data_dir,start=start,end=end)
    if not quality.check(bars,'4h').ok: raise ValueError('Datakvalitetsfel')
    # The original audit fixes all OHLCV and settlement values, not just filenames.
    if hashlib.sha256(bars.to_csv(float_format='%.17g').encode()).hexdigest()!=frozen['bars_sha256']:
        raise ValueError('Staplar matchar inte det frysta datasetet')
    if hashlib.sha256(funding.to_csv(float_format='%.17g').encode()).hexdigest()!=frozen['funding_sha256']:
        raise ValueError('Funding matchar inte det frysta datasetet')
    spec=SPECS[proof['strategy']]
    backtest.check_no_lookahead(lambda b:spec.signals(b).target,bars)
    res=fas1._stitch(spec,SimpleNamespace(windows=proof['windows']),bars,fas1.COSTS,funding)
    full=clean(metrics.full_stats(res,bars[bars.index>=pd.Timestamp('2022-01-01',tz='UTC')]))
    curves=clean(metrics.curves(res))
    if full!=proof['stats'] or curves!=proof['curves']:
        raise ValueError('Reproduktionen avviker från originalet; inget nytt godkännande')
    market=json.loads((repo/'app/data/fas1-market.json').read_text())
    metadata=dict(contract_version=1,dataset_sha256=DATASET,engine_sha256=hashlib.sha256(
        b''.join(p.read_bytes() for p in sorted(Path(__file__).parents[1].rglob('*.py')))).hexdigest(),
        original_result_sha256=proof['result_sha256'],registry_commit=proof['registry_commit'],
        configuration={'windows':proof['windows'],'costs':job['costs'],'holdout_loaded':False})
    metadata['fingerprint']=hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest()
    result=dict(mode='registered',hypothesis_id=proof['hypothesis_id'],reproduction_match=True,
        decision=proof['decision'],stats=full,curves=curves,baseline=market['baseline_curves'],
        baseline_stats=proof['baseline_stats'],effective_params=proof['params'],windows=proof['windows'],
        criteria=proof['criteria'],metadata=metadata,warnings=[
            'Teknisk reproduktion av frysta registrerade fönster; inget nytt parameterurval',
            'Beslutet förblir REJECT; ingen strategi godkänns för papper',
            'Utvecklingsperioden är tidigare använd; slutprovet från 2025 har inte lästs',
            'Originalets förenklade kontraktsbaserade likvidationsmodell återges för spårbarhet'],
        trades=[dict(side=t.side,entry_time=t.entry_time.isoformat(),exit_time=t.exit_time.isoformat() if t.exit_time else None,
                     entry_price=t.entry_price,exit_price=t.exit_price,net_return=t.net_return,exit_reason=t.exit_reason) for t in res.trades])
    output.write_text(json.dumps(clean(result),allow_nan=False))
    output.with_suffix('.progress').write_text('0.9')
