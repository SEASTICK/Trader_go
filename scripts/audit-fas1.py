#!/usr/bin/env python3
"""Reproduce existing Phase 1 protocol; never approve strategies or load holdout."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import optuna
import pandas as pd
from traderlab import backtest, fas1, metrics, optimize, quality, stats
from traderlab.data import binance
from traderlab.research_engine.runner import clean
from traderlab.strategies.rules import SPECS


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    with path.open('x') as f:
        json.dump(clean(value), f, indent=2, allow_nan=False, default=str)
        f.write('\n')


def load_dataset(root):
    manifest = json.loads((root / 'futures-manifest.json').read_text())
    expected_months = binance.months('2020-01', '2024-12')
    expected_names = {f'BTCUSDT-4h-{m}.zip' for m in expected_months} | {
        f'BTCUSDT-fundingRate-{m}.zip' for m in expected_months}
    entries = manifest['files']
    if len(entries) != 120 or {f['name'] for f in entries} != expected_names:
        raise ValueError('Exactly 120 registered development archives required')
    frames, rates = [], []
    for f in entries:
        path = root / f['name']
        raw = path.read_bytes()
        if digest(raw) != f['sha256']:
            raise ValueError('Source archive changed: ' + f['name'])
        binance.verify_checksum(raw, path.with_suffix('.zip.CHECKSUM').read_bytes())
        month = path.stem[-7:]
        funding = '-fundingRate-' in f['name']
        expected_url = binance.funding_url('BTCUSDT', month) if funding else binance.kline_url('um','BTCUSDT','4h',month)
        if f['source'] != expected_url:
            raise ValueError('Unexpected source URL')
        table = binance.parse_funding_csv(binance._unzip_single(raw)) if funding else binance.parse_klines_csv(binance._unzip_single(raw))
        a = pd.Timestamp(month + '-01', tz='UTC')
        if not ((table.index >= a) & (table.index < a + pd.offsets.MonthBegin(1))).all():
            raise ValueError('Archive contains another month')
        (rates if funding else frames).append(table)
    bars, funding = pd.concat(frames), pd.concat(rates)
    report = quality.check(bars, '4h')
    expected = pd.date_range('2020-01-01','2025-01-01',freq='4h',inclusive='left',tz='UTC')
    fe = pd.date_range('2020-01-01','2025-01-01',freq='8h',inclusive='left',tz='UTC')
    if not report.ok or not bars.index.equals(expected) or not np.isfinite(bars.to_numpy()).all():
        raise ValueError('Invalid candle dataset')
    delay = funding.index - funding.index.floor('8h')
    if (not funding.index.floor('8h').equals(fe) or not np.isfinite(funding.to_numpy()).all()
            or (delay > pd.Timedelta(seconds=60)).any()):
        raise ValueError('Invalid funding dataset')
    secondary = json.loads((root / 'secondary-source.json').read_text())
    if {r['time'] for r in secondary['results']} != {str(t) for t, _ in report.outliers}:
        raise ValueError('All outliers require secondary-source evidence')
    for r in secondary['results']:
        t = pd.Timestamp(r['time'])
        if digest((root / ('coinbase-' + t.strftime('%Y%m%dT%H') + '.json')).read_bytes()) != r['sha256']:
            raise ValueError('Secondary source changed')
    frozen = {'contract':1,'market':'Binance USDⓈ-M BTCUSDT','interval':'4h',
              'period':['2020-01-01','2025-01-01'],'holdout_loaded':False,
              'files':entries,'quality':asdict(report),'funding_events':len(funding),
              'funding_max_delay_ms':float(delay.max().total_seconds()*1000),
              'bars_sha256':digest(bars.to_csv(float_format='%.17g').encode()),
              'funding_sha256':digest(funding.to_csv(float_format='%.17g').encode()),
              'secondary_source':secondary,'policy':'No imputation, deletion, timestamp shifting or instrument substitution',
              'limitations':['Previously used development period','Contract OHLC, no independent mark-price dataset',
                             'Secondary source is spot BTC-USD, different exchange and instrument'],
              'secondary_flags':[r['time'] for r in secondary['results'] if abs(r['difference_percentage_points'])>2]}
    dataset_id = digest(json.dumps(clean(frozen),sort_keys=True,default=str,allow_nan=False).encode())
    return bars, funding, frozen, dataset_id


def run(args):
    bars, funding, frozen, dataset_id = load_dataset(args.data)
    freeze = args.data / ('frozen-' + dataset_id + '.json')
    if freeze.exists():
        if json.loads(freeze.read_text()) != clean(json.loads(json.dumps(frozen,default=str))):
            raise ValueError('Frozen manifest changed')
    else:
        write_new(freeze,frozen)
    print('Dataset',dataset_id,flush=True)
    if args.verify_only:
        return
    if args.dataset != dataset_id:
        raise ValueError('Pass exact frozen --dataset hash before research')
    repo = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip():
        raise ValueError('Audit requires a clean, committed checkout')
    run_dir = args.data / ('reproduction-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    run_dir.mkdir()
    metadata = {'kind':'technical_reproduction','dataset_sha256':dataset_id,'code_commit':commit,
                'registered_protocol':'docs/fas1-audit-protocol.md','seed':0,'trials_per_optimization':40,
                'total_parameter_attempts_planned':1120,'original_hypothesis_attempts':12,
                'holdout_loaded':False,'paper_approval':False,'runtime':{'python':platform.python_version(),
                **{p:version(p) for p in ['numpy','pandas','scipy','optuna','ta']}}}
    write_new(run_dir/'metadata.json', metadata)
    original = optuna.study.Study.optimize
    context = {'strategy':None,'study':0}
    def instrument(study, objective, *a, **kw):
        number = context['study']; context['study'] += 1
        def record(s,t):
            row={'strategy':context['strategy'],'optimization':number,'trial':t.number,
                 'state':t.state.name,'params':t.params,'value':t.value,
                 'started':t.datetime_start,'completed':t.datetime_complete}
            with (run_dir/'trials.jsonl').open('a') as f:
                f.write(json.dumps(clean(row),default=str,allow_nan=False)+'\n')
        kw['callbacks'] = [*kw.get('callbacks',[]),record]
        return original(study,objective,*a,**kw)
    optuna.study.Study.optimize = instrument
    try:
        for n,(name,spec) in enumerate(SPECS.items(),9):
            context.update(strategy=name,study=0)
            print('Starting',name,flush=True)
            backtest.check_no_lookahead(lambda b: spec.signals(b).target,bars)
            wf = optimize.walk_forward(spec,bars,fas1.DEV_START,fas1.TEST_STARTS,fas1.HOLDOUT_START,fas1.COSTS,funding,40,0)
            normal=fas1._stitch(spec,wf,bars,fas1.COSTS,funding)
            repeat=fas1._stitch(spec,wf,bars,fas1.COSTS,funding)
            pd.testing.assert_series_equal(normal.equity,repeat.equity,check_exact=True)
            stressed=fas1._stitch(spec,wf,bars,fas1.COSTS.stressed(),funding)
            oos=bars[bars.index>=pd.Timestamp('2022-01-01',tz='UTC')]
            bh=backtest.run(oos,pd.Series(1.,index=oos.index),fas1.COSTS,funding=funding)
            daily=stats.daily_returns(normal.bar_returns)
            yearly=(1+daily).groupby(daily.index.year).prod()-1
            best=int(yearly.idxmax())
            kept=daily[daily.index.year!=best]
            full=metrics.full_stats(normal,oos)
            stress_return=float(stressed.equity.iloc[-1]-1)
            criteria={'t_at_least_required':stats.newey_west_t(daily)>=stats.t_krav(12),
                      'stressed_costs_positive':stress_return>0,
                      'sharpe_above_buy_and_hold':full['sharpe'] is not None and full['sharpe']>stats.sharpe(stats.daily_returns(bh.bar_returns)),
                      'stability_at_least_half':wf.stability>=0.5}
            result={**metadata,'hypothesis_id':f'H-{n:04}','strategy':name,'version':spec.version,
                    'original_decision':'REJECT','decision_changed':False,
                    'audit_criteria':criteria,'audit_meets_all_criteria':all(criteria.values()),
                    'stats':full,'baseline':metrics.full_stats(bh,oos),'stability':wf.stability,
                    'stressed_total_return':stress_return,'t_daily_nw':stats.newey_west_t(daily),
                    't_required':stats.t_krav(12),'bootstrap_sharpe_ci':stats.block_bootstrap_sharpe_ci(daily),
                    'yearly_returns':{str(k):float(v) for k,v in yearly.items()},
                    'excluded_best_year':best,'without_best_year_sharpe':stats.sharpe(kept),
                    'without_best_year_return':float((1+kept).prod()-1),
                    'windows':wf.windows,'final_params':wf.final_params,'trials':wf.trials,
                    'reproducible_equity':True,'curves':metrics.curves(normal),
                    'trades':[asdict(t) for t in normal.trades]}
            write_new(run_dir/(name+'.json'),result)
            print(name,json.dumps(clean({'criteria':criteria,'stats':full,'stability':wf.stability})),flush=True)
        write_new(run_dir/'complete.json',{'complete':True,'strategies':list(SPECS),'paper_approval':False})
    except BaseException as exc:
        write_new(run_dir/'failed.json',{'type':type(exc).__name__,'message':str(exc)})
        raise
    finally:
        optuna.study.Study.optimize=original
    print('Audit complete',run_dir,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--dataset')
    run(parser.parse_args())
