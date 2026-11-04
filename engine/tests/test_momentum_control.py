"""mom-control/1.0.0 (H-0017 leverans D1) på syntetiska minnesdata. Ingen marknadshistorik.

Facit från docs/momentum-a1-orakel.json och oberoende handräkning/Decimal (egna dagscloses, delsignaler, vol och cap),
aldrig från adaptern eller run_component. Alla förlopp startar publikt via EngineState.start.
"""
import json
import math
import statistics
from decimal import Decimal as D, getcontext
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from traderlab import momentum_control as K
from traderlab import momentum_event as V
from traderlab import momentum_funding as F
from traderlab import momentum_ledger as L
from traderlab import momentum_risk as R
from traderlab import momentum_signal as S

getcontext().prec = 60
ORACLE = json.loads((Path(__file__).resolve().parents[2] / "docs/momentum-a1-orakel.json").read_text())
H = V.BAR
T0 = V.START


def path(n, seed=0):
    """Deterministisk syntetisk prisbana med växlande trender (alla åtta delsignalskombinationer förekommer)."""
    k = np.arange(n)
    return 100.0 * np.exp(0.08 * np.sin(k / 40.0 + seed) + 0.05 * np.sin(k / 170.0) + 0.03 * np.sin(k / 13.0))


def market(seed=0, funding=(), mark_shift=1.0):
    idx = pd.date_range(K.WARMUP_START, V.TERMINAL, freq=H)
    close = path(len(idx), seed)
    open_ = np.r_[close[0], close[:-1]]
    contract = pd.DataFrame({"open": open_, "close": close}, index=idx)
    t = contract.loc[V.START:V.TERMINAL]
    mo, mc = t["open"].to_numpy() * mark_shift, t["close"].to_numpy() * mark_shift
    mark = pd.DataFrame({"open": mo, "high": np.maximum(mo, mc) * 1.004, "low": np.minimum(mo, mc) * 0.996, "close": mc},
                        index=t.index)
    return K.Market(contract=contract, mark=mark, funding=tuple(funding))


@pytest.fixture(scope="module")
def mkt():
    return market()


@pytest.fixture(scope="module")
def runs_A(mkt):
    return K.run_controls(mkt, "A", 0.05)


def daily(contract):
    """Egna dagscloses (20-stapeln) för kompletta dagar, oberoende av signalmodulen."""
    c = contract["close"]
    return {d: float(c[d + pd.Timedelta(hours=20)]) for d in pd.date_range(K.WARMUP_START, V.TERMINAL.floor("D"))}


# Komponentval mot oberoende delsignaler, vol och cap.

def test_component_signals_match_independent_computation(mkt):
    dc = daily(mkt.contract)
    table = S.signals(mkt.contract[["close"]])
    sigs = {k: K.component_signals(table, k) for k in K.COMPONENTS}
    combos, differs = set(), 0
    for d in pd.date_range("2021-12-31", "2024-12-30", tz="UTC"):
        s = {h: 1.0 if D(repr(dc[d])) / D(repr(dc[d - pd.Timedelta(days=h)])) - 1 > 0 else 0.0 for h in (7, 14, 28)}
        closes = [dc[d - pd.Timedelta(days=60 - i)] for i in range(61)]
        rets = [closes[i] / closes[i - 1] - 1 for i in range(1, 61)]
        vol = statistics.stdev(rets) * math.sqrt(365)
        cap = min(1.0, 0.10 / vol)
        combos.add((s[7], s[14], s[28]))
        for k, h in (("mom7", 7), ("mom14", 14), ("mom28", 28)):
            cs = sigs[k][d]
            assert cs.available and cs.s_used == s[h] and cs.cap == pytest.approx(cap, rel=1e-12)
            assert cs.w_target == cs.s_used * cs.cap and cs.vol == pytest.approx(vol, rel=1e-12)
            assert cs.s_main == pytest.approx((s[7] + s[14] + s[28]) / 3) and cs.decision_time == d + pd.Timedelta(days=1)
            assert cs.source_version == S.VERSION and cs.adapter_version == K.VERSION
            differs += cs.w_target != cs.s_main * cs.cap
    assert len(combos) == 8 and differs > 0


