#!/usr/bin/env python3
"""Independent, revision-locked C5 review; synthetic inputs only. No network/history.
PASS verifies revised arithmetic, rejects old direct-composition defects, and reproduces remaining restore defects.
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
REV = '3f46aa572d5315527ef45e48ac218e9d80e551c8'
BASE = '8e447cbc4b68174a1b7c4ff821b0e1feb869fcf0'
TARGET = Path(__file__).with_name('verification.json')


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)


def source(path):
    return git('show', REV + ':' + path)


def near(x, y):
    assert math.isclose(float(x), float(y), rel_tol=1e-12, abs_tol=1e-9), (x, y)


def run(mutation=None):
    names = ('ledger', 'signal', 'funding', 'risk', 'margin', 'event')
    paths = ['engine/traderlab/momentum_' + n + '.py' for n in names]
    paths += ['research/h0017-protokoll.md', 'research/registry.md',
              'docs/claude-uppdrag-momentum-C5.md', 'docs/momentum-a1-orakel.json',
              'docs/momentum-C5-01-edwins-beslut.md', 'docs/momentum-C5-01-ordningsbeslut.md',
              'engine/tests/test_momentum_event.py', 'docs/momentum-status.json']
    src = {p: source(p) for p in paths}
    # Entire package and every local dependency are from git show, never the worktree.
    package = types.ModuleType('c5_locked')
    package.__path__ = []
    sys.modules['c5_locked'] = package
    mods = {}
    for n, p in zip(names, paths):
        fullname = 'c5_locked.momentum_' + n
        m = types.ModuleType(fullname)
        m.__package__ = 'c5_locked'
        sys.modules[fullname] = m
        setattr(package, 'momentum_' + n, m)
        code = src[p]
        if n == 'event' and mutation is not None:
            old, new = mutation
            assert old in code
            code = code.replace(old, new)
        exec(compile(code, REV + ':' + p, 'exec'), m.__dict__)
        mods[n] = m
    L, S, F, R, M, V = [mods[n] for n in names]
    changed = git('diff', '--name-only', BASE, REV).splitlines()
    assert changed == ['docs/momentum-C5-01-edwins-beslut.md', 'docs/momentum-checklista.md', 'docs/momentum-event-C5.md',
                       'docs/momentum-status.json', 'engine/tests/test_momentum_event.py',
                       'engine/traderlab/momentum_event.py']
    def sc(order='A', mmr=.05, cost=.0016, key='main'):
        return V.Scenario(key, order, mmr, cost)
    def bar(t, p=100., m=None, low=None, high=None, close=None):
        m = p if m is None else m
        close = m if close is None else close
        return V.Bar(t, p, m, max(m, close) if high is None else high,
                     min(m, close) if low is None else low, close)
    def sig(t, w=.5):
        return R.SignalInput(t-pd.Timedelta(days=1), t, True, 0. if w==0 else 1., .5 if w==0 else w, w, S.VERSION)
    def ev(id, t, rate, price):
        return F.FundingEvent(id, t, rate, price, F.MARK_OPEN, F.bar_open(t))
    def restore(s, a, t, prev, peak=100000., day=100000., permanent=False):
        rs = R.RiskState(a.deposit, max(a.deposit, peak), day, t, started=True, permanent=permanent,
                         permanent_time=t-V.BAR if permanent else None)
        return V.EngineState.restore(s, a, rs, F.FundingState(s.account_key, s.label),
                             M.MarginState(s.account_key, s.label, s.mmr), t, prev)
    def reconciled(a):
        near(a.C, a.deposit+a.realized-a.costs-a.funding_net+a.liquidation_adjustment-a.q*a.avg_price)
    t = V.START
    decimal_cases = 0
    # Independent entry/exit reference: direct self-financing equation solved with Decimal.
    with localcontext() as ctx:
        ctx.prec = 70
        for order in 'AB':
            for mmr in M.MMRS:
                for cost in (.0016, .004):
                    for mark in (99.5, 100., 100.5):
                        p, w, c, m, rate = D(100), D('.5'), D(str(cost)), D(str(mark)), D('.0001')
                        q = w*D(100000)/(m-w*(m-p-c*p))
                        cash = D(100000)-q*p-c*p*q
                        trade = cash+q*m
                        pay = q*m*rate if order == 'B' else D(0)
                        r = V.process_bar(V.EngineState.start(sc(order, mmr, cost)), bar(t, m=mark),
                                          [ev('same', t, .0001, mark)], sig(t))
                        tr = next(x for x in r.trace if x.phase == 'after_trade')
                        near(tr.q, q); near(tr.E, trade); near(tr.q*mark/tr.E, w)
                        near(r.state.account.C, cash-pay)
                        near(r.state.account.funding_net, pay)
                        expected = ['decision', 'gap'] + (['funding_A', 'after_trade'] if order == 'A' else
                                    ['after_trade', 'funding_B', 'after_funding_B'])
                        assert [x.phase for x in r.trace if x.phase != 'margin_basis'] == expected
                        # Six subsequent bars, exit by flat signal on next daily boundary.
                        state = r.state
                        for k in range(1, 7):
                            tk = t+k*V.BAR
                            signal = R.SignalInput(t, tk, True, 0., .5, 0., S.VERSION) if k == 6 else None
                            rr = V.process_bar(state, bar(tk, m=mark),
                                [ev('exit', tk, .0001, mark)] if k == 6 else (), signal)
                            state = rr.state
                        exit_pay = q*m*rate if order == 'A' else D(0)
                        near(state.account.C, cash-pay-exit_pay+q*p-c*p*q)
                        assert state.account.q == 0
                        reconciled(state.account)
                        decimal_cases += 1
    # O6 independently; reset must use old close, then funding and closing cost.
    resets = []
    for order in 'AB':
        tk = pd.Timestamp('2023-03-11', tz='UTC')
        a = L.Account(50000., 1000., 100000., 50.)
        r = V.process_bar(restore(sc(order), a, tk, 47.9), bar(tk, 47.55, 47.5),
                          [ev('reset', tk, .0001, 47.5)], sig(tk, .6))
        near(r.state.risk_state.day_start, D(97900))
        near(r.state.account.C, D(50000)+D(1000)*D('47.55')-D('76.08')-(D('4.75') if order=='A' else 0))
        assert r.step_record.intent.kind == R.DAY
        assert (R.NORMAL, 'strykt av day_stop') in r.step_record.suppressed
        assert r.day_end[1] == 97900
        resets.append({'order':order, 'cash':r.state.account.C})
    # Gap margin must precede a potentially rescuing fill.
    tk = pd.Timestamp('2023-04-10', tz='UTC')
    a = L.Account(-60000., 1000., 100000., 100., realized=-60000.)
    st = restore(sc('B'), a, tk, 160., peak=100000., day=100000.)
    r = V.process_bar(st, bar(tk, 55.), [ev('gap', tk, .0001, 55.)], sig(tk, 1.))
    assert r.state.margin_state.liquidated and not any(x.phase=='after_trade' for x in r.trace)
    assert r.state.account.C == r.state.account.q == 0 and r.absorbed == 1
    reconciled(r.state.account)
    # Independent 32-case Decimal matrix: multiple credits/debits, zero, both orders and simultaneous funding.
    interiors = []
    tk = pd.Timestamp('2023-04-10 08:00', tz='UTC')
    for order in 'AB':
      for mmr in M.MMRS:
       for credit_first in (False, True):
        for simultaneous in (False, True):
         for low in (63.5, 63.9):
            rates = ['-.02', '-.01', '0', '.02', '.005'] if credit_first else ['.02', '.005', '0', '-.02', '-.01']
            events = [ev(str(i), tk+pd.Timedelta(minutes=20*(i+1)), float(rate), 64.) for i,rate in enumerate(rates)]
            all_events = ([ev('sim',tk,.0001,64.)] if simultaneous else [])+events
            # Historical funding of 500 must survive; account remains independently reconciled.
            acct = L.Account(-60000.,1000.,100000.,100.,realized=-59500.,funding_net=500.)
            rr = V.process_bar(restore(sc(order,mmr),acct,tk,160.),
                              bar(tk,64.,low=low,high=66.,close=65.),all_events)
            opening = D(-60000)-(D('6.4') if simultaneous else 0)
            payments = [D(1000)*D(64)*D(rate) for rate in rates]
            cb = opening-sum(x for x in payments if x>0)
            elow = cb+D(1000)*D(str(low)); mm = D(str(mmr))*D(1000)*D(str(low))
            hit = elow <= mm
            assert rr.state.margin_state.liquidated == hit
            for x,y in zip(rr.margin_basis,(cb,elow,mm,low)): near(x,y)
            categories = [x for x in rr.trace if x.phase in set(V.BOOKED)|{V.UNRESOLVED,V.ABSORBED}]
            assert [x.event_id for x in categories] == [e.event_id for e in all_events]
            interior_trace = categories[1:] if simultaneous else categories
            if hit:
                assert all(x.phase==V.UNRESOLVED for x in interior_trace)
                assert rr.interior_booked==rr.absorbed==0
                assert len(rr.unresolved)==5
                for u,e,amount in zip(rr.unresolved,events,payments):
                    assert u[:2]==(e.event_id,e.time) and u[3]==(amount>0); near(u[2],amount)
                near(rr.state.account.funding_net,D(500)+(D('6.4') if simultaneous else 0))
                near(rr.state.account.liquidation_adjustment,-opening-D(100000))
                assert rr.state.account.C==rr.state.account.q==0
                assert next(x for x in rr.trace if x.phase=='liquidation').time==V.UNKNOWN_TIME
                near(rr.state.margin_state.record.C_old,cb)
                # Absorbing through midnight and independently restored near terminal.
                st = rr.state
                for k in range(1,5):
                    tt=tk+k*V.BAR
                    nxt=V.process_bar(st,bar(tt,70.),[ev('later'+str(k),tt+pd.Timedelta(minutes=1),-.01,70.)],
                                      sig(tt) if tt.hour==0 else None)
                    assert nxt.state.account==rr.state.account and nxt.absorbed==1
                    st=nxt.state
                rs=dc.replace(st.risk_state,next_boundary=V.TERMINAL)
                end=V.EngineState.restore(st.scenario,st.account,rs,st.funding_state,st.margin_state,V.TERMINAL,70.)
                endr=V.process_bar(end,bar(V.TERMINAL,70.))
                assert endr.state.account==rr.state.account and endr.terminal_point[1]==0
            else:
                assert all(x.phase=='funding_interior' for x in interior_trace)
                near(rr.state.account.funding_net,D(500)+(D('6.4') if simultaneous else 0)+sum(payments))
                running=opening
                for tr,e,amount in zip(interior_trace,events,payments):
                    running-=amount; near(tr.C,running); assert tr.time==e.time
            reconciled(rr.state.account)
            interiors.append({'order':order,'mmr':mmr,'credit_first':credit_first,'simultaneous':simultaneous,
                              'low':low,'hit':hit,'funding_net':rr.state.account.funding_net,
                              'adjustment':rr.state.account.liquidation_adjustment})
    # Full flat synthetic horizon: independently enumerated expected source/known times and dates.
    state = V.EngineState.start(sc())
    points, days = [(None, V.START, 100000.)], []
    first_result = None
    horizon_log = V.RunLog.begin(state)
    for tk in pd.date_range(V.START, V.TERMINAL, freq='4h'):
        r = V.process_bar(state, bar(tk), signal=sig(tk, 0.) if tk.hour==0 else None)
        horizon_log = horizon_log.add(r)
        if first_result is None: first_result = r
        if r.close_point: points.append(r.close_point)
        if r.day_end: days.append(r.day_end)
        if r.terminal_point:
            points.append((tk, tk, r.terminal_point[1])); days.append((tk.floor('D'), r.terminal_point[1], False))
        state = r.state
    expected_times = list(pd.date_range(V.START, V.TERMINAL-V.BAR, freq='4h'))
    assert points[1:-1] == [(x,x+V.BAR,100000.) for x in expected_times]
    assert len(points)==6577 and len(days)==1096
    assert [x[0] for x in days] == list(pd.date_range(V.START,V.TERMINAL.floor('D'),freq='D'))
    assert state.terminated and state.account.q==0
    assert list(horizon_log.close_points)==points and list(horizon_log.day_ends)==days
    # Terminal O10, simultaneous event plus +1ms/+30s: q=0 after exact terminal.
    terminal_cases = []
    for order in 'AB':
        aterm=L.Account(60000.,400.,100000.,95.,realized=-2000.)
        tk=V.TERMINAL
        events=[ev('at',tk,.0001,95.), ev('ms',tk+pd.Timedelta(milliseconds=1),.0001,95.),
                ev('sec',tk+pd.Timedelta(seconds=30),.0001,95.)]
        rr=V.process_bar(restore(sc(order),aterm,tk,95.,peak=110000.,day=98000.),
                         bar(tk,95.1,95.),events)
        expected=D(60000)+D(400)*D('95.1')-D('.0016')*D('95.1')*D(400)
        if order=='A': expected-=D(400)*D(95)*D('.0001')
        near(rr.terminal_point[1],expected)
        assert rr.state.terminated and rr.state.account.q==0
        assert rr.interior_booked==2 and all(x.funding==0 for x in rr.trace if x.phase=='funding_interior')
        terminal_cases.append({'order':order,'equity':rr.terminal_point[1]})
    # Exact opening and interior timestamps, both A/B, first opening and ordinary boundaries.
    timing_cases=0
    for order in 'AB':
        for tk in (V.START,pd.Timestamp('2023-06-03',tz='UTC'),pd.Timestamp('2023-06-03 08:00',tz='UTC')):
            a0=L.Account.open(100000.)
            st0=V.EngineState.start(sc(order)) if tk==V.START else restore(sc(order),a0,tk,100.)
            events=[ev('exact',tk,.0001,100.),ev('ms',tk+pd.Timedelta(milliseconds=1),.0001,100.),
                    ev('sec',tk+pd.Timedelta(seconds=30),.0001,100.)]
            rr=V.process_bar(st0,bar(tk),events,signal=sig(tk) if tk.hour==0 else None)
            interior=[x for x in rr.trace if x.phase=='funding_interior']
            assert [x.time for x in interior]==[e.time for e in events[1:]]
            assert all(x.q==rr.state.account.q for x in interior)
            assert rr.state.funding_state.processed=={'exact','ms','sec'}
            timing_cases+=1
    # Controlled errors and immutable inputs; original state remains reusable after every failure.
    good=V.EngineState.start(sc())
    bad_calls=[lambda:V.process_bar(good,bar(V.START+V.BAR),signal=sig(V.START)),
               lambda:V.process_bar(good,bar(V.START),[ev('wrong',V.START,.01,101.)],sig(V.START)),
               lambda:V.process_bar(good,bar(V.START),[ev('pre',V.START-pd.Timedelta(milliseconds=1),.01,100.)],sig(V.START)),
               lambda:V.Bar(V.START,10**5000,100.,100.,100.,100.),
               lambda:V.Bar(V.START,100.,100.,100.,True,100.),
               lambda:dc.replace(good,funding_state=F.FundingState('foreign',good.scenario.label)),
               lambda:dc.replace(good,margin_state=M.MarginState('main',good.scenario.label,.005))]
    for call in bad_calls:
        snapshot=repr(good)
        try: call()
        except L.LedgerError as exc:
            assert str(exc) and repr(exc)
        else: raise AssertionError('Expected controlled rejection')
        assert repr(good)==snapshot
    assert V.process_bar(good,bar(V.START),signal=sig(V.START)).state.account.q>0
    def rejected(call):
        try: call()
        except L.LedgerError as exc: assert str(exc); return
        raise AssertionError('Expected rejection')
    # All four old direct replace counterexamples now rejected.
    for acct in (L.Account.open(200000.),L.Account(50000.,500.,100000.,100.),L.Account(0.)):
        rejected(lambda:dc.replace(good,account=acct))
    tk=pd.Timestamp('2023-05-02',tz='UTC')
    locked=restore(sc(key='locked'),L.Account.open(100000.),tk,100.,permanent=True)
    foreign=restore(sc('B',key='other'),L.Account.open(100000.),tk,100.)
    rejected(lambda:dc.replace(locked,risk_state=foreign.risk_state))
    # Public restore bypasses that same gate: no private context or object mutation used.
    swapped=V.EngineState.restore(locked.scenario,locked.account,foreign.risk_state,
                                  locked.funding_state,locked.margin_state,tk,100.)
    genuine=V.process_bar(locked,bar(tk),signal=sig(tk))
    bypass=V.process_bar(swapped,bar(tk),signal=sig(tk))
    assert genuine.state.account.q==0 and bypass.state.account.q>0
    # The same bypass from an actual sequentially generated permanent stop, not a fabricated lock.
    live=V.EngineState.start(sc(key='actual'))
    other=V.EngineState.start(sc('B',key='other_actual'))
    for k in range(6):
        tt=V.START+k*V.BAR
        # Close 300 first raises peak to ~199840, then close 220 triggers permanent stop.
        price=100. if k==0 else 300. if k==1 else 220.
        closing=300. if k==0 else 220.
        live=V.process_bar(live,bar(tt,price,low=min(price,closing),high=max(price,closing),close=closing),
                           signal=sig(tt) if k==0 else None).state
        other=V.process_bar(other,bar(tt),signal=sig(tt,0.) if k==0 else None).state
    assert live.risk_state.permanent and live.account.q==0 and live.account.C>100000.
    actual_swap=V.EngineState.restore(live.scenario,live.account,other.risk_state,live.funding_state,
                                      live.margin_state,live.next_bar,live.prev_mark_close)
    genuine_actual=V.process_bar(live,bar(live.next_bar,220.),signal=sig(live.next_bar))
    bypass_actual=V.process_bar(actual_swap,bar(live.next_bar,220.),signal=sig(live.next_bar))
    assert genuine_actual.state.account.q==0 and bypass_actual.state.account.q>0
    # Other invalid restored histories: non-protocol initial capital; changed booked funding without IDs.
    doubled=restore(sc(),L.Account.open(200000.),tk,100.,peak=200000.,day=200000.)
    doubled_result=V.process_bar(doubled,bar(tk),signal=sig(tk,0.))
    assert doubled_result.state.account.C==200000.
    no_history=restore(sc(),L.Account(99999.,deposit=100000.,funding_net=1.),tk,100.)
    assert not no_history.funding_state.processed
    # New public restore checks timestamp ordering before timezone validation: raw TypeError leaks.
    restore_timezone_errors=[]
    for naive in (tk.tz_localize(None),pd.NaT):
        try:
            V.EngineState.restore(locked.scenario,locked.account,locked.risk_state,locked.funding_state,
                                  locked.margin_state,naive,100.)
        except V.EventError:
            restore_timezone_errors.append('EventError')
        except TypeError as exc:
            restore_timezone_errors.append(type(exc).__name__+': '+str(exc))
        else: raise AssertionError('Invalid timestamp accepted')
    assert restore_timezone_errors[0].startswith('TypeError:')
    # RunLog old duplicate/gap/foreign/midnight defects must now be rejected.
    initial=V.EngineState.start(sc()); first=V.process_bar(initial,bar(t),signal=sig(t,0.))
    second=V.process_bar(first.state,bar(t+V.BAR))
    log=V.RunLog.begin(initial).add(first)
    foreign_result=V.process_bar(V.EngineState.start(sc('B',key='foreign')),bar(t),signal=sig(t))
    mid=V.process_bar(restore(sc(),L.Account.open(100000.),tk,100.),bar(tk),signal=sig(tk,0.))
    log_bad=[lambda:log.add(first),lambda:V.RunLog.begin(initial).add(second),
             lambda:log.add(foreign_result),lambda:V.RunLog.begin(initial).add(mid),
             lambda:log.add(second).add(first),lambda:horizon_log.add(r),
             lambda:V.RunLog.begin(locked),lambda:dc.replace(log,close_points=())]
    for call in log_bad: rejected(call)
    return {'revision':REV,'base':BASE,'changed_files':changed,
            'source_sha256':{p:hashlib.sha256(s.encode()).hexdigest() for p,s in src.items()},
            'decimal_entry_exit_cases':decimal_cases,'terminal_cases':terminal_cases,'timing_cases':timing_cases,
            'controlled_rejections':len(bad_calls),'O6':resets,'interior_cases':interiors,
            'horizon':{'bars':6576,'close_points':len(points),'days':len(days)},
            'C5-01':{'separate_basis_and_unresolved':True},
            'C5-02':{'old_replace_counterexamples_rejected':4,'restore_foreign_unlock_q':bypass.state.account.q,
                     'actual_sequential_permanent_cash':live.account.C,
                     'actual_sequential_unlock_q':bypass_actual.state.account.q,
                     'restore_nonprotocol_capital':doubled_result.state.account.C,'funding_without_ids_accepted':True},
            'C5-03':{'controlled_log_rejections':len(log_bad)},
            'C5-04':{'restore_timestamp_errors':restore_timezone_errors}}



if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    result=run()
    mutations={
        'A_funding_removed': ('if s.order == "A":', 'if False:'),
        'B_on_old_q': ('if s.order == "A":', 'if s.order == "B":'),
        'reset_from_future_open': ('state.prev_mark_close, liquidated=liquidated', 'bar.mark_open, liquidated=liquidated'),
        'start_point_removed': ('close_points=((None, START, INITIAL),)', 'close_points=()'),
        'terminal_point_removed': ('cps += ((T, T, E),)', 'cps += ()'),
    }
    outcomes={}
    for name, mutation in mutations.items():
        try: run(mutation)
        except (AssertionError, ValueError) as exc:
            outcomes[name]='caught: '+type(exc).__name__
        else: raise AssertionError('Missed mutation: '+name)
    result['independent_mutations']=outcomes
    if args.check:
        assert json.loads(TARGET.read_text())==result, 'Verification differs'
        print('PASS: locked C5 revision; revised arithmetic and rejections verified; remaining restore defects reproduced')
    else:
        TARGET.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        print('Wrote',TARGET.relative_to(ROOT))
