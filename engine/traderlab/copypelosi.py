"""Kör H-0017: kopiera Nancy Pelosis redovisade affärer (research/pelosi-protokoll.md).

Slutprovet läses aldrig in: bara redovisningar inlämnade före 2025-01-01 och kurser före samma dag.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import portfolio, stats
from .copy13f import COSTS, save
from .data import house, stocks
from .registry import require_registered

START, END = "2014-01-01", "2025-01-01"
HOLD_DAYS = 365


def holdings_after(events: list[tuple[pd.Timestamp, list[house.Trade]]], day: pd.Timestamp) -> set[str]:
    """Aktier med redovisat köp de senaste 365 dagarna (räknat på redovisningsdagen) utan senare hel försäljning."""
    last_buy: dict[str, pd.Timestamp] = {}
    last_sell: dict[str, pd.Timestamp] = {}
    for filed, trades in events:
        if filed >= day:
            break
        for t in trades:
            (last_buy if t.kind == "buy" else last_sell)[t.ticker] = filed
    return {tk for tk, b in last_buy.items()
            if (day - b).days <= HOLD_DAYS and not (tk in last_sell and last_sell[tk] >= b)}


def build_weights(events, opens: pd.DataFrame) -> pd.DataFrame:
    """Målvikter på dagen efter varje redovisning (beslut vid stängning av den dagen, fyllning nästa öppning
    görs av portfolio.run; därför läggs beslutet på första handelsdag med datum >= inlämningsdagen)."""
    days = opens.index
    rows = {}
    for filed, _ in events:
        pos = days.searchsorted(filed)
        if pos >= len(days):
            continue
        day = days[pos]
        held = [t for t in sorted(holdings_after(events, filed + pd.Timedelta(days=1)))
                if t in opens.columns and np.isfinite(opens.at[day, t])]
        rows[day] = {t: 1 / len(held) for t in held} if held else {"SPY": 1.0}
    # Innehav som löper ut (365 dagar) utan ny redovisning: kontrollera varje månadsskifte.
    month_starts = days[np.r_[True, days.month[1:] != days.month[:-1]]]
    for day in month_starts:
        if day in rows:
            continue
        held = [t for t in sorted(holdings_after(events, day)) if t in opens.columns and np.isfinite(opens.at[day, t])]
        rows[day] = {t: 1 / len(held) for t in held} if held else {"SPY": 1.0}
    return pd.DataFrame.from_dict(rows, orient="index").reindex(columns=opens.columns).fillna(0.0).sort_index()


def run(hypothesis_id: str, repo: Path, data_dir: Path | None = None) -> dict:
    reg = require_registered(hypothesis_id, repo)
    data_dir = data_dir or repo / "data"
    reps = [r for y in range(2013, 2025) for r in house.reports(y, data_dir) if START <= r.filed < END]
    events, unparsed, no_securities = [], [], []
    for r in reps:
        text = house.pdf_text(r, data_dir)
        trades = house.parse(text)
        if not trades:
            if text.strip() and not house.has_securities(text):
                no_securities.append(r.doc_id)
            elif house.rows_read(text) == 0:
                unparsed.append(r.doc_id)   # inskannad eller okänt format
            continue
        events.append((pd.Timestamp(r.filed, tz="UTC"), trades))
    events.sort(key=lambda e: e[0])
    tickers = sorted({t.ticker for _, tr in events for t in tr if t.kind == "buy"})
    lo, hi = pd.Timestamp(START, tz="UTC") - pd.Timedelta(days=10), pd.Timestamp(END, tz="UTC")
    opens, missing = {}, []
    for t in tickers + ["SPY"]:
        df = stocks.load_prices(t, data_dir)
        if df is None:
            missing.append(t)
            continue
        df = df[(df.index >= lo) & (df.index < hi)]
        if len(df):
            opens[t] = df["open"]
        else:
            missing.append(t)
    panel = pd.DataFrame(opens).sort_index()
    panel = panel[panel["SPY"].notna()]
    assert panel.index.max() < hi, "Slutprovet får inte läsas in."
    w = build_weights(events, panel)
    w = w[w.index >= pd.Timestamp(START, tz="UTC")]
    normal = portfolio.run(panel, w, COSTS)
    stressed = portfolio.run(panel, w, COSTS.stressed())
    spy_ret = (panel["SPY"].shift(-1) / panel["SPY"] - 1).reindex(normal.equity.index).fillna(0.0)
    keep = normal.equity.index > w.index[0]
    port_d = stats.daily_returns(normal.bar_returns[keep])
    spy_d = stats.daily_returns(spy_ret[keep])
    excess = (port_d - spy_d).dropna()
    eq = normal.equity[keep] / normal.equity[keep].iloc[0]
    spy_eq = (1 + spy_ret[keep]).cumprod()
    buys = [t for _, tr in events for t in tr if t.kind == "buy"]
    priced_share = sum(1 for t in buys if t.ticker in panel.columns) / max(len(buys), 1)
    parsed_share = 1 - len(unparsed) / max(len(reps) - len(no_securities), 1)
    t_req = stats.t_krav(reg.attempts)
    out = {
        "hypothesis_id": hypothesis_id, "registry_commit": reg.registry_commit,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "phase": "pelosi", "track": "A",
        "period": [str(eq.index[0].date()), str(eq.index[-1].date())],
        "reports": len(reps), "reports_parsed": len(events), "reports_unparsed": unparsed,
        "reports_without_securities": no_securities,
        "buys": len(buys), "sells": sum(1 for _, tr in events for t in tr if t.kind == "sell"),
        "tickers": tickers, "tickers_without_prices": missing,
        "parsed_share": parsed_share, "priced_buy_share": priced_share,
        "data_quality_ok": parsed_share >= 0.9 and priced_share >= 0.9,
        "total_return": float(eq.iloc[-1] - 1), "spy_total_return": float(spy_eq.iloc[-1] - 1),
        "stressed_total_return": float((stressed.equity[keep] / stressed.equity[keep].iloc[0]).iloc[-1] - 1),
        "sharpe": float(stats.sharpe(port_d)), "spy_sharpe": float(stats.sharpe(spy_d)),
        "max_drawdown": float(stats.max_drawdown(eq)), "spy_max_drawdown": float(stats.max_drawdown(spy_eq)),
        "t_excess_nw": float(stats.newey_west_t(excess)), "t_required": t_req, "attempts": reg.attempts,
        "excess_per_year": float(excess.mean() * 252), "rebalances": int(len(w)),
        "share_of_days_in_spy": float((w["SPY"] == 1.0).mean()) if "SPY" in w else 0.0,
        "curve": {"t": [d.isoformat() for d in eq.index[::5]], "strategy": [round(float(v) * 100, 3) for v in eq.iloc[::5]],
                  "spy": [round(float(v) * 100, 3) for v in spy_eq.iloc[::5]]},
        "events": [{"filed": str(f.date()), "trades": [t.__dict__ for t in tr]} for f, tr in events],
        "simulated": False,
    }
    out["criteria"] = {"t_excess_at_least_required": out["t_excess_nw"] >= t_req,
                       "stressed_beats_spy": out["stressed_total_return"] > out["spy_total_return"],
                       "sharpe_above_spy": out["sharpe"] > out["spy_sharpe"]}
    out["meets_all_criteria"] = all(out["criteria"].values())
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--hypothesis", default="H-0017")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--data-only", action="store_true", help="Hämta och tolka redovisningarna, räkna inget resultat")
    a = ap.parse_args()
    if a.data_only:
        data_dir = a.repo / "data"
        reps = [r for y in range(2013, 2025) for r in house.reports(y, data_dir) if START <= r.filed < END]
        texts = {r.doc_id: house.pdf_text(r, data_dir) for r in reps}
        parsed = [(r, house.parse(texts[r.doc_id])) for r in reps]
        ok = [p for p in parsed if p[1]]
        nosec = [r for r, tr in parsed if not tr and texts[r.doc_id].strip() and not house.has_securities(texts[r.doc_id])]
        print(f"utan värdepapper (t.ex. fastigheter): {len(nosec)}; tolkade av de med värdepapper: "
              f"{len(ok) / max(len(reps) - len(nosec), 1):.0%}")
        buys = [t for _, tr in ok for t in tr if t.kind == "buy"]
        print(f"redovisningar {len(reps)}, tolkade {len(ok)} ({len(ok) / max(len(reps), 1):.0%}), köp {len(buys)}, "
              f"sälj {sum(1 for _, tr in ok for t in tr if t.kind == 'sell')}, aktier {len({t.ticker for t in buys})}")
        rest = [p for p in parsed if not p[1] and p[0] not in nosec and house.rows_read(texts[p[0].doc_id]) == 0]
        print(f"lästa (rader hittade eller inga värdepapper): {1 - len(rest) / max(len(reps) - len(nosec), 1):.0%}")
        print("otolkade:", [r.doc_id for r, _ in rest][:30])
        # Utdrag ur några otolkade (offentlig text), för att förbättra tolkningen. Inga resultat räknas.
        for r, _ in rest[:4]:
            text = house.pdf_text(r, data_dir)
            print(f"--- {r.doc_id} ({r.filed}), {len(text)} tecken ---")
            print(text[:1800])
        return
    print(save(a.repo, run(a.hypothesis, a.repo)))


if __name__ == "__main__":
    main()
