"""13F-innehav från SEC EDGAR (research/13f-protokoll.md). Bara offentliga data, inga nycklar.

SEC kräver en kontaktadress i User-Agent för automatiska anrop och högst 10 anrop per sekund. Allt som hämtas
sparas under data/raw/sec/ (inte i Git) och hämtas aldrig igen.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SUBMISSIONS = "https://data.sec.gov/submissions/{name}"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{file}"
NS = "{http://www.sec.gov/edgar/document/thirteenf/informationtable}"


def user_agent() -> str:
    contact = os.environ.get("SEC_CONTACT")
    if not contact:
        raise RuntimeError("Sätt SEC_CONTACT till en kontaktadress (SEC kräver det i User-Agent).")
    return f"TraderGo research {contact}"


def _get(url: str, opener=None) -> bytes:
    if opener:
        return opener(url)
    req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    time.sleep(0.15)  # under SEC:s gräns på 10 anrop per sekund
    return data


def _cached(path: Path, url: str, opener=None) -> bytes:
    if path.exists():
        return path.read_bytes()
    data = _get(url, opener)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.rename(path)
    return data


@dataclass(frozen=True)
class Filing:
    cik: int
    accession: str      # 0001193125-26-352200
    filed: str          # inlämningsdag, ÅÅÅÅ-MM-DD
    period: str         # kvartalet som redovisas


def list_filings(cik: int, data_dir: Path, opener=None, refresh: bool = False) -> list[Filing]:
    """Ursprungliga 13F-HR (inte 13F-HR/A), äldst först. Listan hämtas om när refresh=True."""
    folder = data_dir / "raw" / "sec" / str(cik)
    main = folder / "submissions.json"
    if refresh and main.exists():
        main.unlink()
    d = json.loads(_cached(main, SUBMISSIONS.format(name=f"CIK{cik:010d}.json"), opener))
    pages = [d["filings"]["recent"]]
    for extra in d["filings"].get("files", []):
        pages.append(json.loads(_cached(folder / extra["name"], SUBMISSIONS.format(name=extra["name"]), opener)))
    out = {}
    for p in pages:
        for acc, form, filed, period in zip(p["accessionNumber"], p["form"], p["filingDate"], p.get("reportDate", [""] * len(p["form"]))):
            if form == "13F-HR":
                out[acc] = Filing(cik, acc, filed, period)
    return sorted(out.values(), key=lambda f: (f.filed, f.accession))


def parse_infotable(xml: bytes) -> dict[str, dict]:
    """Aktieinnehav per CUSIP (rader för samma CUSIP summeras). Optioner och obligationer räknas inte."""
    root = ET.fromstring(xml)
    out: dict[str, dict] = {}
    for row in root.iter(f"{NS}infoTable"):
        if row.find(f"{NS}putCall") is not None:
            continue
        amt = row.find(f"{NS}shrsOrPrnAmt")
        if amt is None or (amt.findtext(f"{NS}sshPrnamtType") or "").strip() != "SH":
            continue
        cusip = (row.findtext(f"{NS}cusip") or "").strip().upper()
        value = float(row.findtext(f"{NS}value") or 0)
        shares = float(amt.findtext(f"{NS}sshPrnamt") or 0)
        h = out.setdefault(cusip, {"name": (row.findtext(f"{NS}nameOfIssuer") or "").strip(), "value": 0.0, "shares": 0.0})
        h["value"] += value
        h["shares"] += shares
    return out


def holdings(f: Filing, data_dir: Path, opener=None) -> dict[str, dict]:
    """Innehållet i redovisningens informationstabell (den XML-fil som inte är primary_doc.xml)."""
    acc = f.accession.replace("-", "")
    folder = data_dir / "raw" / "sec" / str(f.cik) / acc
    index = json.loads(_cached(folder / "index.json", ARCHIVE.format(cik=f.cik, acc=acc, file="index.json"), opener))
    names = [i["name"] for i in index["directory"]["item"]]
    for name in names:
        if name.lower().endswith(".xml") and name.lower() != "primary_doc.xml":
            xml = _cached(folder / name, ARCHIVE.format(cik=f.cik, acc=acc, file=name), opener)
            try:
                rows = parse_infotable(xml)
            except ET.ParseError:
                continue
            if rows:
                return rows
    return {}


def top_weights(rows: dict[str, dict], n: int = 10) -> dict[str, float]:
    """De n största innehaven efter värde, viktade efter värde inom de n (summa 1)."""
    top = sorted(rows.items(), key=lambda kv: (-kv[1]["value"], kv[0]))[:n]
    total = sum(v["value"] for _, v in top)
    return {c: v["value"] / total for c, v in top} if total > 0 else {}
