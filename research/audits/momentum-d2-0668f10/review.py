#!/usr/bin/env python3
"""Revision-locked independent synthetic D2 audit. PASS includes reproduced defects."""
import argparse
import dataclasses
from decimal import Decimal as D, localcontext
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
REV='0668f1035f2d6241c196b669f8d264e2650be8d0'
BASE='99e96858b460f00818a8f5bfc36ac15f79660242'
OLD='7345f06b928f25902ab1515008e1c26f99fa7c0c'
OUT=Path(__file__).with_name('verification.json')
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args],text=True)
def near(a,b): assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12),(a,b)
def load(rev,tag):
    pkg=types.ModuleType(tag); pkg.__path__=[]; sys.modules[tag]=pkg
    names=['stats','ledger','signal','funding','risk','margin','event','bound','control']+(['benchmark'] if rev==REV else [])
    src={}
    for n in names:
        name=n if n=='stats' else 'momentum_'+n; p='engine/traderlab/'+name+'.py'; src[p]=git('show',rev+':'+p)
        m=types.ModuleType(tag+'.'+name); m.__package__=tag; sys.modules[m.__name__]=m; setattr(pkg,name,m)
        exec(compile(src[p],rev+':'+p,'exec'),m.__dict__)
    return pkg,src
def canonical(v):
    if dataclasses.is_dataclass(v): return {f.name:canonical(getattr(v,f.name)) for f in dataclasses.fields(v) if not (f.name=='policy' and getattr(v,f.name)=='momentum')}
    if isinstance(v,dict): return {str(k):canonical(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)): return [canonical(x) for x in v]
    if isinstance(v,(set,frozenset)): return sorted(canonical(x) for x in v)
    if isinstance(v,(pd.Timestamp,pd.Timedelta)): return str(v)
    if isinstance(v,float) and math.isnan(v): return 'NaN'
    return v
