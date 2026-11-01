"""Parameteroptimering med Optuna och walk-forward (Fas 1).

Protokoll (research/fas1-protokoll.md):
- Optuna (TPE, fast frö) väljer parametrar BARA på data före testfönstret.
- Walk-forward med växande träningsfönster: optimera på [start, T), testa på [T, T + steg). Testbitarna sätts
  ihop till en sammanhängande kurva utanför urvalet (out-of-sample). Det är den kurvan som bedöms.
- Slutprovet (holdout) körs aldrig här.
- Parameterstabilitet: grannar till de slutliga parametrarna (ett steg upp och ned per parameter) ska behålla
  minst hälften av Sharpe-värdet.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import optuna
import pandas as pd

from . import backtest, stats
from .costs import CostModel
from .strategies.rules import Param, StrategySpec

optuna.logging.set_verbosity(optuna.logging.WARNING)
WARMUP_BARS = 400  # indikatorer behöver historik; signalerna räknas på data före fönstret också


def _suggest(trial: optuna.Trial, name: str, p: Param):
    if p.kind == "int":
        return trial.suggest_int(name, int(p.low), int(p.high), step=int(p.step or 1))
    return trial.suggest_float(name, p.low, p.high, step=p.step)


def evaluate(spec: StrategySpec, params: dict, bars: pd.DataFrame, start, end, costs: CostModel,
             funding: pd.Series | None = None) -> backtest.BacktestResult:
    """Kör strategin med signaler från hela historiken fram till `end`, men handlar bara inom [start, end)."""
    hist = bars[bars.index < end]
    sig = spec.signals(hist, params)
    win = hist.index >= start
    first = max(0, int(np.argmax(win)) - 1)  # stapeln före fönstret behövs för första beslutet
    sl = slice(first, None)
    b = hist.iloc[sl]
    tgt = sig.target.iloc[sl].copy()
    tgt.iloc[0] = 0.0 if first == 0 else tgt.iloc[0]
    return backtest.run(b, tgt, costs, funding=funding,
                        stop_distance=None if sig.stop_distance is None else sig.stop_distance.iloc[sl],
                        take_profit_distance=None if sig.take_profit_distance is None else sig.take_profit_distance.iloc[sl])


def score(res: backtest.BacktestResult, min_trades: int = 10) -> float:
    """Målfunktion: Sharpe på dagsavkastning, straffad när det finns för få affärer att lita på."""
    if len(res.closed_trades) < min_trades:
        return -10.0
    s = stats.sharpe(stats.daily_returns(res.bar_returns))
    return float(s) if np.isfinite(s) else -10.0


def optimize(spec: StrategySpec, bars, start, end, costs, funding=None, n_trials: int = 40, seed: int = 0) -> tuple[dict, float]:
    def objective(trial):
        p = {k: _suggest(trial, k, v) for k, v in spec.space.items()}
        if not spec.valid({**spec.defaults, **p}):
            raise optuna.TrialPruned()
        return score(evaluate(spec, p, bars, start, end, costs, funding))
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials)
    done = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    if not done:
        return dict(spec.defaults), float("nan")
    return {**spec.defaults, **study.best_params}, float(study.best_value)


@dataclass
class WalkForward:
    windows: list[dict]           # per testfönster: träning, test, parametrar, Sharpe i och utanför urvalet
    oos_returns: pd.Series        # avkastning per stapel, ihopsatt utanför urvalet
    trades: list                  # affärer utanför urvalet
    final_params: dict            # optimerade på hela utvecklingsperioden, frysta för slutprov och papper
    stability: float              # andel grannar som behåller minst hälften av Sharpe
    trials: int


def walk_forward(spec: StrategySpec, bars, dev_start, test_starts: list, dev_end, costs, funding=None,
                 n_trials: int = 40, seed: int = 0) -> WalkForward:
    edges = [pd.Timestamp(t, tz="UTC") for t in test_starts] + [pd.Timestamp(dev_end, tz="UTC")]
    dev_start = pd.Timestamp(dev_start, tz="UTC")
    windows, parts, trades = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        params, is_score = optimize(spec, bars, dev_start, a, costs, funding, n_trials, seed)
        res = evaluate(spec, params, bars, a, b, costs, funding)
        r = res.bar_returns[res.bar_returns.index >= a]
        parts.append(r)
        trades += [t for t in res.trades if t.entry_time >= a]
        windows.append({"train": [str(dev_start.date()), str(a.date())], "test": [str(a.date()), str(b.date())],
                        "params": params, "sharpe_in_sample": is_score,
                        "sharpe_out_of_sample": float(stats.sharpe(stats.daily_returns(r)))})
    oos = pd.concat(parts)
    final, _ = optimize(spec, bars, dev_start, edges[-1], costs, funding, n_trials, seed)
    stab = stability(spec, final, bars, dev_start, edges[-1], costs, funding)
    return WalkForward(windows, oos, trades, final, stab, n_trials * (len(edges)))


def stability(spec: StrategySpec, params: dict, bars, start, end, costs, funding=None) -> float:
    base = score(evaluate(spec, params, bars, start, end, costs, funding))
    if not np.isfinite(base) or base <= 0:
        return 0.0
    ok = total = 0
    for k, p in spec.space.items():
        step = p.step or (1 if p.kind == "int" else (p.high - p.low) / 10)
        for d in (-step, step):
            q = dict(params)
            q[k] = params[k] + d
            if q[k] < p.low or q[k] > p.high or not spec.valid(q):
                continue
            total += 1
            ok += score(evaluate(spec, q, bars, start, end, costs, funding)) >= 0.5 * base
    return ok / total if total else 0.0
