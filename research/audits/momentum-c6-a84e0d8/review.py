#!/usr/bin/env python3
"""Revision-locked independent C6 arithmetic and provenance review. Synthetic only.
--check reproduces independent arithmetic and corrected C6-02 time evidence.
"""
import argparse
import dataclasses as dc
from decimal import Decimal as D, localcontext
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import types
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REV = 'a84e0d87e3bfaef06bb916bf8234cbf4e8a1775f'
BASE = '790d4771a88623c6f8630c88b58515664fb5a773'
TARGET = Path(__file__).with_name('verification.json')

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)

def near(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-9), (a, b)

def run(mutation=None):
    names = ['stats'] + ['momentum_'+n for n in ('ledger','signal','funding','risk','margin','event','bound')]
    paths = ['engine/traderlab/'+n+'.py' for n in names]
    paths += ['research/h0017-protokoll.md','research/registry.md','docs/momentum-a1-orakel.json',
              'docs/claude-uppdrag-momentum-C6.md','docs/momentum-C6-01-edwins-beslut.md',
              'docs/momentum-C6-01-granskning-beslut-3.md','engine/tests/test_momentum_bound.py',
              'docs/momentum-status.json']
    src = {p:git('show',REV+':'+p) for p in paths}
    pkg = types.ModuleType('c6_locked'); pkg.__path__=[]; sys.modules[pkg.__name__]=pkg
    mods={}
    for n in names:
        m=types.ModuleType(pkg.__name__+'.'+n); m.__package__=pkg.__name__
        sys.modules[m.__name__]=m; setattr(pkg,n,m)
        code=src['engine/traderlab/'+n+'.py']
        if n=='momentum_bound' and mutation:
            old,new=mutation; assert old in code; code=code.replace(old,new)
        exec(compile(code,REV+':'+n,'exec'),m.__dict__); mods[n]=m
    L,S,F,R,M,V,B=[mods['momentum_'+n] for n in ('ledger','signal','funding','risk','margin','event','bound')]
    changed=git('diff','--name-only',BASE,REV).splitlines()
    assert changed==['docs/momentum-bound-C6.md','docs/momentum-checklista.md','docs/momentum-status.json',
                     'engine/tests/test_momentum_bound.py','engine/traderlab/momentum_bound.py']
    # Only bound implementation and its tests may change among engine sources.
    protected=['engine/traderlab/momentum_'+n+'.py' for n in ('ledger','signal','funding','risk','margin','event')]
    protected+=['engine/traderlab/stats.py','research/h0017-protokoll.md','research/registry.md','research/results']
    assert not git('diff','--name-only',BASE,REV,'--',*protected).strip()
    assert not git('diff','--name-only',BASE,REV,'--','research/audits').strip()
    def sc(order='A',mmr=.05,cost=.0016): return V.Scenario('main',order,mmr,cost)
    def sig(t,w=.5): return R.SignalInput(t-pd.Timedelta(days=1),t,True,1.,w,w,S.VERSION)
    def bar(t,o=100.,h=112.,lo=95.,c=101.): return V.Bar(t,o,o,h,lo,c)
    def event(i,t,rate,o): return F.FundingEvent(i,t,rate,o,F.MARK_OPEN,F.bar_open(t))
    t=pd.Timestamp('2023-04-10 08:00',tz='UTC')
    def fixture(s,C,q,prev=100.,peak=100000.):
        a=L.Account(C,q,100000.,100.,realized=C+q*100.-100000.)
        return V.EngineState._fixture(s,a,R.RiskState(initial=100000.,peak=peak,day_start=100000.,next_boundary=t,started=True),
                 F.FundingState(s.account_key,s.label),M.MarginState(s.account_key,s.label,s.mmr),t,prev)
    counts={'point_sequences':0,'points':0,'noninterference_pairs':0}
    def check_times(points):
        for p in points:
            get = p.__getitem__ if isinstance(p,dict) else lambda k: getattr(p,k)
            phase, opened, actual = get('phase'),get('bar_open'),get('time')
            expected = (opened + V.BAR if phase == 'close' else
                        V.UNKNOWN_TIME if phase in ('high','low') or
                        (phase == 'liquidation' and any((x['phase'] if isinstance(x,dict) else x.phase)=='low' for x in points))
                        else opened)
            assert actual == expected, (phase, actual, expected)
    def verify(points,phases,values,peak=D(100000),minimum=D(0)):
        check_times(points)
        assert [p['phase'] if isinstance(p,dict) else p.phase for p in points]==phases
        assert len(points)==len(values)
        out=[]
        for p,e in zip(points,values):
            actual=p['E'] if isinstance(p,dict) else p.E
            near(actual,e); peak=max(peak,e); dd=e/peak-1; minimum=min(minimum,dd)
            if not isinstance(p,dict): near(p.peak,peak); near(p.drawdown,dd)
            out.append({'E':str(e),'peak':str(peak),'dd':str(dd),'minimum':str(minimum)})
        counts['point_sequences']+=1; counts['points']+=len(values)
        return peak,minimum,out
    normal=['open','trade','post','high','low','close']
    o7=V.process_bar(fixture(sc(),50000.,500.,peak=105000.),bar(t))
    _,_,o7ref=verify(B.bar_points(o7),normal,list(map(D,['100000','100000','100000','106000','97500','100500'])),D(105000))
    near(D(o7ref[4]['dd']),D(97500)/D(106000)-1)
    near(D(100500)/D(105000)-1,json.loads(src['docs/momentum-a1-orakel.json'])['O7_intrastapel_main']['close_dd'])
    matrix=[]
    for order in 'AB':
      for mmr in (.05,.005):
       for reverse in (False,True):
        for low in (63.5,58.):
         for simultaneous in (False,True):
            rates=['.02','-.02','.005','-.01','0']
            if reverse: rates.reverse()
            events=[event(str(k),t+pd.Timedelta(minutes=20*(k+1)),float(rate),64.) for k,rate in enumerate(rates)]
            if simultaneous: events.insert(0,event('sim',t,.0001,64.))
            rr=V.process_bar(fixture(sc(order,mmr),-600000.,10000.,70.,101000.),bar(t,64.,66.,low,65.),events)
            q=D(10000); cash=D(-600000)-(D('64') if simultaneous else 0)
            pays=[q*64*D(rate) for rate in rates]
            high=cash-sum(min(p,0) for p in pays)+q*66
            trough=cash-sum(max(p,0) for p in pays)+q*D(str(low))
            hit=trough<=D(str(mmr))*q*D(str(low))
            assert rr.state.margin_state.liquidated==hit
            vals=[D(40000),cash+q*64 if order=='A' else D(40000),cash+q*64,high,trough,
                  D(0) if hit else cash-sum(pays)+q*65]
            pk,dd,_=verify(B.bar_points(rr),normal[:-1]+['liquidation' if hit else 'close'],vals,D(101000))
            near(rr.state.account.funding_net,(D(64) if simultaneous else 0)+(0 if hit else sum(pays)))
            assert rr.interior_booked==(0 if hit else 5)
            matrix.append({'order':order,'mmr':mmr,'reverse':reverse,'sim':simultaneous,'low':low,'hit':hit,'peak':str(pk),'dd':str(dd)})
    gaps=[]
    for order in 'AB':
        rr=V.process_bar(fixture(sc(order),-600000.,10000.,70.),bar(t,55.,60.,50.,58.),[event('sim',t,.001,55.)])
        vals=list(map(D,['-50000','-50550','0'] if order=='A' else ['-50000','0']))
        phases=['open','gap_check','liquidation'] if order=='A' else ['open','liquidation']
        _,_,ref=verify(B.bar_points(rr),phases,vals); gaps.append(ref)
        st=rr.state
        for k in range(1,6):
            rr=V.process_bar(st,bar(t+k*V.BAR,80.,200.,79.,80.)); st=rr.state
            verify(B.bar_points(rr),['absorbed'],[D(0)])
    # Independent self-financing entry then hold for 15 consecutive bars across two midnights.
    sequential=[]; timestamp_examples=[]
    for order in 'AB':
      for cost in ('.0016','.004'):
        st=V.EngineState.start(sc(order,cost=float(cost))); log=B.BoundLog.begin(st)
        assert log.points[0].phase=='start' and log.points[0].time==V.START and log.points[0].bar_open is None
        q=D('.5')*100000/(100+D('.5')*D(cost)*100)
        cash=D(100000)-q*100-D(cost)*q*100
        peak=D(100000); minimum=D(0)
        first=None
        for k in range(15):
            tk=V.START+k*V.BAR
            hi,lo=(D(150),D(90)) if k==0 else (D(103),D(70))
            rr=V.process_bar(st,bar(tk,100.,float(hi),float(lo),100.),signal=sig(tk) if tk.hour==0 else None)
            alternate=V.process_bar(st,bar(tk,100.,180.,60.,100.),signal=sig(tk) if tk.hour==0 else None)
            assert rr.state==alternate.state
            assert (rr.close_point,rr.day_end,rr.step_record)==(alternate.close_point,alternate.day_end,alternate.step_record)
            assert tuple(x for x in rr.trace if x.phase!='margin_basis')==tuple(x for x in alternate.trace if x.phase!='margin_basis')
            assert B.bar_points(rr)!=B.bar_points(alternate)
            counts['noninterference_pairs']+=1
            if first is None: first=rr
            old=log; log=log.add(rr); assert log.points[:len(old.points)]==old.points
            opening=D(100000) if k==0 else cash+q*100
            peak,minimum,_=verify(log.points[-6:],normal,[opening,cash+q*100,cash+q*100,cash+q*hi,cash+q*lo,cash+q*100],peak,minimum)
            near(log.peak,peak); near(log.max_dd_bound,minimum)
            # C6-02: corrected known-at time, independently compared to the next close_point.
            cp=log.points[-1]
            assert cp.bar_open==tk and cp.time==tk+V.BAR
            if rr.close_point:
                assert rr.close_point[0]==tk-V.BAR and rr.close_point[1]==tk
            st=rr.state
        timestamp_examples.append({'order':order,'cost':cost,'actual':str(log.points[-1].time),'expected':str(tk+V.BAR)})
        for bad in (first,):
            try: log.add(bad)
            except V.EventError: pass
            else: raise AssertionError('Duplicate accepted')
        try: dc.replace(log,peak=100000.)
        except B.BoundError: pass
        else: raise AssertionError('Replace accepted')
        sequential.append({'order':order,'cost':cost,'bars':15,'peak':str(peak),'minimum':str(minimum)})
    # Original defect with interior payments: actual close includes events later than T.
    funded=[]
    for order in 'AB':
        st=V.EngineState.start(sc(order)); log=B.BoundLog.begin(st)
        q=D('.5')*100000/(100+D('.5')*D('.0016')*100)
        cash=D(100000)-q*100-D('.0016')*q*100
        peak=D(100000); minimum=D(0)
        for k in range(4):
            tk=V.START+k*V.BAR
            rates=[D('.001'),D('-.0004')]
            events=[event('paid'+str(k),tk+pd.Timedelta(hours=1,milliseconds=1),float(rates[0]),100.),
                    event('credit'+str(k),tk+pd.Timedelta(hours=3,milliseconds=7),float(rates[1]),100.)]
            rr=V.process_bar(st,bar(tk,100.,104.,98.,101.),events,sig(tk) if k==0 else None)
            opening=D(100000) if k==0 else cash+q*100
            values=[opening,cash+q*100,cash+q*100,cash+q*100*(-rates[1])+q*104,
                    cash-q*100*rates[0]+q*98]
            cash-=q*100*sum(rates); values.append(cash+q*101)
            old=log; log=log.add(rr)
            peak,minimum,_=verify(log.points[-6:],normal,values,peak,minimum)
            near(log.peak,peak); near(log.max_dd_bound,minimum)
            cp=log.points[-1]
            assert cp.time>max(x.time for x in rr.trace if x.phase=='funding_interior')
            if rr.close_point:
                previous=old.points[-1]
                assert (previous.bar_open,previous.time)==rr.close_point[:2]
                near(previous.E,rr.close_point[2])
            funded.append({'order':order,'bar_open':str(tk),'known_at':str(cp.time),'E_decimal':str(values[-1])})
            st=rr.state
    terminal=[]
    for order in 'AB':
        # Terminal fixture is local, not evidence of a complete tradable history.
        ss=sc(order); a=L.Account(60000.,400.,100000.,95.,realized=-2000.)
        ts=V.TERMINAL
        state=V.EngineState._fixture(ss,a,R.RiskState(initial=100000.,peak=110000.,day_start=98000.,next_boundary=ts,started=True),
              F.FundingState(ss.account_key,ss.label),M.MarginState(ss.account_key,ss.label,ss.mmr),ts,95.)
        rr=V.process_bar(state,V.Bar(ts,95.1,95.,120.,50.,95.1),[event('term',ts,.0001,95.)])
        E=D(60000)+400*D('95.1')-400*D('95.1')*D('.0016')-(D('3.8') if order=='A' else 0)
        verify(B.bar_points(rr),['open','trade','post','terminal'],[D(98000),E,E,E],D(110000))
        terminal.append(str(E))
    return {'revision':REV,'base':BASE,'changed_files':changed,'source_sha256':{p:hashlib.sha256(v.encode()).hexdigest() for p,v in src.items()},
            'protected_byte_unchanged_vs_base':True,'counts':counts,'O7':o7ref,'funding_margin_matrix':matrix,'gap_references':gaps,
            'sequential':sequential,'terminal':terminal,'C6-02':{'closed':True,'close_timestamp_examples':timestamp_examples,'interior_funding':funded}}

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    with localcontext() as ctx:
        ctx.prec=70
        result=run()
        mutations={
            'old_close_timestamp':('T + ev.BAR, b.mark_close','T, b.mark_close'),
            'wrong_high_credit_sign':('C_post + received','C_post - received'),
            'wrong_low_payment_sign':('C_post - paid','C_post + paid'),
            'lost_running_minimum':('mdd = min(mdd, dd)','mdd = dd'),
            'lost_running_peak':('peak = max(peak, kw["E"])','peak = max(ev.INITIAL, kw["E"])'),
            'clipped_negative_E':('E=_out(f"E för {phase}", E)','E=max(0.0, _out(f"E för {phase}", E))'),
            'missing_terminal':('out.append(_point(r, "terminal", r.state.account.C, r.state.account.q, r.terminal_point[1], T))','pass'),
        }
        outcomes={}
        for name,m in mutations.items():
            try: run(m)
            except (AssertionError,ValueError): outcomes[name]='caught'
            else: raise AssertionError('Missed mutation '+name)
        result['independent_mutations']=outcomes
    if args.check:
        assert json.loads(TARGET.read_text())==result,'Verification differs'
        print('PASS: locked C6 Decimal reference and corrected C6-02 provenance')
    else:
        TARGET.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        print('Wrote',TARGET.relative_to(ROOT))
