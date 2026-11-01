"""Features som bara använder historik. Varje kolumn kontrolleras mot look-ahead i testerna."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)) / 100 - 0.5


def build_features(bars: pd.DataFrame, lags: tuple[int, ...] = (1, 3, 6, 12, 24),
                   vol_windows: tuple[int, ...] = (12, 48), calendar: bool = True) -> pd.DataFrame:
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    lr = np.log(c).diff()
    f = pd.DataFrame(index=bars.index)
    for k in lags:
        f[f"ret_{k}"] = np.log(c / c.shift(k))
    for w in vol_windows:
        f[f"vol_{w}"] = lr.rolling(w).std()
    f["trend_48"] = c / c.rolling(48).mean() - 1
    f["rsi_14"] = _rsi(c, 14)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    f["atr_14"] = tr.rolling(14).mean() / c
    hi, lo = h.rolling(24).max(), l.rolling(24).min()
    f["range_pos_24"] = (c - lo) / (hi - lo).replace(0, np.nan) - 0.5
    lv = np.log(v.replace(0, np.nan))
    f["volume_z_48"] = (lv - lv.rolling(48).mean()) / lv.rolling(48).std()
    if calendar:
        hour = bars.index.hour + bars.index.minute / 60
        f["hour_sin"] = np.sin(2 * np.pi * hour / 24)
        f["hour_cos"] = np.cos(2 * np.pi * hour / 24)
        dow = bars.index.dayofweek
        f["dow_sin"] = np.sin(2 * np.pi * dow / 7)
        f["dow_cos"] = np.cos(2 * np.pi * dow / 7)
    return f.replace([np.inf, -np.inf], np.nan)
