"""Riskskydd utanför strategin (skillen riskgranser). Strategin kan inte stänga av dem.

risk_overlay() tar en strategi och returnerar en ny strategi med:
- volatilitetsstyrd storlek: målvolatilitet / uppmätt volatilitet, med tak,
- nödstopp: platt om strategins egen nedgång från topp överstiger max_drawdown, och förblir platt,
- daglig förlustgräns: platt resten av dygnet (UTC) efter en dag sämre än -max_daily_loss.

Allt räknas med data till och med stapelns stängning. Nedgång och dagsresultat räknas på strategins
egen bruttoavkastning (före kostnader) från stängning till stängning, som en försiktig uppskattning.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

Strategy = Callable[[pd.DataFrame], pd.Series]


def risk_overlay(strategy: Strategy, target_vol: float | None = 0.02, vol_window: int = 48, max_scale: float = 1.0,
                 max_drawdown: float | None = 0.25, max_daily_loss: float | None = 0.05) -> Strategy:
    """target_vol: önskad volatilitet per stapel (till exempel 0,02 = 2 %). None stänger av storleksstyrningen."""

    def wrapped(bars: pd.DataFrame) -> pd.Series:
        raw = strategy(bars).reindex(bars.index).astype(float).fillna(0.0).clip(-1, 1)
        c = bars["close"].astype(float)
        r = c.pct_change().fillna(0.0).to_numpy()
        if target_vol is not None:
            vol = c.pct_change().rolling(vol_window).std().to_numpy()
            scale = np.where(np.isfinite(vol) & (vol > 0), np.minimum(max_scale, target_vol / np.where(vol > 0, vol, 1)), 0.0)
        else:
            scale = np.ones(len(c))
        desired = raw.to_numpy() * scale
        out = np.zeros(len(c))
        eq, peak, killed = 1.0, 1.0, False
        day, day_start, day_locked = None, 1.0, False
        held = 0.0  # position som hölls under stapeln (beslutad vid förra stängningen)
        days = bars.index.floor("D")
        for i in range(len(c)):
            eq *= 1 + held * r[i]          # resultat för stapel i, känt vid dess stängning
            peak = max(peak, eq)
            if days[i] != day:
                day, day_start, day_locked = days[i], eq / (1 + held * r[i]) if (1 + held * r[i]) else eq, False
            if max_drawdown is not None and eq / peak - 1 <= -max_drawdown:
                killed = True
            if max_daily_loss is not None and eq / day_start - 1 <= -max_daily_loss:
                day_locked = True
            pos = 0.0 if (killed or day_locked) else float(np.clip(desired[i], -1, 1))
            out[i] = pos
            held = pos
        return pd.Series(out, index=bars.index, name="position")

    return wrapped
