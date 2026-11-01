"""Fullständig statistik för ett backtest (Fas 1). Kompletterar report.summarize, som har t-värden och
Deflated Sharpe för beslut. Allt räknas efter kostnader."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import stats
from .backtest import BacktestResult


def _f(x) -> float | None:
    x = float(x)
    return x if np.isfinite(x) else None


def drawdown_curve(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1


def monthly_returns(equity: pd.Series) -> dict[str, float]:
    m = equity.resample("ME").last()
    r = m.pct_change()
    r.iloc[0] = m.iloc[0] / equity.iloc[0] - 1 if len(m) else np.nan
    return {k.strftime("%Y-%m"): round(float(v), 6) for k, v in r.items() if np.isfinite(v)}


def regimes(bars: pd.DataFrame, n_days: int = 200) -> pd.Series:
    """Marknadsregim per stapel, känd vid stapelns stängning: upp eller ned (dagsstängning mot 200-dagarsmedel)
    kombinerat med hög eller låg volatilitet (30 dagars volatilitet mot sin median hittills)."""
    daily = bars["close"].resample("1D").last().dropna()
    trend = np.where(daily > daily.rolling(n_days, min_periods=n_days).mean(), "upp", "ned")
    trend = pd.Series(trend, index=daily.index).where(daily.rolling(n_days, min_periods=n_days).mean().notna())
    vol = daily.pct_change().rolling(30, min_periods=30).std()
    hi = vol > vol.expanding(min_periods=60).median()
    lab = (trend + "/" + np.where(hi, "hög vol", "låg vol")).where(vol.expanding(min_periods=60).median().notna() & trend.notna())
    # Dagens regim blir känd vid dagens stängning; använd gårdagens för staplar under dagen.
    lab = lab.shift(1)
    return lab.reindex(bars.index.floor("D")).set_axis(bars.index)


def full_stats(res: BacktestResult, bars: pd.DataFrame | None = None, start_capital: float = 100_000.0) -> dict:
    eq = res.equity
    daily = stats.daily_returns(res.bar_returns)
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    total = float(eq.iloc[-1] - 1)
    cagr = (eq.iloc[-1]) ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    mdd = stats.max_drawdown(eq)
    neg = daily[daily < 0]
    downside = np.sqrt((np.minimum(daily, 0) ** 2).mean()) * np.sqrt(365)
    sortino = daily.mean() * 365 / downside if downside > 0 else np.nan
    closed = res.closed_trades
    r = np.array([t.net_return for t in closed]) if closed else np.array([])
    wins, losses = r[r > 0], r[r <= 0]
    pf = wins.sum() / -losses.sum() if losses.size and losses.sum() < 0 else (np.inf if wins.size else np.nan)
    reasons: dict[str, int] = {}
    for t in closed:
        reasons[t.exit_reason or "signal"] = reasons.get(t.exit_reason or "signal", 0) + 1
    out = {
        "start_capital": start_capital,
        "end_capital": round(start_capital * float(eq.iloc[-1]), 2),
        "net_return": total,
        "cagr": _f(cagr),
        "sharpe": _f(stats.sharpe(daily)),
        "sortino": _f(sortino),
        "max_drawdown": _f(mdd),
        "calmar": _f(cagr / -mdd) if mdd < 0 else None,
        "profit_factor": _f(pf) if np.isfinite(pf) else None,
        "win_rate": _f((r > 0).mean()) if r.size else None,
        "expectancy": _f(r.mean()) if r.size else None,
        "avg_win": _f(wins.mean()) if wins.size else None,
        "avg_loss": _f(losses.mean()) if losses.size else None,
        "trades": len(closed),
        "exit_reasons": reasons,
        "exposure": _f((res.position != 0).mean()),
        "costs": _f(res.total_costs),
        "funding": _f(res.total_funding),
        "monthly_returns": monthly_returns(eq),
    }
    if bars is not None:
        lab = regimes(bars).reindex(res.bar_returns.index)
        per = {}
        for name, grp in res.bar_returns.groupby(lab):
            d = stats.daily_returns(grp)
            per[name] = {"bars": int(len(grp)), "return": _f((1 + grp).prod() - 1), "sharpe": _f(stats.sharpe(d))}
        out["by_regime"] = per
    return out


def curves(res: BacktestResult, points: int = 500) -> dict:
    eq = res.equity
    dd = drawdown_curve(eq)
    step = max(1, -(-len(eq) // points))
    sel = list(range(0, len(eq), step))
    if sel[-1] != len(eq) - 1:
        sel.append(len(eq) - 1)
    return {"t": [eq.index[i].isoformat() for i in sel],
            "equity": [round(float(eq.iloc[i]), 6) for i in sel],
            "drawdown": [round(float(dd.iloc[i]), 6) for i in sel]}
