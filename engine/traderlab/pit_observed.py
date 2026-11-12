"""Observerade handelsstaplar per COIN-M-kvartalskontrakt, för punkt-i-tid-underlaget.

Läser bara de dagsfiler som redan ligger sparade (till och med 2024-12). Inget pris används för urval: bara *när* en serie
har staplar, hur många och om volymen är noll. Kontrakt som löper ut 2025 eller senare är därför högercensurerade:
sista observerade stapel är 2024-12-31, inte kontraktets verkliga sista handelsdag.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd

from .data import binance, gapcheck

LEFT_LIMIT = "2020-08-01"        # första månaden vi hämtat; serier som börjar här kan ha börjat tidigare (vänstercensurerade)
CUTOFF = "2025-01-01"          # data från och med detta datum läses inte
NAME = re.compile(r"^(?P<base>[A-Z0-9]+?)USD_(?P<ymd>\d{6})$")


def expiry_of(contract: str) -> dt.date:
    m = NAME.match(contract)
    if not m:
        raise ValueError(f"inget kvartalsnamn: {contract}")
    y, mo, d = m["ymd"][:2], m["ymd"][2:4], m["ymd"][4:]
    return dt.date(2000 + int(y), int(mo), int(d))


def is_last_friday_of_quarter_month(day: dt.date) -> bool:
    """Ordinarie förfall enligt Binances leverans-FAQ: sista fredagen i mars, juni, september eller december."""
    return day.weekday() == 4 and day.month in (3, 6, 9, 12) and (day + dt.timedelta(days=7)).month != day.month


def _runs(days: list[dt.date]) -> list[list[str]]:
    """Sammanhängande körningar av dagar [första, sista] (ISO-datum)."""
    out: list[list[str]] = []
    for d in sorted(days):
        if out and (d - dt.date.fromisoformat(out[-1][1])).days == 1:
            out[-1][1] = d.isoformat()
        else:
            out.append([d.isoformat(), d.isoformat()])
    return out


def _empty(contract: str, expiry: dt.date) -> dict:
    return {"contract": contract, "underlying": NAME.match(contract)["base"], "expiry": expiry.isoformat(),
            "ordinary_expiry_rule": is_last_friday_of_quarter_month(expiry), "first_bar": None, "last_bar": None,
            "first_traded_bar": None, "last_traded_bar": None, "bars": 0, "missing_days_between": 0, "zero_volume_bars": 0,
            "traded_runs": [], "missing_days": [], "zero_volume_days": [], "daily_filled_days": [], "gap_fill_unverified": False,
            "left_censored": False, "right_censored": True, "ended_before_expiry": False,
            "days_last_traded_before_expiry": None, "bars_after_expiry": 0}


def observed(contract: str, data_dir: Path) -> dict:
    """Siffror ur de sparade dagsstaplarna för ett kontrakt (utan prisurval).

    Dagar som saknas i månadsfilen fylls bara med **verifierade** dagsstaplar (gapcheck.combined: checksumma, SHA-256 mot
    manifest, grannkontroll). Går verifieringen inte igenom lämnas luckan öppen och `gap_fill_unverified` sätts. En dag räknas
    som handlad bara om en stapel med volym > 0 finns *den dagen*: nollvolym och saknade dagar innanför intervallet räknas aldrig."""
    expiry = expiry_of(contract)
    try:
        frame = binance.load("cm", contract, "1d", data_dir, end=pd.Timestamp(CUTOFF, tz="UTC"))
    except FileNotFoundError:   # serien börjar handlas först 2025 eller senare: inga staplar före gränsen
        return _empty(contract, expiry)
    unverified = False
    try:
        frame = gapcheck.combined(frame, data_dir, "cm", contract, gapcheck.load_manifest(data_dir.parent))
    except gapcheck.UnverifiedGapFill:
        frame["source"] = "monthly"
        unverified = True
    index = frame.index
    traded = frame[frame["volume"] > 0].index
    last = index.max().date()
    censored = expiry >= dt.date.fromisoformat(CUTOFF)
    full_days = pd.date_range(index.min(), index.max(), freq="D", tz=index.tz)
    first_t = traded.min().date() if len(traded) else None
    last_t = traded.max().date() if len(traded) else None
    inside = [d for d in full_days if first_t and first_t <= d.date() <= last_t]
    present = set(index)
    return {
        "contract": contract, "underlying": NAME.match(contract)["base"], "expiry": expiry.isoformat(),
        "ordinary_expiry_rule": is_last_friday_of_quarter_month(expiry),
        "first_bar": index.min().date().isoformat(), "last_bar": last.isoformat(),
        "first_traded_bar": first_t.isoformat() if first_t else None,
        "last_traded_bar": last_t.isoformat() if last_t else None,
        "bars": int(len(frame)), "missing_days_between": int(len(full_days.difference(index))),
        "zero_volume_bars": int((frame["volume"] <= 0).sum()),
        "traded_runs": _runs([d.date() for d in traded if d.date() <= expiry]),
        "missing_days": [d.date().isoformat() for d in inside if d not in present],
        "zero_volume_days": [d.date().isoformat() for d in inside if d in present and frame.loc[d, "volume"] <= 0],
        "daily_filled_days": [d.date().isoformat() for d in index[frame["source"] == "daily"]],
        "gap_fill_unverified": unverified,
        "left_censored": index.min().date() <= dt.date.fromisoformat(LEFT_LIMIT),
        "right_censored": censored,
        "ended_before_expiry": (not censored) and len(traded) > 0 and (expiry - last_t).days > 1,
        "days_last_traded_before_expiry": None if censored or not len(traded) else (expiry - last_t).days,
        "bars_after_expiry": int((index.date > expiry).sum()),
    }


def observed_all(data_dir: Path, underlyings: tuple[str, ...]) -> list[dict]:
    root = data_dir / "raw" / "binance" / "cm"
    rows = []
    for folder in sorted(root.iterdir()):
        m = NAME.match(folder.name)
        if m and m["base"] in underlyings:
            rows.append(observed(folder.name, data_dir))
    return rows
