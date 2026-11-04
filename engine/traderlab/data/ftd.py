"""CUSIP → ticker ur SEC:s fails-to-deliver-filer (offentliga, två per månad, med CUSIP, ticker och namn).

Filerna täcker även avnoterade och uppköpta bolag och ger därför en historisk koppling, till skillnad från dagens
bolagslistor. En CUSIP kan ha bytt ticker; den ticker som oftast förekommer under perioden väljs, och den senaste
vid lika.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from collections import Counter
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
        return json.loads(committed.read_text())
    out_path = data_dir / "raw" / "sec" / "ftd" / f"cusip_ticker_{start}_{end}.json"
    if out_path.exists():
        return json.loads(out_path.read_text())
    counts: dict[str, Counter] = {}
    last: dict[str, tuple[str, str]] = {}
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
            if len(parts) < 3:
                continue
            date, cusip, sym = parts[0].strip(), parts[1].strip().upper(), parts[2].strip().upper()
            if len(cusip) != 9 or not sym:
                continue
            counts.setdefault(cusip, Counter())[sym] += 1
            if cusip not in last or date >= last[cusip][0]:
                last[cusip] = (date, sym)
    result = {}
    for cusip, c in counts.items():
        top = c.most_common()
        best = [s for s, n in top if n == top[0][1]]
        result[cusip] = last[cusip][1] if last[cusip][1] in best else best[0]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, sort_keys=True))
    return result
