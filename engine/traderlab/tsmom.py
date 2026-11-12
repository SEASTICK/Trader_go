"""H-0021: tidsseriemomentum över många kryptoterminer, enligt research/tsmom-protokoll.md (låst före koden).

Varje mynt bedöms mot sin egen 28-dagarsavkastning (senaste dagen överhoppad): positiv ger long, negativ ger short.
Vikt omvänt proportionell mot 60-dagarsvolatiliteten, brutto 1×, högst 10 % per mynt. Söndag vid stängning, fyllning
på måndagens öppning. Förenklat likvidationsstopp per position (portfolio.run). Slutprovet 2025+ läses aldrig in.

Den här modulen innehåller bara motorn och dess kontroller. Ingen körning på riktiga data görs förrän koden är granskad.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import portfolio, stats, xs, xsbig
from .costs import CostModel
from .data import binance
from .experiment import RESULTS
from .registry import require_registered

START, HOLDOUT = xsbig.START, xsbig.HOLDOUT
LOOKBACK, SKIP = 28, 1
VOL_DAYS, MIN_VOL_DAYS = 60, 40
CAP, MIN_COINS, MIN_ELIGIBLE_MEDIAN = 0.10, 10, 30
STOP = 0.05                      # stopp när positionens equity når 5 % av ingångsnotional
COSTS = xsbig.COSTS              # 25 bp per sida, som H-0018
SEED = 0


class InvalidRun(Exception):
    """Datakravet i protokollet är inte uppfyllt: körningen är OGILTIG och kan aldrig ge MORE_RESEARCH."""


def signal(closes: pd.DataFrame) -> pd.DataFrame:
    """Avkastning över 28 dagar där senaste dagen hoppas över: stängning(t−1) / stängning(t−29) − 1."""
    return closes.shift(SKIP) / closes.shift(SKIP + LOOKBACK) - 1


def volatility(closes: pd.DataFrame) -> pd.DataFrame:
    """Standardavvikelse av dagsavkastning över de 60 dagar som slutar dagen före beslutsdagen (minst 40 giltiga)."""
    r = closes.pct_change(fill_method=None)
    return r.shift(1).rolling(VOL_DAYS, min_periods=MIN_VOL_DAYS).std()


def cap_weights(raw: pd.Series, cap: float = CAP) -> pd.Series:
    """Normaliserar till summa 1 och begränsar varje vikt till `cap`. Överskottet fördelas proportionellt på övriga och
    upprepas tills ingen överskrider. Kräver minst 1/cap värden."""
    if len(raw) * cap < 1 - 1e-12:
        raise ValueError("För få värden för taket.")
    capped = pd.Series(False, index=raw.index)
    w = raw / raw.sum()
    for _ in range(len(raw) + 1):
        over = w > cap + 1e-12
        if not over.any():
            break
        capped |= over
        free = ~capped
        w = pd.Series(cap, index=raw.index)
        w[free] = raw[free] / raw[free].sum() * (1 - cap * capped.sum())
    return w


def weights(closes: pd.DataFrame, dvol: pd.DataFrame, random_signs: np.random.Generator | None = None) -> pd.DataFrame:
    """Målvikter på söndagar (rader), fyllning på måndagens öppning. Raden är 0 om färre än 10 mynt har signal."""
    days = xs.rebalance_days(closes.index)
    elig = xsbig.eligible(closes, dvol).loc[days]
    sig = np.sign(signal(closes).loc[days])
    if random_signs is not None:   # slumpkontroll: samma portfölj men slumpade tecken
        sig = pd.DataFrame(random_signs.choice([-1.0, 1.0], size=sig.shape), index=sig.index, columns=sig.columns).where(sig.notna())
    vol = volatility(closes).loc[days]
    w = pd.DataFrame(0.0, index=days, columns=closes.columns)
    for t in days:
        ok = elig.loc[t] & sig.loc[t].notna() & (sig.loc[t] != 0) & vol.loc[t].notna() & (vol.loc[t] > 0)
        if ok.sum() < MIN_COINS:
            continue
        a = cap_weights(1.0 / vol.loc[t][ok])
        w.loc[t, ok[ok].index] = (sig.loc[t][ok] * a).to_numpy()
    return w


def basket_weights(closes: pd.DataFrame, dvol: pd.DataFrame) -> pd.DataFrame:
    """Jämförelse 2: likaviktad long-only-korg av samma valbara mynt, samma söndagar. Platt om färre än 10."""
    days = xs.rebalance_days(closes.index)
    elig = xsbig.eligible(closes, dvol).loc[days]
    w = pd.DataFrame(0.0, index=days, columns=closes.columns)
    for t in days:
        ok = elig.loc[t]
        if ok.sum() >= MIN_COINS:
            w.loc[t, ok[ok].index] = 1.0 / ok.sum()
    return w


def load_panel(data_dir: Path, symbols: list[str]):
    """Som xsbig.load_panel men också high och low. Alla läsare har periodgränser: arkiv från slutprovet öppnas aldrig."""
    lo, hi = pd.Timestamp("2020-11-01", tz="UTC"), pd.Timestamp(HOLDOUT, tz="UTC")
    cols: dict[str, dict] = {k: {} for k in ("open", "high", "low", "close", "dvol")}
    funding: dict[str, pd.Series] = {}
    for s in symbols:
        try:
            b = binance.load("um", s, "1d", data_dir, start=lo, end=hi)
        except FileNotFoundError:
            continue
        if b.empty:
            continue
        for k, v in (("open", b["open"]), ("high", b["high"]), ("low", b["low"]), ("close", b["close"]),
                     ("dvol", b["close"] * b["volume"])):
            cols[k][s] = v
        try:
            funding[s] = binance.load_funding(s, data_dir, start=lo, end=hi)
        except FileNotFoundError:
            funding[s] = pd.Series(dtype=float)
    return (pd.DataFrame(cols["open"]), pd.DataFrame(cols["high"]), pd.DataFrame(cols["low"]),
            pd.DataFrame(cols["close"]), pd.DataFrame(cols["dvol"]), funding)


def simulate(opens, highs, lows, w, costs, funding) -> portfolio.PortfolioResult:
    """Kör portföljen med likvidationsstoppet. Saknad high/low för hållen position ger InvalidRun."""
    try:
        res = portfolio.run(opens, w, costs, funding, highs=highs, lows=lows, stop=STOP)
    except ValueError as exc:
        raise InvalidRun(str(exc)) from exc
    gaps = portfolio.funding_gaps(res.weights, funding)
    if gaps:   # saknad ränta får aldrig bli gratis
        raise InvalidRun(f"Finansieringsränta saknas för hållna dagar: {gaps}")
    return res


def _equity_stats(res: portfolio.PortfolioResult, keep) -> dict:
    eq = res.equity[keep] / res.equity[keep].iloc[0]
    daily = stats.daily_returns(res.bar_returns[keep])
    return {"eq": eq, "daily": daily, "total_return": float(eq.iloc[-1] - 1), "sharpe": float(stats.sharpe(daily)),
            "max_drawdown": float(stats.max_drawdown(eq))}


def run(hypothesis_id: str, repo: Path, data_dir: Path | None = None) -> Path:
    reg = require_registered(hypothesis_id, repo)
    data_dir = data_dir or repo / "data"
    syms = xsbig.universe(data_dir)
    opens, highs, lows, closes, dvol, funding = load_panel(data_dir, syms)
    assert opens.index.max() < pd.Timestamp(HOLDOUT, tz="UTC"), "Slutprovet får inte läsas in."
    base = {"hypothesis_id": hypothesis_id, "registry_commit": reg.registry_commit, "phase": "tsmom", "track": "A",
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "attempts": reg.attempts,
            "universe_size": len(syms), "with_data": int(opens.shape[1]), "simulated": False}
    start = pd.Timestamp(START, tz="UTC")
    reasons: list[str] = []
    elig_median = float(xsbig.eligible(closes, dvol).sum(axis=1).loc[xs.rebalance_days(closes.index)].loc[lambda s: s.index >= start].median())
    if elig_median < MIN_ELIGIBLE_MEDIAN:
        reasons.append(f"Valbara mynt (median) {elig_median:.0f} < {MIN_ELIGIBLE_MEDIAN}")
    w = weights(closes, dvol)
    w = w[w.index >= start]
    try:
        normal = simulate(opens, highs, lows, w, COSTS, funding)
        stressed = simulate(opens, highs, lows, w, COSTS.stressed(), funding)
        wb = basket_weights(closes, dvol)
        basket = simulate(opens, highs, lows, wb[wb.index >= start], COSTS, funding)
        rnd = simulate(opens, highs, lows, weights(closes, dvol, np.random.default_rng(SEED))[lambda x: x.index >= start],
                       CostModel(0, 0, 0), funding)
    except InvalidRun as exc:
        reasons.append(str(exc))
    if reasons:
        out = {**base, "valid": False, "invalid_reasons": reasons, "decision": "OGILTIG",
               "note": "Datakravet i research/tsmom-protokoll.md är inte uppfyllt. Inget beslut, aldrig MORE_RESEARCH."}
        return _save(repo, hypothesis_id, out)

    keep = normal.equity.index >= start
    n_, b_ = _equity_stats(normal, keep), _equity_stats(basket, basket.equity.index >= start)
    spot = binance.load("spot", "BTCUSDT", "1d", data_dir, end=pd.Timestamp(HOLDOUT, tz="UTC"))
    spot = spot[spot.index >= start]
    btc_ret = (spot["open"].shift(-1) / spot["open"] - 1).reindex(n_["daily"].index)
    both = pd.concat([n_["daily"], btc_ret], axis=1).dropna()
    beta = float(both.iloc[:, 0].cov(both.iloc[:, 1]) / both.iloc[:, 1].var())
    btc_sharpe = float(stats.sharpe(btc_ret.dropna()))
    st_eq = stressed.equity[keep] / stressed.equity[keep].iloc[0]
    t_req, t_nw = stats.t_krav(reg.attempts), stats.newey_west_t(n_["daily"])
    years = (n_["eq"].index[-1] - n_["eq"].index[0]).days / 365.25
    live = w[(w != 0).any(axis=1)]
    yearly = n_["eq"].resample("YE").last() / n_["eq"].resample("YE").last().shift(1).fillna(1.0) - 1
    criteria = {"t_at_least_required": bool(t_nw >= t_req), "stressed_costs_positive": bool(st_eq.iloc[-1] > 1),
                "sharpe_above_btc_buy_and_hold": bool(n_["sharpe"] > btc_sharpe),
                "sharpe_above_long_only_basket": bool(n_["sharpe"] > b_["sharpe"])}
    out = {**base, "valid": True, "kind": "tsmom",
           "period": [str(n_["eq"].index[0].date()), str(n_["eq"].index[-1].date())], "rebalances": int(len(live)),
           "eligible_median": elig_median, "costs_bps_per_side": COSTS.per_side * 10_000,
           "t_daily_nw": t_nw, "t_required": t_req,
           "deflated_sharpe": stats.deflated_sharpe(n_["daily"].to_numpy(), max(reg.attempts, 1)),
           "sharpe_ci": list(stats.block_bootstrap_sharpe_ci(n_["daily"])),
           "summary": {"total_return": n_["total_return"], "cagr": float(n_["eq"].iloc[-1] ** (1 / years) - 1) if n_["eq"].iloc[-1] > 0 else -1.0,
                       "sharpe": n_["sharpe"], "max_drawdown": n_["max_drawdown"],
                       "turnover_per_year": float(normal.turnover[keep].sum() / years), "costs": normal.total_costs,
                       "funding": normal.total_funding, "avg_net_exposure": float(normal.weights[keep].sum(axis=1).mean()),
                       "yearly": {str(k.year): round(float(v), 4) for k, v in yearly.items()}},
           "summary_stressed_costs": {"total_return": float(st_eq.iloc[-1] - 1)},
           "benchmarks": {"btc_buy_and_hold": {"sharpe": btc_sharpe, "total_return": float((1 + btc_ret.dropna()).prod() - 1)},
                          "long_only_basket": {"sharpe": b_["sharpe"], "total_return": b_["total_return"], "max_drawdown": b_["max_drawdown"]}},
           "beta_btc": beta,
           "liquidation_stops": {"count": len(normal.stops), "total_loss_of_equity": float(sum(x[2] for x in normal.stops)),
                                 "events": normal.stops[:50]},
           "random_label_t": float(stats.newey_west_t(_equity_stats(rnd, rnd.equity.index >= start)["daily"])),
           "criteria": criteria, "meets_all_criteria": all(criteria.values()),
           "curve": {"t": [d.isoformat() for d in n_["eq"].index[::5]], "strategy": [round(float(v) * 100, 4) for v in n_["eq"].iloc[::5]]}}
    return _save(repo, hypothesis_id, out)


def _save(repo: Path, hypothesis_id: str, out: dict) -> Path:
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{hypothesis_id}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    return path
