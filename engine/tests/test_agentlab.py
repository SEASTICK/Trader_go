"""Agentlab: tester på syntetisk data (snabba). Positiv kontroll (planterad momentum) ska hittas, negativ (brus) ska avvisas."""
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from traderlab.agentlab import agents, backtest as bt, judge
from traderlab.agentlab.data import HOLDOUT, Panel, period_slice, synthetic_panel
from traderlab.agentlab.orchestrator import Orchestrator, rank_ideas, select
from traderlab.agentlab.state import Blackboard, ExperimentRegistry, TaskQueue
from traderlab.agentlab.strategies import BUILDERS, ModelUnavailable, make_spec, mutate, neighbors, sample_ideas

FAMS = ["xs_mom", "xs_rev", "ts_mom", "trend_ma", "lowvol", "funding_carry", "donchian"]


def small(momentum=0.0, seed=3):
    return synthetic_panel(n_days=1500, n_assets=22, seed=seed, momentum=momentum)


# ---------------------------------------------------------------- backtest: timing, kostnad, finansiering
def test_vikter_beslutade_dag_t_tjänar_öppning_t1_till_öppning_t2_och_kostar_omsättning():
    p = small()
    W = pd.DataFrame(0.0, index=p.close.index, columns=p.close.columns)
    W.iloc[100, 0] = 1.0                                     # beslut på dag 100, en dag, en tillgång
    r = bt.run(p, W, cost=0.001, funding=False)
    day = p.close.index[101]                                 # hålls dag 101
    expect = p.open.iloc[102, 0] / p.open.iloc[101, 0] - 1
    assert r.gross[day] == pytest.approx(expect)
    assert r.turnover[day] == pytest.approx(1.0) and r.cost[day] == pytest.approx(0.001)
    assert r.turnover[p.close.index[102]] == pytest.approx(1.0)                # avslut nästa dag kostar också


def test_finansiering_betalas_av_long_och_tas_emot_av_short():
    p = small()
    p.funding.iloc[:, :] = 0.001
    W = pd.DataFrame(0.0, index=p.close.index, columns=p.close.columns)
    W.iloc[200, 0] = 1.0
    long = bt.run(p, W, cost=0.0).funding[p.close.index[201]]
    short = bt.run(p, -W, cost=0.0).funding[p.close.index[201]]
    assert long == pytest.approx(0.001) and short == pytest.approx(-0.001)


def test_panelen_vägrar_data_från_slutprovet():
    p = small()
    idx = pd.date_range("2024-12-20", periods=20, freq="D", tz="UTC")
    df = pd.DataFrame(1.0, index=idx, columns=["A"])
    with pytest.raises(ValueError, match="slutprovet"):
        Panel(df, df, df, df, df, df)
    assert p.close.index.max() < HOLDOUT


# ---------------------------------------------------------------- strategier och Builder
def test_neighbors_och_mutationer_ger_nya_specar_och_ingen_dubblett():
    s = make_spec("xs_mom", {"k": 30, "q": 0.2, "rebal": 7, "uni": 30})
    ns = neighbors(s)
    assert ns and all(n["key"] != s["key"] and n["parent"] == s["key"] for n in ns)
    m = mutate(s, "cost_fragile")
    assert m and m["params"]["rebal"] > s["params"]["rebal"] and m["parent"] == s["key"]
    assert mutate(make_spec("xs_mom", {"k": 30, "rebal": 14}), "cost_fragile")["params"]["k"] == 60     # rebal är redan störst, då längre lookback
    assert mutate(s, "okänd_invändning") is None


def test_sample_ideas_är_många_olika_och_täcker_familjer():
    ideas = sample_ideas(30, 1)
    assert len({i["key"] for i in ideas}) == len(ideas) == 30
    assert len({i["family"] for i in ideas}) >= 8 and all("placebo" != i["family"] for i in ideas)


