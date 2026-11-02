"""Utvärdering, kontroller och beslut för Fas 2 (H-0013), enligt research/fas2-protokoll.md.

Protokollet ändras inte. Tolkningarna står i docs/fas2-utvardering-tolkningar.md (U1–U20 hänvisas nedan).
Alla jämförelser går genom samma sex fönster och samma fönsterkonventioner som H-0013 (fas2.run_window), så att
de har exakt samma observationsperiod. Slutprovet läses aldrig: fas2.check_development och
fas2.load_development stoppar det innan något räknas.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import adaptive, backtest, fas2, metrics, regime, stats
from .costs import CostModel
from .experiment import RESULTS, random_label_control
from .registry import count_attempts, require_registered
from .strategies.rules import SPECS

EVALUATION_VERSION = "h0013-evaluation/1.0.0"
HYPOTHESIS = "H-0013"
T_REQUIRED = 2.67          # registrerat krav, N = 13 (U7)
REGISTERED_N = 13
N_PLAYBOOKS = 81
N_PERMUTATIONS = 200
SEED = 0
RISK_FILTERED = "ned/hög vol"
EMA, BB = fas2.CHOOSABLE
STEP = regime.ALLOWED["4h"]


# Jämförelsernas målpositioner (U3–U6). Varje funktion ger (målposition, stop-avstånd) för staplarna i `hist`.

def buy_and_hold():
    def make(hist, effective, start):
        return pd.Series(1.0, index=hist.index), None
    return make


def candidate_alone(name: str):
    def make(hist, effective, start):
        sig = SPECS[name].signals(hist)
        return sig.target.reindex(hist.index).fillna(0.0), sig.stop_distance
    return make


def risk_filter():
    """ema_adx_trend ensam, men platt när läget för nästa stapel är ned/hög vol (samma tidsregel som spelboken)."""
    def make(hist, effective, start):
        sig = SPECS[EMA].signals(hist)
        nxt = regime.per_bar(pd.DataFrame(index=hist.index + STEP), effective).set_axis(hist.index)
        return sig.target.reindex(hist.index).fillna(0.0).where(nxt != RISK_FILTERED, 0.0), sig.stop_distance
    return make


# Kurvor och nyckeltal

def curve(bars, funding, make_target, costs: CostModel = fas2.COSTS, labels=None) -> dict:
    """En målposition genom de sex fönstren, ihopsatt på gemensam kapitalbas."""
    results = [fas2.run_window(bars, funding, make_target, a, b, costs, labels) for a, b in fas2.windows()]
    returns, trades, c, f, capitals = fas2.stitch(results)
    position = pd.concat([res.position for res, _ in results])
    infos = [{**info, **cap} for (_, info), cap in zip(results, capitals)]
    return {"returns": returns, "position": position, "trades": trades, "costs": c, "funding": f, "windows": infos}


def _years(returns: pd.Series) -> float:
    return max((returns.index[-1] - returns.index[0]).days / 365.25, 1e-9) if len(returns) else 1e-9


def summary(c: dict) -> dict:
    """Samma nyckeltal för H-0013 och varje jämförelse (U8, U11, U15, U16)."""
    r = c["returns"]
    eq = (1 + r).cumprod()
    daily = stats.daily_returns(r)
    res = backtest.BacktestResult(equity=eq, position=c["position"].reindex(r.index).fillna(0.0), trades=c["trades"],
                                  total_costs=c["costs"], total_funding=c["funding"])
    full = metrics.full_stats(res)
    t = stats.newey_west_t(daily) if len(daily) > 1 else float("nan")
    yearly = {str(y): float((1 + g).prod() - 1) for y, g in daily.groupby(daily.index.year)}
    best = max(yearly, key=yearly.get) if yearly else None
    rest = daily[daily.index.year != int(best)] if best else daily
    lo, hi = stats.block_bootstrap_sharpe_ci(daily, block=20, n_boot=2000, seed=SEED)
    turnover = float(res.position.diff().abs().fillna(res.position.abs()).sum() / _years(r))
    return {
        "total_return": float(eq.iloc[-1] - 1) if len(eq) else 0.0,
        "sharpe": float(stats.sharpe(daily)),
        "t_daily_nw": float(t) if np.isfinite(t) else None,
        "sharpe_ci95": [lo, hi],
        "max_drawdown": full["max_drawdown"], "sortino": full["sortino"], "calmar": full["calmar"],
        "exposure": full["exposure"], "turnover_per_year": turnover,
        "trades": len(c["trades"]), "stop_exits": sum(t.exit_reason == "stop" for t in c["trades"]),
        "liquidations": sum(w.get("liquidations", 0) for w in c["windows"]),
        "costs": c["costs"], "funding": c["funding"], "days": int(len(daily)),
        "yearly": yearly, "best_year": best,
        "without_best_year": {"total_return": float((1 + rest).prod() - 1), "sharpe": float(stats.sharpe(rest))},
    }


def mixed(a: dict, b: dict) -> dict:
    """Hälften av kapitalet i varje kurva från start, utan ombalansering (U5)."""
    if not a["returns"].index.equals(b["returns"].index):
        raise AssertionError("Blandningens kurvor har olika staplar")
    eq = 0.5 * (1 + a["returns"]).cumprod() + 0.5 * (1 + b["returns"]).cumprod()
    returns = eq / eq.shift(1).fillna(1.0) - 1
    half = lambda t: backtest.Trade(**{**t.__dict__, "equity_at_entry": t.equity_at_entry / 2, "gross_pnl": t.gross_pnl / 2,
                                       "costs": t.costs / 2, "funding": t.funding / 2})
    windows = [{"liquidations": wa.get("liquidations", 0) + wb.get("liquidations", 0)}
               for wa, wb in zip(a["windows"], b["windows"])]
    return {"returns": returns, "position": 0.5 * (a["position"] + b["position"]),
            "trades": [half(t) for t in a["trades"] + b["trades"]],
            "costs": (a["costs"] + b["costs"]) / 2, "funding": (a["funding"] + b["funding"]) / 2, "windows": windows}


def regime_results(bars, wf: fas2.WalkForward, labels=None) -> dict:
    """Dagar, affärer, avkastning och Sharpe per läge utanför urvalet (U17)."""
    effective = regime.daily(bars) if labels is None else labels
    day_label = fas2._day_labels(bars, effective)
    daily = stats.daily_returns(wf.returns)
    lab = day_label.reindex(daily.index)
    bar_label = regime.per_bar(bars, effective)
    entered = pd.Series([bar_label[t.entry_time] for t in wf.trades], dtype=object)
    out = {}
    for label in list(regime.LABELS) + [regime.UNKNOWN]:
        d = daily[lab == label]
        out[label] = {"days": int(len(d)), "trades": int((entered == label).sum()),
                      "return": float((1 + d).prod() - 1), "sharpe": float(stats.sharpe(d))}
    return out


# Kontroller (U12–U14, U18)

def permutation_test(bars, funding, actual_sharpe: float, n: int = N_PERMUTATIONS, seed: int = SEED,
                     costs: CostModel = fas2.COSTS) -> dict:
    """Lägesetiketterna permuteras per dygn; hela walk-forward, med urval, körs om för varje permutation (U12–U13)."""
    effective = regime.daily(bars)
    known = (effective != regime.UNKNOWN).to_numpy()
    rng = np.random.default_rng(seed)
    runs = []
    for i in range(n):
        values = effective.to_numpy(dtype=object).copy()
        values[known] = rng.permutation(values[known])
        permuted = pd.Series(values, index=effective.index, dtype=object)
        wf = fas2.walk_forward(bars, funding, costs, labels=permuted)
        runs.append({"i": i, "sharpe": float(stats.sharpe(stats.daily_returns(wf.returns))),
                     "playbooks": [w["playbook_id"] for w in wf.windows]})
    k = sum(r["sharpe"] >= actual_sharpe for r in runs)
    return {"n": n, "seed": seed, "at_least_as_high": k, "p_value": k / n if n else None,
            "p_value_plus_one": (k + 1) / (n + 1), "runs": runs}


def all_playbooks(bars, funding, books=None, costs: CostModel = fas2.COSTS) -> dict:
    """Varje fast spelbok genom samma fönster, utan urval (U14)."""
    books = adaptive.all_playbooks() if books is None else books
    out = []
    for book in books:
        c = curve(bars, funding, fas2.selector_target(book), costs)
        out.append({"playbook_id": book.id, "choices": dict(book.choices),
                    "sharpe": float(stats.sharpe(stats.daily_returns(c["returns"])))})
    return {"n": len(out), "playbooks": out}


def deflated(daily: pd.Series, playbooks: dict) -> dict:
    """Deflated Sharpe med 81 försök: standardvarians och variansen mellan de fasta spelböckerna (U14)."""
    per_day = np.array([p["sharpe"] for p in playbooks["playbooks"]]) / np.sqrt(365)
    var = float(per_day.var(ddof=1)) if per_day.size > 1 else None
    return {"n_trials": N_PLAYBOOKS,
            "default_variance": stats.deflated_sharpe(daily.to_numpy(), N_PLAYBOOKS),
            "playbook_variance": (stats.deflated_sharpe(daily.to_numpy(), N_PLAYBOOKS, var)
                                  if var and var > 0 else None),
            "variance_from_playbooks": var, "playbooks_used": playbooks["n"]}


# Beslut (U7–U10)

def criteria(main: dict, stressed: dict, bh: dict, alone: dict[str, dict], mix: dict) -> dict:
    s = main["sharpe"]
    t = main["t_daily_nw"]
    out = {
        "t_at_least_required": t is not None and t >= T_REQUIRED,
        "stressed_costs_positive": stressed["total_return"] > 0,
        "sharpe_above_buy_and_hold": s > bh["sharpe"],
        "sharpe_above_best_candidate": s > max(v["sharpe"] for v in alone.values()),
        "sharpe_above_equal_weight_mix": s > mix["sharpe"],
    }
    return {k: bool(v) for k, v in out.items()}


def decision(crit: dict) -> str:
    return "MORE_RESEARCH" if len(crit) == 5 and all(crit.values()) else "REJECT"


def evaluate(bars, funding, costs: CostModel = fas2.COSTS, n_permutations: int = N_PERMUTATIONS,
             playbooks=None, attempts_now: int | None = None) -> dict:
    """Hela utvärderingen av H-0013 på utvecklingsperioden. Påverkar inga strategier och läser inget slutprov."""
    fas2.check_development(bars, funding)
    wf = fas2.walk_forward(bars, funding, costs)
    books = [adaptive.Playbook.from_dict(w["playbook"]) for w in wf.windows]
    # Samma fönster igen med de valda spelböckerna, för positionerna (exponering och omsättning).
    replay = [fas2.run_window(bars, funding, fas2.selector_target(book), a, b, costs)
              for book, (a, b) in zip(books, fas2.windows())]
    if not pd.concat([res.bar_returns for res, _ in replay]).equals(wf.returns):
        raise AssertionError("Omkörningen av fönstren skiljer sig från walk-forward")
    main = summary({"returns": wf.returns, "position": pd.concat([res.position for res, _ in replay]),
                    "trades": wf.trades, "costs": wf.total_costs, "funding": wf.total_funding, "windows": wf.windows})
    stressed_results = [fas2.run_window(bars, funding, fas2.selector_target(book), a, b, costs.stressed())
                        for book, (a, b) in zip(books, fas2.windows())]
    returns, trades, c, f, caps = fas2.stitch(stressed_results)
    stressed = summary({"returns": returns, "position": pd.concat([r.position for r, _ in stressed_results]),
                        "trades": trades, "costs": c, "funding": f,
                        "windows": [{**i, **cap} for (_, i), cap in zip(stressed_results, caps)]})
    curves = {"buy_and_hold": curve(bars, funding, buy_and_hold(), costs),
              EMA: curve(bars, funding, candidate_alone(EMA), costs),
              BB: curve(bars, funding, candidate_alone(BB), costs),
              "risk_filter": curve(bars, funding, risk_filter(), costs)}
    curves["equal_weight_mix"] = mixed(curves[EMA], curves[BB])
    comp = {k: summary(v) for k, v in curves.items()}
    for k, v in curves.items():
        if not v["returns"].index.equals(wf.returns.index):
            raise AssertionError(f"{k} har inte samma observationsperiod som H-0013")
    crit = criteria(main, stressed, comp["buy_and_hold"], {EMA: comp[EMA], BB: comp[BB]}, comp["equal_weight_mix"])
    daily = stats.daily_returns(wf.returns)
    books81 = all_playbooks(bars, funding, playbooks, costs)
    oos = bars[bars.index >= fas2._ts(fas2.TEST_STARTS[0])]
    return {
        "hypothesis_id": HYPOTHESIS, "evaluation_version": EVALUATION_VERSION,
        "walk_forward": wf.to_dict(), "out_of_sample": [fas2.TEST_STARTS[0], fas2.HOLDOUT_START],
        "holdout": "2025-01-01 och framåt, oläst",
        "h0013": main, "stressed": stressed, "comparisons": comp,
        "criteria": crit, "decision": decision(crit),
        "t_required": T_REQUIRED, "registered_n": REGISTERED_N,
        "attempts_now": attempts_now, "t_required_now": stats.t_krav(attempts_now) if attempts_now else None,
        "regimes": regime_results(bars, wf),
        "permutation": permutation_test(bars, funding, main["sharpe"], n_permutations, SEED, costs),
        "deflated_sharpe": deflated(daily, books81), "playbooks": books81,
        "random_label_t": random_label_control(oos, seed=SEED),
        "curves": {"t": [x.isoformat() for x in wf.returns.index], "h0013": (1 + wf.returns).cumprod().tolist()},
        "simulated": False,
    }


# Spara varje försök (U19–U20)

def _clean(o):
    if isinstance(o, float) and not np.isfinite(o):
        return None
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return _clean(o.item())
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def record(folder: Path, payload: dict, status: str) -> Path:
    """Skriver en ny resultatfil och skriver aldrig över en befintlig. Status: completed, aborted eller invalid."""
    if status not in ("completed", "aborted", "invalid"):
        raise ValueError(f"Okänd status {status}")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = folder / f"{HYPOTHESIS}-{stamp}-{status}.json"
    body = {**payload, "status": status}
    if status != "completed":
        body.pop("decision", None)
    with path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(_clean(body), ensure_ascii=False, indent=1) + "\n")
    return path


def run(repo: Path, data_dir: Path | None = None, **kw) -> Path:
    """Den riktiga körningen: kräver registrerad H-0013 och sparar resultatet även om körningen avbryts."""
    reg = require_registered(HYPOTHESIS, repo)
    meta = {"hypothesis_id": HYPOTHESIS, "registry_commit": reg.registry_commit, "evaluation_version": EVALUATION_VERSION,
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    attempts = count_attempts((repo / "research" / "registry.md").read_text(encoding="utf-8"))
    try:
        bars, funding = fas2.load_development(data_dir or repo / "data")
        result = evaluate(bars, funding, attempts_now=attempts, **kw)
    except BaseException as exc:
        record(repo / RESULTS, {**meta, "error": f"{type(exc).__name__}: {exc}"}, "aborted")
        raise
    return record(repo / RESULTS, {**meta, **result}, "completed")
