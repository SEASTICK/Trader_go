"""Utvärdering, kontroller och beslut för H-0013 på syntetisk data. Ingen riktig data, inget slutprov."""
import json
import subprocess

import numpy as np
import pandas as pd
import pytest

from traderlab import adaptive, fas2, fas2_eval, regime, stats
from traderlab.data import binance
from traderlab.registry import NotRegisteredError
from traderlab.strategies.rules import SPECS
from traderlab.synthetic import make_bars

EMA, BB, FLAT = "ema_adx_trend", "bb_rsi_reversion", adaptive.FLAT
UTC = lambda t: pd.Timestamp(t, tz="UTC")
STEP = pd.Timedelta(hours=4)
N_DEV = int((UTC("2025-01-01") - UTC("2020-01-01")) / STEP)
ALL_BB = adaptive.Playbook.of({l: BB for l in regime.LABELS})
FEW = adaptive.all_playbooks()[:3]


def funding_for(bars, rate=0.0001):
    return pd.Series(rate, index=pd.date_range(bars.index[0], bars.index[-1], freq="8h"))


@pytest.fixture(scope="module")
def dev():
    bars = make_bars(N_DEV, interval="4h", seed=1, vol=0.015)
    return bars, funding_for(bars)


@pytest.fixture(scope="module")
def result(dev):
    return fas2_eval.evaluate(*dev, n_permutations=2, playbooks=FEW, attempts_now=15)


@pytest.fixture(scope="module")
def forced(dev):
    """Urvalet ger alltid bb_rsi_reversion, så att H-0013 handlar och stresstestet har affärer."""
    orig = fas2.select
    fas2.select = lambda by: ALL_BB
    try:
        return fas2_eval.evaluate(*dev, n_permutations=2, playbooks=FEW)
    finally:
        fas2.select = orig


# Samma observationsperiod (U1–U2)

@pytest.mark.parametrize("make", [fas2_eval.buy_and_hold(), fas2_eval.candidate_alone(EMA),
                                  fas2_eval.candidate_alone(BB), fas2_eval.risk_filter()])
def test_every_comparison_has_exactly_the_h0013_bars(dev, make):
    wf = fas2.walk_forward(*dev)
    c = fas2_eval.curve(*dev, make)
    assert c["returns"].index.equals(wf.returns.index)
    for (a, b), w in zip(fas2.windows(), c["windows"]):
        inside = [t for t in c["trades"] if a <= t.entry_time < b]
        assert all(t.entry_time >= a + STEP and t.exit_time is not None and t.exit_time < b for t in inside)


def test_buy_and_hold_is_long_from_the_second_open_to_the_second_to_last(dev):
    bars, funding = dev
    c = fas2_eval.curve(bars, funding, fas2_eval.buy_and_hold())
    assert len(c["trades"]) == 6
    for t, (a, b) in zip(c["trades"], fas2.windows()):
        hist = bars[bars.index < b]
        assert t.side == "Long" and t.entry_time == a + STEP and t.exit_time == hist.index[-2]
        assert t.funding > 0, "a long pays positive funding"
    assert c["costs"] == pytest.approx(sum(t.costs for t in c["trades"]))


def test_candidate_alone_follows_its_own_signal_without_regime_rules(dev):
    bars, funding = dev
    c = fas2_eval.curve(bars, funding, fas2_eval.candidate_alone(BB))
    for (a, b) in fas2.windows():
        raw = SPECS[BB].signals(bars[bars.index < b]).target
        pos = c["position"][(c["position"].index > a) & (c["position"].index < b)]
        hist = bars[bars.index < b]
        held = pos[pos.index < hist.index[-2]]
        # Positionen under en stapel är beslutet vid föregående stängning, utom efter en stop-utgång.
        expected = raw.shift(1).reindex(held.index)
        assert ((held == expected) | (held == 0)).all()
    eff = regime.daily(bars)
    nxt = regime.per_bar(pd.DataFrame(index=c["position"].index), eff)
    assert ((c["position"] < 0) & nxt.str.startswith("upp/")).any() or ((c["position"] > 0) & nxt.str.startswith("ned/")).any(), \
        "no regime filter: the candidate trades against the trend somewhere"