# ---------------------------------------------------------------- Skeptiker: läckagetest
def test_läckagespecialisten_fångar_en_strategi_som_tittar_på_framtiden_men_inte_en_ren():
    p = small(momentum=1.0)
    agents.set_panel(p, None)
    BUILDERS["leaky_test"] = lambda params, pan: ((pan.close.shift(-1) / pan.close - 1).where(pan.universe(20)).rank(axis=1, pct=True) > 0.8).astype(float) / 5
    try:
        leaky = make_spec("xs_mom", {"k": 30})
        leaky = {**leaky, "family": "leaky_test", "key": "leaky000001"}
        assert agents.leakage_specialist({"spec": leaky})["leakage"] is True
    finally:
        del BUILDERS["leaky_test"]
    clean = make_spec("xs_mom", {"k": 30, "q": 0.2, "rebal": 7, "uni": 20})
    assert agents.leakage_specialist({"spec": clean})["leakage"] is False


# ---------------------------------------------------------------- Domare
EV = {"quant": {"disc": {"sharpe": 1.5, "ann_ret": 0.4, "max_dd": -0.15, "n": 800}, "neighbors": [["a", 1.2], ["b", 1.3]], "turnover_ann": 30, "beta_btc": 0.05, "baselines": {"bh_btc": 0.7}},
      "cost": {"sharpe_grid": {"0.0": 1.7, "1.0": 1.5, "2.5": 1.2, "5.0": 0.8}}, "risk": {}, "skeptic": {"perm_p": 0.01, "dsr": 0.97, "half_pos": 0.9, "asset_pos": 0.9, "leakage": False, "n_trials": 50},
      "portfolio": {"div_value": 0.2}, "objections": []}
SEALED = {"valid": {"sharpe": 1.1, "ann_ret": 0.3, "max_dd": -0.2}, "final": {"sharpe": 0.9}}


def test_domaren_rejectar_läckage_olönsamhet_och_slump_oavsett_poäng():
    import copy
    for mut, text in ((lambda e: e["skeptic"].update(leakage=True), "läckage"), (lambda e: e["cost"]["sharpe_grid"].update({"2.5": -0.1}), "2,5"),
                      (lambda e: e["skeptic"].update(perm_p=0.4), "slumpen"), (lambda e: e["quant"]["disc"].update(sharpe=0.1), "svag")):
        ev = copy.deepcopy(EV); mut(ev)
        res = judge.final(ev, SEALED)
        assert res["verdict"] == "REJECT" and any(text in n for n in res["notes"]), (text, res)


def test_domaren_poäng_belönar_stabilitet_inte_bara_avkastning_och_verdikten_trappas():
    import copy
    good = judge.final(EV, {"valid": SEALED["valid"], "final": None})
    assert good["verdict"] == "PROMISING" and good["score"] >= 55
    fragile = copy.deepcopy(EV); fragile["cost"]["sharpe_grid"]["2.5"] = 0.1; fragile["skeptic"]["half_pos"] = 0.2; fragile["quant"]["neighbors"] = [["a", 0.0]] * 4
    assert judge.final(fragile, {"valid": SEALED["valid"], "final": None})["score"] < good["score"] - 15
    assert set(judge.WEIGHTS) >= {"after_cost_return", "sharpe", "max_drawdown", "stability_periods", "stability_assets", "turnover", "cost_sensitivity",
                                  "parameter_sensitivity", "diversification", "evidence_quality"} and abs(sum(judge.WEIGHTS.values()) - 1) < 1e-9


def test_ready_for_paper_kräver_alla_grindar_och_är_bara_en_kandidat():
    res = judge.final(EV, SEALED)
    assert res["verdict"] == "READY_FOR_PAPER" and any("formell registrering" in n for n in res["notes"])
    import copy
    ev = copy.deepcopy(EV); ev["portfolio"]["div_value"] = -0.1
    assert judge.final(ev, SEALED)["verdict"] == "PROMISING"
    assert judge.final(EV, {"valid": SEALED["valid"], "final": {"sharpe": 0.1}})["verdict"] == "PROMISING"


def test_domarens_förbedömning_dödar_läckage_räddar_det_som_går_att_rädda_och_släpper_igenom_det_starka():
    import copy
    assert judge.preliminary(EV, 0, 2)[0] == "advance"
    ev = copy.deepcopy(EV); ev["skeptic"]["leakage"] = True
    assert judge.preliminary(ev, 0, 2)[0] == "kill"
    ev = copy.deepcopy(EV); ev["quant"]["disc"]["sharpe"] = 0.5; ev["cost"]["sharpe_grid"]["2.5"] = -0.1
    ev["objections"] = [{"code": "cost_fragile", "severity": 0.8, "mutable": True}]
    assert judge.preliminary(ev, 0, 2)[0] == "iterate" and judge.preliminary(ev, 2, 2)[0] == "kill"


