"""Papper framåt: 100 000 USD som följer de tio investerarnas 13F-innehav från startdagen.

Samma regler som H-0016 (research/13f-protokoll.md): topp 10 per förvaltare viktade efter värde, lika vikt per
förvaltare, ombalansering vid öppningen första handelsdagen efter en ny redovisning, 10 bp per sida.

Detta är en **observation**, inte ett godkänt test: inga riktiga pengar, inga order. Tillståndet ligger i
research/paper/13f-observation.json och skrivs bara framåt. Varje körning är deterministisk: samma redovisningar
och kurser ger samma resultat, så den kan köras om hur många gånger som helst.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .copy13f import COSTS, MANAGERS, STALE_DAYS, TOP
from .data import ftd, sec13f, stocks

STATE = Path("research/paper/13f-observation.json")
APP = Path("app/data/paper13f.json")
START_CAPITAL = 100_000.0


def _latest_filings(data_dir: Path, since: str) -> list[tuple[pd.Timestamp, int, str, dict]]:
    """Alla ursprungliga 13F-HR inlämnade från `since` (tidigare kvartal behövs som utgångsläge)."""
    out = []
    for cik in MANAGERS:
        for f in sec13f.list_filings(cik, data_dir, refresh=True):
            if f.filed >= since:
                rows = sec13f.holdings(f, data_dir)
                out.append((pd.Timestamp(f.filed, tz="UTC"), cik, f.accession, rows))
    return sorted(out, key=lambda x: (x[0], x[1]))


def _target(latest: dict[int, tuple[pd.Timestamp, dict]], day: pd.Timestamp, tickers: dict, priced) -> dict[str, float]:
    active = {c: v for c, v in latest.items() if (day - v[0]).days <= STALE_DAYS}
    target: dict[str, float] = {}
    for c, (_, rows) in active.items():
        w = sec13f.top_weights(rows, TOP)
        ok = {tickers.get(cu): x for cu, x in w.items() if tickers.get(cu) and priced(tickers.get(cu))}
        s = sum(ok.values())
        for t, x in ok.items():
            target[t] = target.get(t, 0.0) + x / s / len(active)
    tot = sum(target.values())
    return {t: v / tot for t, v in target.items()} if tot else {}


def update(repo: Path, start: str, data_dir: Path | None = None, today: pd.Timestamp | None = None) -> dict:
    data_dir = data_dir or repo / "data"
    start_ts = pd.Timestamp(start, tz="UTC")
    # Utgångsläget kräver redovisningar upp till ett halvår före start (senaste per förvaltare).
    filings = _latest_filings(data_dir, (start_ts - pd.Timedelta(days=STALE_DAYS)).strftime("%Y-%m-%d"))
    fmap = ftd.load_map(data_dir)
    cusips = {cu for _, _, _, rows in filings for cu in sec13f.top_weights(rows, TOP)}
    tickers = {cu: fmap.get(cu) for cu in cusips}
    prices: dict[str, pd.DataFrame] = {}
    for t in sorted({t for t in tickers.values() if t} | {"SPY"}):
        df = stocks.load_prices(t, data_dir, max_age_hours=12)
        if df is not None:
            prices[t] = df[df.index >= start_ts - pd.Timedelta(days=10)]
    spy = prices["SPY"]
    days = spy.index[spy.index >= start_ts]
    if today is not None:
        days = days[days <= today]
    opens = pd.DataFrame({t: p["open"] for t, p in prices.items()}).reindex(days)
    closes = pd.DataFrame({t: p["close"] for t, p in prices.items()}).reindex(days)

    latest: dict[int, tuple[pd.Timestamp, dict]] = {}
    pending = [f for f in filings]
    shares: dict[str, float] = {}
    cash = START_CAPITAL
    history, events = [], []
    first = True
    for day in days:
        # Redovisningar inlämnade före dagens öppning gäller från i dag (nästa handelsdag efter inlämning).
        new = [f for f in pending if f[0] < day]
        pending = [f for f in pending if f[0] >= day]
        for filed, cik, acc, rows in new:
            latest[cik] = (filed, rows)
            if filed >= start_ts:
                events.append({"day": str(day.date()), "filed": str(filed.date()), "manager": MANAGERS[cik],
                               "accession": acc, "top10": [{"ticker": tickers.get(cu), "weight": round(w, 4)}
                                                           for cu, w in sec13f.top_weights(rows, TOP).items()]})
        if new or first:
            o = opens.loc[day]
            value = cash + sum(n * o.get(t, np.nan) for t, n in shares.items() if np.isfinite(o.get(t, np.nan)))
            target = _target(latest, day, tickers, lambda t: t in o.index and np.isfinite(o[t]))
            if target:
                traded = 0.0
                new_shares = {t: value * w / o[t] for t, w in target.items()}
                for t in set(shares) | set(new_shares):
                    px = o.get(t, np.nan)
                    if np.isfinite(px):
                        traded += abs(new_shares.get(t, 0.0) - shares.get(t, 0.0)) * px
                cost = traded * COSTS.per_side
                value -= cost
                shares = {t: value * w / o[t] for t, w in target.items()}
                cash = 0.0
                first = False
        c = closes.loc[day]
        value = cash + sum(n * c[t] for t, n in shares.items() if t in c.index and np.isfinite(c[t]))
        history.append({"day": str(day.date()), "value": round(float(value), 2),
                        "spy": round(float(START_CAPITAL * c["SPY"] / closes["SPY"].iloc[0]), 2)})
    last_close = closes.iloc[-1] if len(closes) else pd.Series(dtype=float)
    holdings = sorted(({"ticker": t, "shares": round(n, 4), "value": round(float(n * last_close.get(t, np.nan)), 2)}
                       for t, n in shares.items() if np.isfinite(last_close.get(t, np.nan))), key=lambda h: -h["value"])
    state = {
        "kind": "observation", "note": "Papper, inga riktiga pengar. Observation, inte ett godkänt test.",
        "rules": "research/13f-protokoll.md", "start": start, "start_capital": START_CAPITAL,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "managers": list(MANAGERS.values()),
        "value": history[-1]["value"] if history else START_CAPITAL,
        "spy_value": history[-1]["spy"] if history else START_CAPITAL,
        "holdings": holdings, "history": history, "events": events[-50:],
    }
    for p in (repo / STATE, repo / APP):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return state


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-11-05")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    a = ap.parse_args()
    try:
        s = update(a.repo, a.start)
    except stocks.PriceSourceUnavailable as exc:
        print(f"Ingen uppdatering: kurskällan svarar inte ({exc}). Sätt hemligheten TIINGO_API_KEY.")
        return
    print(f"värde {s['value']:.2f} USD (SPY {s['spy_value']:.2f}), {len(s['holdings'])} innehav, "
          f"{len(s['events'])} nya redovisningar sedan start")


if __name__ == "__main__":
    main()
