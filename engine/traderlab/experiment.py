"""Kör ett registrerat experiment och sparar resultatet. Vägrar köra oregistrerade hypoteser."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from . import backtest, stats
from .costs import ZERO, CostModel
from .registry import require_registered
from .report import summarize

Strategy = Callable[[pd.DataFrame], pd.Series]
RESULTS = Path("research/results")


def random_label_control(bars: pd.DataFrame, seed: int = 0) -> float:
    """Slumpade positioner utan kostnader. t-värdet ska ligga nära noll (granska-backtest).

    Ett stort värde här betyder att motorn eller datan läcker information.
    """
    rng = np.random.default_rng(seed)
    target = pd.Series(rng.choice([-1.0, 0.0, 1.0], len(bars)), index=bars.index)
    res = backtest.run(bars, target, ZERO)
    return summarize(res, attempts=1, seed=seed).t_daily_nw


def _curve(res: backtest.BacktestResult, bars: pd.DataFrame, points: int = 300) -> dict:
    """Kurva för appen: strategin och köp-och-behåll, nedsamplade till högst `points` punkter."""
    eq = res.equity
    bh = bars["open"].shift(-1).reindex(eq.index) / bars["open"].iloc[1]
    step = max(1, -(-len(eq) // points))  # avrunda uppåt, så det blir högst points+1 punkter
    sel = list(range(0, len(eq), step))
    if sel[-1] != len(eq) - 1:
        sel.append(len(eq) - 1)
    return {"t": [eq.index[i].isoformat() for i in sel],
            "strategy": [round(float(eq.iloc[i]) * 100, 4) for i in sel],
            "buy_and_hold": [round(float(bh.iloc[i]) * 100, 4) if pd.notna(bh.iloc[i]) else None for i in sel]}


def _trades(res: backtest.BacktestResult, last: int = 50) -> list[dict]:
    out = []
    for t in res.trades[-last:]:
        out.append({"entry_time": t.entry_time.isoformat(), "exit_time": t.exit_time.isoformat() if t.exit_time is not None else None,
                    "side": t.side, "size": t.size, "entry_price": t.entry_price, "exit_price": t.exit_price,
                    "gross": t.gross_pnl / t.equity_at_entry, "costs": t.costs / t.equity_at_entry,
                    "funding": t.funding / t.equity_at_entry, "net": t.net_return, "liquidated": t.liquidated})
    return out


def _baseline(bars: pd.DataFrame, costs: CostModel, attempts: int) -> dict:
    """Köp-och-behåll på samma staplar och med samma kostnader. Det alla strategier måste slå."""
    res = backtest.run(bars, pd.Series(1.0, index=bars.index), costs)
    s = summarize(res, attempts).to_dict()
    return {k: s[k] for k in ("total_return", "max_drawdown", "sharpe", "t_daily_nw")}


def _daily_open_returns(bars: pd.DataFrame) -> pd.Series:
    """Avkastning per dag från öppning till öppning, som backtestets egen kurva."""
    r = (bars["open"].shift(-1) / bars["open"] - 1).dropna()
    return stats.daily_returns(r)


def benchmark_stats(res: backtest.BacktestResult, benchmark: pd.DataFrame, name: str) -> dict:
    """Beta och korrelation mot ett jämförelseindex (BTC), på dagsavkastning. Spår C kräver |beta| <= 0,2."""
    strat = stats.daily_returns(res.bar_returns)
    bench = _daily_open_returns(benchmark)
    both = pd.concat([strat, bench], axis=1, join="inner").dropna()
    both.columns = ["s", "b"]
    out = {"name": name, "days": len(both), "beta": None, "correlation": None}
    if len(both) >= 30 and both["b"].var() > 0:
        out["beta"] = float(both["s"].cov(both["b"]) / both["b"].var())
        if both["s"].std() > 0:
            out["correlation"] = float(both["s"].corr(both["b"]))
    return out


def run_experiment(hypothesis_id: str, repo: Path, bars: pd.DataFrame, strategy: Strategy,
                   costs: CostModel, *, market: str, interval: str, leverage: float = 1.0,
                   funding: pd.Series | None = None, note: str = "", track: str = "A",
                   benchmark: pd.DataFrame | None = None, benchmark_name: str = "",
                   baseline_bars: pd.DataFrame | None = None, baseline_costs: CostModel | None = None) -> Path:
    """Kör med normala och stressade kostnader och sparar en JSON-fil som aldrig skrivs över.

    track: forskningsspåret (A slå marknaden, B lägre risk, C marknadsneutral).
    benchmark: staplar att räkna beta och korrelation mot (oftast BTC spot 1d).
    baseline_bars: staplar för köp-och-behåll om de inte är samma som bars (till exempel för säkrade rutor,
    där bars är en syntetisk serie och jämförelsen är spot).
    """
    reg = require_registered(hypothesis_id, repo)
    backtest.check_no_lookahead(strategy, bars)
    target = strategy(bars)
    normal = backtest.run(bars, target, costs, leverage=leverage, funding=funding)
    stressed = backtest.run(bars, target, costs.stressed(), leverage=leverage, funding=funding)
    base = bars if baseline_bars is None else baseline_bars.reindex(bars.index)
    out = {
        "hypothesis_id": hypothesis_id,
        "registry_commit": reg.registry_commit,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "market": market,
        "interval": interval,
        "period": [str(bars.index[0]), str(bars.index[-1])],
        "bars": len(bars),
        "leverage": leverage,
        "costs_bps_per_side": costs.per_side * 10_000,
        "summary": summarize(normal, reg.attempts).to_dict(),
        "summary_stressed_costs": summarize(stressed, reg.attempts).to_dict(),
        "random_label_t": random_label_control(bars),
        "baseline_buy_and_hold": _baseline(base, baseline_costs or costs, reg.attempts),
        "benchmark": benchmark_stats(normal, benchmark, benchmark_name) if benchmark is not None else None,
        "track": track,
        "curve": _curve(normal, base),
        "trades": _trades(normal),
        "trades_total": len(normal.trades),
        "position_now": float(normal.position.iloc[-1]) if len(normal.position) else 0.0,
        "note": note,
        "simulated": False,
    }
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = folder / f"{hypothesis_id}-{stamp}.json"
    if path.exists():
        raise FileExistsError(f"{path} finns redan. Resultat skrivs aldrig över.")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
