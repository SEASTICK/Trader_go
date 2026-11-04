#!/usr/bin/env python3
"""Independent, revision-locked D1 audit. Synthetic memory data only; no network.
PASS reproduces reviewed evidence; it is not implementation approval.
"""
import argparse
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
REV = 'c0da8510f8e932b56bac9e56d4033bc46906009e'
BASE = 'adad84cbf386982517d985552c5d334251afc5fd'
TARGET = Path(__file__).with_name('verification.json')

def git(*a):
    return subprocess.check_output(['git', '-C', str(ROOT), *a], text=True)

def near(a,b):
    assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12),(a,b)

def run():
    names=['stats']+['momentum_'+n for n in ('ledger','signal','funding','risk','margin','event','control')]
    paths=['engine/traderlab/'+n+'.py' for n in names]
    paths+=['research/h0017-protokoll.md','research/registry.md','docs/claude-uppdrag-momentum-D1.md',
            'docs/momentum-a1-orakel.json','docs/momentum-control-D1.md','docs/momentum-status.json',
            'engine/tests/test_momentum_control.py','engine/tests/test_momentum_control_integration.py',
            'scripts/momentum-d1-mutations.py','docs/momentum-D1-mutationer.json']
    src={p:git('show',REV+':'+p) for p in paths}
    pkg=types.ModuleType('d1_locked'); pkg.__path__=[]; sys.modules[pkg.__name__]=pkg
    mods={}
    for n in names:
        m=types.ModuleType(pkg.__name__+'.'+n); m.__package__=pkg.__name__
        sys.modules[m.__name__]=m; setattr(pkg,n,m)
        exec(compile(src['engine/traderlab/'+n+'.py'],REV+':'+n,'exec'),m.__dict__); mods[n]=m
    K,S,V=[mods['momentum_'+n] for n in ('control','signal','event')]
    changed=git('diff','--name-only',BASE,REV).splitlines()
    assert changed==['docs/momentum-D1-mutationer.json','docs/momentum-checklista.md',
                     'docs/momentum-control-D1.md','docs/momentum-status.json',
                     'engine/tests/test_momentum_control.py','scripts/momentum-d1-mutations.py']
    protected=['engine/traderlab/momentum_control.py','engine/traderlab/stats.py','research/audits','research/results','research/registry.md','research/h0017-protokoll.md']
    protected+=['engine/traderlab/momentum_'+n+'.py' for n in ('signal','ledger','funding','risk','margin','event','bound')]
    assert not git('diff','--name-only',BASE,REV,'--',*protected).strip()
    idx=pd.date_range('2021-11-01', '2024-12-31 20:00',freq='4h',tz='UTC')
    days=pd.date_range('2021-11-01','2024-12-31',tz='UTC')
    # Independent daily references: all eight combinations with cap<1; full Decimal std(ddof=1).
    daily=[100*math.exp(.08*math.sin(i*6/40)+.05*math.sin(i*6/170)+.03*math.sin(i*6/13)) for i in range(len(days))]
    bars=pd.DataFrame({'close':[daily[i//6] for i in range(len(idx))]},index=idx)
    table=S.signals(bars); adapters={k:K.component_signals(table,k) for k in K.COMPONENTS}
    combos=set(); count=0; cap_lt=0
    for i in range(60,len(days)-1):
        closes=[D(repr(x)) for x in daily[i-60:i+1]]
        rs=[closes[j]/closes[j-1]-1 for j in range(1,61)]
        mean=sum(rs)/60
        vol=(sum((r-mean)**2 for r in rs)/59*365).sqrt()
        cap=min(D(1),D('.1')/vol)
        ss=[int(closes[-1]/D(repr(daily[i-h]))-1>0) for h in (7,14,28)]
        combos.add(tuple(ss)); cap_lt+=cap<1
        for k,s in zip(K.COMPONENTS,ss):
            a=adapters[k][days[i]]
            near(a.vol,vol); near(a.cap,cap); near(a.w_target,s*cap)
            assert a.s_used==s and a.decision_time==days[i]+pd.Timedelta(days=1)
            near(a.s_main,D(sum(ss))/3); count+=1
    assert len(combos)==8 and cap_lt
    # Equal-price horizons independently give zero, with nonzero volatility.
    equal=bars.copy(); day=days[100]
    for h in (0,7,14,28): equal.loc[day-pd.Timedelta(days=h)+pd.Timedelta(hours=20),'close']=100.
    eq=S.signals(equal)
    assert all(K.component_signals(eq,k)[day].s_used==0 for k in K.COMPONENTS)
    # Full public synthetic histories per component; cap=1, active first decision, constant execution/mark.
    # Price trend has varying positive returns, independently known to imply s_h=1 and vol<.1.
    trend=[100+.01*i+.002*(i%2) for i in range(len(days))]
    contract=pd.DataFrame({'open':100.,'close':[trend[i//6] for i in range(len(idx))]},index=idx)
    mark=pd.DataFrame({c:100. for c in ('open','high','low','close')},index=K.TEST_BARS)
    market=K.Market(contract,mark)
    q=D(100000)/(D(100)+D('.0016')*100)
    E=q*100; end=E-D('.0016')*q*100
    full=[]
    for k in K.COMPONENTS:
        r=K.run_component(market,k,'A',.05)
        assert len(r.log.close_points)==6577 and len(r.day_ends)==1096 and len(r.decisions)==1096
        assert r.log.state.terminated and r.log.state.account.q==0
        for j,cp in enumerate(r.log.close_points):
            near(cp[2],D(100000) if j==0 else end if j==6576 else E)
        for j,point in enumerate(r.day_ends):
            day,e=point[:2]
            assert day==pd.Timestamp('2022-01-01',tz='UTC')+pd.Timedelta(days=j)
            near(e,end if j==1095 else E)
        assert all(a.s_used==1 and a.cap==1 and a.w_target==1 for a in r.decisions)
        full.append({'component':k,'bars':6576,'close_points':6577,'days':1096,'q_entry_decimal':str(q),'E_terminal_decimal':str(end)})
    # Independent changing-position reference: no production output enters the reference ledger.
    spec=[(D('.5'),D('100'),1),(D('.8'),D('100.4'),1),(D('.6'),D('99.7'),1),
          (D('.6'),D('100'),0),(D('1'),D('100'),1)]
    cash,units=D(100000),D(0); expected=[]; c=D('.0016')
    for cap,price,active in spec:
        target=cap*active; equity=cash+units*100
        if not active: new=D(0)
        elif target*equity>units*100:
            j=price*(1+c)-100; new=target*(equity+units*j)/(100+target*j)
        else:
            k=100-price+c*price; new=target*(equity-units*k)/(100-target*k)
        cash-=(new-units)*price+abs(new-units)*price*c
        units=new; expected.append((cash,units))
    terminal=cash+units*D('100.5')*(1-c)
    state=V.EngineState.start(V.Scenario('mom7/L1','A',.05)); log=V.RunLog.begin(state)
    for T in K.TEST_BARS:
        dayno=(T-V.START).days; cap,price,active=spec[min(dayno,4)]
        signal=None
        if T==T.floor('D'):
            day=T-pd.Timedelta(days=1); vol=.05 if cap==1 else .1/float(cap)
            actual_cap=min(1.,.1/vol)
            signal=K.ComponentSignal('mom7',day,T,T,True,float(active)/3,float(active),0.,0.,vol,
                                     actual_cap,float(active),float(active)*actual_cap).to_input()
        P=100.5 if T==V.TERMINAL else float(price) if T==T.floor('D') else 100.
        result=V.process_bar(state,V.Bar(T,P,100.,100.,100.,100.),(),signal)
        state=result.state; log=log.add(result)
        Cref,qref=expected[min(dayno,4)]
        near(state.account.C,terminal if T==V.TERMINAL else Cref)
        near(state.account.q,0 if T==V.TERMINAL else qref)
    for day,e,_ in log.day_ends:
        d=(day-V.START).days; cr,qr=expected[min(d,4)]
        near(e,terminal if d==1095 else cr+qr*100)
    for j,cp in enumerate(log.close_points):
        if j==0: want=D(100000)
        elif j==6576: want=terminal
        else:
            # close before a new day's opening belongs to the preceding bar.
            d=(j-1)//6; cr,qr=expected[min(d,4)]; want=cr+qr*100
        near(cp[2],want)
    changing_reference={'bars':6576,'close_points':len(log.close_points),'days':len(log.day_ends),
                        'terminal_decimal':str(terminal),'reference_states':[[str(x) for x in pair] for pair in expected]}
    qyear=D(100000)/(D(100)*(1+c)); cyear=D(100000)-qyear*100*(1+c)
    peakyear=cyear+qyear*110; m=1
    while cyear+qyear*110*D('.985')**m>D('.85')*peakyear: m+=1
    year_expected=pd.Timestamp('2022-12-24',tz='UTC')+pd.Timedelta(days=m-1,hours=4)
    assert str(year_expected)=='2023-01-03 04:00:00+00:00'
    # Re-run all six original D1-01 counterexamples; all must now be rejected.
    defects={}
    d=days[100]
    for field,value in [('s',.123),('available','False'),('earliest_fill',d+pd.Timedelta(days=2)),
                        ('decision_time',d),('s14',.25),('vol',float('nan'))]:
        bad=table.loc[[d]].copy(); bad[field]=bad[field].astype(object); bad.at[d,field]=value
        try: K.component_signals(bad,'mom7')
        except K.ControlError: defects[field]='rejected'
        else: raise AssertionError(field+' accepted')
    assert adapters['mom7'][d].earliest_fill==d+pd.Timedelta(days=1)
    # Caller mutation is isolated; internal mutation is rejected before signals.
    contract.loc[pd.Timestamp('2025-01-01',tz='UTC')]=[100.,101.]
    assert market.contract.index.max()==V.TERMINAL
    called=[]; original=S.signals
    def spy(frame):
        called.append(str(frame.index.max())); raise AssertionError('signals must not run')
    S.signals=spy
    market.contract.loc[pd.Timestamp('2025-01-01',tz='UTC')]=[100.,101.]
    try:
        K.run_component(market,'mom7','A',.05)
    except K.ControlError: pass
    else: raise AssertionError('Expected ControlError')
    finally: S.signals=original
    assert not called
    # Huge integers must be rejected as controlled domain errors before arithmetic.
    bad=table.loc[[d]].astype(object); bad.at[d,'cap']=10**5000
    try: K.component_signals(bad,'mom7')
    except K.ControlError: adapter_overflow='ControlError'
    else: raise AssertionError('expected controlled rejection')
    # Conflicting duplicate rows must be rejected instead of silently overwritten.
    dup=pd.concat([table.loc[[d]],table.loc[[d]]])
    dup.iloc[1,dup.columns.get_loc('s7')]=1-float(dup.iloc[0]['s7'])
    dup.iloc[1,dup.columns.get_loc('s')]=sum(float(dup.iloc[1][n]) for n in ('s7','s14','s28'))/3
    try: K.component_signals(dup,'mom7')
    except K.ControlError: pass
    else: raise AssertionError('duplicate accepted')
    # Fingerprint rejects changes to actual numerical price content.
    m2=K.Market(contract.loc[:V.TERMINAL],mark)
    m2.mark.iloc[20,0]*=1.1
    try: m2.verified()
    except K.ControlError: pass
    else: raise AssertionError('changed price accepted')
    # Execute only git-show sources in isolated synthetic workspace.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); eng=root/'engine'
        for path,content in src.items():
            out=root/path; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(content)
        script=types.ModuleType('mutation_locked'); script.__file__=str(root/'scripts/momentum-d1-mutations.py')
        exec(compile(src['scripts/momentum-d1-mutations.py'],REV+':mutations','exec'),script.__dict__)
        original_tests = script.TESTS[:]
        baseline = script.baseline(sys.executable)
        assert baseline == '65 passed', baseline
        selftest = script.env_selftest(sys.executable)
        matrix = json.loads(src['docs/momentum-D1-mutationer.json'])
        catches = {r['fel']: r for r in matrix['felprov'] if r['utfall']=='FÅNGAD'}
        replay = []
        for mutation in script.MUTATIONS:
            row = script.run_one(sys.executable, *mutation)
            assert row == {k:v for k,v in catches[mutation[0]].items() if k not in ('fel','fil')}, row
            replay.append({'mutation': mutation[0], **row})
        assert len(replay)==31
        # Prove fallback using the real test runner, not mocked exit codes.
        mut = script.MUTATIONS[0]
        old_target = script.TARGETS[mut[0]]
        fallback = {}
        for label, selection in [('passing_target','test_O2_full_capital_entry'),
                                 ('empty_target','test_no_such_synthetic_test')]:
            script.TARGETS[mut[0]] = selection
            row = script.run_one(sys.executable, *mut)
            assert row['utfall']=='FÅNGAD' and row['körda_prov']=='hela D1-sviten', row
            fallback[label] = row
        script.TARGETS[mut[0]] = old_target
        # A semantically unchanged source replacement must survive the entire real suite.
        noop = ('audit_noop',mut[1],mut[2],mut[2]+'  # synthetic no-op')
        script.TARGETS[noop[0]] = 'test_O2_full_capital_entry'
        survivor = script.run_one(sys.executable, *noop)
        assert survivor == {'utfall':'MISSAD','pytest':'65 passed','körda_prov':'hela D1-sviten'}, survivor
        # Successful baseline above; introduce failures solely in test setup, with no behavior mutation.
        script.TESTS = ['tests/test_momentum_control.py::test_component_signals_match_independent_computation']
        workspace = script._workspace
        environments = {}
        for exception in ('FileNotFoundError','RuntimeError','AssertionError'):
            def broken_fixture(tmp, exception=exception):
                dst = workspace(tmp)
                (dst/'tests/conftest.py').write_text(
                    'import pytest\n@pytest.fixture(autouse=True)\ndef missing_resource():\n'
                    '    raise '+exception+'("synthetic missing test resource")\n')
                return dst
            script._workspace = broken_fixture
            row = script.run_one(sys.executable, *noop)
            assert row['typ']=='error' and row['orsak']==exception, row
            assert row['utfall']==('MILJÖFEL' if exception=='FileNotFoundError' else 'FÅNGAD'), row
            environments[exception] = row
        script._workspace = workspace
        script.TESTS = original_tests
        shared = next(m for m in script.MUTATIONS if m[0].startswith('delat förlopp'))
        assert 'replace(first, component=k)' in shared[3] and 'run_component(market, "mom7"' in shared[3]
        harness = {'baseline':baseline,'selftest':selftest,'all_31_catches_replayed':replay,
                   'fallback_actual_pytest':fallback,'noop_full_suite':survivor,
                   'setup_only_faults_without_behavior_mutation':environments,
                   'year_expected_decimal':str(year_expected),
                   'shared_state_mutant':'all components reuse mom7 RunLog and final state; caught by differing paths',
                   'D1-06':'actual replay equals saved rows without elapsed seconds',
                   'D1-08':'RuntimeError and AssertionError in setup falsely classified FÅNGAD'}
    # O9: band false does not mean hold when cap is breached (§7).
    oracle=json.loads(src['docs/momentum-a1-orakel.json'])
    w=oracle['O9_main_mot_new_mix']['upp_110']['mom7_vikt']
    assert w>.9 and abs(w-.9)<.02
    return {'revision':REV,'base':BASE,'changed_files':changed,'protected_unchanged':True,
            'sha256':{p:hashlib.sha256(s.encode()).hexdigest() for p,s in src.items()},
            'decimal_signal_comparisons':count,'signal_combinations':len(combos),'cap_below_one_days':cap_lt,
            'full_histories':full,'changing_position_reference':changing_reference,'D1-01_adapter_rejected_invalid_fields':defects,
            'D1-02_2025_reached_signal_calculation':called,'O9':'cap_breach; band false is not hold',
            'mutation_harness':harness,
            'D1-05_adapter_huge_cap':adapter_overflow,'adapter_duplicate_rows':'ControlError','decision':'EJ GODKÄND'}

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--check',action='store_true'); args=ap.parse_args()
    with localcontext() as ctx:
        ctx.prec=70; result=run()
    if args.check:
        assert json.loads(TARGET.read_text())==result,'Verification differs'
        print('PASS: revision-locked D1 correction evidence')
    else:
        TARGET.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n'); print('Wrote',TARGET.relative_to(ROOT))
