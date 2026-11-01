"""Strategier som använder finansieringsräntan på terminer.

Finansieringsräntan avräknas på bestämda tider (oftast var åttonde timme). Vid stängningen av en stapel
används bara avräkningar som skett till och med stapelns stängningstid.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _close_times(bars: pd.DataFrame) -> pd.DatetimeIndex:
    step = pd.Series(bars.index).diff().median()
    return bars.index + step


def last_known_funding(bars: pd.DataFrame, funding: pd.Series) -> pd.Series:
    """Senaste avräknade finansieringsränta som var känd vid varje stapels stängning."""
    f = funding.sort_index()
    f = f[~f.index.duplicated(keep="last")]
    closes = _close_times(bars)
    pos = f.index.searchsorted(closes, side="right") - 1
    vals = np.where(pos >= 0, f.to_numpy()[np.clip(pos, 0, None)], np.nan)
    return pd.Series(vals, index=bars.index, name="funding_known")


def funding_contrarian(bars: pd.DataFrame, funding: pd.Series, threshold: float = 0.0005) -> pd.Series:
    """Short när longsidan betalar minst `threshold` per avräkning, long när shortsidan gör det, annars platt."""
    f = last_known_funding(bars, funding)
    pos = np.where(f >= threshold, -1.0, np.where(f <= -threshold, 1.0, 0.0))
    return pd.Series(pos, index=bars.index).where(f.notna(), 0.0)


def funding_carry(bars: pd.DataFrame, funding: pd.Series, threshold: float = 0.0001) -> pd.Series:
    """Kort termin (-1) när longsidan betalar minst `threshold` per avräkning, annars platt.

    Tänkt för säkrade rutor ("hedged" i research/experiments.json), där -1 betyder spot lång och termin kort,
    så att positionen tar emot finansieringsräntan utan att vara exponerad mot priset.
    """
    f = last_known_funding(bars, funding)
    return pd.Series(np.where(f >= threshold, -1.0, 0.0), index=bars.index).where(f.notna(), 0.0)
