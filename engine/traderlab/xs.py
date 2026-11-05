"""Tvärsnittssignaler över många instrument (research/xs-protokoll.md). Inga parametrar optimeras.

Alla signaler använder bara data till och med stängningen av ombalanseringsdagen.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TOP = 5
MIN_ELIGIBLE = 10
MIN_HISTORY = 60


def rebalance_days(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Söndagar (UTC). Beslut vid stängning, fyllning vid måndagens öppning."""
    return index[index.dayofweek == 6]


def long_short(score: pd.DataFrame, eligible: pd.DataFrame, top: int = TOP, long_high: bool = True) -> pd.DataFrame:
    """Lika vikt: long de `top` bästa och short de `top` sämsta. Raden blir 0 om för få är valbara."""
    w = pd.DataFrame(0.0, index=score.index, columns=score.columns)
    for t in score.index:
        s = score.loc[t][eligible.loc[t]].dropna()
        if len(s) < max(MIN_ELIGIBLE, 2 * top):
            continue
        order = s.sort_values(ascending=not long_high, kind="mergesort")  # stabil sortering, samma utfall varje gång
        longs, shorts = order.index[:top], order.index[-top:]
        w.loc[t, longs] = 0.5 / top
        w.loc[t, shorts] = -0.5 / top
    return w


def _eligible(closes: pd.DataFrame) -> pd.DataFrame:
    hist = closes.notna().cumsum()
    return closes.notna() & (hist >= MIN_HISTORY)


def momentum_weights(closes: pd.DataFrame, lookback: int = 28, skip: int = 1) -> pd.DataFrame:
    """H-0014: avkastning från stängningen lookback+skip dagar före till stängningen skip dagar före."""
    days = rebalance_days(closes.index)
    score = closes.shift(skip) / closes.shift(skip + lookback) - 1
    return long_short(score.loc[days], _eligible(closes).loc[days], long_high=True)


def funding_score(index: pd.DatetimeIndex, funding: dict[str, pd.Series], days: int = 7) -> pd.DataFrame:
    """Medel av räntor avräknade under de senaste `days` dagarna, strikt före stängningen av dag t.

    En avräkning exakt vid stängningen (00:00 UTC) räknas inte: beslutet och fyllningen sker i samma ögonblick,
    så den räntan antas inte vara känd. Det försiktiga valet."""
    out = pd.DataFrame(np.nan, index=index, columns=list(funding))
    closes = index + pd.Timedelta(days=1)  # stängning av dagsstapeln
    for sym, f in funding.items():
        f = f.sort_index()
        f = f[~f.index.duplicated(keep="last")]
        cs = np.concatenate([[0.0], np.cumsum(f.to_numpy(dtype=float))])
        hi = f.index.searchsorted(closes, side="left")
        lo = f.index.searchsorted(closes - pd.Timedelta(days=days), side="left")
        cnt = hi - lo
        val = np.where(cnt > 0, (cs[hi] - cs[lo]) / np.maximum(cnt, 1), np.nan)
        # Avrunda: lika räntor (ofta exakt 0,01 %) ska ge exakt lika poäng, så att ordningen inte avgörs av
        # flyttalsbrus från hur lång historik som lästs in.
        out[sym] = np.round(val, 12)
    return out


def carry_weights(closes: pd.DataFrame, funding: dict[str, pd.Series], days: int = 7) -> pd.DataFrame:
    """H-0015: short högst finansieringsränta, long lägst."""
    rdays = rebalance_days(closes.index)
    score = funding_score(closes.index, {s: funding[s] for s in closes.columns if s in funding}, days)
    score = score.reindex(columns=closes.columns)
    return long_short(score.loc[rdays], _eligible(closes).loc[rdays], long_high=False)
