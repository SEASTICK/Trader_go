"""Snabb dagsbacktest för portföljvikter. Beslut på stängningen av dag t, fyllning vid öppningen dag t+1, hålls till öppningen t+2.

Kostnader per sida (avgift + glidning) på omsättningen, finansieringsränta för perpar, hävstångstak. Inga framtida data i beräkningen.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import Panel, period_slice

COST_PER_SIDE = 0.0010          # 0,05 % avgift + 5 bp glidning, samma antagande som övriga projektet
LEV_CAP = 3.0


@dataclass
class BT:
    ret: pd.Series              # nettoavkastning per dag (index = dagen positionen hålls)
    gross: pd.Series            # före kostnader och finansiering
    cost: pd.Series
    funding: pd.Series
    turnover: pd.Series
    exposure: pd.Series         # bruttoexponering per dag


def run(panel: Panel, W: pd.DataFrame, *, cost: float = COST_PER_SIDE, funding: bool = True, lev_cap: float = LEV_CAP, delay: int = 0) -> BT:
    """`delay` > 0 fördröjer utförandet med så många dagar (kostnadsagentens utförandetest)."""
    W = W.reindex(index=panel.close.index, columns=panel.close.columns).fillna(0.0)
    if delay:
        W = W.shift(delay).fillna(0.0)
    g = W.abs().sum(axis=1)
    scale = (lev_cap / g).clip(upper=1.0).where(g > 0, 1.0)
    W = W.mul(scale, axis=0)
    pnl = (W * panel.fwd().fillna(0.0)).sum(axis=1)
    turn = W.diff().abs().sum(axis=1)
    turn.iloc[0] = W.iloc[0].abs().sum()
    c = turn * cost
    f = (W * panel.fwd_funding()).sum(axis=1) if funding else pd.Series(0.0, index=W.index)
    net = pnl - c - f
    # avkastning på dag t+1 (positionen hålls dag t+1): flytta ett steg
    sh = lambda s: s.shift(1)
    return BT(sh(net), sh(pnl), sh(c), sh(f), sh(turn), sh(W.abs().sum(axis=1)))


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    n = len(r)
    if n < 20 or r.std() == 0:
        return {"n": n, "sharpe": 0.0, "ann_ret": 0.0, "ann_vol": 0.0, "max_dd": 0.0, "hit": 0.0, "cvar5": 0.0, "skew": 0.0, "total": 0.0}
    eq = (1 + r).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    k = np.sort(r.values)[: max(1, int(0.05 * n))]
    return {"n": n, "sharpe": float(r.mean() / r.std() * np.sqrt(365)), "ann_ret": float(r.mean() * 365), "ann_vol": float(r.std() * np.sqrt(365)),
            "max_dd": dd, "hit": float((r > 0).mean()), "cvar5": float(k.mean()), "skew": float(r.skew()), "total": float(eq.iloc[-1] - 1)}


def by_period(r: pd.Series, names=("disc", "valid", "final")) -> dict:
    return {p: metrics(r[period_slice(r.index, p)]) for p in names}


def sharpe(r: pd.Series) -> float:
    return metrics(r)["sharpe"]


def baselines(panel: Panel) -> dict[str, pd.Series]:
    """Enkla jämförelser: köp-och-behåll BTC, lika viktad korg av de likvidaste, och 30-dagars tvärsnittsmomentum."""
    idx = panel.close.index
    btc = pd.DataFrame(0.0, index=idx, columns=panel.close.columns)
    if "BTCUSDT" in btc.columns:
        btc["BTCUSDT"] = 1.0
    uni = panel.universe(20)
    ew = uni.astype(float).div(uni.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return {"bh_btc": run(panel, btc, funding=True).ret, "ew_basket": run(panel, ew, funding=True).ret}
