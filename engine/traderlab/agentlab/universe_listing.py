"""Hämtar arkivlistan (bara filnamn, inga data) för Binance USDⓈ-M ur öppna bucketen bakom data.binance.vision.

Listan visar vilka månadsfiler (1d-staplar och finansiering) som finns per symbol. Den är den enda fullständiga historiska
kontraktslistan vi kan nå utan Binances REST-API (`exchangeInfo` svarar 451 härifrån och kringgås inte). Vi sparar bara månader
före slutprovet (< 2025-01); filnamn från 2025 skrivs aldrig ut och ingen data därifrån öppnas.

Körning (nät krävs): `python -m traderlab.agentlab.universe_listing research/agentlab/universe/um-listing.json`
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
LAST_MONTH = "2024-12"          # inget senare än detta sparas


def _get(query: str, tries: int = 6) -> ET.Element:
    req = urllib.request.Request(f"{ENDPOINT}?{query}", headers={"User-Agent": "trader_go-research"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return ET.fromstring(r.read())
        except OSError:                                   # tillfälligt nätfel (URLError/ConnectionReset): vänta och försök igen
            if i == tries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    raise RuntimeError("onåbar")


def list_prefix(prefix: str, delimiter: str | None = None) -> tuple[list[tuple[str, int]], list[str]]:
    """(objekt [(nyckel, storlek)], undermappar). Följer sidor om 1000."""
    objs, dirs, marker = [], [], ""
    while True:
        q = f"prefix={urllib.parse.quote(prefix)}&max-keys=1000" + (f"&delimiter={urllib.parse.quote(delimiter)}" if delimiter else "") + (f"&marker={urllib.parse.quote(marker)}" if marker else "")
        root = _get(q)
        for c in root.findall("s:Contents", NS):
            objs.append((c.find("s:Key", NS).text, int(c.find("s:Size", NS).text)))
        dirs += [p.find("s:Prefix", NS).text for p in root.findall("s:CommonPrefixes", NS)]
        if root.find("s:IsTruncated", NS).text != "true":
            return objs, dirs
        marker = root.find("s:NextMarker", NS).text if root.find("s:NextMarker", NS) is not None else (objs[-1][0] if objs else (dirs[-1] if dirs else ""))


def list_symbols() -> list[str]:
    _, dirs = list_prefix("data/futures/um/monthly/klines/", "/")
    return sorted(d.rstrip("/").split("/")[-1] for d in dirs)


def _months(prefix: str, pattern: str) -> list[str]:
    objs, _ = list_prefix(prefix)
    out = sorted({m.group(1) for k, _ in objs if (m := re.search(pattern, k)) and m.group(1) <= LAST_MONTH})
    return out


def build(workers: int = 8) -> dict:
    syms = list_symbols()

    def one(s: str) -> tuple[str, list[str], list[str]]:
        kl = _months(f"data/futures/um/monthly/klines/{s}/1d/", r"-1d-(\d{4}-\d{2})\.zip$")
        fu = _months(f"data/futures/um/monthly/fundingRate/{s}/", r"-fundingRate-(\d{4}-\d{2})\.zip$") if kl else []
        return s, kl, fu

    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, syms))
    return {"fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "source": f"{ENDPOINT} (bucket listing, filnamn)", "last_month_kept": LAST_MONTH,
            "symbols_in_bucket": len(syms), "symbols": {s: {"klines_1d": kl, "funding": fu} for s, kl, fu in res if kl}}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    data = build()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(len(data["symbols"]), "symboler med arkiv före 2025")
