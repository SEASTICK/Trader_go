"""Urvalsregel och walk-forward för Fas 2 (H-0013), enligt research/fas2-protokoll.md.

Protokollet ändras inte efter registreringen. Tolkningarna där protokollet inte är exakt står i
docs/fas2-walkforward-tolkningar.md (punkt 1–11 hänvisas nedan). Här finns ingen parameteroptimering:
kandidaterna har sina fasta standardparametrar, och det enda som väljs är spelboken.

Slutprovet (2025-01-01 och framåt) läses aldrig: indata som når dit avvisas innan något räknas, och
inläsningen från arkiven slutar före det.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import adaptive, backtest, regime, stats
from .costs import CostModel
from .data import binance

DEV_START = "2020-01-01"
TEST_STARTS = ["2022-01-01", "2022-07-01", "2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"]
HOLDOUT_START = "2025-01-01"
COSTS = CostModel(fee_bps=10, spread_bps=2, slippage_bps=5)
MIN_TRADES = 20
CHOOSABLE = ("ema_adx_trend", "bb_rsi_reversion")  # i den ordningen: vid exakt lika Sharpe vinner den första
WALK_FORWARD_VERSION = "h0013-walk-forward/1.0.0"


def _ts(t) -> pd.Timestamp:
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tz is None else t.tz_convert("UTC")


def check_development(bars: pd.DataFrame, funding: pd.Series) -> None:
    """Avvisar indata utanför utvecklingsperioden innan något räknas (punkt 11)."""
    lo, hi = _ts(DEV_START), _ts(HOLDOUT_START)
    for name, index in (("Staplarna", bars.index), ("Finansieringsräntan", funding.index)):
        if len(index) and index.max() >= hi:
            raise ValueError(f"{name} når slutprovet ({index.max()}); data från {HOLDOUT_START} får inte läsas i Fas 2")
        if len(index) and index.min() < lo:
            raise ValueError(f"{name} börjar före {DEV_START} ({index.min()}); ingen data före utvecklingsperioden används")


def load_development(data_dir: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Utvecklingsperiodens terminsstaplar och finansieringsränta. Arkiven för slutprovet öppnas aldrig."""
    lo, hi = _ts(DEV_START), _ts(HOLDOUT_START)
    bars = binance.load("um", "BTCUSDT", "4h", data_dir, start=lo, end=hi)
    funding = binance.load_funding("BTCUSDT", data_dir, start=lo, end=hi)
    check_development(bars, funding)
    return bars, funding


# Urvalsregeln

def _day_labels(bars: pd.DataFrame, effective: pd.Series) -> pd.Series:
    """Läget som styr varje dag (punkt 2): läget för dagens staplar, alltså gällande läge för dagen före."""
    per_bar = regime.per_bar(bars, effective)
    return per_bar.groupby(bars.index.floor("D")).first()


def regime_stats(bars: pd.DataFrame, funding: pd.Series, candidate: str, costs: CostModel = COSTS,
                 effective: pd.Series | None = None) -> dict[str, dict]:
    """Kandidaten i alla fyra lägen med handelsreglerna (punkt 1), bedömd per läge (punkt 2–4)."""
    effective = regime.daily(bars) if effective is None else effective
    book = adaptive.Playbook.of({label: candidate for label in regime.LABELS})
    sig = adaptive.signals(bars, book, effective=effective)
    res = backtest.run(bars, sig.target, costs, funding=funding, stop_distance=sig.stop_distance)
    daily = stats.daily_returns(res.bar_returns)
    day_label = _day_labels(bars, effective).reindex(daily.index)
    bar_label = regime.per_bar(bars, effective)
    entered = pd.Series([bar_label[t.entry_time] for t in res.trades], dtype=object)
    out = {}
    for label in regime.LABELS:
        d = daily[day_label == label]
        t = float(stats.newey_west_t(d)) if len(d) > 1 else float("nan")
        out[label] = {"days": int(len(d)), "trades": int((entered == label).sum()),
                      "sharpe": float(stats.sharpe(d)), "t": t if np.isfinite(t) else None}
    return out


def eligible(s: dict) -> bool:
    """Minst 20 affärer inledda i läget och t > 0 (punkt 5)."""
    return s["trades"] >= MIN_TRADES and s["t"] is not None and s["t"] > 0


def select(by_candidate: dict[str, dict[str, dict]]) -> adaptive.Playbook:
    """Bäst Sharpe bland valbara kandidater per läge; vid exakt lika Sharpe ema_adx_trend; annars platt."""
    choices = {}
    for label in regime.LABELS:
        best, best_sharpe = adaptive.FLAT, None
        for name in CHOOSABLE:
            s = by_candidate[name][label]
            if eligible(s) and (best_sharpe is None or s["sharpe"] > best_sharpe):
                best, best_sharpe = name, s["sharpe"]
        choices[label] = best
    return adaptive.Playbook.of(choices)


