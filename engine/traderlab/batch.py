"""Kör alla rutor som har en registrerad hypotes, och exporterar resultaten till appen.

Valfritt per ruta: "funding": true laddar finansieringsräntan (terminer). Den dras då i backtestet (long betalar
positiv ränta) och skickas till strategin funding_contrarian.

Valfritt per ruta: "period": {"start": "2020-01-01", "end": "2025-01-01"} (slut exkluderat), för att spara
en ren period till senare.

research/experiments.json kopplar en ruta i appen (E-01 ...) till hypotes, data och strategi:

{
  "E-01": {"hypothesis": "H-0001", "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
           "strategy": {"name": "ml", "params": {"horizon": 1}},
           "costs": {"fee_bps": 10, "spread_bps": 2, "slippage_bps": 5}, "leverage": 1}
}

Valfritt per ruta: "track": "A" | "B" | "C" (forskningsspår, standard A). Se research/tracks.md.

Valfritt per ruta: "benchmark": {"market": "spot", "symbol": "BTCUSDT", "interval": "1d"} (standard). Beta och
korrelation mot den räknas för varje körning.

Valfritt per ruta: "hedged": {"spot_symbol": "BTCUSDT"} på en terminsruta ("market": "um"). Då testas spot lång
och termin kort med samma belopp (se traderlab/hedge.py). Kostnaderna dubblas eftersom varje affär har två ben,
och köp-och-behåll räknas på spot.

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
from .hedge import hedged_bars, two_leg_costs
from .registry import NotRegisteredError
from .strategies.registry import NEEDS_FUNDING, build

DEFAULT_BENCHMARK = {"market": "spot", "symbol": "BTCUSDT", "interval": "1d"}

PLAN = Path("research/experiments.json")
APP_RESULTS = Path("app/data/results.json")


@dataclass
class BatchReport:
    ran: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # ruta -> skäl


def load_plan(repo: Path) -> dict:
    p = repo / PLAN
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def run_all(repo: Path, data_dir: Path | None = None, loader=binance.load, only: list[str] | None = None,
            funding_loader=binance.load_funding) -> BatchReport:
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

        def cut(b: pd.DataFrame) -> pd.DataFrame:
            if period.get("start"):
                b = b[b.index >= pd.Timestamp(period["start"], tz="UTC")]
            if period.get("end"):
                b = b[b.index < pd.Timestamp(period["end"], tz="UTC")]
            return b

        bars = cut(bars)
        q = quality.check(bars, spec["interval"])
        if not q.ok:
            rep.skipped[tile] = "datakvalitet: " + "; ".join(q.problems)
            continue
        costs = CostModel(**spec.get("costs", {}))
        baseline_bars = None
        baseline_costs = None
        market_name = f'{spec.get("market", "spot")} {spec["symbol"]}'
        if spec.get("hedged"):
            spot_symbol = spec["hedged"]["spot_symbol"]
            try:
                spot = cut(loader("spot", spot_symbol, spec["interval"], data_dir))
            except FileNotFoundError as exc:
                rep.skipped[tile] = f"ingen spotdata för säkringen: {exc}"
                continue
            qs = quality.check(spot, spec["interval"])
            if not qs.ok:
                rep.skipped[tile] = "datakvalitet spot: " + "; ".join(qs.problems)
                continue
            baseline_bars, baseline_costs = spot, costs
            bars = hedged_bars(bars, spot)
            costs = two_leg_costs(costs)
            market_name = f"spot {spot_symbol} lång + {market_name} kort (säkrad)"
        bench_spec = {**DEFAULT_BENCHMARK, **(spec.get("benchmark") or {})}
        try:
            benchmark = cut(loader(bench_spec["market"], bench_spec["symbol"], bench_spec["interval"], data_dir))
            bench_name = f'{bench_spec["market"]} {bench_spec["symbol"]} {bench_spec["interval"]}'
        except FileNotFoundError:
            benchmark, bench_name = None, ""
        funding = None
        params = dict(spec["strategy"].get("params") or {})
        if spec.get("funding"):
            try:
                funding = funding_loader(spec["symbol"], data_dir)
            except FileNotFoundError as exc:
                rep.skipped[tile] = f"ingen finansieringsränta: {exc}"
                continue
            if spec["strategy"]["name"] in NEEDS_FUNDING:
                params["funding"] = funding
        try:
            run_experiment(spec["hypothesis"], repo, bars, build(spec["strategy"]["name"], params, spec.get("risk")),
                           costs, market=market_name,
                           interval=spec["interval"], leverage=spec.get("leverage", 1.0), funding=funding,
                           note=f"ruta {tile}" + (f"; datavarningar: {'; '.join(q.warnings)}" if q.warnings else ""),
                           track=spec.get("track", "A"), benchmark=benchmark, benchmark_name=bench_name,
                           baseline_bars=baseline_bars, baseline_costs=baseline_costs)
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
            "track": r.get("track", spec.get("track", "A")),
            "beta": (r.get("benchmark") or {}).get("beta"),
            "correlation": (r.get("benchmark") or {}).get("correlation"),
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
