"""Utvärdering, kontroller och beslut för Fas 2 (H-0013), enligt research/fas2-protokoll.md.

Protokollet ändras inte. Tolkningarna står i docs/fas2-utvardering-tolkningar.md (U1–U20 hänvisas nedan).
Alla jämförelser går genom samma sex fönster och samma fönsterkonventioner som H-0013 (fas2.run_window), så att
de har exakt samma observationsperiod. Slutprovet läses aldrig: fas2.check_development och
fas2.load_development stoppar det innan något räknas.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
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

def _guard(bars, funding=None, labels=None) -> None:
    """Slutprovsskyddet först i varje publik ingång, innan någon regim, signal eller statistik räknas."""
    empty = pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    fas2.check_development(bars, empty if funding is None else funding, effective=labels)


def curve(bars, funding, make_target, costs: CostModel = fas2.COSTS, labels=None) -> dict:
    """En målposition genom de sex fönstren, ihopsatt på gemensam kapitalbas."""
    _guard(bars, funding, labels)
    results = [fas2.run_window(bars, funding, make_target, a, b, costs, labels) for a, b in fas2.windows()]
    returns, trades, c, f, capitals = fas2.stitch(results)
    position = pd.concat([res.position for res, _ in results])
    infos = [{**info, **cap} for (_, info), cap in zip(results, capitals)]
    return {"returns": returns, "position": position, "trades": trades, "costs": c, "funding": f, "windows": infos}


def _years(returns: pd.Series) -> float:
    return max((returns.index[-1] - returns.index[0]).days / 365.25, 1e-9) if len(returns) else 1e-9


EXPOSURE_DEFINITIONS = {
    "net_exposure_mean": "Medel över staplarna av nettopositionen som andel av totalkapitalet vid stapelns början "
                         "(long +, short -). För blandningen viktas delarna med sitt aktuella kapital.",
    "gross_exposure_mean": "Medel över staplarna av summan av delpositionernas absolutbelopp som andel av totalkapitalet.",
    "time_in_market": "Andel staplar med någon öppen position (bruttoexponering > 0).",
    "turnover_per_year": "Handlat belopp (in och ut) för alla affärer, i den ihopsatta kurvans kapitalenhet "
                         "(startkapital 1,0), per år. Passiv viktförändring är ingen handel.",
}


def traded_notional(trades) -> float:
    """Handlat belopp in och ut, i affärernas kapitalenhet. Positionen är en andel av kapitalet vid inträdet."""
    total = 0.0
    for t in trades:
        entry = t.size * t.equity_at_entry
        total += entry
        if t.exit_price is not None and t.entry_price:
            total += entry * t.exit_price / t.entry_price
    return total


def summary(c: dict) -> dict:
    """Samma nyckeltal för H-0013 och varje jämförelse (U8, U11, U15, U16)."""
    r = c["returns"]
    eq = (1 + r).cumprod()
    daily = stats.daily_returns(r)
    position = c["position"].reindex(r.index).fillna(0.0)
    net = c.get("net_position", position).reindex(r.index).fillna(0.0)
    gross = c.get("gross_position", position.abs()).reindex(r.index).fillna(0.0)
    res = backtest.BacktestResult(equity=eq, position=net, trades=c["trades"],
                                  total_costs=c["costs"], total_funding=c["funding"])
    full = metrics.full_stats(res)
    t = stats.newey_west_t(daily) if len(daily) > 1 else float("nan")
    yearly = {str(y): float((1 + g).prod() - 1) for y, g in daily.groupby(daily.index.year)}
    best = max(yearly, key=yearly.get) if yearly else None
    rest = daily[daily.index.year != int(best)] if best else daily
    lo, hi = stats.block_bootstrap_sharpe_ci(daily, block=20, n_boot=2000, seed=SEED)
    return {
        "total_return": float(eq.iloc[-1] - 1) if len(eq) else 0.0,
        "sharpe": float(stats.sharpe(daily)),
        "t_daily_nw": float(t) if np.isfinite(t) else None,
        "sharpe_ci95": [lo, hi],
        "max_drawdown": full["max_drawdown"], "sortino": full["sortino"], "calmar": full["calmar"],
        "net_exposure_mean": float(net.mean()) if len(net) else 0.0,
        "gross_exposure_mean": float(gross.mean()) if len(gross) else 0.0,
        "time_in_market": float((gross > 0).mean()) if len(gross) else 0.0,
        "turnover_per_year": traded_notional(c["trades"]) / _years(r),
        "trades": len(c["trades"]), "stop_exits": sum(t.exit_reason == "stop" for t in c["trades"]),
        "liquidations": sum(w.get("liquidations", 0) for w in c["windows"]),
        "costs": c["costs"], "funding": c["funding"], "days": int(len(daily)),
        "yearly": yearly, "best_year": best,
        "without_best_year": {"total_return": float((1 + rest).prod() - 1), "sharpe": float(stats.sharpe(rest))},
    }


def mixed(a: dict, b: dict) -> dict:
    """Hälften av kapitalet i varje kurva från start, utan ombalansering (U5).

    Varje halva växer för sig. Positionerna viktas med halvornas kapital vid stapelns början, så nettoposition och
    bruttoexponering avser totalkapitalet. Affärernas belopp halveras; inga affärer tar ut varandra.
    """
    if not a["returns"].index.equals(b["returns"].index):
        raise AssertionError("Blandningens kurvor har olika staplar")
    eq_a, eq_b = (1 + a["returns"]).cumprod(), (1 + b["returns"]).cumprod()
    eq = 0.5 * eq_a + 0.5 * eq_b
    returns = eq / eq.shift(1).fillna(1.0) - 1
    w_a = 0.5 * eq_a.shift(1).fillna(1.0)   # kapital vid stapelns början
    w_b = 0.5 * eq_b.shift(1).fillna(1.0)
    p_a = a["position"].reindex(returns.index).fillna(0.0)
    p_b = b["position"].reindex(returns.index).fillna(0.0)
    net = (w_a * p_a + w_b * p_b) / (w_a + w_b)
    gross = (w_a * p_a.abs() + w_b * p_b.abs()) / (w_a + w_b)
    half = lambda t: replace(t, equity_at_entry=t.equity_at_entry / 2, gross_pnl=t.gross_pnl / 2,
                             costs=t.costs / 2, funding=t.funding / 2)
    windows = [{"liquidations": wa.get("liquidations", 0) + wb.get("liquidations", 0)}
               for wa, wb in zip(a["windows"], b["windows"])]
    return {"returns": returns, "position": net, "net_position": net, "gross_position": gross,
            "trades": [half(t) for t in a["trades"] + b["trades"]],
            "costs": (a["costs"] + b["costs"]) / 2, "funding": (a["funding"] + b["funding"]) / 2, "windows": windows}


CURVE_POINTS = 1500
CURVE_SOURCES = {"h0013": "fas2.walk_forward", "buy_and_hold": "fas2_eval.buy_and_hold",
                 EMA: "fas2_eval.candidate_alone(ema_adx_trend)", BB: "fas2_eval.candidate_alone(bb_rsi_reversion)",
                 "equal_weight_mix": "fas2_eval.mixed(ema_adx_trend, bb_rsi_reversion)", "risk_filter": "fas2_eval.risk_filter"}


def _returns_sha256(r: pd.Series) -> str:
    h = hashlib.sha256()
    h.update(r.index.asi8.tobytes())
    h.update(np.ascontiguousarray(r.to_numpy(dtype=float)).tobytes())
    return h.hexdigest()


def curve_selection(n: int, points: int = CURVE_POINTS) -> list[int]:
    """Högst `points` index, jämnt fördelade, alltid med första och sista stapeln (J3)."""
    if points < 2:
        raise ValueError("Minst två punkter behövs för en kurva")
    if n <= points:
        return list(range(n))
    return sorted({round(i * (n - 1) / (points - 1)) for i in range(points)})


def comparison_curves(h0013_returns: pd.Series, others: dict[str, pd.Series], points: int = CURVE_POINTS) -> dict:
    """Kapitalkurvor (start 1,0) för H-0013 och jämförelserna på exakt samma staplar, nedsamplade med samma index
    (docs/fas2-jamforelsekurvor-tolkningar.md, J1–J5). Varje kurva får källa och SHA-256 av hela avkastningsserien."""
    series = {"h0013": h0013_returns, **others}
    for name, r in series.items():   # slutprovsskyddet först, för varje serie, innan något räknas
        _guard(pd.DataFrame(index=r.index))
    for name, r in series.items():
        if not r.index.equals(h0013_returns.index):
            raise AssertionError(f"{name} har inte samma staplar som H-0013")
    n = len(h0013_returns)
    sel = curve_selection(n, points)
    equity = {name: (1 + r).cumprod() for name, r in series.items()}
    return {"t": [h0013_returns.index[i].isoformat() for i in sel],
            "series": {name: [round(float(eq.iloc[i]), 8) for i in sel] for name, eq in equity.items()},
            "sources": {name: {"source": CURVE_SOURCES.get(name, name), "bars": int(len(r)),
                               "returns_sha256": _returns_sha256(r)} for name, r in series.items()},
            "points": len(sel), "bars": n, "start_capital": 1.0, "evaluation_version": EVALUATION_VERSION}


def regime_results(bars, wf: fas2.WalkForward, labels=None) -> dict:
    """Dagar, affärer, avkastning och Sharpe per läge utanför urvalet (U17)."""
    _guard(bars, labels=labels)
    _guard(pd.DataFrame(index=wf.returns.index))
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
                     costs: CostModel = fas2.COSTS, sink: list | None = None) -> dict:
    """Lägesetiketterna permuteras per dygn; hela walk-forward, med urval, körs om för varje permutation (U12–U13).
    Varje färdig permutation läggs i `sink` direkt, så att den sparas även om körningen avbryts."""
    _guard(bars, funding)
    effective = regime.daily(bars)
    known = (effective != regime.UNKNOWN).to_numpy()
    rng = np.random.default_rng(seed)
    runs = [] if sink is None else sink
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


def all_playbooks(bars, funding, books=None, costs: CostModel = fas2.COSTS, sink: list | None = None) -> dict:
    """Varje fast spelbok genom samma fönster, utan urval (U14). Färdiga spelböcker läggs i `sink` direkt."""
    _guard(bars, funding)
    books = adaptive.all_playbooks() if books is None else books
    out = [] if sink is None else sink
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


STEPS = ("walk_forward", "h0013", "stressed", "comparisons", "criteria", "regimes", "permutation", "playbooks",
         "deflated_sharpe", "random_label_t")


def evaluate(bars, funding, costs: CostModel = fas2.COSTS, n_permutations: int = N_PERMUTATIONS,
             playbooks=None, attempts_now: int | None = None, progress: dict | None = None) -> dict:
    """Hela utvärderingen av H-0013 på utvecklingsperioden. Påverkar inga strategier och läser inget slutprov.

    `progress` fylls i under körningen: konfiguration, varje stegs status (pending, incomplete, done) och alla
    färdiga delresultat, också enskilda permutationer och spelböcker. Avbryts körningen finns allt som hunnit
    räknas kvar där (U19).
    """
    _guard(bars, funding)
    p = {} if progress is None else progress
    p["config"] = {"evaluation_version": EVALUATION_VERSION, "walk_forward_version": fas2.WALK_FORWARD_VERSION,
                   "contract": adaptive.CONTRACT_VERSION, "n_permutations": n_permutations, "seed": SEED,
                   "playbooks": N_PLAYBOOKS if playbooks is None else len(playbooks),
                   "costs_bps": {"fee": costs.fee_bps, "spread": costs.spread_bps, "slippage": costs.slippage_bps},
                   "t_required": T_REQUIRED, "registered_n": REGISTERED_N, "exposure_definitions": EXPOSURE_DEFINITIONS}
    p["steps"] = {step: "pending" for step in STEPS}

    def begin(step):
        p["steps"][step] = "incomplete"

    def done(step, value):
        p[step] = value
        p["steps"][step] = "done"
        return value

    begin("walk_forward")
    wf = fas2.walk_forward(bars, funding, costs)
    done("walk_forward", wf.to_dict())
    books = [adaptive.Playbook.from_dict(w["playbook"]) for w in wf.windows]
    begin("h0013")
    # Samma fönster igen med de valda spelböckerna, för positionerna (exponering och omsättning).
    replay = [fas2.run_window(bars, funding, fas2.selector_target(book), a, b, costs)
              for book, (a, b) in zip(books, fas2.windows())]
    if not pd.concat([res.bar_returns for res, _ in replay]).equals(wf.returns):
        raise AssertionError("Omkörningen av fönstren skiljer sig från walk-forward")
    main = done("h0013", summary({"returns": wf.returns, "position": pd.concat([res.position for res, _ in replay]),
                                  "trades": wf.trades, "costs": wf.total_costs, "funding": wf.total_funding,
                                  "windows": wf.windows}))
    begin("stressed")
    stressed_results = [fas2.run_window(bars, funding, fas2.selector_target(book), a, b, costs.stressed())
                        for book, (a, b) in zip(books, fas2.windows())]
    returns, trades, c, f, caps = fas2.stitch(stressed_results)
    stressed = done("stressed", summary({"returns": returns, "position": pd.concat([r.position for r, _ in stressed_results]),
                                         "trades": trades, "costs": c, "funding": f,
                                         "windows": [{**i, **cap} for (_, i), cap in zip(stressed_results, caps)]}))
    begin("comparisons")
    p["comparisons"] = comp = {}
    makers = {"buy_and_hold": buy_and_hold(), EMA: candidate_alone(EMA), BB: candidate_alone(BB),
              "risk_filter": risk_filter()}
    curves = {}
    for name, make in makers.items():
        curves[name] = curve(bars, funding, make, costs)
        if not curves[name]["returns"].index.equals(wf.returns.index):
            raise AssertionError(f"{name} har inte samma observationsperiod som H-0013")
        comp[name] = summary(curves[name])
    mix = mixed(curves[EMA], curves[BB])
    comp["equal_weight_mix"] = summary(mix)
    p["comparison_curves"] = comparison_curves(wf.returns, {**{k: v["returns"] for k, v in curves.items()},
                                                            "equal_weight_mix": mix["returns"]})
    p["steps"]["comparisons"] = "done"
    crit = done("criteria", criteria(main, stressed, comp["buy_and_hold"], {EMA: comp[EMA], BB: comp[BB]},
                                     comp["equal_weight_mix"]))
    begin("regimes")
    done("regimes", regime_results(bars, wf))
    begin("permutation")
    p["permutation"] = {"n": n_permutations, "seed": SEED, "runs": []}
    done("permutation", permutation_test(bars, funding, main["sharpe"], n_permutations, SEED, costs,
                                         sink=p["permutation"]["runs"]))
    begin("playbooks")
    p["playbooks"] = {"n": None, "playbooks": []}
    books81 = done("playbooks", all_playbooks(bars, funding, playbooks, costs, sink=p["playbooks"]["playbooks"]))
    begin("deflated_sharpe")
    done("deflated_sharpe", deflated(stats.daily_returns(wf.returns), books81))
    begin("random_label_t")
    oos = bars[bars.index >= fas2._ts(fas2.TEST_STARTS[0])]
    done("random_label_t", random_label_control(oos, seed=SEED))
    return {
        "hypothesis_id": HYPOTHESIS, "evaluation_version": EVALUATION_VERSION, "config": p["config"],
        "steps": p["steps"],
        "walk_forward": p["walk_forward"], "out_of_sample": [fas2.TEST_STARTS[0], fas2.HOLDOUT_START],
        "holdout": "2025-01-01 och framåt, oläst",
        "h0013": main, "stressed": stressed, "comparisons": comp, "comparison_curves": p["comparison_curves"],
        "criteria": crit, "decision": decision(crit),
        "t_required": T_REQUIRED, "registered_n": REGISTERED_N,
        "attempts_now": attempts_now, "t_required_now": stats.t_krav(attempts_now) if attempts_now else None,
        "regimes": p["regimes"], "permutation": p["permutation"],
        "deflated_sharpe": p["deflated_sharpe"], "playbooks": books81, "random_label_t": p["random_label_t"],
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


def code_revision(repo: Path) -> dict:
    """Den körda kodens commit, och om motorn hade ocommittade ändringar."""
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", "engine"],
                           capture_output=True, text=True)
    return {"commit": head.stdout.strip() or None, "engine_dirty": bool(dirty.stdout.strip())}


def data_fingerprint(bars: pd.DataFrame, funding: pd.Series) -> dict:
    """SHA-256 av de inlästa staplarna och finansieringsräntan (tid och värden), med period och antal."""
    h = hashlib.sha256()
    h.update(bars.index.asi8.tobytes())
    h.update(np.ascontiguousarray(bars[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)).tobytes())
    h.update(funding.index.asi8.tobytes())
    h.update(np.ascontiguousarray(funding.to_numpy(dtype=float)).tobytes())
    return {"sha256": h.hexdigest(), "bars": int(len(bars)), "funding": int(len(funding)),
            "first": bars.index.min().isoformat() if len(bars) else None,
            "last": bars.index.max().isoformat() if len(bars) else None}


def run(repo: Path, data_dir: Path | None = None, **kw) -> Path:
    """Den riktiga körningen: kräver registrerad H-0013 och sparar resultatet även om körningen avbryts.
    Ett avbrutet försök sparas med alla färdiga delresultat och stegstatus, men utan beslut."""
    reg = require_registered(HYPOTHESIS, repo)
    meta = {"hypothesis_id": HYPOTHESIS, "registry_commit": reg.registry_commit, "evaluation_version": EVALUATION_VERSION,
            "code_revision": code_revision(repo), "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    attempts = count_attempts((repo / "research" / "registry.md").read_text(encoding="utf-8"))
    progress: dict = {}
    try:
        bars, funding = fas2.load_development(data_dir or repo / "data")
        meta["data"] = data_fingerprint(bars, funding)
        result = evaluate(bars, funding, attempts_now=attempts, progress=progress, **kw)
    except BaseException as exc:
        record(repo / RESULTS, {**meta, **progress, "error": f"{type(exc).__name__}: {exc}"}, "aborted")
        raise
    return record(repo / RESULTS, {**meta, **result}, "completed")
