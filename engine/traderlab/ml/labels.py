"""Etiketter som speglar en riktig affär: beslut vid stängning av t, in vid öppning t+1, ut vid öppning t+1+h."""
from __future__ import annotations

import numpy as np
import pandas as pd


def forward_return(bars: pd.DataFrame, horizon: int = 1) -> pd.Series:
    o = bars["open"]
    return o.shift(-(1 + horizon)) / o.shift(-1) - 1


def label_end(bars: pd.DataFrame, horizon: int = 1) -> pd.Series:
    """Tidpunkten (stapelns öppningstid) då etiketten för t är känd: stängningen av stapel t+h.

    Utfallet för exemplet t är alltså känt vid stängningen av t+h. Här anges öppningstiden för t+h,
    och exemplet räknas som känt först efter att stapel t+h har stängt.
    """
    pos = np.arange(len(bars)) + horizon
    idx = bars.index
    out = pd.Series(pd.NaT, index=idx, dtype=f"datetime64[ns, {idx.tz}]")
    ok = pos < len(bars)
    out.iloc[np.where(ok)[0]] = idx[pos[ok]]
    return out


def direction(bars: pd.DataFrame, horizon: int = 1) -> pd.Series:
    r = forward_return(bars, horizon)
    return (r > 0).astype(float).where(r.notna())
