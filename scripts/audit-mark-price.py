#!/usr/bin/env python3
"""Execute docs/fas1-mark-price-protocol.md; historical data only, no optimization."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time
from urllib.request import urlopen
import pandas as pd

from traderlab import fas1, metrics, optimize, quality
from traderlab.data import binance
from traderlab.research_engine.margin import liquidation_threshold
from traderlab.research_engine.runner import clean
from traderlab.strategies.rules import SPECS

def digest(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--audit-root',type=Path,required=True);p.add_argument('--data-dir',type=Path,required=True);a=p.parse_args()
    folder=a.audit_root/'mark-price-20261102';folder.mkdir(exist_ok=True)
    entries=[];frames=[]
    for month in binance.months('2020-01','2024-12'):
        name=f'BTCUSDT-4h-{month}.zip';url='https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/4h/'+name
        path=folder/name;check=folder/(name+'.CHECKSUM')
        if not path.exists():
            raw=urlopen(url,timeout=30).read();checksum=urlopen(url+'.CHECKSUM',timeout=30).read()
            binance.verify_checksum(raw,checksum);path.write_bytes(raw);check.write_bytes(checksum);time.sleep(.05)
        raw=path.read_bytes();binance.verify_checksum(raw,check.read_bytes())
        frames.append(binance.parse_klines_csv(binance._unzip_single(raw)))
        entries.append(dict(name=name,source=url,sha256=digest(raw)))
    recovery=folder/'recovery-manifest.json'
    if recovery.exists():
        recovered=[]
        recovery_data=json.loads(recovery.read_text())
        if recovery_data.get('protocol_amendment')!='7839e8a' or recovery_data.get('recovered_bars')!=48:
            raise ValueError('Recovery does not match preregistered amendment')
        for item in recovery_data['files']:
            raw=(folder/item['name']).read_bytes()
            if digest(raw)!=item['sha256']:raise ValueError('Published recovery changed')
            if item['format']=='zip':
                binance.verify_checksum(raw,(folder/(item['name']+'.CHECKSUM')).read_bytes())
                frame=binance.parse_klines_csv(binance._unzip_single(raw))
            else:
                frame=binance.parse_klines_csv(('\n'.join(','.join(str(x) for x in r) for r in json.loads(raw))).encode())
            frame=frame[frame.index.isin(pd.to_datetime(item['recovered_times'],utc=True))]
            recovered.append(frame);entries.append(item)
        extra=pd.concat(recovered)
        extra=extra[~extra.index.duplicated()]
        frames.append(extra)
    marks=pd.concat(frames)
    expected=pd.date_range('2020-01-01','2025-01-01',freq='4h',inclusive='left',tz='UTC')
    report=quality.check(marks,'4h')
    if not marks.index.equals(expected) or not report.ok or (marks[['open','high','low','close']]<=0).any().any():raise ValueError('Invalid/incomplete mark-price series')
    start=pd.Timestamp('2020-01-01',tz='UTC');end=pd.Timestamp('2025-01-01',tz='UTC')
    bars=binance.load('um','BTCUSDT','4h',a.data_dir,start=start,end=end)
    funding=binance.load_funding('BTCUSDT',a.data_dir,start=start,end=end)
    assert bars.index.equals(marks.index)
    results=[]
    for proof in json.loads((a.repo/'app/data/registered-results.json').read_text()):
        spec=SPECS[proof['strategy']]; normal=fas1._stitch(spec,SimpleNamespace(windows=proof['windows']),bars,fas1.COSTS,funding)
        if clean(metrics.full_stats(normal,bars[bars.index>=pd.Timestamp('2022-01-01',tz='UTC')]))!=proof['stats'] or clean(metrics.curves(normal))!=proof['curves']:
            raise ValueError('Original reproduction mismatch')
        possible=[]; minratio=float('inf');checked=0;trades=0
        for w in proof['windows']:
            begin,finish=[pd.Timestamp(t,tz='UTC') for t in w['test']]
            res=optimize.evaluate(spec,w['params'],bars,begin,finish,fas1.COSTS,funding)
            for trade in res.trades:
                if trade.entry_time<begin:continue
                trades+=1
                stop=min(finish,trade.exit_time+pd.Timedelta(hours=4) if trade.exit_time else finish)
                window=marks[(marks.index>=trade.entry_time)&(marks.index<stop)]
                q=(1 if trade.side=='Long' else -1)*trade.size*trade.equity_at_entry/trade.entry_price
                collateral=trade.size*trade.equity_at_entry;cost=abs(q)*trade.entry_price*fas1.COSTS.per_side;paid=0.
                for t,row in window.iterrows():
                    settlements=funding[(funding.index>=t)&(funding.index<t+pd.Timedelta(hours=4))]
                    for rate in settlements:
                        paid+=q*(row.high if q*rate>=0 else row.low)*rate
                    worst=row.low if q>0 else row.high
                    balance=collateral-cost-paid+q*(worst-trade.entry_price)
                    ratio=balance/(abs(q)*worst);minratio=min(minratio,float(ratio));checked+=1
                    if ratio<=.01:
                        possible.append(dict(entry_time=trade.entry_time.isoformat(),bar=t.isoformat(),side=trade.side,margin_ratio=float(ratio),threshold_05=liquidation_threshold(trade.entry_price,q,collateral,cost,paid,.005),threshold_1=liquidation_threshold(trade.entry_price,q,collateral,cost,paid,.01)))
        results.append(dict(hypothesis=proof['hypothesis_id'],trades=trades,checked_trade_bars=checked,minimum_margin_to_mark_notional=minratio,possible_hits=possible,original_reproduction_exact=True,decision='REJECT'))
    out=dict(protocol='docs/fas1-mark-price-protocol.md',protocol_commit='9261e05',recovery_protocol_commit='7839e8a' if recovery.exists() else None,script_sha256=digest(Path(__file__).read_bytes()),period=['2020-01-01','2025-01-01'],holdout_loaded=False,leverage=1,maintenance_rates=[.005,.01],quality=asdict(report),mark_bars=len(marks),mark_dataset_sha256=digest(marks.to_csv(float_format='%.17g').encode()),files=entries,results=results,passed=all(not r['possible_hits'] for r in results),limitations=['Fixed maintenance-rate verification; no historical risk tiers or liquidation fee model','Entire exit bar and adverse funding-price bounds are conservative; intrabar order unknown','Legacy results are preserved, not relabelled exchange-exact'])
    (folder/'verification.json').write_text(json.dumps(clean(out),indent=2,allow_nan=False))
    print(json.dumps({k:out[k] for k in ['mark_bars','holdout_loaded','passed','results']},indent=2))
    if not out['passed']:raise SystemExit('Potential liquidation hit; acceptance blocked')

if __name__=='__main__': main()
