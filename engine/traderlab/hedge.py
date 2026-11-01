"""Säkrad position: lång spot och kort terminskontrakt (perp) med samma belopp.

Priset tar då nästan ut sig. Det som blir kvar är skillnaden mellan termin och spot (basen) och
finansieringsräntan, som den korta terminssidan tar emot när den är positiv.

hedged_bars bygger en syntetisk prisserie X vars avkastning per stapel är r_perp - r_spot. En position
på -1 i X ger då r_spot - r_perp, alltså spot lång och termin kort, och backtestet räknar finansieringsräntan
som för en kort termin. Säkringen antas balanseras om vid varje stapel utan extra kostnad (en förenkling).
Varje affär har två ben, så kostnaderna dubblas med two_leg_costs.
"""
from __future__ import annotations

import pandas as pd

from .costs import CostModel


def hedged_bars(perp: pd.DataFrame, spot: pd.DataFrame, start: float = 100.0) -> pd.DataFrame:
    idx = perp.index.intersection(spot.index)
    if len(idx) < 2:
        raise ValueError("För få gemensamma staplar mellan termin och spot.")
    p, s = perp.loc[idx], spot.loc[idx]
    r = (p["open"].pct_change() - s["open"].pct_change()).fillna(0.0)
    x_open = start * (1 + r).cumprod()
    last = start * (1 + r).prod() * (1 + (p["close"].iloc[-1] / p["open"].iloc[-1]
                                         - s["close"].iloc[-1] / s["open"].iloc[-1]))
    x_close = x_open.shift(-1).fillna(last)
    out = pd.DataFrame({"open": x_open, "close": x_close}, index=idx)
    out["high"] = out[["open", "close"]].max(axis=1)
    out["low"] = out[["open", "close"]].min(axis=1)
    out["volume"] = p["volume"].astype(float)
    return out[["open", "high", "low", "close", "volume"]]


def two_leg_costs(c: CostModel) -> CostModel:
    return CostModel(fee_bps=2 * c.fee_bps, spread_bps=2 * c.spread_bps, slippage_bps=2 * c.slippage_bps)
