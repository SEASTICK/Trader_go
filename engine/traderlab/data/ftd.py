"""CUSIP → ticker ur SEC:s fails-to-deliver-filer (offentliga, två per månad, med CUSIP, ticker och namn).

Filerna täcker även avnoterade och uppköpta bolag och ger därför en historisk koppling, till skillnad från dagens
bolagslistor. En CUSIP kan ha bytt ticker (Facebook FB blev Meta META); den senast använda väljs, eftersom kurskällor
listar hela historiken under dagens ticker. Aktieslag skrivs med bindestreck som hos kurskällorna (BRKB → BRK-B).
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

from .sec13f import _cached, _get

PAGE = "https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data"
BASE = "https://www.sec.gov"


def file_links(data_dir: Path, opener=None) -> list[str]:
    html = _get(PAGE, opener).decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="([^"]*cnsfails\d{6}[ab]\.zip)"', html)))
    return [l if l.startswith("http") else BASE + l for l in links]


def load_map(data_dir: Path, start: str = "2013", end: str = "2025", opener=None) -> dict[str, str]:
    """CUSIP → ticker från alla filer med år i [start, end)."""
    committed = data_dir / "sec" / f"cusip_ticker_{start}_{end}.json"   # incheckad kopia: samma koppling överallt
    if committed.exists():
        return {c: clean_symbol(t) for c, t in json.loads(committed.read_text()).items()}
    out_path = data_dir / "raw" / "sec" / "ftd" / f"cusip_ticker_{start}_{end}.json"
    if out_path.exists():
        return {c: clean_symbol(t) for c, t in json.loads(out_path.read_text()).items()}
    last: dict[str, tuple[str, str, str]] = {}
    for url in file_links(data_dir, opener):
        name = url.rsplit("/", 1)[1]
        year = name[8:12]
        if not (start <= year < end):
            continue
        raw = _cached(data_dir / "raw" / "sec" / "ftd" / name, url, opener)
        try:
            z = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            continue
        text = z.read(z.namelist()[0]).decode("latin1")
        for line in text.splitlines()[1:]:
            parts = line.split("|")
            if len(parts) < 5:
                continue
            date, cusip, sym, desc = parts[0].strip(), parts[1].strip().upper(), parts[2].strip().upper(), parts[4].upper()
            if len(cusip) != 9 or not sym:
                continue
            if cusip not in last or date >= last[cusip][0]:
                last[cusip] = (date, sym, desc)
    listed = {row[2] for row in json.loads(_cached(data_dir / "raw" / "sec" / "company_tickers_exchange.json",
                                                    "https://www.sec.gov/files/company_tickers_exchange.json", opener))["data"] if row[2]}
    result = {c: class_symbol(clean_symbol(sym), listed) for c, (_, sym, _desc) in last.items()}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, sort_keys=True))
    return result


def clean_symbol(sym: str) -> str:
    """Fails-to-deliver-filerna lägger ibland till XXXX efter symbolen (GOOGLXXXX). Kurskällorna känner bara
    själva symbolen, så tillägget tas bort (LRCXXXXX blir LRCX)."""
    return sym[:-4] if sym.endswith("XXXX") and len(sym) > 4 else sym


def class_symbol(sym: str, listed: set[str]) -> str:
    """BRKB blir BRK-B om SEC:s lista över noterade bolag har BRK-B men inte BRKB (aktieslag skrivs med bindestreck
    hos kurskällorna). Annars oförändrad, så att META inte blir MET-A."""
    if sym in listed or "-" in sym or len(sym) < 3:
        return sym
    hyph = f"{sym[:-1]}-{sym[-1]}"
    return hyph if hyph in listed else sym
