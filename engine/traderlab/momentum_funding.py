"""H-0017 fundingbokföring på givna konton och event (research/h0017-protokoll.md §8.3, §12, D03, D18).

Endast bokföringen av en fundinghändelse på det konto som anroparen säger gäller vid eventtiden. Ingen eventloop,
inget beslut om vilken position som gäller, ingen marginal eller likvidation. Kommande eventlager ansvarar för att
skicka rätt konto (A: före affären, B: efter affären, mellanhändelse: q vid t) och för marginalkontrollen.

Betalning = q * M_ref * ränta. Positivt belopp betalas och minskar C; negativt belopp tas emot och ökar C. Beloppet
läggs i Account.funding_net, skilt från handelskostnader och realiserat resultat.

M_ref (D03): mark_open för 4H-stapeln som innehåller eventtiden; vid exakt gräns stapeln som börjar där. Diagnostiken
mark_close (stapelns close, känd vid stapelns slut) finns bara som märkt konfiguration, aldrig i huvudmodellen.

Fundingstress (§12): bara faktiskt betalda positiva belopp dubblas; mottagna belopp lämnas oförändrade.

Varje händelse bokförs högst en gång per konto och scenario (FundingState). Ett återanrop med samma event-id avvisas
utan ändring, även om första bokföringen var ett nollbelopp på ett platt konto.

Inga toleranser, avrundningar eller fördelningar över stapeln. Fel ger FundingError utan ändrat konto eller tillstånd.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from .momentum_ledger import Account, LedgerError, _num, _out

VERSION = "mom-funding/1.0.0"
BAR = pd.Timedelta(hours=4)
MARK_OPEN = "mark_open"
MARK_CLOSE = "mark_close"
PHASES = ("funding_A", "funding_B", "funding_interior")


class FundingError(LedgerError):
    """Ogiltigt event, ogiltig konfiguration eller dubbelbokning. Inget ändras."""


def _fnum(name: str, v) -> float:
    try:
        return _num(name, v)
    except LedgerError as exc:
        raise FundingError(str(exc)) from None


def _utc_ms(name: str, t) -> pd.Timestamp:
    if not isinstance(t, pd.Timestamp) or t.tz is None or str(t.tz) != "UTC":
        raise FundingError(f"{name} måste vara en pd.Timestamp i UTC, fick {t!r}.")
    if t.nanosecond or t.microsecond % 1000:
        raise FundingError(f"{name} har finare upplösning än millisekund: {t}.")
    return t


def bar_open(t: pd.Timestamp) -> pd.Timestamp:
    """Öppningstid för 4H-stapeln som innehåller t; vid exakt gräns stapeln som börjar där."""
    return t.floor(BAR)


@dataclass(frozen=True)
class FundingConfig:
    stress: bool = False                 # §12: dubbla betalda belopp
    price_model: str = MARK_OPEN         # MARK_OPEN i huvudmodellen; MARK_CLOSE endast diagnostik

    def __post_init__(self) -> None:
        if not isinstance(self.stress, bool):
            raise FundingError(f"stress måste vara bool, fick {self.stress!r}.")
        if self.price_model not in (MARK_OPEN, MARK_CLOSE):
            raise FundingError(f"Okänd prismodell {self.price_model!r}.")

    @property
    def label(self) -> str:
        return f"{self.price_model}{'+stress' if self.stress else ''}"


@dataclass(frozen=True)
class FundingEvent:
    event_id: str
    time: pd.Timestamp                   # exakt avräkningstid, UTC, millisekund
    rate: float
    M_ref: float                         # referensmarkpris enligt prismodellen
    M_ref_source: str                    # MARK_OPEN eller MARK_CLOSE
    M_ref_time: pd.Timestamp             # tid för referenspriset

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id:
            raise FundingError(f"event_id måste vara en icke-tom sträng, fick {self.event_id!r}.")
        _utc_ms("time", self.time)
        _utc_ms("M_ref_time", self.M_ref_time)
        object.__setattr__(self, "rate", _fnum("rate", self.rate))
        M = _fnum("M_ref", self.M_ref)
        if M <= 0:
            raise FundingError(f"M_ref måste vara > 0, fick {M}.")
        object.__setattr__(self, "M_ref", M)
        expected = {MARK_OPEN: bar_open(self.time), MARK_CLOSE: bar_open(self.time) + BAR}.get(self.M_ref_source)
        if expected is None:
            raise FundingError(f"Okänd källa för M_ref: {self.M_ref_source!r}.")
        if self.M_ref_time != expected:
            raise FundingError(f"M_ref_time {self.M_ref_time} stämmer inte med {self.M_ref_source} för event vid "
                               f"{self.time} (väntat {expected}).")


@dataclass(frozen=True)
class FundingState:
    """Redan behandlade event för ett konto i ett scenario."""
    account_key: str
    scenario: str
    processed: frozenset = frozenset()

    def __post_init__(self) -> None:
        for name in ("account_key", "scenario"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v:
                raise FundingError(f"{name} måste vara en icke-tom sträng, fick {v!r}.")
        object.__setattr__(self, "processed", frozenset(self.processed))


@dataclass(frozen=True)
class FundingRecord:
    event_id: str
    time: pd.Timestamp
    phase: str
    account_key: str
    scenario: str
    config: str
    q: float                             # innehav vid avräkningen
    rate: float
    M_ref: float
    M_ref_source: str
    M_ref_time: pd.Timestamp
    payment_base: float                  # q * M_ref * ränta
    payment: float                       # bokfört belopp efter eventuell stress
    C_before: float
    C_after: float
    E_before: float                      # E vid M_ref
    E_after: float
    version: str = VERSION

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def apply_funding(acct: Account, state: FundingState, event: FundingEvent, phase: str,
                  config: FundingConfig = FundingConfig()) -> tuple[Account, FundingState, FundingRecord]:
    """Bokför en händelse på det givna kontot. Returnerar nytt konto, nytt tillstånd och spårpost."""
    if not isinstance(acct, Account) or not isinstance(state, FundingState) or not isinstance(event, FundingEvent):
        raise FundingError("Fel typ för konto, tillstånd eller event.")
    if not isinstance(config, FundingConfig):
        raise FundingError("Fel typ för konfiguration.")
    if phase not in PHASES:
        raise FundingError(f"Okänd fas {phase!r}; tillåtna {PHASES}.")
    if event.M_ref_source != config.price_model:
        raise FundingError(f"Eventets källa {event.M_ref_source} matchar inte konfigurationen {config.price_model}.")
    if event.event_id in state.processed:
        raise FundingError(f"Event {event.event_id} är redan bokfört för {state.account_key}/{state.scenario}.")
    base = _out("fundingbelopp", acct.q * event.M_ref * event.rate)
    payment = _out("fundingbelopp", 2 * base) if config.stress and base > 0 else base
    E_before = acct.equity(event.M_ref)
    new = replace(acct, C=_out("C", acct.C - payment), funding_net=_out("funding_net", acct.funding_net + payment))
    E_after = new.equity(event.M_ref)
    record = FundingRecord(event_id=event.event_id, time=event.time, phase=phase, account_key=state.account_key,
                           scenario=state.scenario, config=config.label, q=acct.q, rate=event.rate, M_ref=event.M_ref,
                           M_ref_source=event.M_ref_source, M_ref_time=event.M_ref_time, payment_base=base,
                           payment=payment, C_before=acct.C, C_after=new.C, E_before=E_before, E_after=E_after)
    return new, replace(state, processed=state.processed | {event.event_id}), record
