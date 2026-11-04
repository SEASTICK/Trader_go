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
REV = 'aa2c8669680b017d9d9a98e46d1f9a0cb1a4fb9d'
BASE = 'ab79f2a5f8c63456075f2e1c5d22a28f3c4e1f19'
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
                     'engine/tests/test_momentum_control_integration.py',
                     'engine/traderlab/momentum_control.py','scripts/momentum-d1-mutations.py']
    protected=['engine/traderlab/stats.py','research/audits','research/results','research/registry.md','research/h0017-protokoll.md']
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
    # Adapter arithmetic precedes domain validation: huge finite integer leaks OverflowError.
    bad=table.loc[[d]].astype(object); bad.at[d,'cap']=10**5000
    try: K.component_signals(bad,'mom7')
    except K.ControlError: adapter_overflow='ControlError'
    else: raise AssertionError('expected controlled rejection')
    # Duplicate, conflicting source rows are silently collapsed to the last one.
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
        script.TESTS=['tests/test_momentum_control_integration.py::test_independent_full_horizon_capital_path_with_trades_and_terminal_P_ne_M',
                      'tests/test_momentum_control_integration.py::test_permanent_stop_across_new_year_uses_unbroken_peak']
        baseline=script.baseline(sys.executable)
        year=next(s for s in script.MUTATIONS if s[0]=='peakreset vid årsskifte')
        year_result=script.run_one(sys.executable,*year)
        assert year_result['utfall']=='FÅNGAD' and 'test_permanent_stop_across_new_year' in year_result['första_fel']
        # Re-run every saved catch against its named test, inspecting actual pytest failure output.
        matrix=json.loads(src['docs/momentum-D1-mutationer.json'])
        catches={r['fel']:r for r in matrix['felprov'] if r['utfall']=='FÅNGAD'}
        replay=[]; pytest_original=script._pytest
        def inspected(py,cwd):
            p=subprocess.run([str(py),'-m','pytest','-p','no:cacheprovider','-o','addopts=',
                              '-q','-x','-rfE',*script.TESTS],cwd=cwd,capture_output=True,text=True)
            out=p.stdout+p.stderr
            assert p.returncode==1 and 'FAILED ' in out and 'ERROR collecting' not in out,out
            assert 'FileNotFoundError' not in out and 'ModuleNotFoundError' not in out,out
            assert 'AssertionError' in out or 'Error' in out,out
            failed=[line.split(' ')[1] for line in out.splitlines() if line.startswith('FAILED ')]
            assert failed==script.TESTS,(failed,script.TESTS)
            return 1,'1 failed',failed
        script._pytest=inspected
        for mutation in script.MUTATIONS:
            row=catches[mutation[0]]; script.TESTS=[row['första_fel']]
            result=script.run_one(sys.executable,*mutation)
            assert result['utfall']=='FÅNGAD',result
            replay.append({'mutation':mutation[0],'test':row['första_fel'],'replayed_failure':True})
        script._pytest=pytest_original
        # Independent fixture resource failure after successful collection is not a killed behavior mutant.
        script.TESTS=['tests/test_momentum_control.py::test_component_signals_match_independent_computation']
        workspace=script._workspace
        def broken_fixture(tmp):
            dst=workspace(tmp)
            (dst/'tests/conftest.py').write_text('import pytest\n@pytest.fixture(autouse=True)\ndef missing_resource():\n    raise FileNotFoundError("synthetic missing test resource")\n')
            return dst
        script._workspace=broken_fixture
        environment=script.run_one(sys.executable,*script.MUTATIONS[0])
        assert environment['utfall']=='FÅNGAD' and 'error' in environment['pytest'], environment
        script._workspace=workspace
        identity=next(s for s in script.MUTATIONS if s[0]=='delad kontoidentitet/state mellan konton')
        assert 'EngineState.start' in identity[3] and 'mom7/' in identity[3]
        # Compare --check's exact serialized timings: arbitrary elapsed-time drift changes equality.
        saved=json.loads(src['docs/momentum-D1-mutationer.json'])
        drift=json.loads(json.dumps(saved)); drift['baslinje']='65 passed in 999.99s'
        assert json.dumps(saved)!=json.dumps(drift)
        harness={'all_30_catches_individually_replayed':replay,'year_expected_decimal':str(year_expected),'focused_baseline_passed':2,'year_reset_caught_by_independent_test':True,
                 'runtime_FileNotFoundError_class':environment['utfall'],
                 'shared_state_mutant':'fresh EngineState per invocation; only key changed',
                 'check_compares_elapsed_seconds':True}
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