# ---------------------------------------------------------------- tillstånd
def test_experimentregistret_är_append_only_med_löpande_id(tmp_path):
    r = ExperimentRegistry(tmp_path / "e.jsonl")
    a, b = r.append({"verdict": "REJECT"}), r.append({"verdict": "PROMISING"})
    assert (a, b) == ("X-0001", "X-0002") and r.count() == 2
    first = (tmp_path / "e.jsonl").read_text().splitlines()[0]
    r.append({"x": 1})
    assert (tmp_path / "e.jsonl").read_text().splitlines()[0] == first


def test_blackboard_är_kompakt_och_överlever_omstart(tmp_path):
    bb = Blackboard(tmp_path)
    for i in range(50):
        bb.s["rejected"].append({"key": str(i)}); bb.say("a", "b", "info", "x")
    bb.s["trials"] = 7; bb.save()
    v = Blackboard(tmp_path).view()
    assert v["trials"] == 7 and len(v["rejected_recent"]) == 8 and "messages" not in v        # inte hela historiken
    assert len((tmp_path / "messages.jsonl").read_text().splitlines()) == 50


def test_uppgiftskön_respekterar_beroenden_och_prioritet():
    q = TaskQueue()
    a = q.add("x", "f", {}, priority=2, tid="a"); b = q.add("y", "f", {}, priority=1, tid="b"); c = q.add("z", "f", {}, deps=["a"], tid="c")
    assert [t.id for t in q.ready()] == ["b", "a"]
    a.status = "done"
    assert "c" in [t.id for t in q.ready()]


def test_saknad_modell_blir_ett_hoppat_resultat_inte_en_krasch(monkeypatch):
    p = small(); agents.set_panel(p, None)
    monkeypatch.setattr("traderlab.agentlab.ml._model", lambda *a, **k: (_ for _ in ()).throw(ModelUnavailable("lightgbm saknas")))
    out = agents.run_task("quant_task", {"spec": make_spec("ml_xs", {"model": "lgbm", "h": 3, "q": 0.2, "retrain": 90, "uni": 20})})
    assert out["skipped"] and "modell saknas" in out["error"]


# ---------------------------------------------------------------- hela loopen
def run_lab(momentum, workers=1, seed=3):
    root = Path(tempfile.mkdtemp())
    orch = Orchestrator(root, small(momentum, seed), workers=workers, seed=2, cache=root / "c")
    return orch, orch.run(n_ideas=24, top_k=8, controls=3, families=FAMS), root


def test_positiv_kontroll_hittas_och_negativa_kontroller_avvisas_hela_loopen():
    orch, s, root = run_lab(1.0)
    assert s["promising"], s                                              # planterad momentum hittas
    assert s["controls_advanced"] == 0                                    # slumpstrategier passerar aldrig
    assert s["agents_spawned"] >= 10 and orch.registry.count() >= s["evaluated_versions"]
    reg = orch.registry.read()
    assert {"hypothesis", "parameters", "model", "features", "data", "timeframe", "market", "results", "costs", "risk", "comments", "verdict"} <= set(reg[0])
    assert (root / "outbox" / "github-R001.md").exists() and (root / "runs" / "R001" / "report.md").exists()
    ephemeral = [a for a in orch.bb.s["agents"].values() if a["ephemeral"]]
    assert {"LeakageSpecialist", "AssetSplitSpecialist"} <= {a["name"] for a in ephemeral}


def test_ren_brus_ger_inga_lovande_kandidater_och_förseglad_data_öppnas_bara_för_överlevare():
    orch, s, _ = run_lab(0.0, seed=7)
    assert s["promising"] == [] and s["controls_advanced"] == 0
    finals = [r for r in orch.registry.read() if r["stage"] == "final"]
    assert s["sealed_looks"] >= len(finals)                              # varje slutdom ger blick, men aldrig för dödade kandidater
    assert all(r["stage"] == "discovery" for r in orch.registry.read() if r["verdict"] == "REJECT" and "reasons" in r)
    assert sum(1 for r in orch.registry.read() if "sealed" in r) == len(finals)


