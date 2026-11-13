"""Täckningsaudit av redan körda experiment: hur stor del av bruttoexponeringen vilade på okänd data?

Mäter, per kandidat och totalt, exponeringen (summa av |vikt| över alla dagar och instrument) som (a) saknade nästa öppningskurs (t+1 eller t+2) eller
(b) saknade känd finansiering under hållperioden. Körningarna R001-R004 fyllde båda med 0. Auditen läser bara det som redan är förbrukat och ändrar inga
experimentposter. Vikterna återskapas med den gamla universumregeln (`funding_rule=False, scope_rule=False`) och jämförs mot registrets discovery-Sharpe för att visa att
återskapandet är trogen.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from . import agents, backtest as bt
from .data import load_um_panel, period_slice
from .state import ExperimentRegistry
from .strategies import make_spec


def run_audit(repo: Path, root: Path) -> dict:
    panel = load_um_panel(repo / "data", cache=repo / "data" / "clean" / "agentlab-panel-v2.pkl")
    v1 = replace(panel, funding_rule=False, scope_rule=False, _cache={})                      # körningarna R001-R004: ingen datatäckningsregel
    agents.set_panel(v1, repo / "data" / "clean" / "agentlab-cache")
    rows, seen = [], {}
    for r in ExperimentRegistry(root / "experiments.jsonl").read():
        if r["stage"] in ("discovery", "final") and r["key"] not in seen and r["results"].get("discovery"):
            seen[r["key"]] = r
    out, tot = [], {"gross": 0.0, "mp": 0.0, "uf": 0.0, "any": 0.0, "blk": 0.0, "ex": 0.0, "gf": 0.0}
    repro_ok = 0
    for key, r in seen.items():
        spec = make_spec(r["family"], r["parameters"])
        if spec["key"] != key:
            continue
        with agents.use("final"):
            W = agents.weights(spec)
            res = bt.run(v1, W, strict=False, penalize=False)          # gamla motorn: okänd data blev noll
            pen = bt.run(v1, W, strict=False, penalize=True)           # samma vikter, okänd data debiterad konservativt
            cov = res.coverage
            Wf = W.reindex(index=v1.open.index, columns=v1.open.columns).fillna(0.0).abs()
            deliv = float(Wf[[c for c in Wf.columns if "_" in c]].values.sum() / max(Wf.values.sum(), 1e-12))   # leveranskontrakt (BTCUSDT_230331) behandlades som perpar
        sh = bt.sharpe(res.ret[period_slice(res.ret.index, "disc")])
        sh_pen = bt.sharpe(pen.ret[period_slice(pen.ret.index, "disc")])
        same = abs(sh - r["results"]["discovery"]["sharpe"]) < 0.02
        repro_ok += int(same)
        out.append({"key": key, "family": r["family"], "control": r["control"], "verdict_at_the_time": r["verdict"], "disc_sharpe_registry": r["results"]["discovery"]["sharpe"],
                    "disc_sharpe_reproduced": sh, "disc_sharpe_with_penalties": sh_pen, "delivery_contract_share": deliv, "reproduced": same, **{k: cov[k] for k in ("gross_exposure", "blocked_share", "gap_filled_share", "unknown_exit_share", "missing_price_share", "unknown_funding_share", "any_unknown_share",
                                                                                              "symbol_days_missing_price", "symbol_days_unknown_funding")}})
        g = cov["gross_exposure"]
        tot["gross"] += g; tot["mp"] += cov["blocked_exposure"] + cov["unknown_exit_exposure"]; tot["blk"] += cov["blocked_exposure"]; tot["gf"] += cov["gap_filled_exposure"]; tot["ex"] += cov["unknown_exit_exposure"]; tot["uf"] += cov["unknown_funding_exposure"]
        tot["any"] += cov["any_unknown_share"] * g
    real = [o for o in out if not o["control"]]
    dsh = [o["disc_sharpe_with_penalties"] - o["disc_sharpe_reproduced"] for o in out]
    summary = {"candidates_with_delivery_contract_exposure": sum(1 for o in out if o["delivery_contract_share"] > 0), "max_delivery_contract_share": max(o["delivery_contract_share"] for o in out),
               "mean_delivery_contract_share": float(np.mean([o["delivery_contract_share"] for o in out])), "disc_sharpe_change_with_penalties_mean": float(np.mean(dsh)), "disc_sharpe_change_with_penalties_min": float(np.min(dsh)), "disc_sharpe_change_with_penalties_max": float(np.max(dsh)),
               "candidates": len(out), "reproduced_disc_sharpe": repro_ok, "tolerance": bt.COVERAGE_TOL,
               "total_blocked_share": tot["blk"] / tot["gross"], "total_gap_filled_share": tot["gf"] / tot["gross"], "total_unknown_exit_share": tot["ex"] / tot["gross"], "total_missing_price_share": tot["mp"] / tot["gross"], "total_unknown_funding_share": tot["uf"] / tot["gross"], "total_any_unknown_share": tot["any"] / tot["gross"],
               "candidates_over_tolerance_price": sum(1 for o in out if o["missing_price_share"] > bt.COVERAGE_TOL),
               "candidates_over_tolerance_funding": sum(1 for o in out if o["unknown_funding_share"] > bt.COVERAGE_TOL),
               "candidates_over_tolerance_any": sum(1 for o in out if o["any_unknown_share"] > bt.COVERAGE_TOL),
               "tolerance_new": bt.COVERAGE_TOL, "funding_penalty_per_day": bt.FUNDING_PENALTY, "missing_price_loss": bt.MISSING_PRICE_LOSS, "max_unknown_funding_share": max(o["unknown_funding_share"] for o in out), "max_missing_price_share": max(o["missing_price_share"] for o in out),
               "universe_symbols": len(panel.symbols), "symbols_with_funding": int(panel.funding_known.any().sum()),
               "survivors": [o for o in out if o["verdict_at_the_time"] in ("PROMISING", "REJECT") and o["key"] in {k for k, r in seen.items() if r["stage"] == "final"}]}
    (root / "audits").mkdir(exist_ok=True)
    rep = {"note": "Audit av redan förbrukad data (R001-R004, hela perioden 2020-2024). Ändrar inga experimentposter.", "summary": summary, "per_candidate": out}
    (root / "audits" / "coverage-R001-R004.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    return summary