def train(bars: pd.DataFrame, funding: pd.Series, end, costs: CostModel = COSTS) -> dict:
    """Väljer spelboken på staplar från 2020-01-01 till `end`, exklusivt (punkt 6). Inget efter `end` läses."""
    lo, hi = _ts(DEV_START), _ts(end)
    tb = bars[(bars.index >= lo) & (bars.index < hi)]
    tf = funding[(funding.index >= lo) & (funding.index < hi)]
    effective = regime.daily(tb)
    by_candidate = {name: regime_stats(tb, tf, name, costs, effective) for name in CHOOSABLE}
    book = select(by_candidate)
    return {"train": [str(lo.date()), str(hi.date())], "playbook": book.to_dict(), "playbook_id": book.id,
            "candidates": by_candidate}


# Testfönster och ihopsättning

def evaluate_window(bars: pd.DataFrame, funding: pd.Series, book: adaptive.Playbook, start, end,
                    costs: CostModel = COSTS) -> tuple[backtest.BacktestResult, dict]:
    """Ett testfönster [start, end) med en fast spelbok (punkt 7–8).

    Indikatorer och lägen räknas från 2020-01-01. Spelboken gäller från fönstrets första stapel och positionen är
    platt före den; kandidaten måste ge en ny inträdessignal. Positionen stängs senast vid öppningen av fönstrets
    näst sista stapel. Avkastning och affärer räknas bara inom fönstret.
    """
    a, b = _ts(start), _ts(end)
    hist = bars[(bars.index >= _ts(DEV_START)) & (bars.index < b)]
    if (hist.index >= a).sum() < 3:
        raise ValueError(f"Testfönstret {a.date()}–{b.date()} har för få staplar")
    effective = regime.daily(hist)
    sig = adaptive.signals(hist, [(a, book)], effective=effective)
    target = sig.target.copy()
    target.iloc[-3:] = 0.0  # stäng vid öppningen av näst sista stapeln, platt därefter
    res = backtest.run(hist, target, costs, funding=funding[funding.index < b], stop_distance=sig.stop_distance)
    if any(t.entry_time < a for t in res.trades) or res.position[res.position.index < a].any():
        raise AssertionError("Position före testfönstret")
    keep = res.bar_returns.index >= a
    trades = [t for t in res.trades if t.entry_time >= a]
    window = backtest.BacktestResult(equity=(1 + res.bar_returns[keep]).cumprod(), position=res.position[keep],
                                     trades=trades, total_costs=res.total_costs, total_funding=res.total_funding)
    day_label = _day_labels(hist, effective)
    day_label = day_label[day_label.index >= a]
    bar_label = regime.per_bar(hist, effective)
    entered = pd.Series([bar_label[t.entry_time] for t in trades], dtype=object)
    per_regime = {label: {"days": int((day_label == label).sum()), "trades": int((entered == label).sum())}
                  for label in list(regime.LABELS) + [regime.UNKNOWN]}
    return window, {"test": [str(a.date()), str(b.date())], "per_regime": per_regime, "trades": len(trades),
                    "costs": res.total_costs, "funding": res.total_funding}


@dataclass
class WalkForward:
    windows: list[dict]
    returns: pd.Series                      # ihopsatt avkastning per stapel utanför urvalet
    trades: list[backtest.Trade]
    total_costs: float
    total_funding: float
    final: dict                             # slutlig spelbok, vald på hela utvecklingsperioden
    config: dict = field(default_factory=dict)

    @property
    def equity(self) -> pd.Series:
        return (1 + self.returns).cumprod()

    def to_dict(self) -> dict:
        """Allt som sparas om körningen, utom kurvan (punkt 9–10)."""
        return {"config": self.config, "windows": self.windows, "final": self.final,
                "trades": len(self.trades), "total_costs": self.total_costs, "total_funding": self.total_funding}


def walk_forward(bars: pd.DataFrame, funding: pd.Series, costs: CostModel = COSTS) -> WalkForward:
    """Sex halvårsfönster: spelboken väljs på data före varje fönster och prövas i fönstret."""
    check_development(bars, funding)
    edges = [_ts(t) for t in TEST_STARTS] + [_ts(HOLDOUT_START)]
    windows, parts, trades, c, f = [], [], [], 0.0, 0.0
    for a, b in zip(edges[:-1], edges[1:]):
        trained = train(bars, funding, a, costs)
        book = adaptive.Playbook.from_dict(trained["playbook"])
        res, info = evaluate_window(bars, funding, book, a, b, costs)
        windows.append({**trained, **info})
        parts.append(res.bar_returns)
        trades += res.trades
        c += res.total_costs
        f += res.total_funding
    returns = pd.concat(parts)
    if returns.index.has_duplicates or not returns.index.is_monotonic_increasing:
        raise AssertionError("Testfönstren överlappar")
    final = train(bars, funding, HOLDOUT_START, costs)
    final = {"contract": adaptive.CONTRACT_VERSION, **final}
    config = {"version": WALK_FORWARD_VERSION, "contract": adaptive.CONTRACT_VERSION,
              "dev_start": DEV_START, "test_starts": TEST_STARTS, "holdout_start": HOLDOUT_START,
              "min_trades": MIN_TRADES, "costs_bps": {"fee": costs.fee_bps, "spread": costs.spread_bps,
                                                      "slippage": costs.slippage_bps},
              "candidates": {k: v for k, v in adaptive.CANDIDATES.items()}}
    return WalkForward(windows, returns, trades, c, f, final, config)