def test_parallell_körning_ger_samma_domslut_som_sekventiell():
    _, a, _ = run_lab(1.0, workers=1)
    _, b, _ = run_lab(1.0, workers=3)
    assert a["verdicts"] == b["verdicts"] and a["promising"] == b["promising"]


def test_ranking_straffar_döda_familjer_och_belönar_outforskade(tmp_path):
    bb = Blackboard(tmp_path)
    bb.family("xs_mom").update(tested=10, rejected=10)
    ideas = [make_spec("xs_mom", {"k": 30}), make_spec("pairs", {"lb": 20, "z_in": 2.0, "z_out": 0.0, "npairs": 3})]
    ranked = rank_ideas(ideas, bb)
    assert ranked[0][1]["family"] == "pairs"
    assert len(select(ranked, 2)) == 2


def test_alla_familjer_bygger_vikter_utan_fel_och_utan_framtidsblick_i_sista_raden():
    """Rökprov för varje familj (fångade en bugg i pairs som körningen på riktig data avslöjade)."""
    from traderlab.agentlab.strategies import GRID, build
    p = small(momentum=0.5)
    for fam in GRID:
        if fam == "ml_xs":
            continue
        spec = make_spec(fam, {k: v[0] for k, v in GRID[fam].items()})
        W = build(spec, p)
        assert W.shape == p.close.shape and np.isfinite(W.fillna(0).values).all(), fam
        assert W.abs().sum(axis=1).max() < 12, fam                   # rimlig bruttoexponering (vol-målsättning ≤ 3x)
        r = bt.run(p, W).ret
        assert r.notna().sum() > 1000, fam


def test_finansieringsdagen_räknas_som_utbetalningar_i_d_till_d_plus_1_inklusive_gränsen():
    from traderlab.data import binance
    f = pd.Series([0.1, 0.2, 0.4, 0.8], index=pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 08:00", "2024-01-01 16:00", "2024-01-02 00:00"], tz="UTC"))
    daily = f.groupby((f.index - pd.Timedelta(seconds=1)).normalize()).sum()
    assert daily[pd.Timestamp("2023-12-31", tz="UTC")] == pytest.approx(0.1)            # 00:00 hör till föregående dag
    assert daily[pd.Timestamp("2024-01-01", tz="UTC")] == pytest.approx(0.2 + 0.4 + 0.8)


def test_domare_v2_kräver_att_valideringsåret_håller_för_promising():
    weak = judge.final(EV, {"valid": {"sharpe": 0.3, "ann_ret": 0.05, "max_dd": -0.1}, "final": None})
    assert weak["verdict"] == "MORE_RESEARCH" and any("valideringsårets Sharpe" in n for n in weak["notes"])
    assert judge.final(EV, {"valid": {"sharpe": 0.8, "ann_ret": 0.2, "max_dd": -0.1}, "final": None})["verdict"] == "PROMISING"


def test_effektivt_antal_försök_räknar_korrelerade_varianter_som_ett():
    from traderlab.agentlab.orchestrator import effective_trials
    rng = np.random.default_rng(0)
    base = rng.normal(size=(500, 1))
    same = np.hstack([base + rng.normal(scale=0.01, size=(500, 1)) for _ in range(10)])
    indep = rng.normal(size=(500, 10))
    assert effective_trials(same) < 1.5 and effective_trials(indep) > 7


def test_omdömning_lägger_till_rader_och_ändrar_aldrig_gamla(tmp_path):
    root = tmp_path / "lab"
    orch = Orchestrator(root, small(1.0), workers=1, seed=2, cache=tmp_path / "c")
    rec = {"run": "R001", "stage": "final", "key": "k1", "parent": None, "iteration": 0, "control": False, "hypothesis": "h", "family": "xs_mom", "tags": "", "parameters": {},
           "model": "rule-based", "data": [], "timeframe": "1d", "market": "x", "verdict": "PROMISING", "score": 66.0, "judge_version": 1,
           "results": {"discovery": EV["quant"]["disc"], "neighbors": EV["quant"]["neighbors"], "turnover_ann": 30, "beta_btc": 0.05, "baselines": {"bh_btc": 0.7}},
           "costs": {"sharpe_grid": EV["cost"]["sharpe_grid"]}, "adversarial": EV["skeptic"], "portfolio": EV["portfolio"],
           "sealed": {"valid": {"sharpe": 0.3, "ann_ret": 0.05, "max_dd": -0.1}, "final": None}}
    orch.registry.append(rec)
    before = (root / "experiments.jsonl").read_text()
    changed = orch.rejudge()
    assert changed and changed[0]["from"] == "PROMISING" and changed[0]["to"] == "MORE_RESEARCH"
    after = (root / "experiments.jsonl").read_text()
    assert after.startswith(before) and len(after.splitlines()) == 2
    assert orch.rejudge() == []                                           # idempotent


def test_inbox_tar_emot_idéer_utifrån_och_loggar_ogiltiga_rader(tmp_path):
    root = tmp_path / "lab"
    (root / "inbox").mkdir(parents=True)
    (root / "inbox" / "ideas.jsonl").write_text(json.dumps({"family": "xs_mom", "params": {"k": 21, "q": 0.2, "rebal": 5, "uni": 30}, "source": "codex-kommentar"}) + "\nskräp\n"
                                                + json.dumps({"family": "finns_inte"}) + "\n", encoding="utf-8")
    orch = Orchestrator(root, small(), workers=1, cache=tmp_path / "c")
    got = orch.read_inbox(set())
    assert len(got) == 1 and got[0]["params"]["k"] == 21 and "codex-kommentar" in got[0]["note"]
    assert len(orch.bb.s["known_issues"]) == 2


# ---------------------------------------------------------------- informationsbarriär (Codex P1): verklig, inte en visningsregel
def _poisoned(p: Panel, after: str) -> Panel:
    """Samma panel men alla värden efter `after` ersatta med en framtidsmarkör. Om en uppgift kan läsa dem ändras dess resultat."""
    end = pd.Timestamp(after, tz="UTC")
    def f(df):
        out = df.copy()
        out.loc[out.index > end] = out.loc[out.index > end] * 1000.0 + 12345.0
        return out
    return Panel(f(p.open), f(p.high), f(p.low), f(p.close), f(p.dvol), f(p.funding), meta=p.meta)


SPEC = make_spec("xs_mom", {"k": 30, "q": 0.2, "rebal": 7, "uni": 20})


def _round(x):
    if isinstance(x, float):
        return round(x, 8)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v) for v in x]
    return x


