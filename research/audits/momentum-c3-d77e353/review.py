#!/usr/bin/env python3
"""Revision-locked C3 synthetic decision reference and two API counterexamples.
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
REV = 'd77e3535dc9588bc8454c04112223c594fbbd7ff'
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
    R=load('_review_c3_risk',rs.replace('from . import momentum_ledger as ledger','from . import _review_c3_ledger as ledger').replace('from .momentum_ledger import ','from ._review_c3_ledger import '))
    T0=pd.Timestamp('2022-01-01',tz='UTC');rng=random.Random(1703)
    def sig(T, available=True, version='mom-signal/1.0.0', s=1.,cap=.5):
        return R.SignalInput(T-pd.Timedelta(days=1),T,available,s,cap,s*cap,version)
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
    # Absorbing liquidation must also hold at terminal, but this revision emits an unfillable intent.
    terminal_results=[];T=pd.Timestamp('2024-12-31 20:00',tz='UTC')
    zero=L.Account(C=0,q=0,deposit=100000)
    for already in (False,True):
        state=R.RiskState(100000,100000,0 if already else 100000,T,started=True,liquidated=already)
        new,rec=R.step(state,T,R.CloseInput(T-R.BAR,zero,100.,liquidated=True),terminal=True)
        assert rec.intent.kind=='terminal' and rec.intent.E_decision is None
        try: R.fill_intent(zero,rec.intent,100.,100.)
        except L.LedgerError as exc: error=type(exc).__name__
        else: raise AssertionError('Expected terminal zero-account fill failure')
        terminal_results.append(dict(already_liquidated=already,intent=rec.intent.kind,
                                     E_decision=rec.intent.E_decision,fill_error=error,terminated=new.terminated))
    # Signal truth conversion and ignored version permit unvalidated normal buys.
    signal_results=[]
    for available,version in [('False','mom-signal/1.0.0'),(True,'mom-signal/999')]:
        row=pd.Series(dict(decision_time=T0,available=available,s=1.,cap=.5,w_target=.5,version=version),
                      name=T0-pd.Timedelta(days=1))
        parsed=R.SignalInput.from_row(row)
        _,rec=R.step(R.RiskState.start(100000,T0),T0,signal=parsed)
        filled,_=R.fill_intent(L.Account.open(100000),rec.intent,100.,100.)
        assert rec.intent.kind=='normal' and filled.q>0
        signal_results.append(dict(input_available=available,input_version=version,
                                   parsed_available=parsed.available,intent=rec.intent.kind,filled_q=filled.q))
    try: R.step(R.RiskState.start(100000,T0),T0,signal=sig(T0,available=False))
    except R.RiskError: pass
    else: raise AssertionError('Valid bool False must remain unavailable')
    return dict(reviewed_revision=REV,synthetic_only=True,reference_decision_cases=400,
        source_sha256=dict(ledger=hashlib.sha256(ls.encode()).hexdigest(),risk=hashlib.sha256(rs.encode()).hexdigest()),
        C3_01_liquidated_terminal=terminal_results,C3_02_signal_contract=signal_results)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=run()
    if args.check:
        assert json.loads(TARGET.read_text())==result
        print('PASS: C3 400 independent decision cases and two contract gaps reproduced at d77e353')
    else:
        TARGET.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
        print(TARGET)
