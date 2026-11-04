"""H-0017 avsikter, handelsband och riskstatus, mom-risk/1.0.0 (research/h0017-protokoll.md §4, §7, §8.1, D07, D17).

Rena beslut på syntetiskt tillförda konton och signaler. Ingen eventloop, inga fyllningar (C1), ingen funding (C2),
ingen marginal eller likvidationsbokföring, ingen intrastapel-bound. Kommande eventlager anropar step() vid varje
4H-gräns T i ordning och skickar avsikten vidare till fyllningslagret vid öppningen T.

Vid gränsen T (§8.1 steg 0–1), för konto i huvudmodellen eller ett momentumkonto (long eller platt):
1. E_close = C + q * mark_close för stapeln som slutar vid T (beräknas av ledgern; funding och kostnader ingår redan
   i kontot och bokförs inte igen här). peak = max(peak, E_close); peak startar på startkapitalet.
2. Permanent stopp om E_close / peak - 1 <= -0,15. Absorberande: återställs aldrig.
3. Dagsstopp om E_close / day_start - 1 <= -0,02. lock_day = UTC-dagen för stapeln som stängde.
4. Om T är 00:00: dagsbeslut för dagen D = T - 1 dag, med B-signalens rad för D (decision_time = T):
   permanent spärr; platt signal med position (risk); w_current > cap (risk); abs(w_target - w_current) >= 0,02
   (normal); annars hold_units. Därefter dagsreset: day_start = E_close, före gap, funding och handel vid T.
5. Sammanslagning för fyllningstiden T: högst en avsikt, terminal > permanent > dagsstopp > capbrott/platt > normal.
   En riskavsikt stryker normalavsikten. En normalavsikt stryks också om fyllningsdagen är lock_day.

En avsikt fryser vikt och typ, inte enheter eller riktning. Beslutets pris (mark_close vid T) sparas skilt från
öppningens priser som bara fyllningslagret ser. Riskavsikter fylls reduce-only (C1 fill_risk), normalavsikter exakt
(C1 fill_normal); fill_intent() är den enda kopplingen.

20 % drawdown är protokollets utvärderingskrav, inte ett handelsstopp, och finns inte här.

Tidsregler: T är en UTC-pd.Timestamp på 4H-rutnätet. Första steget har T = start (första testöppningen) och saknar
close; varje följande steg måste ha T = föregående T + 4h. Ett steg för en redan behandlad eller överhoppad tid avvisas.
Allt validerat; fel ger RiskError utan att något tillstånd ändras (allt är oföränderligt).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from . import momentum_ledger as ledger
from .momentum_signal import VERSION as SIGNAL_VERSION
from .momentum_ledger import Account, LedgerError, _num

VERSION = "mom-risk/1.0.0"
BAR = pd.Timedelta(hours=4)
BAND = 0.02
DAY_STOP = -0.02
PERMANENT_STOP = -0.15

TERMINAL = "terminal"
PERMANENT = "permanent_stop"
DAY = "day_stop"
CAP = "cap_breach"
FLAT = "flat_signal"
NORMAL = "normal"
PRIORITY = (TERMINAL, PERMANENT, DAY, CAP, FLAT, NORMAL)   # CAP och FLAT uteslutande varandra från samma beslut
HOLD = "hold_units"


class RiskError(LedgerError):
    """Ogiltigt tillstånd, ogiltig tid eller indata, otillgänglig signal eller dubbelbehandling. Inget ändras."""


def _rnum(name, v) -> float:
    try:
        return _num(name, v)
    except LedgerError as exc:
        raise RiskError(str(exc)) from None


def _finite(name: str, v: float) -> float:
    if not math.isfinite(v):
        raise RiskError(f"Beräknat {name} är inte ändligt ({v}).")
    return v


def _boundary(name: str, t) -> pd.Timestamp:
    if not isinstance(t, pd.Timestamp) or t.tz is None or str(t.tz) != "UTC":
        raise RiskError(f"{name} måste vara en pd.Timestamp i UTC, fick {t!r}.")
    if (t - t.floor("D")) % BAR != pd.Timedelta(0):
        raise RiskError(f"{name} ligger inte på en 4H-gräns: {t}.")
    return t


def _day(t: pd.Timestamp) -> pd.Timestamp:
    return t.floor("D")


@dataclass(frozen=True)
class RiskState:
    initial: float
    peak: float
    day_start: float
    next_boundary: pd.Timestamp            # tiden T som nästa steg måste ha
    started: bool = False                  # första steget (utan close) har körts
    lock_day: pd.Timestamp | None = None
    permanent: bool = False
    permanent_time: pd.Timestamp | None = None
    last_decision_day: pd.Timestamp | None = None
    liquidated: bool = False               # dokumenterat likvidationstillstånd från kommande marginallager
    terminated: bool = False
    version: str = VERSION

    def __post_init__(self) -> None:
        for name in ("initial", "peak", "day_start"):
            object.__setattr__(self, name, _rnum(name, getattr(self, name)))
        if self.initial <= 0 or self.peak < self.initial:
            raise RiskError("Startkapital måste vara > 0 och peak >= startkapital.")
        if not self.liquidated and self.day_start <= 0:
            raise RiskError("day_start måste vara > 0 för ett levande konto.")
        _boundary("next_boundary", self.next_boundary)
        for name in ("started", "permanent", "liquidated", "terminated"):
            if not isinstance(getattr(self, name), bool):
                raise RiskError(f"{name} måste vara bool.")
        for name in ("lock_day", "last_decision_day", "permanent_time"):
            v = getattr(self, name)
            if v is not None and (not isinstance(v, pd.Timestamp) or str(v.tz) != "UTC"):
                raise RiskError(f"{name} måste vara None eller en UTC-pd.Timestamp.")
        if self.permanent != (self.permanent_time is not None):
            raise RiskError("permanent och permanent_time måste följas åt.")

    @classmethod
    def start(cls, initial_capital: float, start: pd.Timestamp) -> "RiskState":
        """Före första testöppningen: peak = day_start = startkapital, inget behandlat."""
        cap = _rnum("initial_capital", initial_capital)
        return cls(initial=cap, peak=cap, day_start=cap, next_boundary=_boundary("start", start))


@dataclass(frozen=True)
class CloseInput:
    """Kontot efter allt som hänt i stapeln (fyllning, funding) och markpriset vid stapelns close."""
    bar_open: pd.Timestamp
    account: Account
    mark_close: float
    liquidated: bool = False

    def __post_init__(self) -> None:
        _boundary("bar_open", self.bar_open)
        if not isinstance(self.account, Account):
            raise RiskError("account måste vara ett ledger-Account.")
        m = _rnum("mark_close", self.mark_close)
        if m <= 0:
            raise RiskError(f"mark_close måste vara > 0, fick {m}.")
        object.__setattr__(self, "mark_close", m)
        if not isinstance(self.liquidated, bool):
            raise RiskError("liquidated måste vara bool.")


@dataclass(frozen=True)
class SignalInput:
    """Raden ur B:s signals() för dag D. Bara de fält beslutet behöver."""
    day: pd.Timestamp
    decision_time: pd.Timestamp
    available: bool
    s: float
    cap: float
    w_target: float
    version: str

    def __post_init__(self) -> None:
        # Kontraktsgränsen kontrolleras på råvärdena innan något tolkas; gäller även dataclasses.replace och from_row.
        if not isinstance(self.available, (bool, np.bool_)):
            raise RiskError(f"available måste vara bool (eller numpy-bool), fick {self.available!r}.")
        object.__setattr__(self, "available", bool(self.available))
        if not isinstance(self.version, str) or self.version != SIGNAL_VERSION:
            raise RiskError(f"Signalversionen måste vara exakt {SIGNAL_VERSION}, fick {self.version!r}.")
        for name in ("day", "decision_time"):
            v = getattr(self, name)
            if not isinstance(v, pd.Timestamp) or v.tz is None or str(v.tz) != "UTC":
                raise RiskError(f"{name} måste vara en pd.Timestamp i UTC, fick {v!r}.")
        if self.day != self.day.floor("D") or self.decision_time != self.day + pd.Timedelta(days=1):
            raise RiskError(f"Signalens dag {self.day} och beslutstid {self.decision_time} följer inte dagskontraktet "
                            "(dag vid 00:00 UTC, beslut nästa 00:00).")

    @classmethod
    def from_row(cls, row: pd.Series) -> "SignalInput":
        """Rad ur B:s signals(); available och version skickas vidare som råvärden och valideras, inte omtolkas."""
        if not isinstance(row, pd.Series):
            raise RiskError("from_row kräver en rad (pd.Series) ur signals().")
        g = row.get                                        # saknat fält blir None och avvisas av valideringen
        return cls(day=row.name, decision_time=g("decision_time"), available=g("available"),
                   s=g("s"), cap=g("cap"), w_target=g("w_target"), version=g("version"))


@dataclass(frozen=True)
class Intent:
    kind: str
    w: float                               # fryst målvikt; inga enheter, ingen riktning
    decision_time: pd.Timestamp            # T
    fill_time: pd.Timestamp                # tidigaste fyllning: öppningen T
    source_bar: pd.Timestamp | None        # stapeln vars close gav beslutet
    E_decision: float                      # E_close vid beslutet
    mark_decision: float | None            # mark_close vid beslutet (None vid första gränsen); öppningens pris ses bara av fyllningslagret
    w_current: float
    reason: str
    version: str = VERSION

    @property
    def risk(self) -> bool:
        return self.kind != NORMAL


@dataclass(frozen=True)
class StepRecord:
    boundary: pd.Timestamp
    source_bar: pd.Timestamp | None
    E_close: float | None
    peak: float
    day_start_used: float                  # kapitalbasen för dagsstoppet vid denna close
    day_return: float | None
    drawdown: float | None
    permanent_triggered: bool
    day_stop_triggered: bool
    daily_decision: str | None             # kind, HOLD eller None när inget dagsbeslut togs
    candidates: tuple                      # alla avsiktstyper som prövades vid T, före sammanslagning
    intent: Intent | None
    suppressed: tuple = field(default_factory=tuple)   # (typ, orsak) som ströks
    version: str = VERSION


def _signal_ok(sig: SignalInput, T: pd.Timestamp) -> SignalInput:
    if not isinstance(sig, SignalInput):
        raise RiskError("signal måste vara SignalInput.")
    if sig.decision_time != T or sig.day != T - pd.Timedelta(days=1):
        raise RiskError(f"Signalen gäller {sig.day} med beslut {sig.decision_time}, inte dagen före {T}.")
    if not sig.available:
        raise RiskError(f"Signalen för {sig.day} är otillgänglig: OGILTIG_DATA, ingen ersättning med platt eller full vikt.")
    s, cap, w = (_rnum(n, v) for n, v in (("s", sig.s), ("cap", sig.cap), ("w_target", sig.w_target)))
    if s not in (0.0, 1 / 3, 2 / 3, 1.0) or not 0 < cap <= 1 or w != s * cap:
        raise RiskError(f"Signalvärden utanför kontraktet: s={s}, cap={cap}, w_target={w} (kräver w_target = s * cap).")
    return replace(sig, s=s, cap=cap, w_target=w)


def step(state: RiskState, T: pd.Timestamp, close: CloseInput | None = None, signal: SignalInput | None = None,
         terminal: bool = False) -> tuple[RiskState, StepRecord]:
    """En 4H-gräns T. Returnerar nytt tillstånd och post med högst en avsikt för fyllning vid öppningen T."""
    if not isinstance(state, RiskState):
        raise RiskError("state måste vara RiskState.")
    T = _boundary("T", T)
    if state.terminated:
        raise RiskError("Kontot är redan stängt vid terminal; inga fler steg.")
    if T != state.next_boundary:
        raise RiskError(f"Fel tid: väntade {state.next_boundary}, fick {T} (ingen dubbelbehandling eller lucka).")
    if not isinstance(terminal, bool):
        raise RiskError("terminal måste vara bool.")
    midnight = T == _day(T)
    if midnight != (signal is not None) and not (midnight and (terminal or state.liquidated)):
        raise RiskError("Signal krävs vid 00:00 och får inte ges vid andra gränser.")
    if state.started == (close is None):
        raise RiskError("Första steget saknar close; varje senare steg kräver close.")
    if close is not None and close.bar_open + BAR != T:
        raise RiskError(f"Close för stapeln {close.bar_open} slutar inte vid {T}.")

    peak, day_start, lock_day = state.peak, state.day_start, state.lock_day
    permanent, permanent_time, liquidated = state.permanent, state.permanent_time, state.liquidated
    E = q = mark = day_ret = dd = None
    perm_now = day_now = False
    candidates: list[tuple[str, float, str]] = []
    suppressed: list[tuple[str, str]] = []
    source_bar = close.bar_open if close is not None else None

    if close is not None and (close.liquidated or liquidated):
        acct = close.account
        if not close.liquidated or acct.q != 0 or acct.C != 0:
            raise RiskError("Ett likviderat konto måste rapporteras som likviderat med E = C = q = 0.")
        liquidated = True
    elif close is not None:
        acct, mark = close.account, close.mark_close
        q = acct.q
        if q < 0:
            raise RiskError("Huvud- och momentumkonton är long eller platta; q < 0 är ogiltigt.")
        E = _finite("E_close", acct.equity(mark))
        if E <= 0:
            raise RiskError(f"E_close = {E} utan dokumenterat likvidationstillstånd.")
        peak = max(peak, E)
        dd = _finite("drawdown", E / peak - 1)
        day_ret = _finite("dagsavkastning", E / day_start - 1)
        if not permanent and dd <= PERMANENT_STOP:
            permanent, permanent_time, perm_now = True, T, True
        if day_ret <= DAY_STOP:
            day_now, lock_day = True, _day(close.bar_open)
        if permanent and q != 0:
            candidates.append((PERMANENT, 0.0, "permanent stopp aktivt" if not perm_now else "E_close/peak - 1 <= -0,15"))
        if (day_now or lock_day == _day(close.bar_open)) and q != 0:
            candidates.append((DAY, 0.0, "E_close/day_start - 1 <= -0,02"))
    else:
        q, E, mark = 0.0, state.initial, None             # första gränsen: platt med startkapital

    if terminal and not liquidated:
        # Ett likviderat konto är absorberande (D21): terminalen markeras behandlad men ger ingen avsikt eller fill.
        candidates.append((TERMINAL, 0.0, "terminal stängning"))

    decision = None
    if midnight and signal is not None and not liquidated:
        sig = _signal_ok(signal, T)
        if state.last_decision_day == sig.day:
            raise RiskError(f"Dagsbeslut för {sig.day} är redan taget.")
        w_cur = 0.0 if q == 0 else _finite("w_current", q * mark / E)
        if permanent:
            decision = PERMANENT if q != 0 else HOLD
        elif sig.s == 0 and q > 0:
            decision = FLAT
            candidates.append((FLAT, 0.0, "platt signal med position"))
        elif w_cur > sig.cap:
            decision = CAP
            candidates.append((CAP, sig.w_target, f"w_current {w_cur} > cap {sig.cap}"))
        elif abs(sig.w_target - w_cur) >= BAND:
            decision = NORMAL
            candidates.append((NORMAL, sig.w_target, f"abs(w_target - w_current) = {abs(sig.w_target - w_cur)} >= 0,02"))
        else:
            decision = HOLD
    else:
        w_cur = 0.0 if not q or E is None or mark is None else _finite("w_current", q * mark / E)

    intent = None
    if candidates:
        candidates.sort(key=lambda c: PRIORITY.index(c[0]))
        kind, w, reason = candidates[0]
        suppressed = [(k, f"strykt av {kind}") for k, _, _ in candidates[1:]]
        if kind == NORMAL and lock_day is not None and _day(T) == lock_day:
            suppressed.append((NORMAL, "fyllningsdagen är lock_day"))
        elif kind == NORMAL and permanent:
            suppressed.append((NORMAL, "permanent stopp"))
        else:
            intent = Intent(kind=kind, w=w, decision_time=T, fill_time=T, source_bar=source_bar,
                            E_decision=E, mark_decision=mark,
                            w_current=w_cur, reason=reason)

    new_day_start = day_start
    last_decision_day = state.last_decision_day
    if midnight and not state.started:
        new_day_start = state.initial                      # E_end(dagen före start) = startkapital
    elif midnight and not liquidated:
        new_day_start = E                                  # dagsreset efter beslutet, före gap/funding/handel
    if midnight and signal is not None and not liquidated:
        last_decision_day = signal.day

    new_state = replace(state, peak=peak, day_start=new_day_start if not liquidated else 0.0,
                        next_boundary=T + BAR, started=True, lock_day=lock_day, permanent=permanent,
                        permanent_time=permanent_time, last_decision_day=last_decision_day,
                        liquidated=liquidated, terminated=terminal)
    record = StepRecord(boundary=T, source_bar=source_bar, E_close=E if close is not None and not liquidated else None,
                        peak=peak, day_start_used=day_start, day_return=day_ret, drawdown=dd,
                        permanent_triggered=perm_now, day_stop_triggered=day_now, daily_decision=decision,
                        candidates=tuple(k for k, _, _ in candidates), intent=intent, suppressed=tuple(suppressed))
    return new_state, record


def fill_intent(acct: Account, intent: Intent, P: float, M: float, c: float = ledger.COST_NORMAL):
    """Enda kopplingen till C1: riskavsikter reduce-only, normalavsikter exakt, med öppningens P och M."""
    if not isinstance(intent, Intent):
        raise RiskError("intent måste vara Intent.")
    fill = ledger.fill_risk if intent.risk else ledger.fill_normal
    return fill(acct, intent.w, P, M, c)