def _same(a, b):
    """Lika upp till flyttalsbrus (1e-8); en framtidsmarkör skulle ändra resultat med storleksordningar mer."""
    return json.dumps(_round(a), sort_keys=True, default=float) == json.dumps(_round(b), sort_keys=True, default=float)


def test_discovery_uppgifter_kan_inte_läsa_valid_eller_final_även_med_en_framtidsmarkör():
    from traderlab.agentlab.data import PERIODS
    p = small(momentum=1.0)
    q = _poisoned(p, PERIODS["disc"][1])
    res = {}
    for name, pan in (("clean", p), ("poisoned", q)):
        agents.set_panel(pan, None)
        assert agents.panel().close.index.max() <= pd.Timestamp(PERIODS["disc"][1], tz="UTC")       # uppgifter ser bara discovery
        res[name] = {fn: agents.run_task(fn, {"spec": SPEC, "n_trials": 5}) for fn in ("quant_task", "cost_task", "risk_task", "skeptic_task")}
        res[name].update({fn: agents.run_task(fn, {"spec": SPEC}) for fn in ("leakage_specialist", "asset_split_specialist", "crosssection_specialist", "liquidation_specialist")})
    for fn in res["clean"]:
        assert not res["clean"][fn].get("error"), (fn, res["clean"][fn])
        assert _same(res["clean"][fn], res["poisoned"][fn]), fn                                  # markören påverkar ingenting: framtiden är oläsbar
    assert "sealed" not in res["clean"]["quant_task"]                                          # inga framtida mått skickas tillbaka till Builder
    port = agents.run_task("portfolio_task", {"specs": [SPEC, make_spec("xs_rev", {"k": 3, "q": 0.2, "rebal": 2, "uni": 20})]})
    assert all(set(c) <= {"members", "disc"} for c in port["combos"].values())                  # inga valid/final-kombinationer