def test_signal_input_is_zero_or_cap_never_main_mean():
    o12 = ORACLE["O12_mal"]
    cs = make_sig(pd.Timestamp("2021-12-31", tz="UTC"), (1, 1, 0), 1 / 6)
    si = cs.to_input()
    assert si.s == 1.0 and si.w_target == 1 / 6 and si.version == S.VERSION and cs.s_main == 2 / 3
    assert o12["w"] == pytest.approx((2 / 3) * (1 / 6)) and si.w_target != o12["w"]           # inte O12:s medelvärde


# O2 och O9 genom publik start.

def vol_for(cap):
    """En vol där min(1, 0,10 / vol) ligger så nära cap som float tillåter (exakt när det går)."""
    if cap == 1.0:
        return 0.05
    v0 = 0.1 / cap
    best, v_up, v_dn = v0, v0, v0
    for _ in range(2000):
        for v in (v_up, v_dn):
            if min(1.0, 0.1 / v) == cap:
                return v
        v_up, v_dn = math.nextafter(v_up, math.inf), math.nextafter(v_dn, 0.0)
    return best


def make_sig(day, subs, cap, comp="mom7"):
    s7, s14, s28 = (float(x) for x in subs)
    used = {"mom7": s7, "mom14": s14, "mom28": s28}[comp]
    vol = vol_for(cap)
    cap = min(1.0, 0.1 / vol)                                          # konsekvent cap = min(1, 0,10/vol)
    return K.ComponentSignal(comp, day, day + pd.Timedelta(days=1), day + pd.Timedelta(days=1), True,
                             (s7 + s14 + s28) / 3, s7, s14, s28, vol, cap, used, used * cap)


def _sig(day, s_used, cap, comp="mom7"):
    return make_sig(day, (s_used, 0.0, 0.0) if comp == "mom7" else (0.0, s_used, 0.0), cap, comp)


def test_O2_full_capital_entry():
    o = ORACLE["O2_avgift_w1"]
    st = V.EngineState.start(V.Scenario("mom7/L1", "A", 0.05))
    r = V.process_bar(st, V.Bar(T0, 100.0, 100.0, 100.0, 100.0, 100.0), (), _sig(T0 - pd.Timedelta(days=1), 1.0, 1.0).to_input())
    assert r.state.account.q == pytest.approx(o["q"], rel=1e-12) and r.state.account.equity(100) == pytest.approx(o["E_after"], rel=1e-12)


def _input(day, s, cap):
    """Komponent (s = 1) via adaptern; main (s = 1/3) som vanlig B-rad. Samma cap."""
    if s == 1.0:
        return _sig(day, 1.0, cap).to_input()
    return R.SignalInput(day, day + pd.Timedelta(days=1), True, s, cap, s * cap, S.VERSION)


def _o9_run(close_day1, s, cap=0.9):
    """Inträde vid 2022-01-01 00:00 till 100; dagens 20-stapel stänger på close_day1; beslut 2022-01-02 00:00."""
    st = V.EngineState.start(V.Scenario("x/L1", "A", 0.05))
    for k in range(6):
        T = T0 + k * H
        c = close_day1 if k == 5 else 100.0
        r = V.process_bar(st, V.Bar(T, 100.0, 100.0, max(100.0, c), min(100.0, c), c), (),
                          _input(T0 - pd.Timedelta(days=1), s, cap) if k == 0 else None)
        st = r.state
    T = T0 + 6 * H
    return st, V.process_bar(st, V.Bar(T, close_day1, close_day1, close_day1, close_day1, close_day1), (), _input(T0, s, cap))


