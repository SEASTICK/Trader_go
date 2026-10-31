"""Gemensamt format för staplar (OHLCV).

En stapel indexeras med sin **öppningstid i UTC**. Kolumner: open, high, low, close, volume.
"""
from __future__ import annotations

import pandas as pd

COLUMNS = ["open", "high", "low", "close", "volume"]

INTERVALS: dict[str, pd.Timedelta] = {
    "1m": pd.Timedelta(minutes=1),
    "5m": pd.Timedelta(minutes=5),
    "15m": pd.Timedelta(minutes=15),
    "1h": pd.Timedelta(hours=1),
    "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
}


def interval_delta(interval: str) -> pd.Timedelta:
    try:
        return INTERVALS[interval]
    except KeyError as exc:
        raise ValueError(f"Okänd tidsram: {interval}. Tillåtna: {', '.join(INTERVALS)}") from exc


def validate_schema(bars: pd.DataFrame) -> None:
    """Kastar ValueError om tabellen inte har rätt form. Säger inget om datakvalitet (se quality.py)."""
    missing = [c for c in COLUMNS if c not in bars.columns]
    if missing:
        raise ValueError(f"Kolumner saknas: {missing}")
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("Indexet måste vara tidsstämplar (DatetimeIndex).")
    if bars.index.tz is None or str(bars.index.tz) != "UTC":
        raise ValueError("Tidsstämplarna måste vara i UTC.")
