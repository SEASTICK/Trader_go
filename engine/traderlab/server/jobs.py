"""Kör köade backtester från tabellen runs och skriver resultatet till run_results och run_trades.

En körning som köas från appen är alltid 'exploration' (utforskning): den räknas som försök men kan aldrig bli ett
beslut. Registrerade hypoteser körs från repot (traderlab.fas1) och laddas upp av registry_sync.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd

from .. import backtest, metrics
from ..costs import CostModel
from ..strategies.rules import SPECS
from .supa import Supabase

log = logging.getLogger("tradergo.jobs")


def load_bars(db: Supabase, market: str, symbol: str, interval: str, end: str) -> pd.DataFrame:
    rows = db.select_all("candles", {"select": "open_time,open,high,low,close,volume", "provider": "eq.binance",
                                     "market": f"eq.{market}", "symbol": f"eq.{symbol}", "interval": f"eq.{interval}",
                                     "closed": "eq.true", "open_time": f"lt.{end}", "order": "open_time.asc"})
    if not rows:
        raise ValueError(f"Inga staplar för {market} {symbol} {interval} i databasen än.")
    df = pd.DataFrame(rows)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("open_time"), utc=True))
    return df.astype(float)


def load_funding(db: Supabase, symbol: str, end: str) -> pd.Series:
    rows = db.select_all("funding_rates", {"select": "funding_time,rate", "symbol": f"eq.{symbol}",
                                           "funding_time": f"lt.{end}", "order": "funding_time.asc"})
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series([r["rate"] for r in rows], index=pd.DatetimeIndex(pd.to_datetime([r["funding_time"] for r in rows], utc=True)))


def claim(db: Supabase) -> dict | None:
    """Tar den äldsta köade körningen. Uppdateringen kräver status=queued, så två workers kan inte ta samma."""
    for run in db.select("runs", {"select": "*", "status": "eq.queued", "order": "created_at.asc", "limit": 5}):
        got = db.update("runs", {"id": f"eq.{run['id']}", "status": "eq.queued"},
                        {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()})
        if got:
            return got[0]
    return None


def execute(db: Supabase, run: dict) -> None:
    spec = SPECS.get(run["strategy"])
    if spec is None or spec.version != run["version"]:
        raise ValueError(f"Okänd strategi eller version: {run['strategy']}@{run['version']}")
    params = run.get("params") or {}
    start, end = pd.Timestamp(run["period_start"]), pd.Timestamp(run["period_end"])
    bars = load_bars(db, run["market"], run["symbol"], run["interval"], end.isoformat())
    funding = load_funding(db, run["symbol"], end.isoformat()) if run["market"] == "um" else None
    costs = CostModel(**(run.get("costs") or {}))
    sig = spec.signals(bars, params)
    first = max(0, int((bars.index >= start).argmax()) - 1)
    b = bars.iloc[first:]
    tgt = sig.target.iloc[first:].copy()
    if first == 0:
        tgt.iloc[0] = 0.0
    res = backtest.run(b, tgt, costs, funding=funding,
                       stop_distance=None if sig.stop_distance is None else sig.stop_distance.iloc[first:],
                       take_profit_distance=None if sig.take_profit_distance is None else sig.take_profit_distance.iloc[first:])
    stats = metrics.full_stats(res, b, start_capital=float(run.get("capital") or 100_000))
    if db.select("runs", {"select": "status", "id": f"eq.{run['id']}"})[0]["status"] == "cancelled":
        log.info("körning %s avbröts, inget sparas", run["id"])
        return
    db.upsert("run_results", [{"run_id": run["id"], "stats": stats, "criteria": None, "curves": metrics.curves(res),
                               "windows": None}], "run_id")
    trades = [{"run_id": run["id"], "n": i + 1, "side": t.side, "entry_time": t.entry_time.isoformat(),
               "entry_price": t.entry_price, "exit_time": t.exit_time.isoformat() if t.exit_time is not None else None,
               "exit_price": t.exit_price, "net_return": t.net_return, "exit_reason": t.exit_reason}
              for i, t in enumerate(res.trades)]
    if trades:
        db.upsert("run_trades", trades, "run_id,n")
    db.update("runs", {"id": f"eq.{run['id']}"}, {"status": "done", "progress": 1.0, "run_key": spec.run_id(params),
                                                   "finished_at": datetime.now(timezone.utc).isoformat()}, returning=False)


def process_one(db: Supabase) -> bool:
    run = claim(db)
    if run is None:
        return False
    try:
        execute(db, run)
    except Exception as exc:
        log.exception("körning %s misslyckades", run["id"])
        db.update("runs", {"id": f"eq.{run['id']}"}, {"status": "failed", "error": str(exc)[:2000],
                                                       "finished_at": datetime.now(timezone.utc).isoformat()}, returning=False)
    return True