def test_O9_component_full_capital_vs_main():
    o = ORACLE["O9_main_mot_new_mix"]
    st_c, _ = _o9_run(100.0, 1.0)
    c = D(repr(L.COST_NORMAL))
    q = D("0.9") * D(100_000) / (D(100) + D("0.9") * c * D(100))
    assert st_c.account.q == pytest.approx(float(q), rel=1e-12) == pytest.approx(3 * o["mom7_delkonto"]["q"], rel=1e-12)
    # Uppgång till 110: komponenten håller (inom band), main bryter bandet.
    _, up_c = _o9_run(110.0, 1.0)
    _, up_m = _o9_run(110.0, 1 / 3)
    w_c = up_c.prev_state.account.weight(110.0)
    assert w_c == pytest.approx(o["upp_110"]["mom7_vikt"], rel=1e-9)
    assert abs(w_c - 0.9) < R.BAND and not o["upp_110"]["mom7_band"]          # bandet bryts inte (O9)
    # Men w_current > cap: §7:s capbrott gäller även inom bandet och ger en riskavsikt tillbaka till cap (C3).
    assert up_c.step_record.intent.kind == R.CAP and up_c.step_record.intent.w == 0.9
    assert up_m.prev_state.account.weight(110.0) == pytest.approx(o["upp_110"]["main_vikt"], rel=1e-9)
    assert up_m.step_record.intent is not None and up_m.step_record.intent.kind == R.NORMAL
    # Nedgång till 97,7: komponenten −2,07 % utlöser dagsstopp, main −0,69 % gör det inte.
    _, dn_c = _o9_run(97.7, 1.0)
    _, dn_m = _o9_run(97.7, 1 / 3)
    assert dn_c.step_record.intent.kind == R.DAY and dn_c.state.account.q == 0
    assert dn_m.step_record.intent is None or dn_m.step_record.intent.kind != R.DAY


# Full horisont, isolering och scenarier.

def test_full_horizon_per_component(runs_A):
    for k, run in runs_A.items():
        log = run.log
        assert len(log.close_points) == 6577 and len(log.day_ends) == 1096 and log.state.terminated
        assert log.close_points[0] == (None, T0, 100_000.0) and log.close_points[-2][0] == pd.Timestamp("2024-12-31 16:00", tz="UTC")
        assert log.day_ends[0][0] == T0 and log.day_ends[-1][0] == pd.Timestamp("2024-12-31", tz="UTC")
        assert len(run.decisions) == 1096 and run.decisions[0].day == pd.Timestamp("2021-12-31", tz="UTC")
        assert log.state.account.q == 0 and log.state.scenario.account_key == f"{k}/L1"
        terminal = [t for t in log.trace if t.phase == "after_trade" and t.bar_open == V.TERMINAL]
        assert len(terminal) == 1


def test_decisions_drive_intents_with_component_target(runs_A):
    run = runs_A["mom14"]
    used = {cs.decision_time: cs for cs in run.decisions}
    normals = [t for t in run.log.trace if t.phase == "decision" and t.intent == R.NORMAL]
    assert normals
    for t in run.log.trace:
        if t.phase == "after_trade" and t.intent == R.NORMAL and t.time in used:
            cs = used[t.time]
            w_after = t.q * t.M / t.E
            assert w_after == pytest.approx(cs.w_target, rel=1e-12, abs=1e-12)


def test_components_differ_from_each_other_and_are_isolated(runs_A, mkt):
    ends = {k: tuple(e[1] for e in r.day_ends) for k, r in runs_A.items()}
    assert len(set(ends.values())) == 3
    alone = K.run_component(mkt, "mom28", "A", 0.05)
    assert alone.log.day_ends == runs_A["mom28"].log.day_ends and alone.log.close_points == runs_A["mom28"].log.close_points


def test_L1_L2_identical_economics_separate_identity(mkt):
    a = K.run_component(mkt, "mom7", "B", 0.005, "L1")
    b = K.run_component(mkt, "mom7", "B", 0.005, "L2")
    assert a.log.day_ends == b.log.day_ends and a.scenario.account_key != b.scenario.account_key


def test_funding_ids_are_booked_independently_per_account_and_pre_start_counted():
    events = [F.FundingEvent("pre", T0 - pd.Timedelta(hours=8), 0.0001, 100.0, F.MARK_OPEN, T0 - pd.Timedelta(hours=8))]
    base = market()
    for T in (T0 + 2 * H, T0 + 8 * H + pd.Timedelta(minutes=30)):
        Tb = T.floor("4h")
        events.append(F.FundingEvent(f"f{T.hour}{T.minute}", T, 0.0001, float(base.mark.at[Tb, "open"]), F.MARK_OPEN, Tb))
    mkt = market(funding=events)
    runs = K.run_controls(mkt, "B", 0.05)
    for r in runs.values():
        assert r.ignored_pre_start == 1 and r.log.state.funding_state.processed == {"f80", "f830"}
        assert r.log.state.funding_state.account_key == r.scenario.account_key


