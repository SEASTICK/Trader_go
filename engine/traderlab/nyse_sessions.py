"""NYSE-sessionskalender 2006-01-01 till 2024-12-31 för H-0024:s datakrav (research/tom-protokoll.md, datakrav 1 och 2).

Kalendern genereras av `generate()` ur NYSE:s helgdagsregler plus de fyra extra stängningarna i perioden och sparas i `research/h0024/nyse-sessions-2006-2024.csv`
(en rad per session). Filen är versionshanterad och fastlåst med SHA-256 (`SESSIONS_SHA256`). `load()` vägrar en fil som inte stämmer.

**Källa och förbehåll.** Reglerna är NYSE:s publicerade helgdagsschema (New Year's Day, Martin Luther King Jr. Day, Washington's Birthday, Good Friday, Memorial Day,
Juneteenth från 2022, Independence Day, Labor Day, Thanksgiving, Christmas) med regeln att en helgdag på lördag flyttas till fredagen och på söndag till måndagen, utom att
nyårsdagen på en lördag *inte* stänger fredagen den 31 december. De fyra extra stängningarna är nationella sorgedagar och en storm: 2007-01-02 (Gerald Ford), 2012-10-29 och
2012-10-30 (Sandy), 2018-12-05 (George H. W. Bush). Reglerna skrevs här utan åtkomst till NYSE:s egen sida (nätspärr), och kalendern är kontrollerad mot de kända antalen
sessioner per år (`EXPECTED_PER_YEAR`, se testet). Den ska granskas mot NYSE:s publicerade kalender av någon med åtkomst innan en körning.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dateutil.easter import easter

FIRST, LAST = pd.Timestamp("2006-01-01"), pd.Timestamp("2024-12-31")
SESSIONS_FILE = Path(__file__).resolve().parents[2] / "research" / "h0024" / "nyse-sessions-2006-2024.csv"
SESSIONS_SHA256 = "47b0f1168a6daa56b4891f5088f87f161b5fd6588076a00bc9a27ec94f685e10"
SPECIAL_CLOSURES = {date(2007, 1, 2): "nationell sorgedag (Gerald Ford)", date(2012, 10, 29): "stormen Sandy", date(2012, 10, 30): "stormen Sandy",
                    date(2018, 12, 5): "nationell sorgedag (George H. W. Bush)"}
EXPECTED_PER_YEAR = {2006: 251, 2007: 251, 2008: 253, 2009: 252, 2010: 252, 2011: 252, 2012: 250, 2013: 252, 2014: 252, 2015: 252, 2016: 252, 2017: 251, 2018: 251,
                     2019: 252, 2020: 253, 2021: 252, 2022: 251, 2023: 250, 2024: 252}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date | None:
    """Lördag flyttas till fredagen, söndag till måndagen."""
    return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d


def holidays(year: int) -> set[date]:
    h: set[date] = set()
    new_year = date(year, 1, 1)
    if new_year.weekday() != 5:                                  # nyårsdagen på en lördag stänger inte fredagen den 31 december
        h.add(_observed(new_year))
    h.add(_nth_weekday(year, 1, 0, 3))                           # Martin Luther King Jr. Day
    h.add(_nth_weekday(year, 2, 0, 3))                           # Washington's Birthday
    h.add(easter(year) - timedelta(days=2))                      # Good Friday
    h.add(_last_weekday(year, 5, 0))                             # Memorial Day
    if year >= 2022:
        h.add(_observed(date(year, 6, 19)))                      # Juneteenth
    h.add(_observed(date(year, 7, 4)))                           # Independence Day
    h.add(_nth_weekday(year, 9, 0, 1))                           # Labor Day
    h.add(_nth_weekday(year, 11, 3, 4))                          # Thanksgiving
    h.add(_observed(date(year, 12, 25)))                         # Christmas
    return h


def generate() -> pd.DatetimeIndex:
    """Alla sessioner (vardagar utom helgdagar och extra stängningar) 2006-01-01..2024-12-31."""
    closed = set(SPECIAL_CLOSURES)
    for y in range(FIRST.year, LAST.year + 1):
        closed |= holidays(y)
    days = [d for d in pd.bdate_range(FIRST, LAST) if d.date() not in closed]
    return pd.DatetimeIndex(days)


def to_csv_text(index: pd.DatetimeIndex) -> str:
    return "date\n" + "".join(f"{d.date().isoformat()}\n" for d in index)


def load(path: Path = SESSIONS_FILE, expected_sha256: str | None = None) -> pd.DatetimeIndex:
    """Läser den versionshanterade kalendern och kontrollerar SHA-256. Kastar ValueError om filen ändrats."""
    raw = path.read_bytes().replace(b"\r\n", b"\n")                    # radslut normaliseras så att SHA-256 är lika på alla OS (git text=auto)
    want = SESSIONS_SHA256 if expected_sha256 is None else expected_sha256
    got = hashlib.sha256(raw).hexdigest()
    if got != want:
        raise ValueError(f"sessionskalendern {path.name} har ändrats (sha256 {got} != {want})")
    import io
    return pd.DatetimeIndex(pd.to_datetime(pd.read_csv(io.BytesIO(raw))["date"]))


def missing_sessions(index: pd.DatetimeIndex, calendar: pd.DatetimeIndex, start: pd.Timestamp = FIRST, end: pd.Timestamp = LAST) -> list[pd.Timestamp]:
    """Förväntade sessioner i perioden som saknas i `index`."""
    want = calendar[(calendar >= start) & (calendar <= end)]
    return [d for d in want if d not in set(index)]


def unexpected_days(index: pd.DatetimeIndex, calendar: pd.DatetimeIndex, start: pd.Timestamp = FIRST, end: pd.Timestamp = LAST) -> list[pd.Timestamp]:
    """Dagar i `index` i perioden som inte är NYSE-sessioner."""
    cal = set(calendar)
    return [d for d in index if start <= d <= end and d not in cal]
