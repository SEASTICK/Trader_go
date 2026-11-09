"""Kör H-0016: kopiera tio investerares största 13F-innehav (research/13f-protokoll.md).

Slutprovet läses aldrig in: bara redovisningar inlämnade före 2025-01-01 och kurser före samma dag används.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import portfolio, stats
from .costs import CostModel
from .data import ftd, sec13f, stocks
from .experiment import RESULTS
from .registry import require_registered

MANAGERS = {1067983: "Berkshire Hathaway", 1061768: "Baupost Group", 1336528: "Pershing Square", 1112520: "Akre Capital",
            1096343: "Markel Group", 1709323: "Himalaya Capital", 1656456: "Appaloosa", 1040273: "Third Point",
            1418814: "ValueAct", 1536411: "Duquesne Family Office"}
START, END = "2014-01-01", "2025-01-01"
COSTS = CostModel(fee_bps=5, spread_bps=4, slippage_bps=3)   # 10 bp per sida
STALE_DAYS = 200
TOP = 10


def manager_events(cik: int, data_dir: Path) -> list[tuple[pd.Timestamp, dict[str, float]]]:
    """(inlämningsdag, topp-10-vikter per CUSIP) för varje ursprunglig 13F-HR före slutprovet."""
    out = []
    # Samma inlämningsdag: den med senast avsedda kvartal kommer sist och gäller (den nyaste bilden av innehaven).
    for f in sorted(sec13f.list_filings(cik, data_dir), key=lambda f: (f.filed, f.period or "")):
        if not ("2013-07-01" <= f.filed < END):
            continue
        w = sec13f.top_weights(sec13f.holdings(f, data_dir), TOP)
        if w:
            out.append((pd.Timestamp(f.filed, tz="UTC"), w))
    return out


def build_weights(events: dict[int, list], tickers: dict[str, str | None], opens: pd.DataFrame,
                  ) -> tuple[pd.DataFrame, list[dict]]:
    """Målvikter per beslutsdag. Beslutsdagen är första handelsdag på eller efter inlämningsdagen; fyllning sker
    vid nästa öppning (portfolio.run). Innehav utan kurs den dagen tas bort och förvaltarens vikt fördelas om."""
    days = opens.index
    # Sortera på dag och förvaltare; ordningen inom samma dag och förvaltare behålls (vikterna jämförs aldrig).
    flat = sorted(((d, cik, w) for cik, evs in events.items() for d, w in evs), key=lambda e: (e[0], e[1]))
    latest: dict[int, tuple[pd.Timestamp, dict]] = {}
    rows, log = {}, []
    for filed, cik, w in flat:
        latest[cik] = (filed, w)
        pos = days.searchsorted(filed)
        if pos >= len(days):
            continue
        day = days[pos]
        target: dict[str, float] = {}
        active = {c: v for c, v in latest.items() if (day - v[0]).days <= STALE_DAYS}
        missing_total = 0.0
        for c, (_, wc) in active.items():
            priced = {tickers.get(cu): x for cu, x in wc.items()
                      if tickers.get(cu) in opens.columns and np.isfinite(opens.at[day, tickers.get(cu)])}
            missing_total += 1 - sum(priced.values())
            s = sum(priced.values())
            if s <= 0:
                continue
            for t, x in priced.items():
                target[t] = target.get(t, 0.0) + x / s / len(active)
        tot = sum(target.values())
        if tot > 0:
            rows[day] = {t: v / tot for t, v in target.items()}
            log.append({"day": str(day.date()), "manager": MANAGERS.get(cik, str(cik)), "managers_active": len(active),
                        "unpriced_share": round(missing_total / max(len(active), 1), 4)})
    w = pd.DataFrame.from_dict(rows, orient="index").reindex(columns=opens.columns).fillna(0.0).sort_index()
    return w, log


def run(hypothesis_id: str, repo: Path, data_dir: Path | None = None, managers: list[int] | None = None,
        diagnostic: bool = False) -> dict:
    reg = require_registered(hypothesis_id, repo)
    data_dir = data_dir or repo / "data"
    ciks = managers or list(MANAGERS)
    events = {c: manager_events(c, data_dir) for c in ciks}
    cusips = sorted({cu for evs in events.values() for _, w in evs for cu in w})
    # CUSIP → ticker ur SEC:s egna fails-to-deliver-filer (historiska, täcker även avnoterade bolag).
    fmap = ftd.load_map(data_dir)
    tickers = {c: fmap.get(c) for c in cusips}
    lo, hi = pd.Timestamp(START, tz="UTC") - pd.Timedelta(days=10), pd.Timestamp(END, tz="UTC")
    opens = {}
    for t in sorted({t for t in tickers.values() if t} | {"SPY"}):
        df = stocks.load_prices(t, data_dir)
        if df is not None:
            df = df[(df.index >= lo) & (df.index < hi)]
            if len(df):
                opens[t] = df["open"]
    panel = pd.DataFrame(opens).sort_index()
    panel = panel[panel["SPY"].notna()]   # handelsdagar enligt SPY
    assert panel.index.max() < hi, "Slutprovet får inte läsas in."
    w, log = build_weights(events, tickers, panel.drop(columns=["SPY"]))
    w = w[w.index >= pd.Timestamp(START, tz="UTC")]
    opens_ = panel.drop(columns=["SPY"])
    normal = portfolio.run(opens_, w, COSTS)
    stressed = portfolio.run(opens_, w, COSTS.stressed())
    spy = panel["SPY"]
    spy_ret = (spy.shift(-1) / spy - 1).reindex(normal.equity.index).fillna(0.0)
    first = w.index[0]
    keep = normal.equity.index > first
    port_d = stats.daily_returns(normal.bar_returns[keep])
    spy_d = stats.daily_returns(spy_ret[keep])
    excess = (port_d - spy_d).dropna()
    eq = normal.equity[keep] / normal.equity[keep].iloc[0]
    spy_eq = (1 + spy_ret[keep]).cumprod()
    t_req = stats.t_krav(reg.attempts)
    out = {
        "hypothesis_id": hypothesis_id, "registry_commit": reg.registry_commit, "diagnostic": diagnostic,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "phase": "13f", "track": "A",
        "managers": [MANAGERS.get(c, str(c)) for c in ciks],
        "period": [str(eq.index[0].date()), str(eq.index[-1].date())],
        "filings": sum(len(v) for v in events.values()), "rebalances": int(len(w)),
        "cusips": len(cusips), "cusips_without_ticker": sum(1 for v in tickers.values() if not v),
        "tickers_without_prices": sorted({t for t in tickers.values() if t and t not in panel.columns}),
        "mean_unpriced_share": float(np.mean([r["unpriced_share"] for r in log])) if log else None,
        "total_return": float(eq.iloc[-1] - 1), "spy_total_return": float(spy_eq.iloc[-1] - 1),
        "stressed_total_return": float((stressed.equity[keep] / stressed.equity[keep].iloc[0]).iloc[-1] - 1),
        "sharpe": float(stats.sharpe(port_d)), "spy_sharpe": float(stats.sharpe(spy_d)),
        "max_drawdown": float(stats.max_drawdown(eq)), "spy_max_drawdown": float(stats.max_drawdown(spy_eq)),
        "t_excess_nw": float(stats.newey_west_t(excess)), "t_required": t_req, "attempts": reg.attempts,
        "excess_per_year": float(excess.mean() * 252), "turnover_per_year": float(normal.turnover.sum() / max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)),
        "costs": normal.total_costs,
        "last_holdings": {k: round(v, 4) for k, v in sorted(w.iloc[-1].items(), key=lambda kv: -kv[1]) if v > 0},
        "curve": {"t": [d.isoformat() for d in eq.index[::5]], "strategy": [round(float(v) * 100, 3) for v in eq.iloc[::5]],
                  "spy": [round(float(v) * 100, 3) for v in spy_eq.iloc[::5]]},
        "rebalance_log": log[-60:], "simulated": False,
    }
    out["criteria"] = {"t_excess_at_least_required": out["t_excess_nw"] >= t_req,
                       "stressed_beats_spy": out["stressed_total_return"] > out["spy_total_return"],
                       "sharpe_above_spy": out["sharpe"] > out["spy_sharpe"]}
    out["meets_all_criteria"] = all(out["criteria"].values())
    # Datakrav i protokollet: minst 90 % av vikten måste ha pris, annars ogiltig körning utan beslut.
    out["data_quality_ok"] = out["mean_unpriced_share"] is not None and out["mean_unpriced_share"] <= 0.10
    return out


def main() -> None:
    """Kör H-0016 och diagnostiken (varje förvaltare ensam) och sparar resultaten. Används av research-13f.yml."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--hypothesis", default="H-0016")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args()
    main_out = run(a.hypothesis, a.repo)
    paths = [save(a.repo, main_out)]
    diag = {}
    for cik, name in MANAGERS.items():
        try:
            d = run(a.hypothesis, a.repo, managers=[cik], diagnostic=True)
        except Exception as exc:   # en förvaltare utan data stoppar inte resten
            diag[name] = {"error": str(exc)}
            continue
        diag[name] = {k: d[k] for k in ("period", "total_return", "spy_total_return", "sharpe", "spy_sharpe",
                                        "t_excess_nw", "max_drawdown", "mean_unpriced_share", "rebalances")}
    main_out_path = paths[0]
    data = json.loads(main_out_path.read_text())
    data["diagnostic_per_manager"] = diag
    main_out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    print(main_out_path)


def save(repo: Path, out: dict, suffix: str = "") -> Path:
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{out["hypothesis_id"]}{suffix}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    main()
