"""Dagliga aktiekurser, justerade för split och utdelning, och CUSIP → ticker (OpenFIGI).

Kurskälla, i den här ordningen:
1. Tiingo (officiellt API) om miljövariabeln TIINGO_API_KEY finns.
2. Yahoo Finance chart-API (ingen nyckel). Inofficiellt: kan ändras eller strypas. Svarar källan inte med data
   avbryts körningen med PriceSourceUnavailable; ingen blockering kringgås.
3. Stooq om PRICE_SOURCE=stooq. Stooq blockerar molnservrar, och det kringgås inte.
Alla kurser justeras för split och utdelning. Allt sparas under data/raw/.
"""
from __future__ import annotations

import io
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

STOOQ = "https://stooq.com/q/d/l/?s={sym}.us&i=d"
YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1=1325376000&period2={end}"
         "&interval=1d&events=div%2Csplits&includeAdjustedClose=true")
TIINGO = "https://api.tiingo.com/tiingo/daily/{sym}/prices?startDate=2012-01-01&format=csv&token={key}"


class PriceSourceUnavailable(RuntimeError):
    """Kurskällan svarar inte med data (blockerad, gräns nådd eller nyckel saknas). Inget sparas."""
FIGI = "https://api.openfigi.com/v3/mapping"


def _open(req, opener=None, tries: int = 5) -> bytes:
    if opener:
        return opener(req)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except (OSError, urllib.error.URLError):
            if attempt == tries - 1:
                raise
            time.sleep(2 * 2 ** attempt)   # 2, 4, 8, 16 s
    raise RuntimeError("oåtkomlig")


def stooq_symbol(ticker: str) -> str:
    return ticker.lower().replace("/", "-").replace(".", "-")


def tiingo_symbol(ticker: str) -> str:
    return ticker.upper().replace("/", "-").replace(".", "-")


def yahoo_symbol(ticker: str) -> str:
    return ticker.upper().replace("/", "-").replace(".", "-")