def test_equal_weight_mix_is_the_mean_of_two_curves_without_rebalancing(dev):
    a = fas2_eval.curve(*dev, fas2_eval.candidate_alone(EMA))
    b = fas2_eval.curve(*dev, fas2_eval.candidate_alone(BB))
    m = fas2_eval.mixed(a, b)
    eq = (1 + m["returns"]).cumprod()
    expected = 0.5 * (1 + a["returns"]).cumprod() + 0.5 * (1 + b["returns"]).cumprod()
    np.testing.assert_allclose(eq.to_numpy(), expected.to_numpy(), rtol=1e-12)
    assert m["costs"] == pytest.approx((a["costs"] + b["costs"]) / 2)
    assert sum(t.net_pnl for t in m["trades"]) == pytest.approx(eq.iloc[-1] - 1)


def test_risk_filter_is_ema_alone_except_flat_in_down_high_vol(dev):
    bars, funding = dev
    filt = fas2_eval.curve(bars, funding, fas2_eval.risk_filter())
    eff = regime.daily(bars)
    label_of_bar = regime.per_bar(bars, eff).reindex(filt["position"].index)
    assert (filt["position"][label_of_bar == "ned/hög vol"] == 0).all()
    for (a, b) in fas2.windows():
        raw = SPECS[EMA].signals(bars[bars.index < b]).target
        held = filt["position"][(filt["position"].index > a) & (filt["position"].index < b)]
        # En position är alltid ema_adx_trends eget beslut från föregående stängning, annars platt.
        assert ((held == raw.shift(1).reindex(held.index)) | (held == 0)).all()
    assert (filt["position"] != 0).any()


# Kostnadsstress och riskmodell (U9, U11)

def test_stress_reuses_the_playbooks_with_2_5_times_costs(forced):
    main, stressed = forced["h0013"], forced["stressed"]
    assert main["trades"] == stressed["trades"] > 0
    assert stressed["costs"] == pytest.approx(2.5 * main["costs"], rel=0.15)
    assert stressed["total_return"] < main["total_return"]
    assert forced["criteria"]["stressed_costs_positive"] == (stressed["total_return"] > 0)


def test_risk_model_is_one_times_with_funding_and_liquidations_reported(forced):
    for name in ("h0013", "stressed"):
        s = forced[name]
        assert s["liquidations"] == 0 and s["funding"] != 0 and s["exposure"] <= 1.0
        assert set(s) >= {"stop_exits", "turnover_per_year", "max_drawdown", "sortino", "calmar"}


# Kriterier och beslut (U7–U10)

def summ(sharpe=1.0, t=3.0, total=0.5):
    return {"sharpe": sharpe, "t_daily_nw": t, "total_return": total}


@pytest.mark.parametrize("t, ok", [(2.67, True), (2.6699, False), (None, False), (10.0, True)])
def test_t_criterion_uses_the_registered_2_67(t, ok):
    crit = fas2_eval.criteria(summ(t=t), summ(), summ(sharpe=0), {EMA: summ(sharpe=0), BB: summ(sharpe=0)}, summ(sharpe=0))
    assert crit["t_at_least_required"] is ok


@pytest.mark.parametrize("field, other", [
    ("stressed_costs_positive", lambda: (summ(), summ(total=0.0), summ(sharpe=0), {EMA: summ(0), BB: summ(0)}, summ(0))),
    ("sharpe_above_buy_and_hold", lambda: (summ(), summ(), summ(sharpe=1.0), {EMA: summ(0), BB: summ(0)}, summ(0))),
    ("sharpe_above_best_candidate", lambda: (summ(), summ(), summ(0), {EMA: summ(0), BB: summ(sharpe=1.0)}, summ(0))),
    ("sharpe_above_equal_weight_mix", lambda: (summ(), summ(), summ(0), {EMA: summ(0), BB: summ(0)}, summ(sharpe=1.0))),
])
def test_each_comparison_is_strict_and_one_failure_rejects(field, other):
    crit = fas2_eval.criteria(*other())
    assert crit[field] is False and sum(crit.values()) == 4
    assert fas2_eval.decision(crit) == "REJECT"


