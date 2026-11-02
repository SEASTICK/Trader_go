"""Marknadsläge för Fas 2 (H-0013), enligt research/fas2-protokoll.md. Ändras inte efter registreringen.

Ett läge per dag, satt vid dagens stängning (UTC):
  trend:       dagsstängningen mot sitt 200-dagarsmedel, över = upp, annars ned
  volatilitet: 30 dagars standardavvikelse för dagsavkastningen mot sin expanderande median (minst 60 värden),
               över = hög vol, annars låg vol
Samma etiketter och samma beräkning som metrics.regimes, men `okänt` i stället för NaN.

Hysteres: ett nytt läge gäller först när det råa läget hållit i 3 dagar i rad. `ned/hög vol` och `okänt` gäller
direkt. En 4h-stapel använder läget från den senaste stängda dagen före stapelns dag, aldrig sin egen dag.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TREND_DAYS = 200
VOL_DAYS = 30
MEDIAN_MIN = 60
CONFIRM_DAYS = 3

UNKNOWN = "okänt"
LABELS = ("upp/hög vol", "upp/låg vol", "ned/hög vol", "ned/låg vol")
IMMEDIATE = frozenset({"ned/hög vol", UNKNOWN})

DAY = pd.Timedelta(days=1)


def _require_utc(index: pd.DatetimeIndex) -> None:
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None or index.tz.utcoffset(None) != pd.Timedelta(0):
        raise ValueError("Staplarna måste ha ett DatetimeIndex i UTC")
    if not index.is_monotonic_increasing or index.has_duplicates:
        raise ValueError("Staplarna måste vara sorterade och utan dubbletter")


def _step(index: pd.DatetimeIndex) -> pd.Timedelta:
    if len(index) < 2:
        raise ValueError("Minst två staplar behövs för att avgöra tidsramen")
    return pd.Timedelta(np.median(np.diff(index.asi8)), unit="ns")


def daily_closes(bars: pd.DataFrame) -> pd.Series:
    """Stängningen för varje **stängd** dag. En dag är stängd när datan når dagens slut, så en påbörjad sista dag
    räknas inte (dess stängning är inte känd än)."""
    _require_utc(bars.index)
    step = _step(bars.index)
    day = bars.index.floor("D")
    last = pd.Series(bars.index, index=bars.index).groupby(day).max()
    closed = last.index[(last + step).values >= (last.index + DAY).values]
    return bars["close"].groupby(day).last().loc[closed].dropna()


def raw_daily(bars: pd.DataFrame) -> pd.Series:
    """Rått läge per stängd dag, känt vid dagens stängning. `okänt` under uppvärmningen."""
    daily = daily_closes(bars)
    sma = daily.rolling(TREND_DAYS, min_periods=TREND_DAYS).mean()
    vol = daily.pct_change().rolling(VOL_DAYS, min_periods=VOL_DAYS).std()
    median = vol.expanding(min_periods=MEDIAN_MIN).median()
    trend = np.where(daily > sma, "upp", "ned")
    level = np.where(vol > median, "hög vol", "låg vol")
    label = pd.Series(trend, index=daily.index) + "/" + pd.Series(level, index=daily.index)
    return label.where(sma.notna() & median.notna(), UNKNOWN).rename("regime")


def with_hysteresis(raw: pd.Series, confirm_days: int = CONFIRM_DAYS) -> pd.Series:
    """Gällande läge per dag. Startar i `okänt`; varje dag beror bara på den dagen och dagarna före."""
    state, run_label, run = UNKNOWN, None, 0
    out = []
    for label in raw:
        run = run + 1 if label == run_label else 1
        run_label = label
        if label in IMMEDIATE or run >= confirm_days:
            state = label
        out.append(state)
    return pd.Series(out, index=raw.index, name=raw.name)


def daily(bars: pd.DataFrame) -> pd.Series:
    """Gällande läge per stängd dag (rått läge med hysteres)."""
    return with_hysteresis(raw_daily(bars))


def per_bar(bars: pd.DataFrame, effective: pd.Series | None = None) -> pd.Series:
    """Läget för varje stapel: det gällande läget från den senaste stängda dagen före stapelns dag."""
    effective = daily(bars) if effective is None else effective
    days = bars.index.floor("D")
    pos = effective.index.searchsorted(days, side="left") - 1
    values = np.where(pos >= 0, effective.to_numpy()[np.maximum(pos, 0)], UNKNOWN) if len(effective) \
        else np.full(len(bars), UNKNOWN, dtype=object)
    return pd.Series(values, index=bars.index, name="regime")


def current(bars: pd.DataFrame) -> str:
    """Läget som gäller för nästa stapel efter datan: den senaste stängda dagens gällande läge."""
    effective = daily(bars)
    return str(effective.iloc[-1]) if len(effective) else UNKNOWN
