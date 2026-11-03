"""H-0017 signalmodul, mom-signal/1.0.0 (research/h0017-protokoll.md §4–§5).

Ren funktion av stängda 4H-kontraktsstaplar. Inget konto, band, order, avgift, funding eller risk här.

Tidsregler:
- Stapel med index t omfattar [t, t+4h); dess close är känd vid t+4h.
- Dag D är komplett bara med alla sex staplar 00, 04, 08, 12, 16, 20. Dagsclose C_D = close för 20-stapeln.
- Beslutet för dag D har decision_time = D+1 00:00 UTC. Nästa lager får fylla tidigast vid öppningen med samma
  tid (earliest_fill). Modulen läser aldrig open, high eller low, så öppningspriset kan inte påverka beslutet.
- Horisonter räknas i kalenderdagar, inte observationer. Saknade dagar ersätts aldrig.

Per dag D:
- s_h = 1 om C_D / C_(D-h) - 1 > 0, annars 0, för h = 7, 14, 28. s = medel av de tre.
- vol = std(ddof=1) av de 60 enkla dagsavkastningarna C_i / C_(i-1) - 1 för i = D-59..D (61 stängningar),
  gånger sqrt(365). cap = min(1, 0,10 / vol). w_target = s * cap.
- Otillgänglig dag: available = False, numeriska fält NaN och en uttrycklig orsak. Ingen ersättning med platt eller
  full vikt. I en bedömningsperiod är det OGILTIG_DATA för körlagret (protokollet §3, D13).

Felaktigt index eller pris ger ValueError i stället för att sorteras, rensas eller fyllas i smyg.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

VERSION = "mom-signal/1.0.0"
HORIZONS = (7, 14, 28)
VOL_RETURNS = 60          # 60 avkastningar kräver 61 stängningar
TARGET_VOL = 0.10
ANNUALIZATION = 365
BAR = pd.Timedelta(hours=4)
DAY_BARS = 6
LAST_BAR_HOUR = 20

# Orsaker när en dag är otillgänglig, i den ordning de prövas.
INCOMPLETE_DAY = "incomplete_day"   # dag D saknar någon av sina sex staplar (även en pågående sista dag)
WARMUP = "warmup"                   # för få kalenderdagar före D i indata
MISSING_DAY = "missing_day"         # en dag som behövs för horisonter eller volatilitet är ofullständig
INVALID_VOL = "invalid_vol"         # volatiliteten är inte ändlig och > 0

COLUMNS = ["decision_time", "earliest_fill", "close", "s7", "s14", "s28", "s", "vol", "cap", "w_target",
           "available", "reason", "version"]


def validate_bars(bars: pd.DataFrame) -> None:
    """Kontrollerar index och stängningspriser enligt kontraktet. Kastar ValueError, ändrar inget."""
    if "close" not in bars.columns:
        raise ValueError("Kolumnen close saknas.")
    idx = bars.index
    if not isinstance(idx, pd.DatetimeIndex):
        raise ValueError("Indexet måste vara tidsstämplar (DatetimeIndex).")
    if idx.tz is None or str(idx.tz) != "UTC":
        raise ValueError("Tidsstämplarna måste vara i UTC.")
    if idx.has_duplicates:
        raise ValueError("Dubbletter i indexet.")
    if not idx.is_monotonic_increasing:
        raise ValueError("Indexet är inte sorterat stigande.")
    off = idx - idx.floor("D")
    if ((off % BAR) != pd.Timedelta(0)).any():
        raise ValueError("Tidsstämpel ligger inte på en 4H-gräns (00, 04, ..., 20 UTC).")
    close = bars["close"].to_numpy(dtype=float)
    if not np.isfinite(close).all() or (close <= 0).any():
        raise ValueError("Stängningspriser måste vara ändliga och > 0.")


def daily_closes(bars: pd.DataFrame) -> pd.DataFrame:
    """Dagsclose per kalenderdag i indatans spann. close är NaN för en ofullständig dag."""
    validate_bars(bars)
    if bars.empty:
        return pd.DataFrame({"close": pd.Series(dtype=float), "complete": pd.Series(dtype=bool)},
                            index=pd.DatetimeIndex([], tz="UTC"))
    day = bars.index.floor("D")
    days = pd.date_range(day[0], day[-1], freq="D")
    count = pd.Series(1, index=day).groupby(level=0).sum().reindex(days, fill_value=0)
    last = bars["close"][bars.index.hour == LAST_BAR_HOUR]
    last.index = last.index.floor("D")
    complete = count == DAY_BARS
    close = last.reindex(days).where(complete)
    return pd.DataFrame({"close": close.astype(float), "complete": complete})


def signals(bars: pd.DataFrame) -> pd.DataFrame:
    """En rad per kalenderdag D med beslutet som blir känt vid D+1 00:00. Kolumner enligt COLUMNS."""
    daily = daily_closes(bars)
    c = daily["close"].to_numpy(dtype=float)
    n = len(c)
    need = max(max(HORIZONS), VOL_RETURNS)
    rows = []
    for i in range(n):
        row = dict.fromkeys(["s7", "s14", "s28", "s", "vol", "cap", "w_target"], math.nan)
        reason = None
        if not np.isfinite(c[i]):
            reason = INCOMPLETE_DAY
        elif i < need:
            reason = WARMUP
        else:
            window = c[i - VOL_RETURNS:i + 1]                 # 61 stängningar D-60..D
            lags = [c[i - h] for h in HORIZONS]
            if not (np.isfinite(window).all() and np.isfinite(lags).all()):
                reason = MISSING_DAY
            else:
                rets = window[1:] / window[:-1] - 1
                vol = float(np.std(rets, ddof=1)) * math.sqrt(ANNUALIZATION)
                sig = [1.0 if c[i] / lag - 1 > 0 else 0.0 for lag in lags]
                row.update(s7=sig[0], s14=sig[1], s28=sig[2], s=sum(sig) / len(sig), vol=vol)
                if math.isfinite(vol) and vol > 0:
                    row["cap"] = min(1.0, TARGET_VOL / vol)
                    row["w_target"] = row["s"] * row["cap"]
                else:
                    reason = INVALID_VOL
                    row.update(s7=math.nan, s14=math.nan, s28=math.nan, s=math.nan, vol=math.nan)
        rows.append({**row, "close": c[i], "available": reason is None, "reason": reason})
    out = pd.DataFrame(rows, index=daily.index)
    out["decision_time"] = daily.index + pd.Timedelta(days=1)
    out["earliest_fill"] = out["decision_time"]
    out["version"] = VERSION
    return out[COLUMNS]


def latest_decision(sig: pd.DataFrame, t) -> pd.Series:
    """Senaste dagsrad vars beslut är känt vid tiden t (decision_time <= t). KeyError om ingen finns."""
    t = pd.Timestamp(t)
    known = sig[sig["decision_time"] <= t]
    if known.empty:
        raise KeyError(f"Inget beslut känt vid {t}.")
    return known.iloc[-1]
