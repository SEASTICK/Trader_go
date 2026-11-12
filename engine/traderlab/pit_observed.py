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

from .data import binance

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


def observed(contract: str, data_dir: Path) -> dict:
    """Siffror ur de sparade dagsstaplarna för ett kontrakt (utan prisurval)."""
    expiry = expiry_of(contract)
    try:
        frame = binance.load("cm", contract, "1d", data_dir, end=pd.Timestamp(CUTOFF, tz="UTC"))
    except FileNotFoundError:   # serien börjar handlas först 2025 eller senare: inga staplar före gränsen
        return {"contract": contract, "underlying": NAME.match(contract)["base"], "expiry": expiry.isoformat(),
                "ordinary_expiry_rule": is_last_friday_of_quarter_month(expiry), "first_bar": None, "last_bar": None,
                "first_traded_bar": None, "last_traded_bar": None, "bars": 0, "missing_days_between": 0, "zero_volume_bars": 0,
                "left_censored": False, "right_censored": True, "ended_before_expiry": False,
                "days_last_traded_before_expiry": None, "bars_after_expiry": 0}
    index = frame.index
    traded = frame[frame["volume"] > 0].index
    last = index.max().date()
    censored = expiry >= dt.date.fromisoformat(CUTOFF)
    full_days = pd.date_range(index.min(), index.max(), freq="D", tz=index.tz)
    return {
        "contract": contract, "underlying": NAME.match(contract)["base"], "expiry": expiry.isoformat(),
        "ordinary_expiry_rule": is_last_friday_of_quarter_month(expiry),
        "first_bar": index.min().date().isoformat(), "last_bar": last.isoformat(),
        "first_traded_bar": traded.min().date().isoformat() if len(traded) else None,
        "last_traded_bar": traded.max().date().isoformat() if len(traded) else None,
        "bars": int(len(frame)), "missing_days_between": int(len(full_days.difference(index))),
        "zero_volume_bars": int((frame["volume"] <= 0).sum()),
        "left_censored": index.min().date() <= dt.date.fromisoformat(LEFT_LIMIT),
        "right_censored": censored,
        "ended_before_expiry": (not censored) and len(traded) > 0 and (expiry - traded.max().date()).days > 1,
        "days_last_traded_before_expiry": None if censored or not len(traded) else (expiry - traded.max().date()).days,
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
