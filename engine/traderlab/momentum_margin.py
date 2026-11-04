"""H-0017 marginal och absorberande likvidation, mom-margin/1.0.0 (research/h0017-protokoll.md §4, §8.1, §8.3, §9, D21).

Prövning och nollställning på redan givna konton och prispunkter. Ingen eventloop: kommande eventlager väljer vilket q
som kunde ha funnits, ordnar gap, scenario A-funding, marginalprövning och fyllning enligt §8.1, och anropar inga
fills eller funding efter en likvidation.

Modell (förregistrerad forsknings-/stressmodell, inte historiska Binance-villkor):
- Korsmarginal, en position, hela E som säkerhet. Underhållskrav MM = mmr * |q| * m med mmr 0,05 eller 0,005 som
  separata scenarier. Träff när E(m) = C + q * m <= MM, utan epsilon.
- Prispunkter: gappunkten (mark_open, fas "gap") och den ogynnsamma extremen inom stapeln (fas "intrabar_adverse"):
  mark_low för long, mark_high för short. En träff inom stapeln har känd stapel men okänd exakt tid; ingen tid anges.
- Träff ger total förlust: C = q = avg_price = 0 och dokumenterat likvidationstillstånd. Ingen likvidationsavgift, ingen
  artificiell fill. Nollställningen bokförs i Account.liquidation_adjustment (förändring -C_old - q_old * avg_old), så att
  avstämningen C = C0 + realized - costs - funding_net + liquidation_adjustment - q * avg_price fortsatt håller.
  Spåret delar förändringen i mark-to-market q_old * (m - avg_old) och kapitalreset -E_before. Ett negativt E_before
  (gap förbi tröskeln) ger en positiv resetkomponent; det är modellens nollgolv, ingen marknadsvinst.
- Trösklarna (long -C/(q(1 - mmr)), short C/(|q|(1 + mmr))) är bara diagnostik; beslutet tas av direktvillkoret.

Fel ger MarginError utan att konto eller tillstånd ändras (allt är oföränderligt).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import pandas as pd

from .momentum_ledger import Account, LedgerError, _num, _out

VERSION = "mom-margin/1.0.0"
MMRS = (0.05, 0.005)
GAP = "gap"
INTRABAR = "intrabar_adverse"
MARK_OPEN, MARK_LOW, MARK_HIGH = "mark_open", "mark_low", "mark_high"
RECONCILE_TOL = 1e-9                     # relativ tolerans för mtm + reset mot justeringens förändring


class MarginError(LedgerError):
    """Ogiltig indata, gammal prövning, dubbel nollställning eller oförklarat nollkonto. Inget ändras."""


def _mnum(name, v) -> float:
    """Ledgerns numeriska validering. Ett reellt tal som inte kan bli en ändlig float (till exempel 10**400) ger
    OverflowError vid konverteringen; bara det och LedgerError från själva valideringen översätts till MarginError."""
    try:
        return _num(name, v)
    except LedgerError as exc:
        raise MarginError(str(exc)) from None
    except OverflowError:
        raise MarginError(f"{name} kan inte representeras som ett ändligt flyttal: {type(v).__name__}.") from None


def _bar(t) -> pd.Timestamp:
    if not isinstance(t, pd.Timestamp) or t.tz is None or str(t.tz) != "UTC":
        raise MarginError(f"bar_open måste vara en pd.Timestamp i UTC, fick {t!r}.")
    if (t - t.floor("D")) % pd.Timedelta(hours=4) != pd.Timedelta(0):
        raise MarginError(f"bar_open ligger inte på en 4H-gräns: {t}.")
    return t


def _mmr(mmr) -> float:
    """Numerisk validering först (reellt, ändligt, inte bool eller komplext), därefter medlemskap."""
    try:
        value = _mnum("mmr", mmr)
    except MarginError:
        raise MarginError(f"Underhållssatsen måste vara exakt en av {MMRS}, fick {mmr!r}.") from None
    if value not in MMRS:
        raise MarginError(f"Underhållssatsen måste vara exakt en av {MMRS}, fick {mmr!r}.")
    return value


def _account(acct) -> Account:
    if not isinstance(acct, Account):
        raise MarginError(f"Kontot måste vara ett ledger-Account, fick {type(acct).__name__}.")
    return acct


def threshold(acct: Account, mmr: float) -> float | None:
    """Diagnostisk likvidationsgräns enligt §9; None för platt konto. Används aldrig för beslutet."""
    acct, mmr = _account(acct), _mmr(mmr)
    if acct.q == 0:
        return None
    # Nämnaren kontrolleras före divisionen: en oändlig mellanprodukt får inte bli ett legitimt nollpris.
    if acct.q > 0:
        return _out("tröskel", -acct.C / _out("tröskelns nämnare", acct.q * (1 - mmr)))
    return _out("tröskel", acct.C / _out("tröskelns nämnare", -acct.q * (1 + mmr)))


@dataclass(frozen=True)
class MarginCheck:
    account: Account                      # exakt konto som prövades; nollställning kräver samma konto
    phase: str
    bar_open: pd.Timestamp
    mmr: float
    price_source: str
    m: float
    q: float
    E: float                              # C + q * m, ej klippt
    MM: float
    hit: bool
    threshold: float | None
    version: str = VERSION


@dataclass(frozen=True)
class MarginState:
    """Likvidationstillstånd för ett konto i ett scenario (inklusive underhållssats)."""
    account_key: str
    scenario: str
    mmr: float
    liquidated: bool = False
    record: "LiquidationRecord | None" = None

    def __post_init__(self) -> None:
        for name in ("account_key", "scenario"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v:
                raise MarginError(f"{name} måste vara en icke-tom sträng, fick {v!r}.")
        object.__setattr__(self, "mmr", _mmr(self.mmr))
        if not isinstance(self.liquidated, bool) or self.liquidated != (self.record is not None):
            raise MarginError("liquidated och record måste följas åt.")


@dataclass(frozen=True)
class LiquidationRecord:
    account_key: str
    scenario: str
    phase: str
    bar_open: pd.Timestamp
    mmr: float
    price_source: str
    m: float
    q_old: float
    C_old: float
    avg_price_old: float
    E_before: float                       # kan vara negativt efter gap
    MM: float
    adjustment_delta: float               # -C_old - q_old * avg_old
    mark_to_market: float                 # q_old * (m - avg_old)
    capital_reset: float                  # -E_before
    account_before: Account
    account_after: Account
    version: str = VERSION


def check(acct: Account, state: MarginState, phase: str, m: float, price_source: str,
          bar_open: pd.Timestamp) -> MarginCheck:
    """Pröva direktvillkoret E(m) <= mmr * |q| * m vid en given markpunkt."""
    if not isinstance(acct, Account) or not isinstance(state, MarginState):
        raise MarginError("Fel typ för konto eller tillstånd.")
    if state.liquidated:
        raise MarginError(f"{state.account_key}/{state.scenario} är redan likviderat; ingen ny prövning.")
    bar_open = _bar(bar_open)
    m = _mnum("m", m)
    if m <= 0:
        raise MarginError(f"Markpriset måste vara > 0, fick {m}.")
    if phase == GAP:
        if price_source != MARK_OPEN:
            raise MarginError(f"Gapprövning kräver mark_open, fick {price_source!r}.")
    elif phase == INTRABAR:
        if acct.q == 0:
            raise MarginError("Ingen ogynnsam extrem för ett platt konto.")
        expected = MARK_LOW if acct.q > 0 else MARK_HIGH
        if price_source != expected:
            raise MarginError(f"Ogynnsam extrem för {'long' if acct.q > 0 else 'short'} är {expected}, fick {price_source!r}.")
    else:
        raise MarginError(f"Okänd fas {phase!r}; tillåtna {GAP!r} och {INTRABAR!r}.")
    E = _out("E", acct.C + acct.q * m)
    if acct.q == 0 and E <= 0:
        raise MarginError(f"Platt konto med E = {E} utan likvidation: oförklarat nollkonto, inte ett likvidationsbevis.")
    MM = _out("MM", state.mmr * abs(acct.q) * m)
    return MarginCheck(account=acct, phase=phase, bar_open=bar_open, mmr=state.mmr, price_source=price_source, m=m,
                       q=acct.q, E=E, MM=MM, hit=acct.q != 0 and E <= MM, threshold=threshold(acct, state.mmr))


def check_bar(acct: Account, state: MarginState, bar_open: pd.Timestamp, mark_open: float, mark_high: float,
              mark_low: float, mark_close: float) -> MarginCheck:
    """Ogynnsam extrem inom en hel markstapel, efter validering av OHLC. Inga beslut tas från high/low."""
    acct = _account(acct)
    if not isinstance(state, MarginState):
        raise MarginError("Fel typ för tillstånd.")
    o, h, l, c = (_mnum(n, v) for n, v in (("mark_open", mark_open), ("mark_high", mark_high),
                                            ("mark_low", mark_low), ("mark_close", mark_close)))
    if min(o, h, l, c) <= 0 or not (l <= min(o, c) and max(o, c) <= h):
        raise MarginError(f"Ogiltig mark-OHLC: open {o}, high {h}, low {l}, close {c}.")
    if acct.q > 0:
        return check(acct, state, INTRABAR, l, MARK_LOW, bar_open)
    return check(acct, state, INTRABAR, h, MARK_HIGH, bar_open)


def liquidate(acct: Account, state: MarginState, result: MarginCheck) -> tuple[Account, MarginState, LiquidationRecord]:
    """Atomisk nollställning efter en träff på exakt samma konto. Ingen fill, ingen avgift."""
    acct = _account(acct)
    if not isinstance(result, MarginCheck) or not isinstance(state, MarginState):
        raise MarginError("Fel typ för prövning eller tillstånd.")
    if state.liquidated:
        raise MarginError(f"{state.account_key}/{state.scenario} är redan likviderat; nollställs inte igen.")
    if result.account != acct:
        raise MarginError("Prövningen gäller inte detta konto (gammalt resultat); inget nollställs.")
    if result.mmr != state.mmr:
        raise MarginError("Prövningens underhållssats matchar inte tillståndets scenario.")
    if not result.hit:
        raise MarginError("Ingen träff; kontot nollställs inte.")
    delta = _out("justering", -acct.C - acct.q * acct.avg_price)
    mtm = _out("mark-to-market", acct.q * (result.m - acct.avg_price))
    reset = -result.E
    if abs((mtm + reset) - delta) > RECONCILE_TOL * max(1.0, abs(acct.C), abs(acct.q * result.m)):
        raise MarginError("mark-to-market + reset stämmer inte med justeringen.")
    after = replace(acct, C=0.0, q=0.0, avg_price=0.0,
                    liquidation_adjustment=_out("liquidation_adjustment", acct.liquidation_adjustment + delta))
    record = LiquidationRecord(account_key=state.account_key, scenario=state.scenario, phase=result.phase,
                               bar_open=result.bar_open, mmr=result.mmr, price_source=result.price_source, m=result.m,
                               q_old=acct.q, C_old=acct.C, avg_price_old=acct.avg_price, E_before=result.E,
                               MM=result.MM, adjustment_delta=delta, mark_to_market=mtm, capital_reset=reset,
                               account_before=acct, account_after=after)
    return after, replace(state, liquidated=True, record=record), record
