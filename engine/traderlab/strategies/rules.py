"""Regelbaserade strategier med ett gemensamt gränssnitt (Fas 1).

Varje strategi tar staplar och parametrar och returnerar Signals: målposition (-1, 0, 1) beräknad vid stängning,
samt valfritt stop-loss- och take-profit-avstånd i pris. Motorn fyller vid nästa stapels öppning.

Varje strategi har en version. Ändras logiken höjs versionen, och en ny version är en ny strategi (CLAUDE.md
regel 3). Ett körnings-id är namn@version#parameterhash, så samma id ger alltid samma signaler på samma data.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .. import indicators as ind


@dataclass(frozen=True)
class Signals:
    target: pd.Series
    stop_distance: pd.Series | None = None
    take_profit_distance: pd.Series | None = None


@dataclass(frozen=True)
class Param:
    kind: str            # "int" eller "float"
    low: float
    high: float
    step: float | None = None


@dataclass(frozen=True)
class StrategySpec:
    name: str
    version: str
    description: str
    fn: Callable[..., Signals]
    defaults: dict
    space: dict[str, Param] = field(default_factory=dict)
    # Villkor mellan parametrar (till exempel snabb < långsam). Optimeringen hoppar över ogiltiga kombinationer.
    valid: Callable[[dict], bool] = lambda p: True

    def run_id(self, params: dict) -> str:
        p = {**self.defaults, **params}
        h = hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:8]
        return f"{self.name}@{self.version}#{h}"

    def signals(self, bars: pd.DataFrame, params: dict | None = None) -> Signals:
        p = {**self.defaults, **(params or {})}
        if not self.valid(p):
            raise ValueError(f"Ogiltiga parametrar för {self.name}: {p}")
        return self.fn(bars, **p)


def hold(entry_long: pd.Series, exit_long: pd.Series, entry_short: pd.Series, exit_short: pd.Series,
         allow_short: bool = True) -> pd.Series:
    """Tillståndsmaskin: går in på en inträdessignal och ligger kvar tills utgångssignalen kommer."""
    el, xl = entry_long.fillna(False).to_numpy(bool), exit_long.fillna(False).to_numpy(bool)
    es, xs = entry_short.fillna(False).to_numpy(bool), exit_short.fillna(False).to_numpy(bool)
    out = np.zeros(len(el))
    state = 0.0
    for i in range(len(el)):
        if state > 0 and xl[i]:
            state = 0.0
        elif state < 0 and xs[i]:
            state = 0.0
        if state == 0.0:
            if el[i]:
                state = 1.0
            elif allow_short and es[i]:
                state = -1.0
        out[i] = state
    return pd.Series(out, index=entry_long.index)


def ema_adx_trend(bars, fast=50, slow=200, adx_n=14, adx_min=20.0, atr_n=14, stop_atr=3.0, allow_short=True) -> Signals:
    """Trendföljare: long när EMA fast > EMA slow och trenden är stark (ADX), ut när snitten korsar tillbaka."""
    c = bars["close"]
    ef, es = ind.ema(c, fast), ind.ema(c, slow)
    strong = ind.adx(bars, adx_n) >= adx_min
    up, down = ef > es, ef < es
    tgt = hold(up & strong, down, down & strong, up, allow_short)
    return Signals(tgt.where(es.notna(), 0.0), stop_atr * ind.atr(bars, atr_n))


def donchian_breakout(bars, entry_n=20, exit_n=10, atr_n=14, stop_atr=2.0, allow_short=True) -> Signals:
    """Utbrott: long när stängningen slår högsta high på entry_n staplar, ut under lägsta low på exit_n."""
    c = bars["close"]
    hi_e, lo_e = ind.donchian(bars, entry_n)
    hi_x, lo_x = ind.donchian(bars, exit_n)
    tgt = hold(c > hi_e, c < lo_x, c < lo_e, c > hi_x, allow_short)
    return Signals(tgt.where(hi_e.notna(), 0.0), stop_atr * ind.atr(bars, atr_n))


def bb_rsi_reversion(bars, bb_n=20, bb_k=2.0, rsi_n=14, rsi_low=30.0, atr_n=14, stop_atr=2.0, allow_short=True) -> Signals:
    """Återgång: long under nedre bandet med låg RSI, ut vid mittlinjen. Short spegelvänt (RSI över 100 - rsi_low)."""
    c = bars["close"]
    lo, mid, hi = ind.bollinger(c, bb_n, bb_k)
    r = ind.rsi(c, rsi_n)
    tgt = hold((c < lo) & (r < rsi_low), c >= mid, (c > hi) & (r > 100 - rsi_low), c <= mid, allow_short)
    return Signals(tgt.where(mid.notna(), 0.0), stop_atr * ind.atr(bars, atr_n))


def squeeze_breakout(bars, n=20, bb_k=2.0, kc_k=1.5, atr_n=14, stop_atr=2.0, allow_short=True) -> Signals:
    """Volatilitetskläm: när Bollingerbanden lämnar Keltnerkanalen efter en kläm, gå med riktningen. Ut vid mittlinjen."""
    c = bars["close"]
    bl, mid, bh = ind.bollinger(c, n, bb_k)
    kl, _, kh = ind.keltner(bars, n, kc_k)
    squeeze = (bh < kh) & (bl > kl)
    released = squeeze.shift(1, fill_value=False) & ~squeeze
    tgt = hold(released & (c > mid), c < mid, released & (c < mid), c > mid, allow_short)
    return Signals(tgt.where(kh.notna() & mid.notna(), 0.0), stop_atr * ind.atr(bars, atr_n))


SPECS: dict[str, StrategySpec] = {s.name: s for s in [
    StrategySpec("ema_adx_trend", "1.0.0", "EMA-trend med ADX-filter och ATR-stop", ema_adx_trend,
                 {"fast": 50, "slow": 200, "adx_n": 14, "adx_min": 20.0, "atr_n": 14, "stop_atr": 3.0},
                 {"fast": Param("int", 10, 100, 5), "slow": Param("int", 100, 300, 10),
                  "adx_min": Param("float", 10, 35, 1), "stop_atr": Param("float", 1.5, 6.0, 0.5)},
                 valid=lambda p: p["fast"] * 2 <= p["slow"]),
    StrategySpec("donchian_breakout", "1.0.0", "Donchian-utbrott med ATR-stop", donchian_breakout,
                 {"entry_n": 20, "exit_n": 10, "atr_n": 14, "stop_atr": 2.0},
                 {"entry_n": Param("int", 10, 100, 5), "exit_n": Param("int", 5, 50, 5),
                  "stop_atr": Param("float", 1.5, 6.0, 0.5)},
                 valid=lambda p: p["exit_n"] < p["entry_n"]),
    StrategySpec("bb_rsi_reversion", "1.0.0", "Bollinger + RSI återgång med ATR-stop", bb_rsi_reversion,
                 {"bb_n": 20, "bb_k": 2.0, "rsi_n": 14, "rsi_low": 30.0, "atr_n": 14, "stop_atr": 2.0},
                 {"bb_n": Param("int", 10, 50, 5), "bb_k": Param("float", 1.5, 3.0, 0.25),
                  "rsi_low": Param("float", 15, 40, 1), "stop_atr": Param("float", 1.5, 6.0, 0.5)}),
    StrategySpec("squeeze_breakout", "1.0.0", "Volatilitetskläm (Bollinger i Keltner) med ATR-stop", squeeze_breakout,
                 {"n": 20, "bb_k": 2.0, "kc_k": 1.5, "atr_n": 14, "stop_atr": 2.0},
                 {"n": Param("int", 10, 50, 5), "bb_k": Param("float", 1.5, 2.5, 0.25),
                  "kc_k": Param("float", 1.0, 2.5, 0.25), "stop_atr": Param("float", 1.5, 6.0, 0.5)}),
]}
