"""Punkt-i-tid-universum för Binance USDⓈ-M-perpetuals: vad fanns och gick att handla på datum t, med bara det som var känt då.

Principer
- **Perpar skiljs från leveranskontrakt med verifierbar metadata.** Leveranskontrakt heter `SYMBOL_YYMMDD` (utgång = datumet i namnet, kontrolleras mot sista stapeln) och har
  inga finansieringsarkiv. Perpar har finansieringsarkiv. `*SETTLED` är efterhandsnamn på avnoterade kontrakt, `*BUSD`/`*USDC` är andra kvotvalutor (utanför omfånget, redovisas).
- **Inget härleds ur dagens lista.** Ett kontrakt är handlingsbart dag t bara om det har en stapel dag t, minst `min_age` staplar bakåt, känd finansiering enligt datatäckningsregeln och
  rankas efter omsättning till och med t. Avnoterade kontrakt finns kvar i universumet fram till sin sista stapel; ett kontrakt som inte börjat än finns inte. Ingenting efter t läses.
- **Hål är hål.** Saknas en stapel mitt i ett kontrakts liv är kontraktet inte handlingsbart den dagen (vi fyller aldrig i). Efterhandsrapporten (`audit_universe`) räknar hålen,
  men `universe_at` ser dem bara som "ingen stapel idag", eftersom ett hål och en avnotering inte går att skilja åt i realtid.
- **Det som saknas blockerar.** `universe_gap(panel, listing)` listar perpar som arkivlistan visar men som saknas i panelen. Är listan inte tom kan inget bekräftande påstående göras (se judge).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

LISTING = Path("research/agentlab/universe/um-listing.json")
_DELIVERY = re.compile(r"^(?P<base>.+?)(?P<quote>USDT|BUSD|USDC|USD)_(?P<ymd>\d{6})$")


def classify(symbol: str) -> dict:
    """Art enligt namnet. `kind`: perp_usdt | perp_usdc | perp_busd | delivery | settled | other. `in_scope` = ska ingå i Agentlabs universum (bara USDT-perpar)."""
    m = _DELIVERY.match(symbol)
    if m:
        yy, mm, dd = int(m["ymd"][:2]), int(m["ymd"][2:4]), int(m["ymd"][4:])
        try:
            exp = str(pd.Timestamp(2000 + yy, mm, dd).date())
        except ValueError:
            exp = None
        return {"kind": "delivery", "quote": m["quote"], "expiry": exp, "in_scope": False}
    if "SETTLED" in symbol:
        return {"kind": "settled", "quote": None, "expiry": None, "in_scope": False}
    if symbol.endswith("USDT"):
        return {"kind": "perp_usdt", "quote": "USDT", "expiry": None, "in_scope": True}
    if symbol.endswith("USDC"):
        return {"kind": "perp_usdc", "quote": "USDC", "expiry": None, "in_scope": False}
    if symbol.endswith("BUSD"):
        return {"kind": "perp_busd", "quote": "BUSD", "expiry": None, "in_scope": False}
    return {"kind": "other", "quote": None, "expiry": None, "in_scope": False}      # t.ex. ETHBTC, BTCUSD1: andra produkter, inte USDT-perpar


def in_scope(symbol: str) -> bool:
    return classify(symbol)["in_scope"]


def scope_mask(columns) -> pd.Series:
    return pd.Series([in_scope(c) for c in columns], index=list(columns))


def load_listing(repo: Path) -> dict:
    return json.loads((repo / LISTING).read_text(encoding="utf-8"))


def universe_at(panel, t, top_n: int = 30, min_age: int = 90) -> list[str]:
    """Handlingsbara symboler vid stängningen av dag t (beslut på stängd stapel, fyllning t+1). Använder bara data till och med t: samma resultat om panelen kapas vid t."""
    t = pd.Timestamp(t)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    u = panel.universe(top_n, min_age)
    return [] if t not in u.index else list(u.columns[u.loc[t].to_numpy()])


def explain_at(panel, t, min_age: int = 90) -> dict[str, str]:
    """Skäl per symbol varför den inte är handlingsbar dag t (bara info känd vid t). Tom sträng = uppfyller kraven (rankning kan ändå utesluta)."""
    t = pd.Timestamp(t)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    out = {}
    close = panel.close.loc[:t]
    for s in panel.close.columns:
        c = close[s]
        if panel.scope_rule and not in_scope(s):
            out[s] = "utanför omfånget (" + classify(s)["kind"] + ")"
        elif c.notna().sum() == 0:
            out[s] = "inte noterad än"
        elif np.isnan(c.get(t, np.nan)):
            out[s] = "ingen stapel idag (avnoterad eller arkivhål)"
        elif c.notna().sum() < min_age:
            out[s] = "för ung"
        elif panel.funding_rule and panel.funding_known[s].loc[:t].iloc[-8:-1].sum() < 5:
            out[s] = "finansiering okänd"
        else:
            out[s] = ""
    return out


def universe_gap(panel, listing: dict, *, until: str = "2022-12") -> list[str]:
    """Perpar (i omfånget) som arkivlistan visar med dagsstaplar senast `until` men som saknas i panelen. Tom lista = panelen innehåller allt arkivet kan visa."""
    have = set(panel.close.columns)
    return sorted(s for s, v in listing["symbols"].items() if in_scope(s) and v["klines_1d"] and v["klines_1d"][0] <= until and s not in have)
