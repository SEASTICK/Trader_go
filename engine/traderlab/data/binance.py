"""Hämtar öppen historik från Binance publika datafiler (data.binance.vision). Inga nycklar.

Rådata sparas som den kom (zip) och skrivs aldrig över. Varje fil kontrolleras mot Binances
SHA-256-kontrollsumma. Se skillen hamta-data.
"""
from __future__ import annotations

import csv
import hashlib
import io
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from ..bars import COLUMNS, interval_delta

BASE = "https://data.binance.vision/data"
MARKETS = {"spot": "spot", "um": "futures/um"}  # um = USDⓈ-M-terminer

Opener = Callable[[str], bytes]


def _default_opener(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "trader_go-research"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # följer HTTPS_PROXY
        return resp.read()


def months(start: str, end: str) -> list[str]:
    """'2024-01', '2024-03' → ['2024-01', '2024-02', '2024-03']."""
    return [p.strftime("%Y-%m") for p in pd.period_range(start, end, freq="M")]


def kline_url(market: str, symbol: str, interval: str, month: str) -> str:
    interval_delta(interval)
    return f"{BASE}/{MARKETS[market]}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"


def funding_url(symbol: str, month: str) -> str:
    return f"{BASE}/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"


def _to_utc(ts: pd.Series) -> pd.DatetimeIndex:
    """Binance använder millisekunder, men spotdata från 2025 är i mikrosekunder."""
    v = ts.astype("int64")
    unit_us = v > 10**14
    ms = v.where(~unit_us, v // 1000)
    return pd.DatetimeIndex(pd.to_datetime(ms, unit="ms", utc=True))


def parse_klines_csv(raw: bytes) -> pd.DataFrame:
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
    if rows and not rows[0][0].strip().lstrip("-").isdigit():
        rows = rows[1:]  # nyare filer har en rubrikrad
    if not rows:
        return pd.DataFrame(columns=COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))
    df = pd.DataFrame([r[:6] for r in rows], columns=["open_time", *COLUMNS])
    idx = _to_utc(df["open_time"])
    out = df[COLUMNS].astype(float)
    out.index = idx
    out.index.name = "open_time"
    return out


def parse_funding_csv(raw: bytes) -> pd.Series:
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
    if rows and not rows[0][0].strip().isdigit():
        rows = rows[1:]
    if not rows:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    t = _to_utc(pd.Series([r[0] for r in rows]))
    rate = [float(r[-1]) for r in rows]
    return pd.Series(rate, index=t, name="funding_rate")


def _unzip_single(raw: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Väntade en CSV i zip-filen, fick {names}")
        return z.read(names[0])


def verify_checksum(raw: bytes, checksum_file: bytes) -> None:
    expected = checksum_file.decode().split()[0].strip().lower()
    actual = hashlib.sha256(raw).hexdigest()
    if expected != actual:
        raise ValueError(f"Kontrollsumman stämmer inte: väntade {expected}, fick {actual}")


@dataclass
class FetchResult:
    downloaded: list[Path]
    skipped_existing: list[Path]
    missing: list[str]  # månader som inte fanns hos Binance


def fetch(market: str, symbol: str, interval: str, start: str, end: str, data_dir: Path,
          opener: Opener = _default_opener, kind: str = "klines") -> FetchResult:
    """Hämtar månadsfiler till data/raw/binance/... Befintliga filer hoppas över, aldrig överskrivna."""
    if market not in MARKETS:
        raise ValueError(f"Okänd marknad {market}. Tillåtna: {', '.join(MARKETS)}")
    folder = data_dir / "raw" / "binance" / market / symbol / (interval if kind == "klines" else "fundingRate")
    folder.mkdir(parents=True, exist_ok=True)
    res = FetchResult([], [], [])
    for m in months(start, end):
        url = kline_url(market, symbol, interval, m) if kind == "klines" else funding_url(symbol, m)
        target = folder / url.rsplit("/", 1)[1]
        if target.exists():
            res.skipped_existing.append(target)
            continue
        try:
            raw = opener(url)
        except Exception as exc:  # 404 när månaden inte finns
            if "404" in str(exc):
                res.missing.append(m)
                continue
            raise
        verify_checksum(raw, opener(url + ".CHECKSUM"))
        tmp = target.with_suffix(".part")
        tmp.write_bytes(raw)
        tmp.rename(target)
        res.downloaded.append(target)
    if res.downloaded:
        _append_manifest(data_dir, market, symbol, interval if kind == "klines" else "fundingRate",
                         start, end, res)
    return res


def load(market: str, symbol: str, interval: str, data_dir: Path) -> pd.DataFrame:
    """Läser alla sparade månadsfiler i tidsordning. Lagar ingenting; kör quality.check efteråt."""
    folder = data_dir / "raw" / "binance" / market / symbol / interval
    files = sorted(folder.glob(f"{symbol}-{interval}-*.zip"))
    if not files:
        raise FileNotFoundError(f"Ingen data i {folder}. Kör fetch först.")
    parts = [parse_klines_csv(_unzip_single(f.read_bytes())) for f in files]
    return pd.concat(parts)


def load_funding(symbol: str, data_dir: Path) -> pd.Series:
    folder = data_dir / "raw" / "binance" / "um" / symbol / "fundingRate"
    files = sorted(folder.glob(f"{symbol}-fundingRate-*.zip"))
    if not files:
        raise FileNotFoundError(f"Ingen finansieringsränta i {folder}.")
    return pd.concat([parse_funding_csv(_unzip_single(f.read_bytes())) for f in files])


def _append_manifest(data_dir: Path, market: str, symbol: str, interval: str, start: str, end: str,
                     res: FetchResult) -> None:
    path = data_dir / "MANIFEST.md"
    new = not path.exists()
    with path.open("a", encoding="utf-8") as f:
        if new:
            f.write("# Datamanifest\n\nRådata ligger i data/raw/ och committas inte. Den här filen committas.\n\n"
                    "| Hämtad (UTC) | Källa | Marknad | Symbol | Tidsram | Period | Nya filer | Saknade månader |\n"
                    "|---|---|---|---|---|---|---|---|\n")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        f.write(f"| {now} | data.binance.vision | {market} | {symbol} | {interval} | {start} till {end} | "
                f"{len(res.downloaded)} | {', '.join(res.missing) or '-'} |\n")
