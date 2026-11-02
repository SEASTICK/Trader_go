from copy import deepcopy
from urllib.parse import urlparse, parse_qs
import pytest
from traderlab.research_engine import sync

S=sync.millis('2026-11-02T00:00:00+00:00')
class Store:
    def __init__(self):
        self.rows=[]; self.rates=[]; self.writes=[]
    def _get(self,table,q):
        field='open_time' if table=='candles' else 'funding_time'
        rows=self.rows if table=='candles' else self.rates
        rows=[r for r in rows if sync.millis(r[field])>=S]
        if table=='candles': rows=[r for r in rows if r['market']==q['market'][3:] and r['interval']==q['interval'][3:] and r['closed']]
        return sorted(rows,key=lambda r:r[field],reverse=True)[:1]
    def closed_candles(self,**q):
        return [r for r in self.rows if r['closed'] and r['market']==q['market'] and r['interval']==q['interval'] and sync.millis(q['start'])<=sync.millis(r['open_time'])<sync.millis(q['end'])]
    def _write(self,table,rows,prefer):
        self.writes.append(deepcopy(rows))
        for r in rows:
            self.rows[:]=[old for old in self.rows if not all(old[k]==r[k] for k in ('market','interval','open_time'))]
            self.rows.append(dict(r))
    def insert_market_rows(self,table,rows):
        for r in rows:
            if not any(old['funding_time']==r['funding_time'] for old in self.rates):self.rates.append(r)

def kline(t,step=14400000): return [t,'100','102','98','101','10',t+step-1]

def test_incremental_current_bar_closes_without_touching_frozen_data():
    store=Store(); old=dict(provider='binance',market='um',symbol='BTCUSDT',interval='4h',open_time='2024-01-01T00:00:00+00:00',closed=True,open=1,high=1,low=1,close=1,volume=1)
    store.rows.append(old.copy()); step=sync.STEP['4h']; clock=[S+step*3+100]; urls=[]
    def fetch(url):
        urls.append(url); q=parse_qs(urlparse(url).query); start=int(q['startTime'][0]);end=int(q['endTime'][0])
        assert start>=S
        return [kline(t) for t in range(start,end+1,step)][:100]
    sync.sync_series(store,'um','4h',S,clock[0],fetch,pause=0)
    assert len(store.rows)==5 and sum(not r['closed'] for r in store.rows)==1
    clock[0]+=step
    sync.sync_series(store,'um','4h',S,clock[0],fetch,pause=0)
    assert len(store.rows)==6 and store.rows[0]==old
    before=deepcopy(store.rows)
    sync.sync_series(store,'um','4h',S,clock[0],fetch,pause=0)
    assert store.rows==before
    assert int(parse_qs(urlparse(urls[-1]).query)['startTime'][0])==S+4*step

@pytest.mark.parametrize('bad',[lambda r:r+r,lambda r:[kline(S+14400000)],lambda r:[kline(S+1)],lambda r:[kline(S,1)],lambda r:[[S,'nan','102','98','101','10',S+14400000-1]],lambda r:[[S,'0','102','0','101','10',S+14400000-1]]])
def test_bad_page_never_written(bad):
    store=Store()
    with pytest.raises(ValueError): sync.sync_series(store,'um','4h',S,S+20000000,lambda u:bad([kline(S)]),pause=0)
    assert store.writes==[]

def test_original_funding_timestamps_idempotent_and_complete():
    store=Store(); now=S+10*3600000
    raw=[dict(fundingTime=S+2,fundingRate='0.0001'),dict(fundingTime=S+28800000+3,fundingRate='0.0002')]
    def fetch(url):
        q=parse_qs(urlparse(url).query);start=int(q['startTime'][0]);assert start>=S
        return [r for r in raw if r['fundingTime']>=start]
    assert sync.sync_funding(store,S,now,fetch)['written']==2
    assert sync.sync_funding(store,S,now,fetch)['written']==0
    assert store.rates[0]['funding_time']==sync.iso(S+2)
    with pytest.raises(ValueError,match='funding'):sync.sync_funding(Store(),S,now,lambda u:raw[1:])
    with pytest.raises(ValueError,match='funding'):sync.sync_funding(Store(),S,now,lambda u:[])
