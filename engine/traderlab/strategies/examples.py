"""Exempelstrategier för att prova motorn. Inga av dem är testade på riktig data.

Varje funktion tar staplar och returnerar målposition per stapel, beräknad vid stängning.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def ma_cross(bars: pd.DataFrame, fast: int = 20, slow: int = 50, allow_short: bool = True) -> pd.Series:
    """Long när snabbt medelvärde ligger över långsamt, annars short (eller platt)."""
    c = bars["close"]
    f, s = c.rolling(fast).mean(), c.rolling(slow).mean()
    pos = np.where(f > s, 1.0, -1.0 if allow_short else 0.0)
    return pd.Series(pos, index=bars.index).where(s.notna(), 0.0)


def zscore_reversion(bars: pd.DataFrame, window: int = 48, entry: float = 2.0) -> pd.Series:
    """Köp när priset ligger långt under sitt medel, sälj blankt när det ligger långt över."""
    c = bars["close"]
    z = (c - c.rolling(window).mean()) / c.rolling(window).std()
    pos = np.where(z < -entry, 1.0, np.where(z > entry, -1.0, 0.0))
    return pd.Series(pos, index=bars.index).where(z.notna(), 0.0)


def peeking(bars: pd.DataFrame) -> pd.Series:
    """FUSK: tittar på nästa stapel. Finns bara för att visa att kontrollen av look-ahead fungerar."""
    nxt = bars["close"].shift(-1)
    return pd.Series(np.where(nxt > bars["close"], 1.0, -1.0), index=bars.index)
