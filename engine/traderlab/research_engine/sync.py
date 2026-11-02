"""Forward-only public market sync, isolated from frozen research and its holdout.

The installed scope starts on the deployment UTC date. It never backfills the
2025 holdout or changes closed research candles. No queue claims or strategies.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen

from .supabase import SupabaseStore

STEP = {'1h':3600000,'4h':14400000,'1d':86400000}
SERIES = [(m,f) for m in ('spot','um') for f in STEP]

def iso(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()

def millis(s):
    value=datetime.fromisoformat(s.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('UTC scope required')
    return int(value.timestamp()*1000)

def fetch(url):
    with urlopen(url,timeout=30) as r:
        value=json.load(r)
    if not isinstance(value,list): raise ValueError('Unexpected public market response')
    return value

def candles(raw, market, frame, now, start):
    step=STEP[frame]; out=[]; previous=None
    for k in raw:
        t=int(k[0]); close=int(k[6]); values=[float(x) for x in k[1:6]]
        o,h,l,c,v=values
        if (t<start or t%step or t>now//step*step or close!=t+step-1
                or previous is not None and t!=previous+step
                or not all(math.isfinite(x) for x in values)
                or min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or l>h or v<0):
            raise ValueError('Invalid/gapped/duplicate market candles; no page written')
        previous=t
        out.append(dict(provider='binance',market=market,symbol='BTCUSDT',interval=frame,
                        open_time=iso(t),open=o,high=h,low=l,close=c,volume=v,closed=close<now))
    return out

def sync_series(store, market, frame, scope, now, opener=fetch, pause=0.2):
    step=STEP[frame]
    latest=store._get('candles',dict(select='open_time',provider='eq.binance',market='eq.'+market,
        symbol='eq.BTCUSDT',interval='eq.'+frame,closed='eq.true',open_time='gte.'+iso(scope),order='open_time.desc',limit=1))
    cursor=max(scope, millis(latest[0]['open_time'])+step if latest else scope)
    origin='https://data-api.binance.vision/api/v3/klines' if market=='spot' else 'https://fapi.binance.com/fapi/v1/klines'
    count=0; ongoing=0; digest=hashlib.sha256()
    for _ in range(50):
        if cursor>now: break
        url=origin+'?'+urlencode(dict(symbol='BTCUSDT',interval=frame,startTime=cursor,endTime=now,limit=100))
        raw=opener(url)
        if not raw: raise ValueError('Missing forward market data')
        rows=candles(raw,market,frame,now,cursor)
        if millis(rows[0]['open_time'])!=cursor: raise ValueError('Gap at forward cursor')
        # A closed row must never be overwritten, including after an interrupted run.
        old=store.closed_candles(provider='binance',market=market,symbol='BTCUSDT',interval=frame,
                                 start=iso(cursor),end=iso(millis(rows[-1]['open_time'])+step))
        existing={millis(r['open_time']):r for r in old}
        write=[]
        for row in rows:
            prior=existing.get(millis(row['open_time']))
            if prior:
                if any(prior[k]!=row[k] for k in ('open','high','low','close','volume')):
                    raise ValueError('Closed candle differs; immutable history retained')
            else: write.append(row)
        if write: store._write('candles',write,'resolution=merge-duplicates,return=minimal')
        digest.update(json.dumps(rows,sort_keys=True,allow_nan=False).encode())
        count+=len(write); ongoing+=sum(not r['closed'] for r in write)
        cursor=millis(rows[-1]['open_time'])+step
        if len(raw)<100 or cursor>now: break
        time.sleep(pause)
    else: raise ValueError('Forward sync page limit reached; resume on next run')
    return dict(written=count,ongoing=ongoing,next_open=iso(cursor),page_sha256=digest.hexdigest())

def sync_funding(store,scope,now,opener=fetch):
    latest=store._get('funding_rates',dict(select='funding_time',symbol='eq.BTCUSDT',
        funding_time='gte.'+iso(scope),order='funding_time.desc',limit=1))
    cursor=max(scope,millis(latest[0]['funding_time'])+1 if latest else scope)
    raw=opener('https://fapi.binance.com/fapi/v1/fundingRate?'+urlencode(dict(symbol='BTCUSDT',startTime=cursor,endTime=now,limit=1000)))
    rows=[]; previous=None
    expected=(cursor+28799999)//28800000
    for r in raw:
        t=int(r['fundingTime']); rate=float(r['fundingRate']); bucket=t//28800000
        if (t<cursor or t>now or t%28800000>60000 or not math.isfinite(rate)
                or bucket!=(expected if previous is None else previous+1)):
            raise ValueError('Invalid or incomplete forward funding')
        previous=bucket; rows.append(dict(symbol='BTCUSDT',funding_time=iso(t),rate=rate))
    next_bucket=expected if previous is None else previous+1
    if next_bucket*28800000<=now-60000:
        raise ValueError('Forward funding missing after settlement grace period')
    if rows: store.insert_market_rows('funding_rates',rows)
    return dict(written=len(rows),sha256=hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest())

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file',type=Path,required=True);p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--scope-start',required=True,help='Forward collection start, UTC midnight, deployment date')
    a=p.parse_args(); now=int(datetime.now(timezone.utc).timestamp()*1000); scope=millis(a.scope_start)
    if scope%86400000 or scope<millis('2026-11-02T00:00:00+00:00') or scope>now:
        raise ValueError('Forward scope must be deployment UTC day or later; research/holdout backfill forbidden')
    a.data_dir.mkdir(parents=True,exist_ok=True)
    with (a.data_dir/'forward-sync.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        store=SupabaseStore.from_env_file(a.env_file)
        result={'scope_start':iso(scope),'captured_at':iso(now),'kind':'forward_market_collection','series':{}}
        for market,frame in SERIES:
            result['series'][market+' '+frame]=sync_series(store,market,frame,scope,now)
        result['funding']=sync_funding(store,scope,now)
        folder=a.data_dir/'sync-manifests';folder.mkdir(exist_ok=True)
        target=folder/(str(now)+'.json');target.write_text(json.dumps(result,indent=2))
        print(json.dumps(result))

if __name__=='__main__': main()
