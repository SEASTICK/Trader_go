"""Kör en registrerad tvärsnittshypotes (research/xs-protokoll.md). Slutprovet 2025– läses aldrig in."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import portfolio, quality, stats, xs
from .costs import CostModel
from .data import binance
from .experiment import RESULTS, benchmark_stats
from .registry import require_registered

CANDIDATES = ["BTC", "ETH", "BCH", "XRP", "EOS", "LTC", "TRX", "ETC", "LINK", "XLM", "ADA", "XMR", "DASH", "ZEC",
              "XTZ", "BNB", "ATOM", "ONT", "IOTA", "BAT", "VET", "NEO", "QTUM", "IOST"]
START, HOLDOUT = "2020-01-01", "2025-01-01"
COSTS = CostModel(fee_bps=10, spread_bps=2, slippage_bps=5)


def universe(data_dir: Path) -> list[str]:
    """Regeln i protokollet: kandidater som har en månadsfil för 2020-01."""
    return [f"{c}USDT" for c in CANDIDATES
            if (data_dir / "raw/binance/um" / f"{c}USDT" / "1d" / f"{c}USDT-1d-2020-01.zip").exists()]


def load_panel(data_dir: Path, symbols: list[str]):
    lo, hi = pd.Timestamp(START, tz="UTC"), pd.Timestamp(HOLDOUT, tz="UTC")
    opens, closes, funding, dropped = {}, {}, {}, {}
    for s in symbols:
        b = binance.load("um", s, "1d", data_dir)
        b = b[(b.index >= lo) & (b.index < hi)]
        q = quality.check(b, "1d")
        if not q.ok:
            dropped[s] = "; ".join(q.problems)
            continue
        opens[s], closes[s] = b["open"], b["close"]
        try:
            f = binance.load_funding(s, data_dir)
            funding[s] = f[f.index < hi]
        except FileNotFoundError:
            funding[s] = pd.Series(dtype=float)
    return pd.DataFrame(opens), pd.DataFrame(closes), funding, dropped


def _stats(res: portfolio.PortfolioResult) -> dict:
    eq = res.equity
    daily = stats.daily_returns(res.bar_returns)
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    cagr = eq.iloc[-1] ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    downside = np.sqrt((np.minimum(daily, 0) ** 2).mean()) * np.sqrt(365)
    m = eq.resample("ME").last()
    monthly = (m / m.shift(1).fillna(eq.iloc[0]) - 1)
    return {"total_return": float(eq.iloc[-1] - 1), "cagr": float(cagr), "sharpe": float(stats.sharpe(daily)),
            "sortino": float(daily.mean() * 365 / downside) if downside > 0 else None,
            "max_drawdown": float(stats.max_drawdown(eq)), "turnover_per_year": float(res.turnover.sum() / years),
            "costs": res.total_costs, "funding": res.total_funding,
            "monthly_returns": {k.strftime("%Y-%m"): round(float(v), 6) for k, v in monthly.items()}}


def random_control(opens: pd.DataFrame, closes: pd.DataFrame, seed: int = 0) -> float:
    """Slumpade long/short-korgar samma söndagar, utan kostnader. t ska ligga nära noll."""
    rng = np.random.default_rng(seed)
    score = pd.DataFrame(rng.normal(size=closes.shape), index=closes.index, columns=closes.columns)
    days = xs.rebalance_days(closes.index)
    w = xs.long_short(score.loc[days], xs._eligible(closes).loc[days])
    res = portfolio.run(opens, w, CostModel(0, 0, 0))
    return float(stats.newey_west_t(stats.daily_returns(res.bar_returns)))


def run(hypothesis_id: str, kind: str, repo: Path, data_dir: Path | None = None) -> Path:
    reg = require_registered(hypothesis_id, repo)
    data_dir = data_dir or repo / "data"
    syms = universe(data_dir)
    opens, closes, funding, dropped = load_panel(data_dir, syms)
    assert opens.index.max() < pd.Timestamp(HOLDOUT, tz="UTC"), "Slutprovet får inte läsas in."
    if kind == "momentum":
        signal = lambda p: xs.momentum_weights(p["c"])
    elif kind == "carry":
        signal = lambda p: xs.carry_weights(p["c"], {k: v for k, v in p.items() if k != "c"})
    else:
        raise ValueError(kind)
    panel = {"c": closes, **{k: v for k, v in funding.items()}}
    portfolio.check_no_lookahead(signal, panel, [400, 900, 1500],
                                 known_until={k: pd.Timedelta(days=1) for k in funding})
    w = signal(panel)
    normal = portfolio.run(opens, w, COSTS, funding)
    stressed = portfolio.run(opens, w, COSTS.stressed(), funding)
    daily = stats.daily_returns(normal.bar_returns)
    t_req, t_nw = stats.t_krav(reg.attempts), stats.newey_west_t(daily)
    spot = binance.load("spot", "BTCUSDT", "1d", data_dir)
    spot = spot[(spot.index >= pd.Timestamp(START, tz="UTC")) & (spot.index < pd.Timestamp(HOLDOUT, tz="UTC"))]
    bench = benchmark_stats(normal, spot, "spot BTCUSDT 1d")
    bh = spot["open"].shift(-1) / spot["open"].iloc[0]
    s_normal, s_stress = _stats(normal), _stats(stressed)
    criteria = {"t_at_least_required": bool(t_nw >= t_req), "stressed_costs_positive": s_stress["total_return"] > 0,
                "beta_within_0_2": bench["beta"] is not None and abs(bench["beta"]) <= 0.2}
    live = w[(w != 0).any(axis=1)]
    out = {"hypothesis_id": hypothesis_id, "registry_commit": reg.registry_commit,
           "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "phase": "xs", "track": "C",
           "kind": kind, "universe": list(opens.columns), "dropped": dropped,
           "period": [str(opens.index[0].date()), str(opens.index[-1].date())], "rebalances": int(len(live)),
           "costs_bps_per_side": COSTS.per_side * 10_000, "attempts": reg.attempts,
           "t_daily_nw": t_nw, "t_required": t_req,
           "deflated_sharpe": stats.deflated_sharpe(daily.to_numpy(), max(reg.attempts, 1)),
           "sharpe_ci": list(stats.block_bootstrap_sharpe_ci(daily)),
           "summary": s_normal, "summary_stressed_costs": s_stress, "benchmark": bench,
           "baseline_btc_buy_and_hold": {"total_return": float(bh.dropna().iloc[-1] - 1)},
           "random_label_t": random_control(opens, closes),
           "criteria": criteria, "meets_all_criteria": all(criteria.values()),
           "curve": {"t": [d.isoformat() for d in normal.equity.index[::5]],
                     "strategy": [round(float(v) * 100, 4) for v in normal.equity.iloc[::5]],
                     "btc": [round(float(v) * 100, 4) if pd.notna(v) else None for v in bh.reindex(normal.equity.index).iloc[::5]]},
           "last_weights": {k: v for k, v in (live.iloc[-1] if len(live) else pd.Series(dtype=float)).items() if v != 0},
           "simulated": False}
    def clean(o):
        if isinstance(o, float) and not np.isfinite(o):
            return None
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, np.integer)):
            return clean(o.item())
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{hypothesis_id}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(clean(out), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path
