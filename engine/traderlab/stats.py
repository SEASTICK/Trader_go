"""Statistik för att avgöra om ett resultat kan vara tur.

Kravet på t-värde följer skillen ny-hypotes: Bonferroni, ensidigt, aldrig under 2,0.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

_N = NormalDist()


def t_krav(n_attempts: int, alpha: float = 0.05, floor: float = 2.0) -> float:
    """Krav på t-värde efter n försök. Samma regel som appen (app/src/lib/stats.ts)."""
    if n_attempts < 1:
        return floor
    return max(floor, _N.inv_cdf(1 - alpha / n_attempts))


def t_stat(x: np.ndarray | pd.Series) -> float:
    """Vanligt t-värde för medelvärdet mot noll. Antar oberoende observationer."""
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    n = a.size
    if n < 2:
        return 0.0
    sd = a.std(ddof=1)
    return 0.0 if sd == 0 else float(a.mean() / (sd / math.sqrt(n)))


def newey_west_t(x: np.ndarray | pd.Series, lags: int | None = None) -> float:
    """t-värde med Newey-West-fel, som tål att dagar hänger ihop (autokorrelation)."""
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    n = a.size
    if n < 3:
        return 0.0
    if lags is None:
        lags = int(math.floor(4 * (n / 100) ** (2 / 9)))
    lags = max(0, min(lags, n - 1))
    e = a - a.mean()
    gamma0 = float(e @ e) / n
    var = gamma0
    for k in range(1, lags + 1):
        w = 1 - k / (lags + 1)
        gk = float(e[k:] @ e[:-k]) / n
        var += 2 * w * gk
    if var <= 0:
        return 0.0
    return float(a.mean() / math.sqrt(var / n))


def daily_returns(bar_returns: pd.Series) -> pd.Series:
    """Slår ihop avkastning per stapel till avkastning per dag (UTC), med ränta på ränta."""
    if bar_returns.empty:
        return bar_returns
    return (1 + bar_returns).groupby(bar_returns.index.floor("D")).prod() - 1


def sharpe(daily: pd.Series | np.ndarray, periods_per_year: int = 365) -> float:
    a = np.asarray(daily, dtype=float)
    a = a[np.isfinite(a)]
    if a.size < 2 or a.std(ddof=1) == 0:
        return 0.0
    return float(a.mean() / a.std(ddof=1) * math.sqrt(periods_per_year))


def block_bootstrap_sharpe_ci(daily: pd.Series | np.ndarray, block: int = 20, n_boot: int = 2000,
                              level: float = 0.95, seed: int = 0, periods_per_year: int = 365) -> tuple[float, float]:
    """Osäkerhetsintervall för Sharpe med block-bootstrap (behåller beroende inom block)."""
    a = np.asarray(daily, dtype=float)
    a = a[np.isfinite(a)]
    n = a.size
    if n < 2 * block:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / block)
    out = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n - block + 1, n_blocks)
        sample = np.concatenate([a[s:s + block] for s in starts])[:n]
        sd = sample.std(ddof=1)
        out[b] = 0.0 if sd == 0 else sample.mean() / sd * math.sqrt(periods_per_year)
    lo, hi = np.quantile(out, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)


def max_drawdown(equity: pd.Series | np.ndarray) -> float:
    """Största fall från topp, som negativt tal (till exempel -0.25 för -25 %)."""
    e = np.asarray(equity, dtype=float)
    if e.size == 0:
        return 0.0
    peak = np.maximum.accumulate(e)
    return float(np.min(e / peak - 1))
