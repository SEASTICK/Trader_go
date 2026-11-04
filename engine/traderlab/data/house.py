"""Redovisade aktieaffärer (Periodic Transaction Report) från USA:s representanthus (research/pelosi-protokoll.md).

Källa: disclosures-clerk.house.gov. Årsindexet YYYYFD.zip innehåller en XML-lista över alla redovisningar; varje PTR
finns som PDF. Elektroniskt inlämnade PDF:er har text som går att läsa; inskannade har ingen text och räknas som
otolkade (andelen redovisas).
"""
from __future__ import annotations

import io
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

INDEX = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip"
PTR = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{doc}.pdf"


def _get(url: str, opener=None) -> bytes:
    if opener:
        return opener(url)
    req = urllib.request.Request(url, headers={"User-Agent": "TraderGo research"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            time.sleep(0.3)
            return data
        except OSError:
            if attempt == 4:
                raise
            time.sleep(2 * 2 ** attempt)
    raise RuntimeError("oåtkomlig")


def _cached(path: Path, url: str, opener=None) -> bytes:
    if path.exists():
        return path.read_bytes()
    data = _get(url, opener)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


@dataclass(frozen=True)
class Report:
    doc_id: str
    year: int
    filed: str      # ÅÅÅÅ-MM-DD


def reports(year: int, data_dir: Path, last: str = "Pelosi", first: str = "Nancy", opener=None) -> list[Report]:
    raw = _cached(data_dir / "raw" / "house" / f"{year}FD.zip", INDEX.format(year=year), opener)
    z = zipfile.ZipFile(io.BytesIO(raw))
    name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
    root = ET.fromstring(z.read(name))
    out = []
    for m in root.iter("Member"):
        if (m.findtext("Last") or "").strip().lower() != last.lower():
            continue
        if not (m.findtext("First") or "").strip().lower().startswith(first.lower()):
            continue
        if (m.findtext("FilingType") or "").strip() != "P":
            continue
        mm, dd, yy = (m.findtext("FilingDate") or "").strip().split("/")
        out.append(Report((m.findtext("DocID") or "").strip(), year, f"{yy}-{int(mm):02d}-{int(dd):02d}"))
    return sorted(out, key=lambda r: (r.filed, r.doc_id))


def pdf_text(report: Report, data_dir: Path, opener=None) -> str:
    raw = _cached(data_dir / "raw" / "house" / str(report.year) / f"{report.doc_id}.pdf",
                  PTR.format(year=report.year, doc=report.doc_id), opener)
    from pypdf import PdfReader   # bara här, så att resten av motorn inte kräver pypdf
    try:
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""


# Nyare format: "Alphabet Inc. - Class A (GOOGL) [ST] P 12/30/2020" (med radbrytningar och ägarkod emellan).
# Äldre format (2014–2015): "alcoa Inc. (aa)s 10/23/2014" utan typtagg och med trasig versalisering i PDF-texten.
ROW = re.compile(r"\(([A-Za-z][A-Za-z0-9.\-]{0,6})\)\s*(?:\[([A-Za-z]{2})\])?\s*(S\s*\(partial\)|P|S|E)\s+(\d{1,2}/\d{1,2}/\d{4})",
                 re.S | re.I)


@dataclass(frozen=True)
class Trade:
    ticker: str
    kind: str        # "buy" eller "sell"
    asset: str       # "ST" eller "OP"
    traded: str      # ÅÅÅÅ-MM-DD (affärsdagen; används inte för tidpunkten, bara för redovisning)


def parse(text: str) -> list[Trade]:
    """Affärer enligt protokollet: köp av aktie eller köpoption = buy, hel försäljning av aktie = sell.
    Delförsäljningar, säljoptioner, utbyten (E) och försäljning av optioner räknas inte."""
    flat = re.sub(r"\s+", " ", text)
    out = []
    for m in ROW.finditer(flat):
        ticker = m.group(1).upper()
        tag = (m.group(2) or "").upper()
        typ = re.sub(r"\s+", " ", m.group(3)).upper()
        mm, dd, yy = m.group(4).split("/")
        when = f"{yy}-{int(mm):02d}-{int(dd):02d}"
        nxt = ROW.search(flat, m.end())
        tail = flat[m.end(): nxt.start() if nxt else m.end() + 400].lower()
        if tag and tag not in ("ST", "OP"):
            continue   # fonder, obligationer och annat räknas inte
        asset = tag or ("OP" if "option" in tail else "ST")
        if asset == "OP":
            # Köpoptioner räknas som köp av aktien. Äldre redovisningar skriver bara "Options" utan typ; de räknas
            # som köpoptioner om "put" inte står där (tolkning bestämd före körning, se protokollet).
            if typ == "P" and "put" not in tail:
                out.append(Trade(ticker, "buy", "OP", when))
            continue
        if typ == "P":
            out.append(Trade(ticker, "buy", "ST", when))
        elif typ == "S":
            out.append(Trade(ticker, "sell", "ST", when))
    return out