def test_prefix_later_prices_do_not_change_earlier_decisions(mkt):
    other = mkt.contract.copy()
    cut = pd.Timestamp("2023-06-01", tz="UTC")
    other.loc[cut:, ["open", "close"]] *= 1.3
    mark = mkt.mark.copy()
    mark.loc[cut:, :] *= 1.3
    a = K.run_component(mkt, "mom7", "A", 0.05)
    b = K.run_component(K.Market(other, mark), "mom7", "A", 0.05)
    da = [cs for cs in a.decisions if cs.decision_time <= cut]
    assert da == [cs for cs in b.decisions if cs.decision_time <= cut]
    assert [cp for cp in a.log.close_points if cp[1] <= cut] == [cp for cp in b.log.close_points if cp[1] <= cut]


# Indatafel: kontrollerade, före beräkning.

def _bad(kind):
    m = market()
    c, mk, f = m.contract.copy(), m.mark.copy(), list(m.funding)
    if kind == "lucka":
        mk = mk.drop(mk.index[100])
    elif kind == "kontrakt_lucka":
        c = c.drop(c.index[50])
    elif kind == "2025_mark":
        mk.loc[V.END] = mk.iloc[-1]
    elif kind == "2025_funding":
        f = [F.FundingEvent("late", V.END, 0.0001, 100.0, F.MARK_OPEN, V.END)]
    elif kind == "naiv_tid":
        mk.index = mk.index.tz_localize(None)
    elif kind == "nan":
        mk.iloc[10, 0] = float("nan")
    elif kind == "inf":
        c.iloc[10, 1] = float("inf")
    elif kind == "bool":
        mk["open"] = mk["open"].astype(object)
        mk.iloc[5, 0] = True
    elif kind == "huge":
        mk["open"] = mk["open"].astype(object)
        mk.iloc[5, 0] = 10 ** 400
    elif kind == "osorterad_funding":
        f = [F.FundingEvent("b", T0 + H, 0.0001, 100.0, F.MARK_OPEN, T0 + H),
             F.FundingEvent("a", T0, 0.0001, 100.0, F.MARK_OPEN, T0)]
    return c, mk, f


@pytest.mark.parametrize("kind", ["lucka", "kontrakt_lucka", "2025_mark", "2025_funding", "naiv_tid", "nan", "inf", "bool",
                                  "huge", "osorterad_funding"])
def test_invalid_market_is_rejected_before_any_computation(kind):
    c, mk, f = _bad(kind)
    with pytest.raises(K.ControlError) as err:
        K.Market(c, mk, tuple(f))
    assert str(err.value) and ("2025" in str(err.value) if kind.startswith("2025") else True)


def test_invalid_signal_day_via_constant_window_is_rejected():
    m = market()
    c = m.contract.copy()
    days = pd.date_range("2023-01-01", "2023-03-15", tz="UTC")
    for d in days:                                                     # konstant pris: vol = 0, otillgänglig signal
        c.loc[d:d + pd.Timedelta(hours=20), ["open", "close"]] = 100.0
    with pytest.raises(K.ControlError, match="otillgänglig"):
        K.run_component(K.Market(c, m.mark), "mom7", "A", 0.05)


@pytest.mark.parametrize("comp", ["mom21", True, None, 7])
def test_unknown_component_is_rejected(mkt, comp):
    with pytest.raises(K.ControlError):
        K.run_component(mkt, comp, "A", 0.05)


def test_legacy_order_and_synthetic_flag_validated(mkt):
    with pytest.raises(K.ControlError):
        K.run_component(mkt, "mom7", "A", 0.05, "L3")
    with pytest.raises(K.ControlError):
        K.Market(mkt.contract, mkt.mark, (), synthetic=False)
