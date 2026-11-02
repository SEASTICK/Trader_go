"""Kör en registrerad Fas 1-hypotes: walk-forward på BTCUSDT-terminer 4h med finansieringsränta.

Protokollet står i research/fas1-protokoll.md och får inte ändras efter registreringen.
Slutprovet (2025-01-01 och framåt) läses aldrig in här.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest, metrics, optimize, stats
from .costs import CostModel
from .data import binance
from .experiment import RESULTS, benchmark_stats, random_label_control
from .registry import require_registered
from .strategies.rules import SPECS

DEV_START = "2020-01-01"
TEST_STARTS = ["2022-01-01", "2022-07-01", "2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"]
HOLDOUT_START = "2025-01-01"
COSTS = CostModel(fee_bps=10, spread_bps=2, slippage_bps=5)
N_TRIALS = 40
SEED = 0


def _stitch(spec, wf, bars, costs, funding):
    """Kör varje testfönster igen med fönstrets parametrar (ingen ny optimering), till exempel med stressade kostnader."""
    edges = [pd.Timestamp(t, tz="UTC") for t in TEST_STARTS] + [pd.Timestamp(HOLDOUT_START, tz="UTC")]
    rets, pos, trades, c, f = [], [], [], 0.0, 0.0
    for w, a, b in zip(wf.windows, edges[:-1], edges[1:]):
        res = optimize.evaluate(spec, w["params"], bars, a, b, costs, funding)
        keep = res.bar_returns.index >= a
        rets.append(res.bar_returns[keep]); pos.append(res.position[keep])
        trades += [t for t in res.trades if t.entry_time >= a]
        c += res.total_costs; f += res.total_funding
    r = pd.concat(rets)
    eq = (1 + r).cumprod()
    return backtest.BacktestResult(equity=eq, position=pd.concat(pos), trades=trades, total_costs=c, total_funding=f)


def run(hypothesis_id: str, strategy: str, repo: Path, data_dir: Path | None = None, n_trials: int = N_TRIALS) -> Path:
    reg = require_registered(hypothesis_id, repo)
    data_dir = data_dir or repo / "data"
    spec = SPECS[strategy]
    cut = pd.Timestamp(HOLDOUT_START, tz="UTC")
    bars = binance.load("um", "BTCUSDT", "4h", data_dir, start=pd.Timestamp(DEV_START, tz="UTC"), end=cut)
    bars = bars[(bars.index >= pd.Timestamp(DEV_START, tz="UTC")) & (bars.index < cut)]
    funding = binance.load_funding("BTCUSDT", data_dir, start=pd.Timestamp(DEV_START, tz="UTC"), end=cut)
    funding = funding[funding.index < cut]
    assert bars.index.max() < cut and funding.index.max() < cut, "Slutprovet får inte läsas in."

    backtest.check_no_lookahead(lambda b: spec.signals(b).target, bars)
    wf = optimize.walk_forward(spec, bars, DEV_START, TEST_STARTS, HOLDOUT_START, COSTS, funding, n_trials, SEED)
    normal = _stitch(spec, wf, bars, COSTS, funding)
    stressed = _stitch(spec, wf, bars, COSTS.stressed(), funding)

    oos_start = pd.Timestamp(TEST_STARTS[0], tz="UTC")
    oos_bars = bars[bars.index >= oos_start]
    bh = backtest.run(oos_bars, pd.Series(1.0, index=oos_bars.index), COSTS, funding=funding)
    daily = stats.daily_returns(normal.bar_returns)
    t_req = stats.t_krav(reg.attempts)
    t_nw = stats.newey_west_t(daily)
    bh_sharpe = stats.sharpe(stats.daily_returns(bh.bar_returns))
    spot1d = binance.load("spot", "BTCUSDT", "1d", data_dir, start=oos_start, end=cut)
    spot1d = spot1d[(spot1d.index >= oos_start) & (spot1d.index < cut)]
    bench = benchmark_stats(normal, spot1d, "spot BTCUSDT 1d")
    full = metrics.full_stats(normal, oos_bars)
    stressed_ret = float(stressed.equity.iloc[-1] - 1)
    criteria = {
        "t_at_least_required": bool(t_nw >= t_req),
        "stressed_costs_positive": stressed_ret > 0,
        "sharpe_above_buy_and_hold": bool(full["sharpe"] is not None and full["sharpe"] > bh_sharpe),
        "stability_at_least_half": wf.stability >= 0.5,
    }
    out = {
        "hypothesis_id": hypothesis_id, "registry_commit": reg.registry_commit,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "phase": "fas1", "track": "A", "strategy": spec.name, "strategy_version": spec.version,
        "final_run_id": spec.run_id(wf.final_params), "final_params": wf.final_params,
        "market": "um BTCUSDT (terminer, med finansieringsränta)", "interval": "4h",
        "development_period": [DEV_START, HOLDOUT_START], "out_of_sample": [TEST_STARTS[0], HOLDOUT_START],
        "holdout": "2025-01-01 och framåt, oläst",
        "costs_bps_per_side": COSTS.per_side * 10_000, "trials_per_optimization": n_trials, "trials_total": wf.trials,
        "seed": SEED, "windows": wf.windows, "stability": wf.stability,
        "t_daily_nw": t_nw, "t_required": t_req, "attempts": reg.attempts,
        "deflated_sharpe": stats.deflated_sharpe(daily.to_numpy(), max(reg.attempts, 1)),
        "stressed_total_return": stressed_ret,
        "baseline_buy_and_hold": {"total_return": float(bh.equity.iloc[-1] - 1), "sharpe": bh_sharpe,
                                  "max_drawdown": stats.max_drawdown(bh.equity)},
        "benchmark": bench, "random_label_t": random_label_control(oos_bars),
        "stats": full, "criteria": criteria, "meets_all_criteria": all(criteria.values()),
        "curves": metrics.curves(normal),
        "trades": [{"entry_time": t.entry_time.isoformat(), "exit_time": t.exit_time.isoformat() if t.exit_time is not None else None,
                    "side": t.side, "entry_price": t.entry_price, "exit_price": t.exit_price, "net": t.net_return,
                    "exit_reason": t.exit_reason} for t in normal.trades[-300:]],
        "simulated": False,
    }
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{hypothesis_id}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    if path.exists():
        raise FileExistsError(path)
    def clean(o):
        if isinstance(o, float) and not np.isfinite(o):
            return None
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, np.integer)):
            return clean(o.item())
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    path.write_text(json.dumps(clean(out), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path
