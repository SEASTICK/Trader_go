#!/usr/bin/env python3
"""Published-source recovery defined by protocol amendment 7839e8a; never impute."""
import argparse,hashlib,io,json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
import pandas as pd
from traderlab.data import binance
from traderlab import quality

DAYS=['2021-07-01','2021-07-24','2021-07-25','2021-07-26','2021-07-27','2022-07-31','2022-10-02','2023-02-24']
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();folder=a.folder
 monthly=pd.concat([binance.parse_klines_csv(binance._unzip_single((folder/f'BTCUSDT-4h-{m}.zip').read_bytes())) for m in binance.months('2020-01','2024-12')])
 expected=pd.date_range('2020-01-01','2025-01-01',freq='4h',inclusive='left',tz='UTC');missing=expected.difference(monthly.index)
 if len(missing)!=48 or sorted({str(t.date()) for t in missing})!=DAYS:raise ValueError('Missing set differs from protocol amendment')
 entries=[];frames=[]
 for day in DAYS:
  name=f'BTCUSDT-4h-{day}.zip';path=folder/name
  url='https://data.binance.vision/data/futures/um/daily/markPriceKlines/BTCUSDT/4h/'+name
  try:
   if not path.exists():
    raw=urlopen(url,timeout=30).read();checksum=urlopen(url+'.CHECKSUM',timeout=30).read();binance.verify_checksum(raw,checksum);path.write_bytes(raw);path.with_suffix('.zip.CHECKSUM').write_bytes(checksum)
   raw=path.read_bytes();binance.verify_checksum(raw,path.with_suffix('.zip.CHECKSUM').read_bytes());frame=binance.parse_klines_csv(binance._unzip_single(raw))
   entry=dict(name=name,source=url,sha256=digest(raw),format='zip')
  except HTTPError as exc:
   if exc.code!=404:raise
   start=pd.Timestamp(day,tz='UTC')-pd.Timedelta(hours=4);end=pd.Timestamp(day,tz='UTC')+pd.Timedelta(days=1,hours=4)
   url='https://fapi.binance.com/fapi/v1/markPriceKlines?'+urlencode(dict(symbol='BTCUSDT',interval='4h',startTime=int(start.timestamp()*1000),endTime=int(end.timestamp()*1000)-1,limit=1000))
   path=folder/(day+'-api.json')
   if not path.exists():path.write_bytes(urlopen(url,timeout=30).read())
   raw=path.read_bytes();rows=json.loads(raw)
   if not isinstance(rows,list):raise ValueError('Unexpected mark API response')
   frame=binance.parse_klines_csv(('\n'.join(','.join(str(x) for x in row) for row in rows)).encode())
   if not frame.index.equals(pd.date_range(start,end,freq='4h',inclusive='left')):raise ValueError('API boundary coverage mismatch')
   overlaps=frame.index.intersection(monthly.index)
   if not len(overlaps):raise ValueError('No published overlap for API verification')
   if ((frame.loc[overlaps,['open','high','low','close']]-monthly.loc[overlaps,['open','high','low','close']]).abs()>1e-8).any().any():raise ValueError('Published/API OHLC overlap differs')
   entry=dict(name=path.name,source=url,sha256=digest(raw),format='api-json',monthly_overlap_verified=len(overlaps))
  if not quality.check(frame,'4h').ok:raise ValueError('Invalid published recovery candles')
  selected=frame[frame.index.isin(missing)]
  frames.append(selected);entries.append({**entry,'recovered_times':[str(t) for t in selected.index]})
 recovered=pd.concat(frames)
 # Overlap across API windows must be identical before deduplication.
 for t,group in recovered.groupby(level=0):
  if not group.eq(group.iloc[0]).all().all():raise ValueError('Recovery sources conflict')
 recovered=recovered[~recovered.index.duplicated()].sort_index()
 if not recovered.index.equals(missing):raise ValueError('Recovery incomplete')
 combined=pd.concat([monthly,recovered]).sort_index()
 if not combined.index.equals(expected) or not quality.check(combined,'4h').ok:raise ValueError('Recovered dataset invalid')
 report=dict(protocol_amendment='7839e8a',missing_before=48,recovered_bars=len(recovered),files=entries,holdout_loaded=False,policy='published original mark candles only; no imputation')
 (folder/'recovery-manifest.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