def run():
    p,src=load(REV,'d2_locked'); old,oldsrc=load(OLD,'d2_baseline')
    V,K,F,B=[getattr(p,'momentum_'+n) for n in ('event','control','funding','benchmark')]
    changed=git('diff','--name-only',BASE,REV).splitlines()
    assert changed==['docs/momentum-D2-mutationer.json','docs/momentum-benchmark-D2.md','docs/momentum-checklista.md','docs/momentum-status.json','engine/tests/test_momentum_benchmark.py','engine/traderlab/momentum_benchmark.py','engine/traderlab/momentum_event.py','scripts/momentum-d2-mutations.py']
    protected=['research','engine/traderlab/stats.py','scripts/momentum-d1-mutations.py']+['engine/traderlab/momentum_'+n+'.py' for n in ('signal','ledger','funding','risk','margin','bound','control')]
    assert not git('diff','--name-only',BASE,REV,'--',*protected).strip()
    assert git('merge-base',BASE,REV).strip()==BASE
    for f in ('research/h0017-protokoll.md','research/registry.md','docs/claude-uppdrag-momentum-D2.md','docs/momentum-a1-orakel.json','scripts/momentum-d2-mutations.py','engine/tests/test_momentum_benchmark.py'):
        src[f]=git('show',REV+':'+f)
    # Independent calendars and data: no test or production data helpers.
    times=pd.date_range('2022-01-01','2024-12-31 20:00',freq='4h',tz='UTC')
    warm=pd.date_range(pd.Timestamp('2021-11-01',tz='UTC'),times[-1],freq='4h')
    contract=pd.DataFrame({'open':[100.+(i%19)/10 for i in range(len(warm))],'close':100.},index=warm)
    mark=pd.DataFrame({n:[99.+(i%13)/10 for i in range(len(times))] for n in ('open','high','low','close')},index=times)
    events=[]
    for i,offset,rate in [(0,0,.0001),(0,1,-.0002),(6,0,.0003),(100,30,-.0004),(4000,1,.0002),(6575,0,.0001),(6575,30,-.0005)]:
        t=times[i]+pd.Timedelta(milliseconds=offset)
        events.append(F.FundingEvent(str(len(events)),t,rate,float(mark.iloc[i,0]),F.MARK_OPEN,t.floor('4h')))
    market=K.Market(contract,mark,events)
    full=[]; norms={}; c=D('.0016')
    for order in 'AB':
      for mmr in (.05,.005):
       for legacy in ('L1','L2'):
        r=B.run_buy_and_hold(market,order,mmr,legacy); log=r.log
        q=D(100000)/(D(str(contract.at[times[0],'open']))*(1+c)); cash=D(100000)-q*D(str(contract.at[times[0],'open']))*(1+c)
        expected=[]; paid=D(0); costs=q*D(str(contract.at[times[0],'open']))*c
        for i,T in enumerate(times):
            for e in events:
                if e.time.floor('4h')!=T: continue
                units=D(0) if (i==0 and e.time==T and order=='A') or (i==6575 and (order=='B' or e.time>T)) else q
                payment=units*D(str(e.M_ref))*D(str(e.rate)); cash-=payment; paid+=payment
            if i==6575:
                costs+=q*D(str(contract.at[T,'open']))*c
                cash+=q*D(str(contract.at[T,'open']))*(1-c)
            expected.append(cash+(q*D(str(mark.at[T,'close'])) if i<6575 else 0))
        assert len(log.close_points)==6577 and len(log.day_ends)==1096
        for j,(source,known,e) in enumerate(log.close_points):
            if j==0: assert source is None and known==times[0]; near(e,100000)
            else:
                assert source==times[j-1] and known==(times[j] if j<6576 else times[-1]); near(e,expected[j-1])
        for j,(day,e,liq) in enumerate(log.day_ends):
            assert day==times[0]+pd.Timedelta(days=j) and not liq; near(e,expected[min(j*6+5,6575)])
        for t in log.trace:
            if t.phase=='after_trade': near(t.q,0 if t.time==times[-1] else q)
        near(log.state.account.costs,costs); near(log.state.account.funding_net,paid)
        norm=[(t.phase,str(t.time),t.C,t.q,t.E,t.cost,t.funding) for t in log.trace]
        if legacy=='L2': assert norms[(order,mmr)]==norm
        else: norms[(order,mmr)]=norm
        full.append({'order':order,'mmr':mmr,'legacy':legacy,'bars':6576,'points':6577,'days':1096,'q_decimal':str(q),'terminal_decimal':str(expected[-1])})
    # O11/C5-01: independent reference for booked funding, adverse basis, unresolved and absorbing zero.
    liquidation=[]
    for order in 'AB':
     for mmr in (.05,.005):
      for kind in ('gap','intrabar'):
        st=V.EngineState.start(V.Scenario('bh',order,mmr,policy=V.BUY_AND_HOLD)); log=V.RunLog.begin(st)
        q=D(100000)/(D(100)*(1+c)); cash=D(100000)-q*100*(1+c)
        for i,T in enumerate(times):
            M=.4 if kind=='gap' and i==2 else 100.
            low=.4 if kind=='intrabar' and i==2 else M
            es=[]
            if i==1: es=[F.FundingEvent('paid',T+pd.Timedelta(seconds=30),.005,100.,F.MARK_OPEN,T)]; cash-=q*100*D('.005')
            if i==2: es=[F.FundingEvent('credit',T+pd.Timedelta(seconds=1),-.01,M,F.MARK_OPEN,T),F.FundingEvent('debit',T+pd.Timedelta(seconds=30),.001,M,F.MARK_OPEN,T)]
            if i==3: es=[F.FundingEvent('later',T,-.1,M,F.MARK_OPEN,T)]
            rr=V.process_bar(st,V.Bar(T,M,M,M,low,M),es); log=log.add(rr); st=rr.state
            if i==2:
                basis=cash-(q*D(str(M))*D('.001') if kind=='intrabar' else 0)
                assert basis+q*D('.4')<=D(str(mmr))*q*D('.4')
                assert st.margin_state.liquidated and st.account.C==st.account.q==0
                if kind=='intrabar':
                    near(rr.margin_basis[0],basis); assert len(rr.unresolved)==2
                    near(rr.unresolved[0][2],-q*100*D('.01')); near(rr.unresolved[1][2],q*100*D('.001'))
                else: assert rr.absorbed==2
            if i>=2:
                near(st.account.funding_net,q*100*D('.005')); near(st.account.costs,q*100*c)
                near(st.account.liquidation_adjustment,-(D(100000)-q*100*c-q*100*D('.005')))
                assert st.account.q==st.account.C==0
        assert log.day_ends[-1][1:]==(0.,True)
        liquidation.append({'order':order,'mmr':mmr,'kind':kind,'bars':6576,'zero_terminal':True})
    # Compare complete momentum result objects (including ordered traces, StepRecord and BoundLog input)
    # from independently loaded old/new sources; no production values form the Decimal reference above.
    regress=[]
    for account in ('main','mom7','mom14','mom28'):
     for order in 'AB':
      for mmr in (.05,.005):
        states=[x.momentum_event.EngineState.start(x.momentum_event.Scenario(account,order,mmr)) for x in (p,old)]
        bounds=[x.momentum_bound.BoundLog.begin(st) for x,st in zip((p,old),states)]
        traces=0
        for i in range(120):
            T=times[i]; price=[100.,110.,97.7,100.,84.,120.][min(i//6,5)]
            outputs=[]
            for z,x in enumerate((p,old)):
                v=x.momentum_event; risk=x.momentum_risk; fund=x.momentum_funding
                signal=None
                if T==T.floor('D'):
                    s=1/3 if account=='main' else float((i//6)%3!=1); cap=[.9,.195,.6,1.][(i//6)%4]
                    signal=risk.SignalInput(T-pd.Timedelta(days=1),T,True,s,cap,s*cap,risk.SIGNAL_VERSION)
                e=fund.FundingEvent('e'+str(i),T+pd.Timedelta(milliseconds=i%2),(-1 if i%3 else 1)*.0001,price,fund.MARK_OPEN,T)
                rr=v.process_bar(states[z],v.Bar(T,price*1.001,price,price*1.01,price*.99,price),[e],signal)
                states[z]=rr.state; bounds[z]=bounds[z].add(rr); outputs.append(canonical(rr))
            assert outputs[0]==outputs[1],(account,order,mmr,i)
            traces+=len(outputs[0]['trace'])
        assert canonical(bounds[0])==canonical(bounds[1])
        regress.append({'account':account,'order':order,'mmr':mmr,'bars':120,'trace_rows':traces})
    # Independent input defects: spy is audit-only and counts economic calls before rejection.
    defects={}; original=V.process_bar
    for kind in ('OHLC','funding_reference','duplicate_funding'):
        badmark=mark.copy(); es=[]
        T=times[12]
        if kind=='OHLC': badmark.at[T,'low']=badmark.at[T,'high']+1
        else:
            e=F.FundingEvent('bad',T,.0001,float(mark.at[T,'open'])+(1 if kind=='funding_reference' else 0),F.MARK_OPEN,T)
            es=[e,e] if kind=='duplicate_funding' else [e]
        calls=[]
        def spy(*a,**kw): calls.append(str(a[1].open_time)); return original(*a,**kw)
        V.process_bar=spy
        try:
            bad=K.Market(contract,badmark,es); B.run_buy_and_hold(bad,'A',.05)
        except V.EventError as exc: defects[kind]={'economic_calls_before_rejection':len(calls),'error':str(exc)}
        else: raise AssertionError('bad data accepted')
        finally: V.process_bar=original
        assert len(calls)>=12
    # D15/§12: comparator incorrectly accepts stress cost through its public full-horizon API.
    stress=B.run_buy_and_hold(market,'A',.05,cost=.004)
    assert stress.scenario.cost==.004
    # Own neutral-source first-use CALL fault: must never be called a behavior catch.
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for path in git('ls-tree','-r','--name-only',REV,'engine','docs/momentum-a1-orakel.json').splitlines():
            f=root/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(git('show',REV+':'+path))
        script=types.ModuleType('d2_mutation_locked'); script.__file__=str(root/'scripts/momentum-d2-mutations.py')
        exec(compile(src['scripts/momentum-d2-mutations.py'],'locked mutations','exec'),script.__dict__)
        workspace=script._workspace
        def fault(tmp):
            dst=workspace(tmp)
            (dst/'tests/test_audit_fault.py').write_text('from pathlib import Path\ndef test_resource():\n    m=Path(__file__).with_name("used")\n    if not m.exists():\n        m.write_text("used")\n        raise RuntimeError("audit first use call failure")\n')
            return dst
        real_workspace=workspace
        script._workspace=fault; script.TESTS=['tests/test_audit_fault.py']; script.TARGETS['audit_neutral']='test_resource'
        row=script.run_one(sys.executable,'audit_neutral','momentum_benchmark.py','VERSION = "mom-bh/1.0.0"','VERSION = "mom-bh/1.0.0" # neutral')
        assert row['utfall']=='MILJÖFEL' and row['tvilling_utan_mutation']=='fallerar också',row
        script._workspace=real_workspace
        script.TESTS=['tests/test_momentum_benchmark.py','tests/test_momentum_event.py','tests/test_momentum_control.py']
        anchor='    return BenchmarkRun(policy=ev.BUY_AND_HOLD'
        shared_new=('    global _audit_last_L1\n'
                    '    if legacy_order == "L1": _audit_last_L1 = log\n'
                    '    elif "_audit_last_L1" in globals(): log = _audit_last_L1\n'+anchor)
        shared=script.run_one(sys.executable,'audit_actual_shared_log','momentum_benchmark.py',anchor,shared_new)
        assert shared['utfall']=='MISSAD',shared
    return {'revision':REV,'diff_base':BASE,'momentum_baseline':OLD,'changed_files':changed,'protected_unchanged':True,'baseline_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in oldsrc.items()},'sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in src.items()},'full_decimal_histories':full,'liquidation_decimal_histories':liquidation,'momentum_complete_result_regressions':regress,'D2-01_prevalidation':defects,'D2-02_stress_cost_accepted':stress.scenario.cost,'own_mutation_classification_injection':row,'D2-03_actual_shared_log_mutant':shared,'decision':'EJ GODKÄND'}
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    with localcontext() as ctx:
        ctx.prec=70; result=run()
    result=json.loads(json.dumps(result,ensure_ascii=False))
    if args.check:
        assert json.loads(OUT.read_text())==result,'Verification differs'
        print('PASS: revision-locked D2 evidence (includes open findings)')
    else: OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n'); print('Wrote',OUT)
