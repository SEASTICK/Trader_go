"""Kör alla rutor som har en registrerad hypotes, och exporterar resultaten till appen.

Valfritt per ruta: "period": {"start": "2020-01-01", "end": "2025-01-01"} (slut exkluderat), för att spara
en ren period till senare.

research/experiments.json kopplar en ruta i appen (E-01 ...) till hypotes, data och strategi:

{
  "E-01": {"hypothesis": "H-0001", "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
           "strategy": {"name": "ml", "params": {"horizon": 1}},
           "costs": {"fee_bps": 10, "spread_bps": 2, "slippage_bps": 5}, "leverage": 1}
}

Rutor utan rad här, eller vars hypotes inte är registrerad, hoppas över och förblir SIM i appen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import quality
from .costs import CostModel
from .data import binance
from .experiment import RESULTS, run_experiment
from .registry import NotRegisteredError
from .strategies.registry import build

PLAN = Path("research/experiments.json")
APP_RESULTS = Path("app/data/results.json")


@dataclass
class BatchReport:
    ran: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # ruta -> skäl


def load_plan(repo: Path) -> dict:
    p = repo / PLAN
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def run_all(repo: Path, data_dir: Path | None = None, loader=binance.load, only: list[str] | None = None) -> BatchReport:
    rep = BatchReport()
    data_dir = data_dir or repo / "data"
    for tile, spec in load_plan(repo).items():
        if only and tile not in only:
            continue
        try:
            bars = loader(spec.get("market", "spot"), spec["symbol"], spec["interval"], data_dir)
        except FileNotFoundError as exc:
            rep.skipped[tile] = f"ingen data: {exc}"
            continue
        period = spec.get("period") or {}
        if period.get("start"):
            bars = bars[bars.index >= pd.Timestamp(period["start"], tz="UTC")]
        if period.get("end"):
            bars = bars[bars.index < pd.Timestamp(period["end"], tz="UTC")]
        q = quality.check(bars, spec["interval"])
        if not q.ok:
            rep.skipped[tile] = "datakvalitet: " + "; ".join(q.problems)
            continue
        try:
            run_experiment(spec["hypothesis"], repo, bars, build(spec["strategy"]["name"], spec["strategy"].get("params"), spec.get("risk")),
                           CostModel(**spec.get("costs", {})), market=f'{spec.get("market", "spot")} {spec["symbol"]}',
                           interval=spec["interval"], leverage=spec.get("leverage", 1.0),
                           note=f"ruta {tile}" + (f"; datavarningar: {'; '.join(q.warnings)}" if q.warnings else ""))
            rep.ran.append(tile)
        except NotRegisteredError as exc:
            rep.skipped[tile] = f"inte registrerad: {exc}"
    return rep


def export_to_app(repo: Path) -> dict:
    """Skriver app/data/results.json med det senaste resultatet per ruta. Bara riktiga körningar."""
    plan = load_plan(repo)
    folder = repo / RESULTS
    out: dict[str, dict] = {}
    for tile, spec in plan.items():
        files = sorted(folder.glob(f'{spec["hypothesis"]}-*.json')) if folder.exists() else []
        if not files:
            continue
        r = json.loads(files[-1].read_text(encoding="utf-8"))
        s = r["summary"]
        out[tile] = {
            "source": "HISTORIK",
            "hypothesis": r["hypothesis_id"],
            "registry_commit": r["registry_commit"],
            "run_at": r["run_at"],
            "period": r["period"],
            "total_return": s["total_return"],
            "max_drawdown": s["max_drawdown"],
            "trades": s["trades"],
            "win_rate": s["win_rate"],
            "t": s["t_daily_nw"],
            "t_required": s["t_required"],
            "passes": s["passes"],
            "deflated_sharpe": s.get("deflated_sharpe"),
            "stressed_total_return": r["summary_stressed_costs"]["total_return"],
            "sharpe": s["sharpe"],
            "baseline": r.get("baseline_buy_and_hold"),
            "costs_bps_per_side": r["costs_bps_per_side"],
            "curve": r.get("curve"),
            "recent_trades": r.get("trades", [])[-20:],
            "position_now": r.get("position_now", 0.0),
            "result_file": files[-1].relative_to(repo).as_posix(),
        }
    path = repo / APP_RESULTS
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return out