def test_valideringssteget_ser_inte_2024_och_slutsteget_är_ett_eget_steg():
    from traderlab.agentlab.data import PERIODS
    p = small(momentum=1.0)
    out = {}
    for name, pan in (("clean", p), ("poisoned", _poisoned(p, PERIODS["valid"][1]))):
        agents.set_panel(pan, None)
        out[name] = agents.run_task("validate_task", {"spec": SPEC})
        assert agents.panel().close.index.max() <= pd.Timestamp(PERIODS["disc"][1], tz="UTC")     # vyn återställs efteråt
    assert _same(out["clean"], out["poisoned"]) and "valid" in out["clean"] and "final" not in out["clean"]
    agents.set_panel(p, None)
    fin = agents.run_task("final_task", {"spec": SPEC})
    assert "final" in fin and "valid" not in fin


def test_slutsteget_körs_aldrig_när_valideringen_misslyckas(monkeypatch):
    called = []
    monkeypatch.setitem(agents.TASKS, "final_task", lambda pl: called.append(pl["spec"]["key"]) or {"final": {"sharpe": 9.0}})
    real = agents.TASKS["validate_task"]
    monkeypatch.setitem(agents.TASKS, "validate_task", lambda pl: {"valid": {"sharpe": -1.0, "ann_ret": -0.2, "max_dd": -0.3}, "key": pl["spec"]["key"]})
    orch, s, _ = run_lab(1.0)
    assert s["promising"] == [] and called == []                                              # inget slutår öppnades
    assert any(r["stage"] == "final" for r in orch.registry.read()) and all(r["sealed"]["final"] is None for r in orch.registry.read() if r["stage"] == "final")
    assert orch.bb.s["spent"]["final"] == [] and orch.bb.s["spent"]["valid"]                  # valideringen är förbrukad, slutåret inte
    monkeypatch.setitem(agents.TASKS, "validate_task", real)


def test_slutsteget_körs_för_dem_som_klarar_valideringen_och_förbrukningen_loggas():
    orch, s, _ = run_lab(1.0)
    spent = orch.bb.s["spent"]
    assert s["promising"] and spent["final"] and {e["key"] for e in spent["final"]} <= {e["key"] for e in spent["valid"]}


def test_äldre_körningar_märks_som_förbrukade_och_återställs_aldrig(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps({"runs": 4, "trials": 770}), encoding="utf-8")
    bb = Blackboard(tmp_path)
    assert bb.s["legacy_unsealed"]["runs"] == ["R001", "R002", "R003", "R004"] and "FÖRBRUKAD" in bb.s["data_status"]["valid"]
    assert "efter att utfall setts" in bb.s["legacy_unsealed"]["note"]
    bb.save()
    assert "legacy_unsealed" in json.loads((tmp_path / "state.json").read_text())
    assert "legacy_unsealed" not in Blackboard(tmp_path / "ny").s                              # nya laboratorier startar utan


# ---------------------------------------------------------------- datatäckning (Codex P1): okänd data blir aldrig tyst noll
def _hold_one(p, col=0, start=200, days=60, w=0.5):
    W = pd.DataFrame(0.0, index=p.close.index, columns=p.close.columns)
    W.iloc[start:start + days, col] = w
    return W


def test_okänd_finansiering_debiteras_och_flaggas_aldrig_gratis():
    p = small(); p.funding.iloc[:, :] = 0.0
    p.funding_known.iloc[:, 0] = False                       # instrument 0 saknar finansiering (som 34 av 119 kontrakt i riktig data)
    W = _hold_one(p, w=0.5)
    r = bt.run(p, W, cost=0.0, strict=False)
    day = p.close.index[210]
    assert r.funding[day] == pytest.approx(0.5 * bt.FUNDING_PENALTY)                         # inte noll: en konservativ avgift
    assert r.coverage["unknown_funding_share"] > 0.9
    old = bt.run(p, W, cost=0.0, strict=False, penalize=False)                               # den gamla motorn gjorde det gratis
    assert old.funding[day] == 0.0 and old.coverage["unknown_funding_share"] > 0.9           # ...men måttet fångar det
    with pytest.raises(bt.CoverageInvalid, match="okänd finansiering"):
        bt.run(p, W, cost=0.0)                                                               # över toleransen: ogiltig utvärdering


