"""Inkrementell synk av publik marknadsdata till Supabase (tabellerna candles och funding_rates).

Spot via data-api.binance.vision och terminer via fapi.binance.com, bara publika marknadsdata-anrop utan nycklar.
Pågående stapel sparas med closed = false och skrivs över när den stängt. Hämtningen börjar efter den senaste
stängda stapeln, så en stängd stapel hämtas och skrivs aldrig om.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone

from .supa import Supabase

log = logging.getLogger("tradergo.sync")

SPOT = "https://data-api.binance.vision/api/v3/klines"
PERP = "https://fapi.binance.com/fapi/v1/klines"
FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate"
SERIES = [("spot", "BTCUSDT", "1h"), ("spot", "BTCUSDT", "4h"), ("spot", "BTCUSDT", "1d"), ("um", "BTCUSDT", "4h")]
START = {"spot": "2017-08-17", "um": "2020-01-01"}
STEP_MS = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}

Fetch = Callable[[str], list]


def _get(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "tradergo-research/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _ms(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() * 1000)


def klines_url(market: str, symbol: str, interval: str, start_ms: int, limit: int) -> str:
    base = SPOT if market == "spot" else PERP
    return base + "?" + urllib.parse.urlencode({"symbol": symbol, "interval": interval, "startTime": start_ms, "limit": limit})


def rows_from_klines(market: str, symbol: str, interval: str, data: list, now_ms: int) -> list[dict]:
    out = []
    for k in data:
        open_ms, close_ms = int(k[0]), int(k[6])
        o, h, l, c, v = (float(x) for x in k[1:6])
        if not (l <= min(o, c) and h >= max(o, c) and v >= 0):
            log.warning("felaktig stapel %s %s %s %s hoppas över", market, symbol, interval, _iso(open_ms))
            continue
        out.append({"provider": "binance", "market": market, "symbol": symbol, "interval": interval,
                    "open_time": _iso(open_ms), "open": o, "high": h, "low": l, "close": c, "volume": v,
                    "closed": close_ms < now_ms})
    return out


def last_closed(db: Supabase, market: str, symbol: str, interval: str) -> int | None:
    rows = db.select("candles", {"select": "open_time", "provider": "eq.binance", "market": f"eq.{market}",
                                 "symbol": f"eq.{symbol}", "interval": f"eq.{interval}", "closed": "eq.true",
                                 "order": "open_time.desc", "limit": 1})
    return _ms(rows[0]["open_time"]) if rows else None


def sync_series(db: Supabase, market: str, symbol: str, interval: str, fetch: Fetch = _get,
                now_ms: int | None = None, limit: int = 1000, pause: float = 0.2) -> int:
    """Hämtar från senaste stängda stapel och framåt. Returnerar antal skrivna rader."""
    now_ms = now_ms or int(time.time() * 1000)
    last = last_closed(db, market, symbol, interval)
    start = (last + STEP_MS[interval]) if last is not None else _ms(START[market] + "T00:00:00+00:00")
    written = 0
    while start <= now_ms:
        data = fetch(klines_url(market, symbol, interval, start, limit))
        if not data:
            break
        rows = rows_from_klines(market, symbol, interval, data, now_ms)
        written += db.upsert("candles", rows, "provider,market,symbol,interval,open_time")
        nxt = int(data[-1][0]) + STEP_MS[interval]
        if nxt <= start or len(data) < limit:
            break
        start = nxt
        time.sleep(pause)
    return written


def sync_funding(db: Supabase, symbol: str = "BTCUSDT", fetch: Fetch = _get, limit: int = 1000, pause: float = 0.2) -> int:
    rows = db.select("funding_rates", {"select": "funding_time", "symbol": f"eq.{symbol}", "order": "funding_time.desc", "limit": 1})
    start = _ms(rows[0]["funding_time"]) + 1 if rows else _ms(START["um"] + "T00:00:00+00:00")
    written = 0
    while True:
        data = fetch(FUNDING + "?" + urllib.parse.urlencode({"symbol": symbol, "startTime": start, "limit": limit}))
        if not data:
            break
        written += db.upsert("funding_rates", [{"symbol": symbol, "funding_time": _iso(int(d["fundingTime"])),
                                                "rate": float(d["fundingRate"])} for d in data], "symbol,funding_time")
        if len(data) < limit:
            break
        start = int(data[-1]["fundingTime"]) + 1
        time.sleep(pause)
    return written


def sync_all(db: Supabase, fetch: Fetch = _get) -> dict:
    out = {}
    for m, s, i in SERIES:
        try:
            out[f"{m} {s} {i}"] = sync_series(db, m, s, i, fetch)
        except Exception as exc:  # en serie som fallerar stoppar inte de andra
            log.exception("synk misslyckades för %s %s %s", m, s, i)
            out[f"{m} {s} {i}"] = f"fel: {exc}"
    try:
        out["funding BTCUSDT"] = sync_funding(db, "BTCUSDT", fetch)
    except Exception as exc:
        log.exception("synk av finansieringsränta misslyckades")
        out["funding BTCUSDT"] = f"fel: {exc}"
    return out
