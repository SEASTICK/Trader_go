"""Workern testas mot en låtsasdatabas i minnet och låtsade Binance-svar. Inget nätverk."""
import json
from pathlib import Path

import pandas as pd
import pytest

from traderlab.server import jobs, registry_sync, sync
from traderlab.server.supa import Supabase
from traderlab.synthetic import make_bars


class FakeDB:
    """Förstår filtren eq., lt. samt order och limit, som workern använder."""
    def __init__(self):
        self.t: dict[str, list[dict]] = {}

    def _match(self, row, params):
        for k, v in (params or {}).items():
            if k in ("select", "order", "limit", "offset"):
                continue
            op, _, val = str(v).partition(".")
            cur = row.get(k)
            if op == "eq" and str(cur).lower() != val.lower():
                return False
            if op == "lt" and not (str(cur) < val):
                return False
        return True

    def select(self, table, params=None):
        rows = [r for r in self.t.get(table, []) if self._match(r, params)]
        if params and "order" in params:
            col, _, d = params["order"].partition(".")
            rows.sort(key=lambda r: r[col], reverse=d == "desc")
        off = int((params or {}).get("offset", 0))
        lim = (params or {}).get("limit")
        rows = rows[off:]
        rows = rows[: int(lim)] if lim else rows
        cols = (params or {}).get("select", "*")
        return [dict(r) if cols == "*" else {c: r.get(c) for c in cols.split(",")} for r in rows]

    select_all = select

    def upsert(self, table, rows, on_conflict, batch=1000):
        keys = on_conflict.split(",")
        cur = self.t.setdefault(table, [])
        for r in rows:
            for i, old in enumerate(cur):
                if all(old.get(k) == r.get(k) for k in keys):
                    cur[i] = {**old, **r}
                    break
            else:
                cur.append(dict(r))
        return len(rows)

    def update(self, table, filters, values, returning=True):
        out = []
        for r in self.t.get(table, []):
            if self._match(r, filters):
                r.update(values)
                out.append(dict(r))
        return out if returning else []


def kline(open_ms, o, h, l, c, step):
    return [open_ms, str(o), str(h), str(l), str(c), "10", open_ms + step - 1]


def test_client_builds_postgrest_requests():
    seen = []
    def opener(req):
        seen.append(req)
        return b"[]"
    db = Supabase("https://x.supabase.co", "secret", opener)
    db.upsert("candles", [{"a": 1}], "provider,open_time")
    r = seen[0]
    assert r.full_url == "https://x.supabase.co/rest/v1/candles?on_conflict=provider,open_time"
    assert r.get_method() == "POST" and r.headers["Prefer"].startswith("resolution=merge-duplicates")
    assert r.headers["Authorization"] == "Bearer secret"


def test_sync_is_incremental_and_marks_open_bar():
    db, step = FakeDB(), sync.STEP_MS["4h"]
    t0 = sync._ms("2026-01-01T00:00:00+00:00")
    now = t0 + 3 * step + 100   # tre stängda staplar, den fjärde pågår
    calls, clock = [], {"now": now}

    def fetch(url):
        calls.append(url)
        start = int(url.split("startTime=")[1].split("&")[0])
        return [kline(t, 100, 101, 99, 100.5, step) for t in range(start, clock["now"], step)]

    sync.START["um"] = "2026-01-01"
    n = sync.sync_series(db, "um", "BTCUSDT", "4h", fetch, now_ms=now, pause=0)
    rows = db.t["candles"]
    assert n == 4 and [r["closed"] for r in rows] == [True, True, True, False]
    # Nästa synk börjar efter senaste stängda stapel och stänger den pågående.
    clock["now"] = now + step
    sync.sync_series(db, "um", "BTCUSDT", "4h", fetch, now_ms=now + step, pause=0)
    assert f"startTime={t0 + 3 * step}" in calls[-1]
    assert len(db.t["candles"]) == 5 and db.t["candles"][3]["closed"] is True


def test_sync_skips_broken_bars():
    rows = sync.rows_from_klines("spot", "BTCUSDT", "1h", [kline(0, 100, 99, 98, 100, 3600000)], now_ms=10**13)
    assert rows == []


def test_registry_parse_takes_latest_decision_and_track():
    md = """| id | datum | commit | hypotes | beslut |
|---|---|---|---|---|
| H-0003 | 2026-11-01 | a | Volstyrd | |
| H-0003 | 2026-11-01 | b | OGILTIG KÖRNING | OGILTIG |
| H-0003 | 2026-11-01 | c | Resultat | REJECT |
| H-0006 | 2026-11-01 | d | Spår B (lägre risk). Trend | |
"""
    rows = {r["id"]: r for r in registry_sync.parse_registry(md)}
    assert rows["H-0003"]["decision"] == "REJECT" and rows["H-0003"]["registry_commit"] == "a"
    assert rows["H-0006"]["track"] == "B" and rows["H-0006"]["decision"] is None


def test_real_registry_parses():
    repo = Path(__file__).resolve().parents[2]
    rows = registry_sync.parse_registry((repo / "research/registry.md").read_text())
    assert len(rows) >= 12 and all(r["registered_at"] for r in rows)


def _db_with_bars():
    db = FakeDB()
    bars = make_bars(1200, interval="4h", seed=3, vol=0.02, start="2024-01-01")
    db.upsert("candles", [{"provider": "binance", "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
                           "open_time": t.isoformat(), "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                           "volume": r.volume, "closed": True} for t, r in bars.iterrows()],
              "provider,market,symbol,interval,open_time")
    return db, bars


def test_queued_exploration_runs_and_writes_results():
    db, bars = _db_with_bars()
    db.t["runs"] = [{"id": "r1", "kind": "exploration", "status": "queued", "created_at": "1", "strategy": "donchian_breakout",
                     "version": "1.0.0", "params": {"entry_n": 30}, "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
                     "period_start": bars.index[400].isoformat(), "period_end": bars.index[1100].isoformat(),
                     "capital": 100000, "costs": {"fee_bps": 10, "spread_bps": 2, "slippage_bps": 5}}]
    assert jobs.process_one(db) is True
    run = db.t["runs"][0]
    assert run["status"] == "done" and run["run_key"].startswith("donchian_breakout@1.0.0#")
    res = db.t["run_results"][0]
    assert res["stats"]["start_capital"] == 100000 and res["criteria"] is None
    assert all(t["entry_time"] >= bars.index[400].isoformat() for t in db.t.get("run_trades", []))
    assert jobs.process_one(db) is False   # kön är tom


def test_failed_run_is_marked_with_error():
    db, bars = _db_with_bars()
    db.t["runs"] = [{"id": "r2", "kind": "exploration", "status": "queued", "created_at": "1", "strategy": "finns_inte",
                     "version": "1.0.0", "params": {}, "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
                     "period_start": bars.index[10].isoformat(), "period_end": bars.index[100].isoformat()}]
    jobs.process_one(db)
    assert db.t["runs"][0]["status"] == "failed" and "Okänd strategi" in db.t["runs"][0]["error"]


def test_worker_has_no_order_or_key_code():
    src = "".join(p.read_text() for p in (Path(jobs.__file__).parent).glob("*.py"))
    for bad in ("/api/v3/order", "/fapi/v1/order", "X-MBX-APIKEY", "signature=", "/account", "withdraw"):
        assert bad not in src
