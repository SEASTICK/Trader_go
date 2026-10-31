"""Påhittade staplar för tester. Aldrig för beslut.

Allt här är slumpat med fast frö, så ett test ger samma svar varje gång.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .bars import interval_delta


def make_bars(n: int = 2000, interval: str = "4h", seed: int = 0, drift: float = 0.0,
              vol: float = 0.01, start: str = "2020-01-01", price: float = 100.0) -> pd.DataFrame:
    """Geometrisk slumpvandring. drift och vol är per stapel."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq=interval_delta(interval), tz="UTC")
    log_ret = rng.normal(drift - 0.5 * vol**2, vol, n)
    close = price * np.exp(np.cumsum(log_ret))
    open_ = np.empty(n)
    open_[0] = price
    open_[1:] = close[:-1]
    wiggle = np.abs(rng.normal(0, vol / 2, n))
    high = np.maximum(open_, close) * (1 + wiggle)
    low = np.minimum(open_, close) * (1 - wiggle)
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def from_closes(closes: list[float], interval: str = "4h", start: str = "2020-01-01") -> pd.DataFrame:
    """Enkla staplar där open = föregående close. Bra för handräknade tester."""
    closes = list(map(float, closes))
    idx = pd.date_range(start, periods=len(closes), freq=interval_delta(interval), tz="UTC")
    opens = [closes[0]] + closes[:-1]
    highs = [max(o, c) for o, c in zip(opens, closes)]
    lows = [min(o, c) for o, c in zip(opens, closes)]
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": 1.0}, index=idx)