def test_all_five_give_more_research_and_nothing_else_does():
    crit = fas2_eval.criteria(summ(), summ(), summ(0), {EMA: summ(0), BB: summ(0)}, summ(0))
    assert all(crit.values()) and fas2_eval.decision(crit) == "MORE_RESEARCH"
    assert fas2_eval.decision({k: True for k in list(crit)[:4]}) == "REJECT", "a missing criterion is not a pass"


def test_result_reports_registered_and_current_t_requirement(result):
    assert result["t_required"] == 2.67 and result["registered_n"] == 13
    assert result["attempts_now"] == 15 and result["t_required_now"] == pytest.approx(stats.t_krav(15))
    assert result["decision"] == fas2_eval.decision(result["criteria"])
    assert set(result["criteria"]) == {"t_at_least_required", "stressed_costs_positive", "sharpe_above_buy_and_hold",
                                       "sharpe_above_best_candidate", "sharpe_above_equal_weight_mix"}


# Kontroller (U12–U18)

def test_supplied_true_labels_give_the_same_walk_forward(dev):
    a = fas2.walk_forward(*dev)
    b = fas2.walk_forward(*dev, labels=regime.daily(dev[0]))
    assert json.dumps(a.to_dict(), sort_keys=True) == json.dumps(b.to_dict(), sort_keys=True)
    pd.testing.assert_series_equal(a.returns, b.returns)


def test_permutation_shuffles_known_days_only_and_reruns_the_whole_walk_forward(dev, monkeypatch):
    bars, funding = dev
    seen = []
    orig = fas2.walk_forward

    def spy(b, f, costs=fas2.COSTS, labels=None):
        seen.append(labels)
        return orig(b, f, costs, labels=labels)
    monkeypatch.setattr(fas2, "walk_forward", spy)
    out = fas2_eval.permutation_test(bars, funding, actual_sharpe=0.0, n=3, seed=0)
    eff = regime.daily(bars)
    unknown = eff == regime.UNKNOWN
    assert len(seen) == 3 and out["n"] == 3 and len(out["runs"]) == 3
    for p in seen:
        assert p.index.equals(eff.index)
        assert (p[unknown] == regime.UNKNOWN).all()
        assert sorted(p[~unknown]) == sorted(eff[~unknown])
    assert not seen[0].equals(seen[1])
    assert out["p_value"] == out["at_least_as_high"] / 3
    again = fas2_eval.permutation_test(bars, funding, actual_sharpe=0.0, n=3, seed=0)
    assert [r["sharpe"] for r in again["runs"]] == [r["sharpe"] for r in out["runs"]]


def test_deflated_sharpe_uses_81_trials_and_the_playbook_variance(result, dev):
    d = result["deflated_sharpe"]
    assert d["n_trials"] == 81 and d["playbooks_used"] == 3
    per_day = np.array([p["sharpe"] for p in result["playbooks"]["playbooks"]]) / np.sqrt(365)
    assert d["variance_from_playbooks"] == pytest.approx(per_day.var(ddof=1))


def test_all_81_playbooks_by_default():
    assert len(adaptive.all_playbooks()) == fas2_eval.N_PLAYBOOKS == 81


def test_summary_yearly_and_without_best_year():
    idx = pd.date_range("2022-01-01", "2024-12-31 20:00", freq="4h", tz="UTC")
    r = pd.Series(0.0, index=idx)
    r[idx.year == 2023] = 0.0005
    r[idx.year == 2024] = -0.0001
    c = {"returns": r, "position": pd.Series(1.0, index=idx), "trades": [], "costs": 0.0, "funding": 0.0, "windows": []}
    s = fas2_eval.summary(c)
    assert s["best_year"] == "2023"
    assert s["yearly"]["2022"] == pytest.approx(0.0)
    assert s["without_best_year"]["total_return"] == pytest.approx((1 + r[idx.year != 2023]).prod() - 1)
    assert s["sharpe_ci95"] == fas2_eval.summary(c)["sharpe_ci95"]


def test_regime_results_cover_every_out_of_sample_day_and_trade(forced):
    reg = forced["regimes"]
    assert sum(v["days"] for v in reg.values()) == forced["h0013"]["days"]
    assert sum(v["trades"] for v in reg.values()) == forced["h0013"]["trades"]