def parse_yahoo(raw: bytes) -> pd.DataFrame | None:
    """Chart-svaret som justerade dagsstaplar. Faktorn justerad/ojusterad stängning läggs på öppning, hög och låg."""
    res = (json.loads(raw).get("chart") or {}).get("result") or []
    if not res or not res[0].get("timestamp"):
        return None
    r = res[0]
    q = r["indicators"]["quote"][0]
    adj = (r["indicators"].get("adjclose") or [{}])[0].get("adjclose") or q["close"]
    tz = (r.get("meta") or {}).get("exchangeTimezoneName") or "America/New_York"
    days = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None).tz_localize("UTC")
    df = pd.DataFrame({"open": q["open"], "high": q["high"], "low": q["low"], "close": q["close"],
                       "volume": q.get("volume"), "adj": adj}, index=pd.DatetimeIndex(days, name="date")).astype(float)
    df = df.dropna(subset=["open", "close", "adj"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    if df.empty:
        return None
    f = df["adj"] / df["close"]
    return pd.DataFrame({"open": df["open"] * f, "high": df["high"] * f, "low": df["low"] * f,
                         "close": df["adj"], "volume": df["volume"]}, index=df.index)


def _load_yahoo(ticker: str, data_dir: Path, opener=None, max_age_hours: float | None = None) -> pd.DataFrame | None:
    path = data_dir / "raw" / "yahoo" / f"{yahoo_symbol(ticker)}.json"
    if path.exists() and max_age_hours is not None and time.time() - path.stat().st_mtime > max_age_hours * 3600:
        path.unlink()
    if not path.exists():
        url = YAHOO.format(sym=yahoo_symbol(ticker), end=int(time.time()))
        try:
            raw = _open(urllib.request.Request(url, headers={"User-Agent": "TraderGo research"}), opener, tries=3)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:   # okänd eller avnoterad aktie. Sparas inte, så att ett tillfälligt fel inte fastnar.
                return None
            raise PriceSourceUnavailable(f"Yahoo svarade {exc.code} för {ticker}") from exc
        except OSError as exc:
            raise PriceSourceUnavailable(f"Yahoo svarar inte för {ticker}: {exc}") from exc
        try:
            json.loads(raw)
        except ValueError as exc:   # felsida i stället för data: sparas inte
            raise PriceSourceUnavailable(f"Oväntat svar från Yahoo för {ticker}: {raw[:80]!r}") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        if opener is None:
            time.sleep(float(os.environ.get("YAHOO_SLEEP", "0.5")))
    return parse_yahoo(path.read_bytes())


def _load_tiingo(ticker: str, data_dir: Path, key: str, opener=None, max_age_hours: float | None = None) -> pd.DataFrame | None:
    path = data_dir / "raw" / "tiingo" / f"{tiingo_symbol(ticker)}.csv"
    if path.exists() and max_age_hours is not None and time.time() - path.stat().st_mtime > max_age_hours * 3600:
        path.unlink()
    if not path.exists():
        url = TIINGO.format(sym=tiingo_symbol(ticker), key=key)
        try:
            raw = _open(urllib.request.Request(url, headers={"User-Agent": "TraderGo research"}), opener, tries=2)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raw = b"No data"
            elif exc.code in (401, 403, 429):
                raise PriceSourceUnavailable(f"Tiingo svarade {exc.code} för {ticker} (nyckel eller gräns)") from exc
            else:
                raise
        head = raw[:200].decode("utf-8", "replace").strip().lower()
        if not (head.startswith("date") or head.startswith("no data")):
            raise PriceSourceUnavailable(f"Oväntat svar från Tiingo för {ticker}: {head[:80]!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        time.sleep(float(os.environ.get("TIINGO_SLEEP", "1")))   # gratisnivån: sätt 72 för 50 anrop per timme
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text.lower().startswith("date"):
        return None
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.lower() for c in df.columns]
    if df.empty:
        return None
    idx = pd.DatetimeIndex(pd.to_datetime(df["date"], utc=True).dt.normalize(), name="date")
    out = pd.DataFrame({"open": df["adjopen"].to_numpy(), "high": df["adjhigh"].to_numpy(), "low": df["adjlow"].to_numpy(),
                        "close": df["adjclose"].to_numpy(), "volume": df["adjvolume"].to_numpy()}, index=idx)
    return out.astype(float)


def load_prices(ticker: str, data_dir: Path, opener=None, max_age_hours: float | None = None) -> pd.DataFrame | None:
    """Dagsstaplar (open, high, low, close, volume) i UTC, eller None om källan inte har aktien.

    max_age_hours: hämta om filen om den är äldre (för papper framåt, där nya dagar tillkommer)."""
    key = os.environ.get("TIINGO_API_KEY")
    if key:
        return _load_tiingo(ticker, data_dir, key, opener, max_age_hours)
    if os.environ.get("PRICE_SOURCE", "yahoo") != "stooq":
        return _load_yahoo(ticker, data_dir, opener, max_age_hours)
    path = data_dir / "raw" / "stooq" / f"{stooq_symbol(ticker)}.csv"
    if path.exists() and max_age_hours is not None and time.time() - path.stat().st_mtime > max_age_hours * 3600:
        path.unlink()
    if not path.exists():
        url = STOOQ.format(sym=stooq_symbol(ticker))
        try:
            raw = _open(urllib.request.Request(url, headers={"User-Agent": "TraderGo research"}), opener)
        except OSError as exc:   # nätverksfel, tidsgräns eller blockering efter omförsöken
            raise PriceSourceUnavailable(f"Stooq svarar inte för {ticker}: {exc}") from exc
        head = raw[:200].decode("utf-8", "replace").strip().lower()
        # Bara riktiga svar sparas: en tabell, eller "No data" (källan saknar aktien). Gränsmeddelanden och
        # felsidor sparas inte, så att de inte senare tolkas som "aktien finns inte".
        if not (head.startswith("date") or head.startswith("no data")):
            raise PriceSourceUnavailable(f"Oväntat svar från Stooq för {ticker}: {head[:80]!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        time.sleep(0.5)
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text.lower().startswith("date"):
        return None   # "No data" eller felsida
    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.lower() for c in df.columns]
    if df.empty:
        return None
    df.index = pd.DatetimeIndex(pd.to_datetime(df.pop("date")), name="date").tz_localize("UTC")
    return df[["open", "high", "low", "close"] + (["volume"] if "volume" in df else [])].astype(float)


def map_cusips(cusips: list[str], data_dir: Path, opener=None) -> dict[str, str | None]:
    """CUSIP → amerikansk ticker via OpenFIGI. Okända blir None. Svaren sparas och frågas aldrig igen."""
    path = data_dir / "raw" / "figi" / "cusip_ticker.json"
    known: dict[str, str | None] = json.loads(path.read_text()) if path.exists() else {}
    todo = [c for c in dict.fromkeys(cusips) if c not in known]
    for i in range(0, len(todo), 10):   # utan nyckel: högst 10 per anrop och 25 anrop per minut
        batch = todo[i:i + 10]
        body = json.dumps([{"idType": "ID_CUSIP", "idValue": c, "exchCode": "US"} for c in batch]).encode()
        req = urllib.request.Request(FIGI, data=body, headers={"Content-Type": "application/json"}, method="POST")
        res = json.loads(_open(req, opener))
        for c, r in zip(batch, res):
            data = r.get("data") or []
            eq = [d for d in data if d.get("marketSector") == "Equity"] or data
            known[c] = eq[0]["ticker"] if eq else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(known, indent=0, sort_keys=True))
        if opener is None:
            time.sleep(2.5)
    return {c: known.get(c) for c in cusips}
