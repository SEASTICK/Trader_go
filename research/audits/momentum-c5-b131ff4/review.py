#!/usr/bin/env python3
"""Independent, revision-locked C5 review; synthetic inputs only. No network/history.
PASS reproduces the historical defects as well as the verified arithmetic.
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
REV = 'b131ff47a03f9d49f6e9df0ebd172a4bea0b6fcf'
BASE = 'cd25ac80f087079b9632a845cc81b63ae9c649b4'
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
    assert changed == ['docs/momentum-checklista.md', 'docs/momentum-event-C5.md',
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
        rs = R.RiskState(min(100000., peak), peak, day, t, started=True, permanent=permanent,
                         permanent_time=t-V.BAR if permanent else None)
        return V.EngineState(s, a, rs, F.FundingState(s.account_key, s.label),
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
                        assert [x.phase for x in r.trace] == expected
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
    a = L.Account(-60000., 1000., 40000., 100.)
    st = restore(sc('B'), a, tk, 70., peak=100000., day=10100.)
    r = V.process_bar(st, bar(tk, 55.), [ev('gap', tk, .0001, 55.)], sig(tk, 1.))
    assert r.state.margin_state.liquidated and not any(x.phase=='after_trade' for x in r.trace)
    assert r.state.account.C == r.state.account.q == 0 and r.absorbed == 1
    reconciled(r.state.account)
    # Intrabar matrix: independent adverse basis vs actual chronological event evidence.
    interiors = []
    tk = pd.Timestamp('2023-04-10 08:00', tz='UTC')
    for mmr in M.MMRS:
        for credit_first in (False, True):
            early, late = tk+pd.Timedelta(minutes=30), tk+pd.Timedelta(hours=2)
            events = [ev('credit', early if credit_first else late, -.02, 64.),
                      ev('debit', late if credit_first else early, .02, 64.)]
            events.sort(key=lambda x:x.time)
            r = V.process_bar(restore(sc(mmr=mmr), a, tk, 70., peak=10100., day=10100.),
                              bar(tk, 64., low=63.5, high=66., close=65.), events)
            basis = D(-60000)-D(1000)*D(64)*D('.02')+D(1000)*D('63.5')
            hit = basis <= D(str(mmr))*D(1000)*D('63.5')
            assert hit == r.state.margin_state.liquidated
            reconciled(r.state.account)
            booked = [x.event_id for x in r.trace if x.phase=='funding_interior']
            if hit:
                assert booked == ['debit'] and r.absorbed == 1
                near(r.state.margin_state.record.E_before, basis)
                assert next(x for x in r.trace if x.phase=='liquidation').time == V.UNKNOWN_TIME
            else:
                assert booked == [x.event_id for x in events]
                near(r.state.account.funding_net, 0.)
            interiors.append({'mmr':mmr, 'credit_first':credit_first, 'hit':hit, 'booked':booked,
                              'funding_net':r.state.account.funding_net, 'absorbed':r.absorbed})
    # Full flat synthetic horizon: independently enumerated expected source/known times and dates.
    state = V.EngineState.start(sc())
    points, days = [(None, V.START, 100000.)], []
    first_result = None
    horizon_log = V.RunLog.begin()
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
        aterm=L.Account(60000.,400.,98000.,95.)
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
    # C5-02: invalid initial capital/position/zero accepted, and foreign risk state clears permanent stop.
    initial_breaches = []
    for label, acct in [('double_capital',L.Account.open(200000.)),
                        ('prestart_position',L.Account(50000.,500.,100000.,100.)),
                        ('unexplained_zero',L.Account(0.))]:
        bad = dc.replace(V.EngineState.start(sc()), account=acct)
        r = V.process_bar(bad, bar(t), signal=sig(t, 0.))
        initial_breaches.append({'case':label,'C':r.state.account.C,'q':r.state.account.q,
                                 'liquidated':r.state.margin_state.liquidated})
    tk = pd.Timestamp('2023-05-02',tz='UTC')
    locked = restore(sc(key='locked'), L.Account.open(100000), tk, 100., permanent=True)
    foreign = restore(sc('B',key='other'), L.Account.open(100000), tk, 100.)
    swapped = dc.replace(locked, risk_state=foreign.risk_state)
    genuine = V.process_bar(locked, bar(tk), signal=sig(tk))
    bypass = V.process_bar(swapped, bar(tk), signal=sig(tk))
    assert genuine.state.account.q==0 and bypass.state.account.q>0
    # C5-03: log accepts duplicate and foreign result with no cursor/identity checks.
    log = V.RunLog.begin().add(first_result).add(first_result)
    foreign_result = V.process_bar(V.EngineState.start(sc('B',key='foreign')),bar(t),signal=sig(t))
    mixed = log.add(foreign_result)
    assert len(mixed.trace)==2*len(first_result.trace)+len(foreign_result.trace)
    mid = V.process_bar(restore(sc(), L.Account.open(100000),tk,100.),bar(tk),signal=sig(tk,0.))
    duplicated = V.RunLog.begin().add(mid).add(mid)
    assert len(duplicated.day_ends)==2 and duplicated.day_ends[0]==duplicated.day_ends[1]
    return {'revision':REV,'base':BASE,'changed_files':changed,
            'source_sha256':{p:hashlib.sha256(s.encode()).hexdigest() for p,s in src.items()},
            'decimal_entry_exit_cases':decimal_cases,'terminal_cases':terminal_cases,'timing_cases':timing_cases,
            'controlled_rejections':len(bad_calls),'O6':resets,'interior_cases':interiors,
            'horizon':{'bars':6576,'close_points':len(points),'days':len(days)},
            'C5-01':{'early_credit_discarded':True,'separate_adverse_basis_required':True},
            'C5-02':{'invalid_initial_states':initial_breaches,'foreign_risk_unlock_q':bypass.state.account.q},
            'C5-03':{'duplicate_day_ends':len(duplicated.day_ends),'foreign_trace_accepted':True}}


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
        print('PASS: C5 locked arithmetic/horizon and C5-01/C5-02/C5-03 counterexamples reproduced')
    else:
        TARGET.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
        print('Wrote',TARGET.relative_to(ROOT))
