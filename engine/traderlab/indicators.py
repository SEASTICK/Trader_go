"""Tekniska indikatorer. Varje värde vid stapel i använder bara staplar t.o.m. i (ingen framtidsdata).

Formlerna följer de vanliga definitionerna (Wilder för RSI, ATR och ADX). Testerna jämför mot biblioteket `ta`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n, min_periods=n).mean()


def ema(x: pd.Series, n: int) -> pd.Series:
    """Exponentiellt medel med alpha = 2/(n+1). Tomt under de första n-1 staplarna."""
    out = x.ewm(span=n, adjust=False, min_periods=n).mean()
    return out


def _wilder(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def true_range(bars: pd.DataFrame) -> pd.Series:
    prev = bars["close"].shift(1)
    tr = pd.concat([bars["high"] - bars["low"], (bars["high"] - prev).abs(), (bars["low"] - prev).abs()], axis=1).max(axis=1)
    return tr.where(prev.notna(), bars["high"] - bars["low"])


def atr(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    return _wilder(true_range(bars), n)


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = _wilder(d.clip(lower=0), n)
    down = _wilder((-d).clip(lower=0), n)
    rs = up / down
    out = 100 - 100 / (1 + rs)
    return out.where(down != 0, 100.0).where(up.notna())


def adx(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l = bars["high"], bars["low"]
    up = h.diff()
    down = -l.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=bars.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=bars.index)
    tr = _wilder(true_range(bars), n)
    plus_di = 100 * _wilder(plus_dm, n) / tr
    minus_di = 100 * _wilder(minus_dm, n) / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return _wilder(dx, n)


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Nedre, mitt och övre band. Standardavvikelse för populationen (ddof=0), som i de flesta plattformar."""
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return mid - k * sd, mid, mid + k * sd


def donchian(bars: pd.DataFrame, n: int) -> tuple[pd.Series, pd.Series]:
    """Högsta high och lägsta low för de n FÖREGÅENDE staplarna (stapeln själv ingår inte)."""
    return bars["high"].rolling(n, min_periods=n).max().shift(1), bars["low"].rolling(n, min_periods=n).min().shift(1)


def keltner(bars: pd.DataFrame, n: int = 20, k: float = 1.5) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = ema(bars["close"], n)
    a = atr(bars, n)
    return mid - k * a, mid, mid + k * a
