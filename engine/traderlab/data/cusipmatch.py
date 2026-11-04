"""CUSIP → ticker via namnet i 13F och SEC:s lista över noterade bolag (när OpenFIGI inte går att nå).

13F-namn är förkortade ("BANK AMER CORP"). Båda namnen normaliseras och matchas exakt efter normalisering.
Osäkra fall matchas inte: hellre ett saknat innehav (som redovisas) än fel aktie.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SUFFIX = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC", "LP", "LLC", "SA", "NV", "AG", "SE",
          "THE", "NEW", "DEL", "DE", "HLDGS", "HOLDINGS", "HLDG", "HOLDING", "GROUP", "GRP", "CL", "CLASS", "A", "B", "C",
          "COM", "SHS", "ORD", "SPONSORED", "ADR", "ADS", "LTD.", "TR", "TRUST", "INTL", "INTERNATIONAL", "N", "V"}
ABBR = {"AMER": "AMERICA", "AMERN": "AMERICAN", "FINL": "FINANCIAL", "SVCS": "SERVICES", "SVC": "SERVICE", "TECHNOLOGIES": "TECH",
        "TECHNOLOGY": "TECH", "TECHS": "TECH", "COMMUNICATIONS": "COMM", "COMMUNICATION": "COMM", "COMMUNICATNS": "COMM",
        "PHARMACEUTICALS": "PHARM", "PHARMACEUTICAL": "PHARM", "PHARMA": "PHARM", "INDS": "INDUSTRIES", "MGMT": "MANAGEMENT",
        "SYS": "SYSTEMS", "LABS": "LABORATORIES", "LAB": "LABORATORIES", "BANCORPORATION": "BANCORP", "NATL": "NATIONAL",
        "ENTMT": "ENTERTAINMENT", "PPTYS": "PROPERTIES", "RES": "RESOURCES", "MTRS": "MOTORS", "ELEC": "ELECTRIC",
        "MED": "MEDICAL", "INTERACTIVE": "INTERACT", "ENTERPRISES": "ENTERPRISE", "SOLUTIONS": "SOLUTION"}


def norm(name: str) -> str:
    s = re.sub(r"/[A-Z]{2,3}/?", " ", name.upper())          # /DE/, /MD
    s = re.sub(r"[^A-Z0-9& ]", " ", s.replace(".COM", "COM").replace("&", " & "))
    words = [ABBR.get(w, w) for w in s.split()]
    words = [w for w in words if w not in SUFFIX and w not in {"&", "OF", "AND"}]
    return " ".join(words)


def match(names: dict[str, str], sec_list: dict) -> dict[str, str | None]:
    """names: CUSIP → 13F-namn. sec_list: SEC:s company_tickers_exchange.json. Bara entydiga träffar."""
    by_name: dict[str, set[str]] = {}
    for _cik, title, ticker, exch in sec_list["data"]:
        if exch not in ("NYSE", "Nasdaq", "CBOE", "NYSE American") or not ticker or "-" in ticker:
            continue   # preferensaktier och obligationer har bindestreck
        by_name.setdefault(norm(title), set()).add(ticker)
    out = {}
    for cusip, n in names.items():
        hit = by_name.get(norm(n), set())
        # Flera vanliga aktieslag (GOOGL/GOOG): det kortaste är oftast A-aktien. Fler än två räknas som osäkert.
        cands = sorted(hit, key=lambda t: (len(t), t))
        out[cusip] = cands[0] if len(cands) == 1 or (len(cands) == 2 and len(cands[0]) < len(cands[1])) else None
    return out


def load_overrides(path: Path) -> dict[str, str | None]:
    """Handgjorda kopplingar för entydiga fall som namnmatchningen missar, med bolagsnamnet som kontroll."""
    if not path.exists():
        return {}
    return {c: v["ticker"] for c, v in json.loads(path.read_text(encoding="utf-8")).items()}