def test_random_label_control_and_all_reported_fields(result):
    assert result["random_label_t"] is not None
    for key in ("h0013", "stressed", "comparisons", "permutation", "deflated_sharpe", "playbooks", "regimes",
                "walk_forward"):
        assert key in result
    assert set(result["comparisons"]) == {"buy_and_hold", EMA, BB, "risk_filter", "equal_weight_mix"}


def test_same_data_and_configuration_give_the_same_evaluation(dev, result):
    again = fas2_eval.evaluate(*dev, n_permutations=2, playbooks=FEW, attempts_now=15)
    assert json.dumps(fas2_eval._clean(again), sort_keys=True) == json.dumps(fas2_eval._clean(result), sort_keys=True)


# Slutprovet

def test_holdout_is_rejected_before_any_evaluation(dev, monkeypatch):
    bars, funding = dev
    monkeypatch.setattr(fas2, "walk_forward", lambda *a, **k: pytest.fail("evaluated holdout data"))
    extra = make_bars(3, interval="4h", seed=9, start="2025-01-01")
    with pytest.raises(ValueError, match="slutprovet"):
        fas2_eval.evaluate(pd.concat([bars, extra]), funding)


# Spara alla försök (U19–U20)

def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch, dev):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    (tmp_path / "research/registry.md").write_text("| id | datum | hypotes |\n|---|---|---|\n| H-0013 | 2026-11-02 | x |\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "reg")
    bars, funding = dev
    monkeypatch.setattr(binance, "load", lambda m, s, i, d, *, start, end: bars)
    monkeypatch.setattr(binance, "load_funding", lambda s, d, *, start, end: funding)
    return tmp_path


def test_record_never_overwrites_and_keeps_every_status(tmp_path):
    a = fas2_eval.record(tmp_path, {"x": 1, "decision": "REJECT"}, "completed")
    b = fas2_eval.record(tmp_path, {"x": 1, "decision": "REJECT"}, "completed")
    c = fas2_eval.record(tmp_path, {"x": 2, "decision": "MORE_RESEARCH"}, "aborted")
    assert len({a, b, c}) == 3 and all(p.exists() for p in (a, b, c))
    assert json.loads(c.read_text())["status"] == "aborted" and "decision" not in json.loads(c.read_text())
    with pytest.raises(ValueError):
        fas2_eval.record(tmp_path, {}, "skipped")


def test_run_refuses_unregistered(tmp_path):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    (tmp_path / "research/registry.md").write_text("| id | datum | hypotes |\n|---|---|---|\n| H-0001 | 2026-11-01 | x |\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "reg")
    with pytest.raises(NotRegisteredError):
        fas2_eval.run(tmp_path)
    assert not (tmp_path / "research/results").exists()


def test_run_saves_an_aborted_attempt_and_reraises(repo, monkeypatch):
    monkeypatch.setattr(fas2_eval, "evaluate", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stopp")))
    with pytest.raises(RuntimeError, match="stopp"):
        fas2_eval.run(repo)
    files = list((repo / "research/results").glob("H-0013-*-aborted.json"))
    assert len(files) == 1
    body = json.loads(files[0].read_text())
    assert body["status"] == "aborted" and "stopp" in body["error"] and body["registry_commit"]


def test_run_completes_and_records_a_decision(repo):
    path = fas2_eval.run(repo, n_permutations=1, playbooks=FEW[:2])
    body = json.loads(path.read_text())
    assert body["status"] == "completed" and body["decision"] in ("REJECT", "MORE_RESEARCH")
    assert body["attempts_now"] == 1 and body["t_required"] == 2.67
    assert body["holdout"].startswith("2025-01-01")


def test_record_refuses_to_replace_a_file_with_the_same_name(tmp_path, monkeypatch):
    from datetime import datetime as real

    class Frozen(real):
        @classmethod
        def now(cls, tz=None):
            return real(2026, 11, 2, 12, 0, 0, tzinfo=tz)
    monkeypatch.setattr(fas2_eval, "datetime", Frozen)
    first = fas2_eval.record(tmp_path, {"x": 1}, "completed")
    with pytest.raises(FileExistsError):
        fas2_eval.record(tmp_path, {"x": 2}, "completed")
    assert json.loads(first.read_text())["x"] == 1
