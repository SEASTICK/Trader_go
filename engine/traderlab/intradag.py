"""H-0027, H-0028 och H-0029: intradag på BTC-terminer. Reglerna står i research/intradag-protokoll.md.

Varje funktion tar staplar (index = öppningstid i UTC) och ger målposition per stapel, beräknad vid stapelns
stängning. Motorn fyller vid nästa stapels öppning. Inga parametrar söks; konstanterna är låsta i protokollet.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

H = pd.Timedelta(hours=1)
Q = pd.Timedelta(minutes=15)
NY = "America/New_York"

# Periodens slut avgörs av klockan, inte av datan (annars skulle look-ahead-kontrollen slå till).
LAST_OPEN_1H = pd.Timestamp("2024-12-31 23:00", tz="UTC")
LAST_OPEN_15M = pd.Timestamp("2024-12-31 23:45", tz="UTC")

# H-0027
WINDOW = 720
K_SIGMA = 3.0
HOLD_HOURS = 3


def _zero(bars: pd.DataFrame) -> pd.Series:
    return pd.Series(0.0, index=bars.index)


def extreme_hour_reversal(bars: pd.DataFrame, last_open: pd.Timestamp = LAST_OPEN_1H) -> pd.Series:
    """H-0027. Mot den första extrema timmen per UTC-dygn, i högst tre timmar och aldrig över 00:00 UTC."""
    target = _zero(bars)
    if len(bars) < WINDOW + 2:
        return target
    idx = bars.index
    close = bars["close"].astype(float)
    contiguous = pd.Series(idx, index=idx).diff() == H
    r = (close / close.shift(1) - 1).where(contiguous)
    # 720 föregående avkastningar, inte r_t själv; en lucka i fönstret ger NaN.
    sigma = r.shift(1).where(contiguous).rolling(WINDOW, min_periods=WINDOW).std(ddof=1)
    extreme = (r.abs() > K_SIGMA * sigma) & sigma.notna() & r.notna()
    day = idx.floor("D")
    first = extreme & (extreme.astype(int).groupby(day).cumsum() == 1)   # bara den första per dygn
    first_pos = np.flatnonzero(first.to_numpy())
    tvals = target.to_numpy()
    for i in first_pos:
        t0 = idx[i]
        d = t0.floor("D")
        stop = min(t0 + HOLD_HOURS * H, d + pd.Timedelta(hours=23))   # sista målstapeln öppnar före stop
        exit_at = min(t0 + (HOLD_HOURS + 1) * H, d + pd.Timedelta(hours=24))
        if stop <= t0 or exit_at > last_open:
            continue
        sign = -float(np.sign(r.iloc[i]))
        sel = (idx >= t0) & (idx < stop)
        tvals[sel] = sign
    return pd.Series(tvals, index=idx)


def us_open_range_breakout(bars: pd.DataFrame, last_open: pd.Timestamp = LAST_OPEN_15M) -> pd.Series:
    """H-0028. Utbrott ur 09:30–10:30 New York-tid före 12:00, ut vid 16:00 New York-tid. Vardagar."""
    target = _zero(bars)
    if bars.empty:
        return target
    local = bars.index.tz_convert(NY)
    minutes = local.hour * 60 + local.minute
    day = local.normalize()
    tvals = target.to_numpy()
    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    for d in day.unique():
        if d.weekday() >= 5:
            continue
        in_day = np.flatnonzero(day == d)
        m = minutes[in_day]
        rng = in_day[(m >= 570) & (m < 630)]          # 09:30, 09:45, 10:00, 10:15
        if len(rng) != 4:
            continue
        hi, lo = high[rng].max(), low[rng].min()
        exit_utc = (d.tz_localize(None) + pd.Timedelta(hours=16)).tz_localize(NY).tz_convert("UTC")
        if exit_utc > last_open:
            continue
        cands = in_day[(m >= 630) & (m <= 705)]       # öppnar 10:30–11:45, stänger senast 12:00
        for i in cands:
            s = 1.0 if close[i] > hi else -1.0 if close[i] < lo else 0.0
            if s == 0.0:
                continue
            hold = in_day[(m >= minutes[i]) & (m < 945)]   # till och med stapeln som öppnar 15:30
            tvals[hold] = s
            break
    return pd.Series(tvals, index=bars.index)


def early_late_momentum(bars: pd.DataFrame, last_open: pd.Timestamp = LAST_OPEN_1H) -> pd.Series:
    """H-0029. Tecknet på 00:00–06:00 UTC ger positionen 18:00–24:00 UTC samma dygn."""
    target = _zero(bars)
    if bars.empty:
        return target
    idx = bars.index
    hour = idx.hour
    day = idx.floor("D")
    tvals = target.to_numpy()
    opens = bars["open"].to_numpy(dtype=float)
    closes = bars["close"].to_numpy(dtype=float)
    for d in day.unique():
        in_day = np.flatnonzero(day == d)
        h = hour[in_day]
        early = in_day[h < 6]
        if len(early) != 6 or sorted(h[h < 6].tolist()) != list(range(6)):
            continue
        if d + pd.Timedelta(hours=24) > last_open:
            continue
        first = in_day[h == 0][0]
        last = in_day[h == 5][0]
        s = float(np.sign(closes[last] / opens[first] - 1))
        if s == 0.0:
            continue
        hold = in_day[(h >= 17) & (h < 23)]
        tvals[hold] = s
    return pd.Series(tvals, index=idx)


STRATEGIES = {
    "H-0027": ("1h", extreme_hour_reversal),
    "H-0028": ("15m", us_open_range_breakout),
    "H-0029": ("1h", early_late_momentum),
}
