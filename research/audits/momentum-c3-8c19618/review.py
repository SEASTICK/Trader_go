#!/usr/bin/env python3
"""Revision-locked C3 synthetic decision reference and C3 regression checks.
No archives, external services or research runs.
"""
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys
import types
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
REV = '8c19618d431ad59c22fbbcf43171ab5f38b7b13f'
TARGET = Path(__file__).with_name('verification.json')
sys.path.insert(0, str(ROOT / 'engine'))
import traderlab

def source(path):
    return subprocess.check_output(['git','-C',str(ROOT),'show',REV+':'+path],text=True)

def load(name, text):
    mod=types.ModuleType('traderlab.'+name);mod.__package__='traderlab'
    sys.modules[mod.__name__]=mod
    exec(compile(text,mod.__name__,'exec'),mod.__dict__)
    return mod

def run():
    ls=source('engine/traderlab/momentum_ledger.py')
    rs=source('engine/traderlab/momentum_risk.py')
    L=load('_review_c3_ledger',ls)
    ss=source('engine/traderlab/momentum_signal.py')
    load('_review_c3_signal',ss)
    rs_bound=rs.replace('from .momentum_signal import VERSION as SIGNAL_VERSION','from ._review_c3_signal import VERSION as SIGNAL_VERSION')
    R=load('_review_c3_risk',rs_bound.replace('from . import momentum_ledger as ledger','from . import _review_c3_ledger as ledger').replace('from .momentum_ledger import ','from ._review_c3_ledger import '))
    T0=pd.Timestamp('2022-01-01',tz='UTC');rng=random.Random(1703)
    def sig(T, available=True, version='mom-signal/1.0.0', s=1.,cap=.5):
        return R.SignalInput(T-pd.Timedelta(days=1),T,available,s,cap,s*cap,version)
    old_rs=subprocess.check_output(['git','-C',str(ROOT),'show','d77e353:engine/traderlab/momentum_risk.py'],text=True)
    old=load('_review_c3_old_risk',old_rs.replace('from . import momentum_ledger as ledger','from . import _review_c3_ledger as ledger').replace('from .momentum_ledger import ','from ._review_c3_ledger import '))
    for i in range(400):
        midnight=i%2==0
        T=T0+pd.Timedelta(days=i+1,hours=0 if midnight else 8)
        peak=rng.uniform(100000,140000);day_start=rng.uniform(80000,130000)
        equity=rng.uniform(70000,150000);weight=0. if i%9==0 else rng.uniform(0,1.2)
        q=weight*equity/100.;C=equity-q*100.
        account=L.Account(C=C,q=q,deposit=100000,avg_price=100.)
        E=C+q*100.;pk=max(peak,E);dd=E/pk-1;dr=E/day_start-1
        was_permanent=i%17==0;permanent=was_permanent or dd<=-.15
        old_day=(T-R.BAR).floor('D')
        locked=old_day if i%11==0 else None
        day_stop=dr<=-.02
        terminal=not midnight and i%23==0
        state=R.RiskState(100000,peak,day_start,T,started=True,lock_day=locked,
            permanent=was_permanent,permanent_time=T-R.BAR if was_permanent else None)
        s=rng.choice([0.,1/3,2/3,1.]);cap=rng.uniform(.01,1.);target=s*cap
        w=q*100./E
        decision=None;daily_kind=None
        if midnight:
            if permanent: decision='permanent_stop' if q else 'hold_units'
            elif s==0 and q>0: decision=daily_kind='flat_signal'
            elif w>cap: decision=daily_kind='cap_breach'
            elif abs(target-w)>=.02: decision=daily_kind='normal'
            else: decision='hold_units'
        if terminal: expected='terminal'
        elif permanent and q: expected='permanent_stop'
        elif (day_stop or locked==old_day) and q: expected='day_stop'
        else: expected=daily_kind
        expected_w=0. if expected in ('terminal','permanent_stop','day_stop','flat_signal') else target
        new,rec=R.step(state,T,R.CloseInput(T-R.BAR,account,100.),
                       sig(T,s=s,cap=cap) if midnight else None,terminal=terminal)
        assert (None if rec.intent is None else rec.intent.kind)==expected
        if expected is not None: assert rec.intent.w==expected_w
        assert rec.daily_decision==decision and rec.E_close==E and new.peak==pk
        assert new.permanent==permanent and new.day_start==(E if midnight else day_start)
        assert new.terminated==terminal and state.next_boundary==T
        old_state=old.RiskState(**dataclasses.asdict(state))
        old_sig=old.SignalInput(**dataclasses.asdict(sig(T,s=s,cap=cap))) if midnight else None
        old_new,old_rec=old.step(old_state,T,old.CloseInput(T-R.BAR,account,100.),old_sig,terminal=terminal)
        assert dataclasses.asdict(new)==dataclasses.asdict(old_new)
        assert dataclasses.asdict(rec)==dataclasses.asdict(old_rec)
    def reject(call):
        try: call()
        except R.RiskError: return
        raise AssertionError('Expected controlled RiskError')
    T=pd.Timestamp('2024-12-31 20:00',tz='UTC');zero=L.Account(C=0,q=0,deposit=100000)
    for already in (False,True):
        state=R.RiskState(100000,100000,0 if already else 100000,T,started=True,liquidated=already)
        new,rec=R.step(state,T,R.CloseInput(T-R.BAR,zero,100.,liquidated=True),terminal=True)
        assert rec.intent is None and rec.candidates==() and new.liquidated and new.terminated
        reject(lambda: R.step(new,T+R.BAR,R.CloseInput(T,zero,100.,liquidated=True)))
    for with_signal in (False,True):
        t=T-pd.Timedelta(days=1)
        st=R.RiskState(100000,100000,0,t,started=True,liquidated=True)
        while t<=T:
            st,rec=R.step(st,t,R.CloseInput(t-R.BAR,zero,100.,liquidated=True),
                sig(t) if with_signal and t==t.floor('D') else None,terminal=t==T)
            assert rec.intent is None and rec.candidates==() and st.liquidated
            t+=R.BAR
        assert st.terminated
    st=R.RiskState(100000,100000,100000,T,started=True)
    live=L.Account(C=50000,q=500,deposit=100000,avg_price=100)
    _,rec=R.step(st,T,R.CloseInput(T-R.BAR,live,100.),terminal=True)
    closed,fill=R.fill_intent(live,rec.intent,100.,100.)
    assert closed.q==0 and fill.cost==80
    valid=sig(T0);state=R.RiskState.start(100000,T0)
    checks=0
    for field,values in [('available',['False','True',0,1,None,float('nan'),1.]),
                         ('version',['mom-signal/999',None,1,b'mom-signal/1.0.0'])]:
        for value in values:
            kw=dataclasses.asdict(valid);kw[field]=value
            reject(lambda: R.SignalInput(**kw));checks+=1
            reject(lambda: dataclasses.replace(valid,**{field:value}));checks+=1
            row=pd.Series({k:v for k,v in kw.items() if k!='day'},name=kw['day'])
            reject(lambda: R.SignalInput.from_row(row));checks+=1
    for field,value in [('day',T0-pd.Timedelta(hours=20)),
                        ('day',(T0-pd.Timedelta(days=1)).tz_convert('Etc/GMT-4')),
                        ('day','2021-12-31'),('decision_time',T0.tz_localize(None)),
                        ('decision_time',T0.tz_convert('Etc/GMT-4')),('decision_time',T0+R.BAR)]:
        reject(lambda: dataclasses.replace(valid,**{field:value}));checks+=1
    import numpy as np
    for b in (True,np.bool_(True)):
        _,rec=R.step(state,T0,signal=dataclasses.replace(valid,available=b))
        assert rec.intent.kind=='normal'
    for b in (False,np.bool_(False)):
        reject(lambda: R.step(state,T0,signal=dataclasses.replace(valid,available=b)))
    assert state==R.RiskState.start(100000,T0)
    return dict(reviewed_revision=REV,synthetic_only=True,reference_decision_cases=400,
        valid_before_after_identical_cases=400,liquidated_terminal_cases=4,
        live_terminal_cost=fill.cost,invalid_signal_contract_checks=checks,
        python_numpy_bool_compatibility=True,
        source_sha256=dict(ledger=hashlib.sha256(ls.encode()).hexdigest(),risk=hashlib.sha256(rs.encode()).hexdigest(),signal=hashlib.sha256(ss.encode()).hexdigest()))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=run()
    if args.check:
        assert json.loads(TARGET.read_text())==result
        print('PASS: C3 fixes, 400 unchanged decision cases and terminal/signal regressions at 8c19618')
    else:
        TARGET.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        print(TARGET)
