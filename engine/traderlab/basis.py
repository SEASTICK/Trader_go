"""H-0020: kassa-och-termin (basis) på BTC och ETH, enligt research/basis-protokoll.md.

Köp spot och sälj närmaste kvartalstermin blankt med samma belopp när basis är hög, stäng när den blir negativ och
rulla 14 dagar före förfall. Beslut på stängning, fyllning på nästa dags öppning för båda benen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import stats
from .costs import CostModel
from .data import binance
from .experiment import RESULTS
from .registry import require_registered

ASSETS = ("BTCUSDT", "ETHUSDT")
START, HOLDOUT = "2021-01-01", "2025-01-01"
ENTER, EXIT, MIN_DAYS = 0.05, 0.0, 14
SPOT_SHARE = 2 / 3            # resten är säkerhet för terminen (50 %)
COSTS = CostModel(fee_bps=10, spread_bps=2, slippage_bps=5)
CASH_HURDLE = 0.03
LIQUIDATION_RISE = 0.45


def expiry_of(symbol: str) -> pd.Timestamp:
    """BTCUSDT_210326 -> 2021-03-26 08:00 UTC är förfallet; dagsstapeln för förfallodagen räknas inte."""
    return pd.Timestamp("20" + symbol.rsplit("_", 1)[1], tz="UTC")


def contracts(asset: str, data_dir: Path) -> list[str]:
    syms = json.loads((data_dir / "raw" / "binance" / "um-symbols.json").read_text())
    out = [s for s in syms if s.startswith(asset + "_")]
    # Kontrakt som kan vara aktiva före slutprovet: förfall senast ett kvartal efter periodens slut.
    return sorted((s for s in out if expiry_of(s) <= pd.Timestamp("2025-03-31", tz="UTC")), key=expiry_of)


def fetch(data_dir: Path) -> None:
    """Dagsstaplar för kvartalsterminerna fram till 2024-12. Slutprovet hämtas inte."""
    for a in ASSETS:
        binance.fetch("spot", a, "1d", "2020-11", "2024-12", data_dir)
        for c in contracts(a, data_dir):
            end = min(expiry_of(c), pd.Timestamp("2024-12-01", tz="UTC")).strftime("%Y-%m")
            binance.fetch("um", c, "1d", "2020-09", end, data_dir)


LO, HI = pd.Timestamp("2020-11-01", tz="UTC"), pd.Timestamp(HOLDOUT, tz="UTC")


def _load(market: str, symbol: str, data_dir: Path) -> pd.DataFrame:
    """Begränsad läsning: arkiv från slutprovet öppnas aldrig."""
    return binance.load(market, symbol, "1d", data_dir, start=LO, end=HI)


def load(asset: str, data_dir: Path) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    spot = _load("spot", asset, data_dir)
    futs = {}
    for c in contracts(asset, data_dir):
        try:
            f = _load("um", c, data_dir)
        except FileNotFoundError:
            continue
        if not f.empty:
            futs[c] = f
    return spot, futs


def days_left(symbol: str, day: pd.Timestamp) -> int:
    return (expiry_of(symbol).normalize() - day.normalize()).days


def active(futs: dict[str, pd.DataFrame], day: pd.Timestamp) -> str | None:
    """Närmaste kvartalstermin med mer än 14 dagar kvar och en stängd stapel samma dag."""
    for c in sorted(futs, key=expiry_of):
        if days_left(c, day) > MIN_DAYS and day in futs[c].index:
            return c
    return None


def basis(spot_close: float, fut_close: float, left: int) -> float:
    return (fut_close / spot_close - 1) * 365 / left


@dataclass
class Leg:
    equity: pd.Series
    trades: int = 0
    days_hedged: int = 0
    max_rise: float = 0.0
    costs: float = 0.0
    min_cash: float = 0.0
    events: list = field(default_factory=list)


def simulate(spot: pd.DataFrame, futs: dict[str, pd.DataFrame], costs: CostModel, capital: float,
             start: str = START) -> Leg:
    """En tillgång. Avkastning på hela kapitalet; spot köps för 2/3, resten är säkerhet."""
    days = spot.index[spot.index >= pd.Timestamp(start, tz="UTC")]
    c = costs.per_side
    cash, q_s, q_f, held, f_entry = capital, 0.0, 0.0, None, 0.0
    target = None
    eq, leg = [], Leg(pd.Series(dtype=float))
    prev_close_f = None
    for i, t in enumerate(days):
        s_open, s_close = spot.at[t, "open"], spot.at[t, "close"]
        # 1) Fyll gårdagens beslut på dagens öppning.
        if target != held:
            if held is not None:   # stäng terminen
                f_open = futs[held].at[t, "open"]
                cash += q_f * (f_entry - f_open) - q_f * f_open * c
                leg.costs += q_f * f_open * c
                leg.events.append((t.date().isoformat(), "stäng", held))
                q_f, held = 0.0, None
            if target is None and q_s > 0:   # sälj spoten
                cash += q_s * s_open * (1 - c)
                leg.costs += q_s * s_open * c
                q_s = 0.0
            if target is not None:
                if q_s == 0:       # ny säkring: köp spot för 2/3 av kapitalet
                    notional = SPOT_SHARE * cash
                    q_s = notional / (s_open * (1 + c))
                    cash -= q_s * s_open * (1 + c)
                    leg.costs += q_s * s_open * c
                else:              # rullning: spoten behålls men återställs till 2/3 av kapitalet (ingen belåning)
                    want = SPOT_SHARE * (cash + q_s * s_open) / s_open
                    trade = (want - q_s) * s_open
                    cash -= trade + abs(trade) * c
                    leg.costs += abs(trade) * c
                    q_s = want
                f_open = futs[target].at[t, "open"]
                q_f = q_s * s_open / f_open      # samma belopp som spotbenet
                f_entry, held = f_open, target
                cash -= q_f * f_open * c
                leg.costs += q_f * f_open * c
                leg.trades += 1
                leg.events.append((t.date().isoformat(), "sälj termin", held))
                prev_close_f = f_open
        # 2) Värdera på stängningen, kontrollera likvidation.
        value = cash + q_s * s_close
        if held is not None:
            bar = futs[held].loc[t]
            leg.max_rise = max(leg.max_rise, bar["high"] / prev_close_f - 1)
            prev_close_f = bar["close"]
            value += q_f * (f_entry - bar["close"])
            leg.days_hedged += 1
        leg.min_cash = min(leg.min_cash, cash)
        eq.append(value)
        # 3) Beslut på stängningen inför morgondagen.
        act = active(futs, t)
        if held is None:
            target = act if act is not None and basis(s_close, futs[act].at[t, "close"], days_left(act, t)) >= ENTER else None
        elif held != act:      # 14 dagar kvar: rulla eller gå ur
            target = act if act is not None and basis(s_close, futs[act].at[t, "close"], days_left(act, t)) >= ENTER else None
        elif basis(s_close, futs[held].at[t, "close"], days_left(held, t)) <= EXIT:
            target = None
        else:
            target = held
        if target is not None and i + 1 < len(days) and days[i + 1] not in futs[target].index:
            raise ValueError(f"{target} saknar stapel {days[i + 1].date()}")
    leg.equity = pd.Series(eq, index=days)
    return leg


def run_portfolio(data_dir: Path, costs: CostModel) -> tuple[pd.Series, dict[str, Leg]]:
    legs = {}
    for a in ASSETS:
        spot, futs = load(a, data_dir)
        legs[a] = simulate(spot, futs, costs, capital=1 / len(ASSETS))
    eq = sum(l.equity for l in legs.values())
    return eq.dropna(), legs


def run(hypothesis_id: str, repo: Path, data_dir: Path | None = None) -> Path:
    reg = require_registered(hypothesis_id, repo)
    data_dir = data_dir or repo / "data"
    eq, legs = run_portfolio(data_dir, COSTS)
    st_eq, _ = run_portfolio(data_dir, COSTS.stressed())
    daily = eq.pct_change().dropna()
    t_req, t_nw = stats.t_krav(reg.attempts), stats.newey_west_t(daily)
    btc_close = _load("spot", "BTCUSDT", data_dir)["close"]
    btc = btc_close.pct_change().reindex(daily.index)
    bh = btc_close.reindex(eq.index) / btc_close.reindex(eq.index).iloc[0]
    both = pd.concat([daily, btc], axis=1).dropna()
    beta = float(both.iloc[:, 0].cov(both.iloc[:, 1]) / both.iloc[:, 1].var())
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = float(eq.iloc[-1] ** (1 / years) - 1)
    yearly = eq.resample("YE").last() / eq.resample("YE").last().shift(1).fillna(1.0) - 1
    m = eq.resample("ME").last()
    max_rise = max(l.max_rise for l in legs.values())
    criteria = {"t_at_least_required": bool(t_nw >= t_req), "stressed_costs_positive": bool(st_eq.iloc[-1] > 1),
                "beta_within_0_2": abs(beta) <= 0.2, "cagr_above_cash": cagr > CASH_HURDLE,
                "no_liquidation": bool(max_rise < LIQUIDATION_RISE)}
    out = {
        "hypothesis_id": hypothesis_id, "registry_commit": reg.registry_commit, "phase": "basis", "track": "C",
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period": [str(eq.index[0].date()), str(eq.index[-1].date())], "attempts": reg.attempts,
        "universe": list(ASSETS), "rebalances": int(sum(l.trades for l in legs.values())),
        "baseline_btc_buy_and_hold": {"total_return": float(bh.iloc[-1] - 1)},
        "costs_bps_per_side": COSTS.per_side * 10_000, "t_daily_nw": t_nw, "t_required": t_req,
        "deflated_sharpe": stats.deflated_sharpe(daily.to_numpy(), max(reg.attempts, 1)),
        "sharpe_ci": list(stats.block_bootstrap_sharpe_ci(daily)),
        "summary": {"total_return": float(eq.iloc[-1] - 1), "cagr": cagr, "sharpe": float(stats.sharpe(daily)),
                    "max_drawdown": float(stats.max_drawdown(eq)), "yearly": {str(k.year): round(float(v), 4) for k, v in yearly.items()},
                    "monthly_returns": {k.strftime("%Y-%m"): round(float(v), 6) for k, v in (m / m.shift(1).fillna(1.0) - 1).items()}},
        "summary_stressed_costs": {"total_return": float(st_eq.iloc[-1] - 1)},
        "benchmark": {"name": "spot BTCUSDT 1d", "beta": beta, "correlation": float(both.corr().iloc[0, 1])},
        "per_asset": {a: {"trades": l.trades, "days_hedged": l.days_hedged, "share_hedged": l.days_hedged / len(l.equity),
                          "max_daily_rise_while_short": l.max_rise, "costs": l.costs, "min_cash": l.min_cash, "events": l.events,
                          "total_return": float(l.equity.iloc[-1] / l.equity.iloc[0] - 1)} for a, l in legs.items()},
        "criteria": criteria, "meets_all_criteria": all(criteria.values()),
        "curve": {"t": [d.isoformat() for d in eq.index[::5]], "strategy": [round(float(v) * 100, 4) for v in eq.iloc[::5]],
                  "btc": [round(float(v) * 100, 4) for v in bh.iloc[::5]]},
        "simulated": False,
    }
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{hypothesis_id}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    return path
