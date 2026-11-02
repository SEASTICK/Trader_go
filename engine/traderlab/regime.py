"""Marknadsläge för Fas 2 (H-0013), enligt research/fas2-protokoll.md. Ändras inte efter registreringen.

Ett läge per kalenderdag, satt vid dagens stängning (UTC):
  trend:       dagsstängningen mot sitt 200-dagarsmedel, över = upp, annars ned
  volatilitet: 30 dagars standardavvikelse för dagsavkastningen mot sin expanderande median (minst 60 värden),
               över = hög vol, annars låg vol
Samma etiketter och samma beräkning som metrics.regimes på en komplett serie, men `okänt` i stället för NaN.

Hysteres: ett nytt läge gäller först när det råa läget hållit i 3 sammanhängande kalenderdagar. `ned/hög vol` och
`okänt` gäller direkt. En 4h-stapel använder läget från dagen före stapelns dag, aldrig sin egen dag.

Luckor stängs, de hoppas inte över. En dag är stängd bara när alla dess staplar finns, vilket avgörs av dagens egna
staplar och inte av senare tidsstämplar. En saknad eller ofullständig dag har ingen stängning: den blir `okänt`
(som nollställer hysteresen), och fönstren över den (200 dagar, 30 dagar) räknas inte förrän de är hela igen.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .bars import INTERVALS

TREND_DAYS = 200
VOL_DAYS = 30
MEDIAN_MIN = 60
CONFIRM_DAYS = 3

UNKNOWN = "okänt"
LABELS = ("upp/hög vol", "upp/låg vol", "ned/hög vol", "ned/låg vol")
IMMEDIATE = frozenset({"ned/hög vol", UNKNOWN})

DAY = pd.Timedelta(days=1)
# Tidsramar som delar dygnet jämnt, så att varje dag har ett fast antal staplar från 00:00 UTC.
ALLOWED = {k: v for k, v in INTERVALS.items() if v <= DAY and DAY % v == pd.Timedelta(0)}


def _require_index(index, what: str) -> None:
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None or index.tz.utcoffset(None) != pd.Timedelta(0):
        raise ValueError(f"{what} måste ha ett DatetimeIndex i UTC")
    if index.has_duplicates:
        raise ValueError(f"{what} har dubbletter i tiden")
    if not index.is_monotonic_increasing:
        raise ValueError(f"{what} är inte sorterade i tid")


def validate(bars: pd.DataFrame, interval: str = "4h") -> pd.Timedelta:
    """Kastar ValueError om staplarna inte är en UTC-serie på tidsramens rutnät från 00:00. Luckor är tillåtna;
    de gör bara dagen ofullständig. Returnerar tidsramens längd."""
    if interval not in ALLOWED:
        raise ValueError(f"Tidsram {interval} stöds inte. Tillåtna: {', '.join(ALLOWED)}")
    step = ALLOWED[interval]
    _require_index(bars.index, "Staplarna")
    off = bars.index[(bars.index - bars.index.floor("D")) % step != pd.Timedelta(0)]
    if len(off):
        raise ValueError(f"{len(off)} staplar ligger inte på {interval}-rutnätet från 00:00 UTC, första {off[0]}")
    return step


def _validate_daily(daily: pd.Series) -> None:
    _require_index(daily.index, "Dagslägena")
    if (daily.index != daily.index.floor("D")).any():
        raise ValueError("Dagslägena måste ligga på 00:00 UTC")


def daily_closes(bars: pd.DataFrame, interval: str = "4h") -> pd.Series:
    """Stängningen för varje stängd dag. En dag är stängd när alla dess staplar finns och har en stängning."""
    step = validate(bars, interval)
    day = bars.index.floor("D")
    close = bars["close"].groupby(day)
    complete = (close.count() == DAY // step)
    return close.last()[complete]


def _calendar(bars: pd.DataFrame, closes: pd.Series) -> pd.DatetimeIndex:
    """Varje kalenderdag från datans första dag till den senaste stängda dagen."""
    if closes.empty:
        return pd.DatetimeIndex([], tz="UTC")
    return pd.date_range(bars.index[0].floor("D"), closes.index[-1], freq="D")


def raw_daily(bars: pd.DataFrame, interval: str = "4h") -> pd.Series:
    """Rått läge för varje kalenderdag, känt vid dagens stängning. `okänt` under uppvärmning och för dagar som
    saknas, är ofullständiga eller vars fönster når över en sådan dag."""
    closes = daily_closes(bars, interval)
    daily = closes.reindex(_calendar(bars, closes))
    sma = daily.rolling(TREND_DAYS, min_periods=TREND_DAYS).mean()
    vol = daily.pct_change(fill_method=None).rolling(VOL_DAYS, min_periods=VOL_DAYS).std()
    median = vol.expanding(min_periods=MEDIAN_MIN).median()
    trend = np.where(daily > sma, "upp", "ned")
    level = np.where(vol > median, "hög vol", "låg vol")
    label = pd.Series(trend, index=daily.index, dtype=object) + "/" + pd.Series(level, index=daily.index, dtype=object)
    known = daily.notna() & sma.notna() & vol.notna() & median.notna()
    return label.where(known, UNKNOWN).rename("regime")


def with_hysteresis(raw: pd.Series, confirm_days: int = CONFIRM_DAYS) -> pd.Series:
    """Gällande läge per kalenderdag. Dagar som saknas i `raw` fylls med `okänt`, så en bekräftelse kan aldrig
    räknas över en lucka. Startar i `okänt`; varje dag beror bara på den dagen och dagarna före."""
    _validate_daily(raw)
    if len(raw):
        raw = raw.reindex(pd.date_range(raw.index[0], raw.index[-1], freq="D"), fill_value=UNKNOWN)
    state, run_label, run = UNKNOWN, None, 0
    out = []
    for label in raw:
        run = run + 1 if label == run_label else 1
        run_label = label
        if label in IMMEDIATE or run >= confirm_days:
            state = label
        out.append(state)
    return pd.Series(out, index=raw.index, name=raw.name, dtype=object)


def daily(bars: pd.DataFrame, interval: str = "4h") -> pd.Series:
    """Gällande läge per kalenderdag (rått läge med hysteres)."""
    return with_hysteresis(raw_daily(bars, interval))


def per_bar(bars: pd.DataFrame, effective: pd.Series | None = None, interval: str = "4h") -> pd.Series:
    """Läget för varje stapel: det gällande läget för kalenderdagen före stapelns dag. Finns den dagen inte i
    `effective` blir stapeln `okänt`; ett äldre läge förs aldrig vidare över en lucka."""
    validate(bars, interval)
    if effective is None:
        effective = daily(bars, interval)
    else:
        _validate_daily(effective)
    prev = effective.reindex(bars.index.floor("D") - DAY)
    return pd.Series(prev.fillna(UNKNOWN).to_numpy(dtype=object), index=bars.index, name="regime")


def current(bars: pd.DataFrame, interval: str = "4h") -> str:
    """Läget som gäller för staplarna dagen efter den senaste stängda dagen."""
    effective = daily(bars, interval)
    return str(effective.iloc[-1]) if len(effective) else UNKNOWN
