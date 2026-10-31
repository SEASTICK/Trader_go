"""Strategier som kan anges med namn i research/experiments.json."""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from ..ml.walkforward import ml_strategy
from . import examples


def buy_and_hold(bars: pd.DataFrame) -> pd.Series:
    return pd.Series(1.0, index=bars.index)


FACTORIES: dict[str, Callable[..., Callable[[pd.DataFrame], pd.Series]]] = {
    "buy_and_hold": lambda **_: buy_and_hold,
    "ma_cross": lambda **p: (lambda b: examples.ma_cross(b, **p)),
    "zscore_reversion": lambda **p: (lambda b: examples.zscore_reversion(b, **p)),
    "ml": lambda **p: ml_strategy(**p),
}


def build(name: str, params: dict | None = None) -> Callable[[pd.DataFrame], pd.Series]:
    if name not in FACTORIES:
        raise ValueError(f"Okänd strategi: {name}. Tillåtna: {', '.join(FACTORIES)}")
    return FACTORIES[name](**(params or {}))