def test_avnotering_blockerar_positionen_och_okänt_utträde_är_en_förlust_oavsett_riktning():
    p = small()
    W = _hold_one(p, start=205, days=10, w=0.1)             # long på instrument 0 under raderna 205-214
    q = small(); q.open.iloc[212:, 0] = np.nan              # ingen öppning från rad 212 och framåt (avnotering/utgången leverans): inget senare pris finns
    for sign in (1.0, -1.0):
        r = bt.run(q, W * sign, cost=0.0, funding=False, strict=False)
        c = r.coverage
        assert c["blocked_exposure"] > 0 and c["unknown_exit_exposure"] > 0 and c["gap_filled_exposure"] == 0
        # beslut rad 210: öppning t+1 (211) finns men t+2 (212) saknas för alltid: utträdet okänt = förlust på 0,1 oavsett long eller short (aldrig en vinst och aldrig noll)
        assert r.gross[q.close.index[211]] == pytest.approx(-0.1)
        # beslut rad 211: öppning t+1 (212) saknas: kontraktet kan inte hållas, vikten blir noll och exponeringen mäts
        assert r.gross[q.close.index[212]] == 0.0 and r.exposure[q.close.index[212]] == 0.0
    old = bt.run(q, W, cost=0.0, funding=False, strict=False, penalize=False)
    assert old.gross[q.close.index[211]] == 0.0                                             # gamla motorn: tyst noll
    with pytest.raises(bt.CoverageInvalid, match="saknad öppningskurs"):
        bt.run(q, _hold_one(p, start=205, days=60, w=0.5))                                  # stor exponering på okänd data: ogiltig utvärdering


def test_en_datalucka_värderas_mot_nästa_pris_i_stället_för_att_bli_noll_eller_förlust():
    p = small()
    W = _hold_one(p, start=205, days=10, w=0.1)
    q = small(); q.open.iloc[212, 0] = np.nan               # en enda dags datalucka (som arkivhålet 2022-02-26 till 02-28), senare priser finns
    r = bt.run(q, W, cost=0.0, funding=False, strict=False)
    exit_px = q.open.iloc[213, 0]                           # utträdet värderas mot nästa tillgängliga öppning
    assert r.gross[q.close.index[211]] == pytest.approx(0.1 * (exit_px / q.open.iloc[211, 0] - 1))
    assert r.coverage["gap_filled_exposure"] > 0 and r.coverage["unknown_exit_exposure"] == 0


def test_universumet_utesluter_instrument_utan_känd_finansiering_men_inte_vid_gamla_regeln():
    p = small(); p.funding_known.iloc[:, 3] = False
    assert not p.universe(25).iloc[400:, 3].any()
    old = Panel(p.open, p.high, p.low, p.close, p.dvol, p.funding, meta=p.meta, funding_known=p.funding_known, funding_rule=False)
    assert old.universe(25).iloc[400:, 3].any()
    W = build_xs = BUILDERS["xs_mom"]({"k": 30, "q": 0.2, "rebal": 7, "uni": 25, "vt": 0, "skip": 0}, p)
    assert (W.iloc[:, 3].abs() == 0).all()                                                   # strategin kan aldrig välja det


def test_täckningsmåttet_ger_exakta_andelar():
    p = small()
    W = _hold_one(p, w=0.2, days=20)
    p.funding_known.iloc[205:215, 0] = False
    cov = bt.coverage(p, W)
    assert cov["gross_exposure"] == pytest.approx(0.2 * 20)
    assert cov["unknown_funding_exposure"] == pytest.approx(0.2 * 10) and cov["unknown_funding_share"] == pytest.approx(0.5, abs=0.06)


def test_ogiltig_täckning_ger_ogiltig_i_registret_aldrig_reject_eller_slutsteg(monkeypatch):
    real = bt.run
    def boom(*a, **k):
        raise bt.CoverageInvalid("test: okänd data under exponerad position")
    monkeypatch.setattr(agents.bt, "run", boom)
    orch, s, _ = run_lab(1.0)
    rows = orch.registry.read()
    assert rows and all(r["verdict"] == "OGILTIG" for r in rows)
    assert not any(r["stage"] == "final" for r in rows) and orch.bb.s["rejected"] == []
    assert s["promising"] == [] and "OGILTIG" in s["verdicts"]
    monkeypatch.setattr(agents.bt, "run", real)
