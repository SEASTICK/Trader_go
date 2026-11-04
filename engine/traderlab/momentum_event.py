"""H-0017 eventkomposition för ett huvudmodellskonto, mom-event/1.0.0 (research/h0017-protokoll.md §4, §8.1–§8.4, §9,
§10.1, §15, D07, D17–D21).

Komponerar de godkända modulerna – signalrader (B), ledger (C1), funding (C2), risk (C3) och marginal (C4) – för ett
long/platt-konto i ett givet scenario (ordning A eller B, underhållssats, kostnad). Inga egna formler för storlek,
funding, beslut eller marginal. Matas med syntetiska staplar, fundingevent och signalrader; ingen historikläsare.

En stapel b med öppning T behandlas i ett anrop av process_bar, i protokollets ordning:
  §8.1 steg 0–1 (gränsen T): close för föregående stapel b-1 med dess mark_close till C3 (peak, permanent stopp,
     dagsstopp, vid 00:00 dagsbeslut och reset). Första stapeln har ingen close.
  §8.1 steg 2–6 (öppningen T): gappunkt med q_old vid mark_open; scenario A: samtidig funding på q_old; marginal vid
     gappunkten; vid träff nollställning och ingen fill eller B-funding; annars högst en avsikt via C3/C1 vid
     kontraktsöppning P med mark_open som värderingspris (E_trade); scenario B: samtidig funding på q efter fyllning
     (E_post).
  §8.3 inom stapeln: marginalprövning vid mark_low med C efter betald och före mottagen funding från stapelns
     mellanhändelser. Utan träff bokförs mellanhändelserna kronologiskt på q_open. Vid träff är träfftiden okänd och
     ingen ordning mot de exakta fundingtiderna påstås (Edwins beslut 2026-11-04, docs/momentum-C5-01-edwins-beslut.md):
     ingen av stapelns mellanhändelser bokförs i ledgern; var och en redovisas som olöst med exakt tid och belopp, och
     nollställningen tar hela kontot efter öppningen. Prövningsunderlaget (C4:s post) hålls skilt från ledgern; en
     kredit kan varken rädda prövningen eller återuppliva kontot, och ingen betalning räknas två gånger.

Horisont (§4): första öppning 2022-01-01 00:00 med 100 000 och q = 0; terminal vid öppningen 2024-12-31 20:00, där
C3:s terminalavsikt stänger allt efter gap, A-funding och marginalprövning. Därefter avvisas fler staplar. Inga
staplar eller event före start eller från 2025-01-01. Inga dagsbeslut vid 2025-01-01.

Kapitalpunkter (§10.1): start, close för staplarna 2022-01-01 00 till 2024-12-31 16 och terminalt kapital vid
2024-12-31 20. Dagliga E_end (§4): E_close för dagens 20-stapel, känt vid nästa 00:00 före gap, funding och handel;
sista dagen är terminalt kapital. Ingen statistik, inga drawdownmått, ingen intrastapel-bound (§10.2) här.

Allt är oföränderligt; fel ger EventError utan att något tillstånd ändras. EngineState, BarResult och RunLog skapas
bara av EngineState.start, process_bar och RunLog.begin/add; dataclasses.replace och direkt konstruktion avvisas, så
att ett tillstånd inte kan sättas ihop av delar från olika konton eller förlopp. Det finns ingen publik återställning
mitt i horisonten; den privata fixturvägen EngineState._fixture är bara för syntetiska prov och ingår inte i API:t.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, replace

import pandas as pd

from . import momentum_funding as fund
from . import momentum_ledger as ledger
from . import momentum_margin as margin
from . import momentum_risk as risk
from .momentum_ledger import Account, LedgerError, _num, _out, _show

VERSION = "mom-event/1.0.0"
PROTOCOL = "momentum-protokoll/1.0.0"
BAR = pd.Timedelta(hours=4)
START = pd.Timestamp("2022-01-01 00:00", tz="UTC")
TERMINAL = pd.Timestamp("2024-12-31 20:00", tz="UTC")
END = pd.Timestamp("2025-01-01 00:00", tz="UTC")
INITIAL = 100_000.0
ORDERS = ("A", "B")
COSTS = (ledger.COST_NORMAL, ledger.COST_STRESS)
UNKNOWN_TIME = "okänd inom stapeln"
# Fundingkategorier i spåret: varje event i en stapel får exakt en.
BOOKED = ("funding_A", "funding_B", "funding_interior")
ABSORBED = "funding_absorbed"        # efter känd likvidation (gappunkt eller tidigare stapel): ingen effekt
UNRESOLVED = "funding_unresolved"    # i en stapel med intrastapelträff: ordning mot träffen okänd, ej bokförd

_ISSUING = contextvars.ContextVar("mom_event_issuing", default=False)


@contextmanager
def _issuing():
    token = _ISSUING.set(True)
    try:
        yield
    finally:
        _ISSUING.reset(token)


def _require_issued(what: str) -> None:
    if not _ISSUING.get():
        raise EventError(f"{what} skapas bara av modulens egna vägar (start, process_bar, RunLog); "
                         "replace eller direkt konstruktion avvisas.")


class EventError(LedgerError):
    """Ogiltig indata, fel ordning, fel konto/scenario eller steg efter terminal. Inget ändras."""


def _enum(name, v) -> float:
    try:
        return _num(name, v)
    except LedgerError as exc:
        raise EventError(str(exc)) from None


def _bar_time(name: str, t) -> pd.Timestamp:
    if not isinstance(t, pd.Timestamp) or t.tz is None or str(t.tz) != "UTC":
        raise EventError(f"{name} måste vara en pd.Timestamp i UTC, fick {_show(t)}.")
    if (t - t.floor("D")) % BAR != pd.Timedelta(0):
        raise EventError(f"{name} ligger inte på en 4H-gräns: {t}.")
    return t


@dataclass(frozen=True)
class Scenario:
    """Ett komplett scenario för ett konto. L1/L2 är identiska för huvudmodellen (ingen legacy-stop)."""
    account_key: str
    order: str                   # "A" eller "B" (§8.1)
    mmr: float                   # 0,05 eller 0,005 (§9)
    cost: float = ledger.COST_NORMAL

    def __post_init__(self) -> None:
        if not isinstance(self.account_key, str) or not self.account_key:
            raise EventError(f"account_key måste vara en icke-tom sträng, fick {_show(self.account_key)}.")
        if not isinstance(self.order, str) or self.order not in ORDERS:
            raise EventError(f"Ordningen måste vara A eller B, fick {_show(self.order)}.")
        try:
            object.__setattr__(self, "mmr", margin._mmr(self.mmr))
        except LedgerError as exc:
            raise EventError(str(exc)) from None
        c = _enum("cost", self.cost)
        if c not in COSTS:
            raise EventError(f"Kostnaden måste vara {COSTS[0]} eller {COSTS[1]}, fick {_show(self.cost)}.")
        object.__setattr__(self, "cost", c)

    @property
    def label(self) -> str:
        return f"{self.order}-mmr{self.mmr}-c{self.cost}"


@dataclass(frozen=True)
class Bar:
    """Syntetisk 4H-stapel: kontraktsöppning för fyllning, mark-OHLC för värdering, funding-referens och marginal."""
    open_time: pd.Timestamp
    contract_open: float
    mark_open: float
    mark_high: float
    mark_low: float
    mark_close: float
    synthetic: bool = True

    def __post_init__(self) -> None:
        _bar_time("open_time", self.open_time)
        for name in ("contract_open", "mark_open", "mark_high", "mark_low", "mark_close"):
            v = _enum(name, getattr(self, name))
            if v <= 0:
                raise EventError(f"{name} måste vara > 0, fick {v}.")
            object.__setattr__(self, name, v)
        if not (self.mark_low <= min(self.mark_open, self.mark_close) and max(self.mark_open, self.mark_close) <= self.mark_high):
            raise EventError(f"Ogiltig mark-OHLC för {self.open_time}.")
        if self.synthetic is not True:
            raise EventError("Endast syntetiska staplar accepteras i C5.")


@dataclass(frozen=True)
class Trace:
    phase: str
    time: object                 # pd.Timestamp eller UNKNOWN_TIME för intrastapelträff
    bar_open: pd.Timestamp | None
    account_key: str
    scenario: str
    C: float
    q: float
    E: float | None
    M: float | None = None
    P: float | None = None
    source: str | None = None
    cost: float = 0.0
    funding: float = 0.0
    event_id: str | None = None
    intent: str | None = None
    intent_decision_time: pd.Timestamp | None = None
    reason: str | None = None
    risk_status: str | None = None
    mmr: float | None = None
    versions: tuple = (VERSION, PROTOCOL, risk.VERSION, ledger.VERSION, fund.VERSION, margin.VERSION)


@dataclass(frozen=True)
class EngineState:
    """Tillståndet för ett konto i ett scenario före stapeln next_bar.

    Skapas publikt bara via start (det låsta startläget) och process_bar. Varje konstruktion prövar invarianterna
    nedan; replace och direkt konstruktion avvisas.
    """
    scenario: Scenario
    account: Account
    risk_state: risk.RiskState
    funding_state: fund.FundingState
    margin_state: margin.MarginState
    next_bar: pd.Timestamp                       # öppningstid för nästa stapel som får behandlas
    prev_mark_close: float | None = None         # föregående stapels mark_close för closen vid next_bar
    terminated: bool = False

    def __post_init__(self) -> None:
        s, a, rs, ms = self.scenario, self.account, self.risk_state, self.margin_state
        if not isinstance(s, Scenario) or not isinstance(a, Account):
            raise EventError("Fel typ för scenario eller konto.")
        if not isinstance(rs, risk.RiskState) or not isinstance(self.funding_state, fund.FundingState) \
                or not isinstance(ms, margin.MarginState):
            raise EventError("Fel typ för risk-, funding- eller marginaltillstånd.")
        if (self.funding_state.account_key, self.funding_state.scenario) != (s.account_key, s.label) or \
                (ms.account_key, ms.scenario) != (s.account_key, s.label):
            raise EventError("Funding- och marginaltillstånd hör inte till detta konto och scenario.")
        if ms.mmr != s.mmr:
            raise EventError("Marginaltillståndets sats matchar inte scenariot.")
        _bar_time("next_bar", self.next_bar)
        if not isinstance(self.terminated, bool) or self.terminated != rs.terminated:
            raise EventError("terminated måste följa riskmodulens terminalstatus.")
        if not self.terminated and rs.next_boundary != self.next_bar:
            raise EventError("Riskmodulens nästa gräns matchar inte nästa stapel.")
        if ms.liquidated != rs.liquidated and rs.started:
            # Riskmodulen får veta om likvidationen först vid nästa close; tillåt bara den ordningen.
            if not (ms.liquidated and not rs.liquidated):
                raise EventError("Likvidationsflaggorna i risk- och marginaltillstånd är inkonsekventa.")
        if ms.liquidated and (a.C != 0 or a.q != 0 or a.avg_price != 0):
            raise EventError("Ett likviderat konto måste ha C = q = 0.")
        if a.q < 0:
            raise EventError("Huvudmodellen är long eller platt; q < 0 är ogiltigt.")
        if not rs.started and (self.prev_mark_close is not None or self.next_bar != START or a != Account.open(INITIAL)
                               or rs != risk.RiskState.start(INITIAL, START) or self.funding_state.processed
                               or ms.liquidated):
            raise EventError("Ett ostartat tillstånd måste vara exakt startläget: 100 000, q = 0, orörd bokföring, "
                             "START och inget föregående close.")
        if a.deposit != INITIAL or rs.initial != INITIAL:
            raise EventError(f"Insättning {a.deposit} och riskmodulens startkapital {rs.initial} måste båda vara det "
                             f"låsta startkapitalet {INITIAL} (§4, inga tillskott, D21).")
        if a.funding_net != 0 and not self.funding_state.processed:
            raise EventError("Kontot har bokförd funding men fundingtillståndet saknar behandlade event.")
        gap = a.reconciliation_gap()
        if abs(gap) > margin.RECONCILE_TOL * max(1.0, abs(a.deposit), abs(a.C), abs(a.q * a.avg_price)):
            raise EventError(f"Kontot stämmer inte av mot sin bokföring (gap {gap}).")
        if rs.started:
            if self.prev_mark_close is None:
                raise EventError("prev_mark_close krävs efter första stapeln.")
            pm = _enum("prev_mark_close", self.prev_mark_close)
            if pm <= 0:
                raise EventError(f"prev_mark_close måste vara > 0, fick {pm}.")
            object.__setattr__(self, "prev_mark_close", pm)
            if not ms.liquidated:
                if a.equity(pm) <= 0:
                    raise EventError("Levande konto med E <= 0 utan likvidation: oförklarat nollkonto (D21).")
                last_day = (self.next_bar - BAR).floor("D")
                if a.q != 0 and (rs.permanent or (rs.lock_day is not None and rs.lock_day == last_day)):
                    raise EventError("Riskstatet har permanent stopp eller dagslås men kontot har position; "
                                     "konto och risklås hör inte ihop.")
        _require_issued("EngineState")

    @classmethod
    def start(cls, scenario: Scenario) -> "EngineState":
        if not isinstance(scenario, Scenario):
            raise EventError("scenario måste vara Scenario.")
        with _issuing():
            return cls(scenario=scenario, account=Account.open(INITIAL),
                       risk_state=risk.RiskState.start(INITIAL, START),
                       funding_state=fund.FundingState(scenario.account_key, scenario.label),
                       margin_state=margin.MarginState(scenario.account_key, scenario.label, scenario.mmr),
                       next_bar=START)

    @classmethod
    def _fixture(cls, scenario: Scenario, account: Account, risk_state: risk.RiskState,
                 funding_state: fund.FundingState, margin_state: margin.MarginState, next_bar: pd.Timestamp,
                 prev_mark_close: float) -> "EngineState":
        """PRIVAT, endast syntetiska prov: ett tillstånd mitt i horisonten byggt av givna delar.

        Ingen publik återställning eller delhorisont ingår i C5. Delarnas gemensamma proveniens kan inte bevisas här;
        invarianterna ovan prövas ändå (låst kapitalbas, avstämning, levande E > 0, inget risklås med position,
        likviderat konto platt och noll). Ett fixturtillstånd kan inte börja en RunLog.
        """
        _bar_time("next_bar", next_bar)
        if not isinstance(risk_state, risk.RiskState) or not risk_state.started or risk_state.terminated:
            raise EventError("En fixtur kräver ett startat, icke-terminalt riskstate; startläget fås via start.")
        if not START < next_bar <= TERMINAL:
            raise EventError(f"En fixtur kräver START < next_bar <= TERMINAL, fick {next_bar}.")
        with _issuing():
            return cls(scenario=scenario, account=account, risk_state=risk_state, funding_state=funding_state,
                       margin_state=margin_state, next_bar=next_bar, prev_mark_close=prev_mark_close)


@dataclass(frozen=True)
class BarResult:
    prev_state: EngineState      # tillståndet som stapeln behandlades från
    state: EngineState
    bar_open: pd.Timestamp
    trace: tuple                 # ordnade Trace-poster
    close_point: tuple | None    # (källstapel, tid känd, E_close) för föregående stapel, None för första
    day_end: tuple | None        # (dag, E_end, likviderad) vid 00:00-gränser
    terminal_point: tuple | None # (terminalstapel, E efter terminalens händelser) vid terminal
    step_record: risk.StepRecord
    simultaneous: int
    interior_booked: int
    absorbed: int                # event utan effekt efter känd likvidation (gappunkt eller tidigare)
    unresolved: tuple = ()       # (event_id, tid, belopp, i prövningsunderlaget) vid intrastapelträff, ej bokförda
    margin_basis: tuple | None = None   # (C, E, MM, mark_low) för intrastapelprövningen när positionen fanns

    def __post_init__(self) -> None:
        _require_issued("BarResult")


def _validate_events(bar: Bar, events) -> tuple[list, list]:
    if not isinstance(events, (list, tuple)):
        raise EventError("events måste vara en lista eller tuple av FundingEvent.")
    ids, last = set(), None
    simultaneous, interior = [], []
    for e in events:
        if not isinstance(e, fund.FundingEvent):
            raise EventError(f"Fel typ för fundingevent: {type(e).__name__}.")
        if not bar.open_time <= e.time < bar.open_time + BAR:
            raise EventError(f"Event {e.event_id} vid {e.time} ligger inte i stapeln {bar.open_time}.")
        if e.time < START or e.time >= END:
            raise EventError(f"Event {e.event_id} ligger utanför horisonten.")
        if last is not None and e.time < last:
            raise EventError("Fundingevent måste vara sorterade efter tid.")
        if e.event_id in ids:
            raise EventError(f"Dubblerat event-id {e.event_id} i stapeln.")
        if e.M_ref_source != fund.MARK_OPEN or e.M_ref != bar.mark_open:
            raise EventError(f"Event {e.event_id} har M_ref {e.M_ref} ({e.M_ref_source}); stapelns mark_open är "
                             f"{bar.mark_open}.")
        ids.add(e.event_id)
        last = e.time
        (simultaneous if e.time == bar.open_time else interior).append(e)
    return simultaneous, interior


def _trace(state_like, phase, acct, M=None, **kw) -> Trace:
    s = state_like.scenario
    E = acct.equity(M) if M is not None else None
    return Trace(phase=phase, account_key=s.account_key, scenario=s.label, C=acct.C, q=acct.q, E=E, M=M,
                 mmr=s.mmr, **kw)


def process_bar(state: EngineState, bar: Bar, events=(), signal: risk.SignalInput | None = None) -> BarResult:
    """Behandla stapeln som börjar vid state.next_bar: close för föregående stapel, öppning, mellanhändelser."""
    if not isinstance(state, EngineState) or not isinstance(bar, Bar):
        raise EventError("Fel typ för tillstånd eller stapel.")
    if state.terminated:
        raise EventError("Terminal är redan behandlad; inga fler handelssteg.")
    T = bar.open_time
    if T != state.next_bar:
        raise EventError(f"Fel stapel: väntade {state.next_bar}, fick {T} (ingen lucka, dubblett eller bakåtsteg).")
    if T < START or T > TERMINAL:
        raise EventError(f"Stapeln {T} ligger utanför horisonten {START}–{TERMINAL}.")
    simultaneous, interior = _validate_events(bar, events)
    s = state.scenario
    acct, rs, fs, ms = state.account, state.risk_state, state.funding_state, state.margin_state
    trace: list[Trace] = []
    liquidated = ms.liquidated

    # §8.1 steg 0–1: close för föregående stapel och eventuellt dagsbeslut vid T.
    close_point = day_end = None
    close = None
    if rs.started:
        prev_bar = T - BAR
        close = risk.CloseInput(prev_bar, acct, state.prev_mark_close, liquidated=liquidated)
        E_close = 0.0 if liquidated else acct.equity(state.prev_mark_close)
        close_point = (prev_bar, T, E_close)
        trace.append(_trace(state, "close", acct, state.prev_mark_close if not liquidated else None,
                            time=T, bar_open=prev_bar, source="mark_close"))
        if T == T.floor("D"):
            day_end = (T - pd.Timedelta(days=1), E_close, liquidated)
    try:
        rs, rec = risk.step(rs, T, close, signal, terminal=T == TERMINAL)
    except LedgerError as exc:
        raise EventError(f"Riskmodulen avvisade gränsen {T}: {exc}") from None
    intent = rec.intent
    status = ("likviderad" if liquidated else "permanent stopp" if rs.permanent else
              f"lock_day {rs.lock_day.date()}" if rs.lock_day is not None and rs.lock_day == T.floor("D") else "levande")
    if rec.daily_decision is not None or intent is not None:
        trace.append(_trace(state, "decision", acct, time=T, bar_open=close.bar_open if close is not None else None,
                            intent=intent.kind if intent else rec.daily_decision,
                            intent_decision_time=intent.decision_time if intent else None,
                            reason=intent.reason if intent else None, risk_status=status))

    # §8.1 steg 2–6: öppningen T.
    booked = absorbed = 0
    unresolved: list[tuple] = []
    margin_basis = None

    def absorb(evts, why):
        nonlocal absorbed
        for e in evts:
            absorbed += 1
            trace.append(_trace(state, ABSORBED, acct, time=e.time, bar_open=T, event_id=e.event_id, reason=why))

    if liquidated:
        trace.append(_trace(state, "absorbed", acct, time=T, bar_open=T, reason="likviderat konto: inga event, ingen avsikt"))
        absorb(simultaneous + interior, "likviderat i tidigare stapel")
    else:
        trace.append(_trace(state, "gap", acct, bar.mark_open, time=T, bar_open=T, source="mark_open"))
        if s.order == "A":
            for e in simultaneous:
                acct, fs, fr = fund.apply_funding(acct, fs, e, "funding_A")
                trace.append(_trace(state, "funding_A", acct, bar.mark_open, time=e.time, bar_open=T,
                                    source="mark_open", funding=fr.payment, event_id=e.event_id))
        chk = margin.check(acct, ms, margin.GAP, bar.mark_open, margin.MARK_OPEN, T) if acct.q != 0 else None
        if chk is not None and chk.hit:
            acct, ms, lr = margin.liquidate(acct, ms, chk)
            liquidated = True
            trace.append(_trace(state, "liquidation", acct, time=T, bar_open=T, M=bar.mark_open, source="mark_open",
                                reason=f"E {lr.E_before} <= MM {lr.MM} vid gappunkten; avsikt {intent.kind if intent else None} struken",
                                risk_status="likviderad"))
            absorb((simultaneous if s.order == "B" else []) + interior, "efter likvidation vid gappunkten")
        else:
            if intent is not None:
                acct, f = risk.fill_intent(acct, intent, bar.contract_open, bar.mark_open, s.cost)
                trace.append(_trace(state, "after_trade", acct, bar.mark_open, time=T, bar_open=T, P=bar.contract_open,
                                    source="mark_open", cost=f.cost, intent=intent.kind,
                                    intent_decision_time=intent.decision_time,
                                    reason="risk_reduce_only_hold" if f.risk_reduce_only_hold else intent.reason))
            else:
                trace.append(_trace(state, "after_trade", acct, bar.mark_open, time=T, bar_open=T, source="mark_open",
                                    reason="ingen avsikt"))
            if s.order == "B":
                for e in simultaneous:
                    acct, fs, fr = fund.apply_funding(acct, fs, e, "funding_B")
                    trace.append(_trace(state, "funding_B", acct, bar.mark_open, time=e.time, bar_open=T,
                                        source="mark_open", funding=fr.payment, event_id=e.event_id))
                trace.append(_trace(state, "after_funding_B", acct, bar.mark_open, time=T, bar_open=T,
                                    source="mark_open"))

            # §8.3: mellanhändelser och intrastapelmarginal. Beloppen tas från C2 på en kladdkopia i tidsordning.
            records, scratch, scratch_fs = [], acct, fs
            for e in interior:
                scratch, scratch_fs, fr = fund.apply_funding(scratch, scratch_fs, e, "funding_interior")
                records.append(fr)
            ichk = None
            if acct.q != 0:
                basis, basis_fs = acct, fs                           # C efter betald, före mottagen (§8.3)
                for e, fr in zip(interior, records):
                    if fr.payment > 0:
                        basis, basis_fs, _ = fund.apply_funding(basis, basis_fs, e, "funding_interior")
                ichk = margin.check_bar(basis, ms, T, bar.mark_open, bar.mark_high, bar.mark_low, bar.mark_close)
                margin_basis = (basis.C, ichk.E, ichk.MM, ichk.m)
                trace.append(_trace(state, "margin_basis", basis, ichk.m, time=UNKNOWN_TIME, bar_open=T,
                                    source=ichk.price_source,
                                    reason=f"prövningsunderlag, ej ledger: E {ichk.E} {'<=' if ichk.hit else '>'} MM {ichk.MM}"))
            if ichk is not None and ichk.hit:
                # Edwins beslut (C5-01): ingen mellanhändelse bokförs; C4 nollställer prövningsunderlaget och
                # ledgerns justering är C4:s justering minus de betalningar som bara fanns i underlaget.
                basis_after, ms, lr = margin.liquidate(ichk.account, ms, ichk)
                in_basis = _out("underlagsfunding", ichk.account.funding_net - acct.funding_net)
                delta = _out("justering", lr.adjustment_delta - in_basis)
                acct = replace(acct, C=0.0, q=0.0, avg_price=0.0,
                               liquidation_adjustment=_out("liquidation_adjustment", acct.liquidation_adjustment + delta))
                gap = acct.reconciliation_gap()
                if abs(gap) > margin.RECONCILE_TOL * max(1.0, abs(lr.C_old), abs(lr.q_old * lr.avg_price_old)) or \
                        (basis_after.C, basis_after.q) != (acct.C, acct.q):
                    raise EventError(f"Intern inkonsekvens vid nollställning inom stapeln (avstämningsgap {gap}).")
                liquidated = True
                for e, fr in zip(interior, records):
                    unresolved.append((e.event_id, e.time, fr.payment, fr.payment > 0))
                    trace.append(_trace(state, UNRESOLVED, acct, time=e.time, bar_open=T, funding=fr.payment,
                                        event_id=e.event_id, source="mark_open",
                                        reason="olöst: ordning mot likvidationen okänd, ej bokförd; "
                                               + ("i prövningsunderlaget" if fr.payment > 0 else "ej i prövningsunderlaget")))
                trace.append(_trace(state, "liquidation", acct, time=UNKNOWN_TIME, bar_open=T, M=bar.mark_low,
                                    source="mark_low", reason=f"E {lr.E_before} <= MM {lr.MM} inom stapeln; "
                                    f"{len(unresolved)} mellanhändelser olösta", risk_status="likviderad"))
            else:
                for e in interior:                                   # kronologiskt på q_open (§8.3, D18)
                    acct, fs, fr = fund.apply_funding(acct, fs, e, "funding_interior")
                    booked += 1
                    trace.append(_trace(state, "funding_interior", acct, bar.mark_open, time=e.time, bar_open=T,
                                        source="mark_open", funding=fr.payment, event_id=e.event_id))

    terminated = T == TERMINAL
    terminal_point = (T, acct.C + acct.q * bar.mark_close if not liquidated else 0.0) if terminated else None
    if terminated and not liquidated and acct.q != 0:
        raise EventError("Intern inkonsekvens: positionen är inte stängd vid terminal.")
    with _issuing():
        new_state = EngineState(scenario=s, account=acct, risk_state=rs, funding_state=fs, margin_state=ms,
                                next_bar=T + BAR, prev_mark_close=bar.mark_close, terminated=terminated)
        return BarResult(prev_state=state, state=new_state, bar_open=T, trace=tuple(trace), close_point=close_point,
                         day_end=day_end, terminal_point=terminal_point, step_record=rec,
                         simultaneous=len(simultaneous), interior_booked=booked, absorbed=absorbed,
                         unresolved=tuple(unresolved), margin_basis=margin_basis)


@dataclass(frozen=True)
class RunLog:
    """Samlade punkter från en obruten följd av process_bar för ett konto i ett scenario: §10.1-closepunkter och
    §4-dagsögonblick, ingen statistik.

    Börjar bara från startläget (RunLog.begin) och tar bara emot resultatet som behandlades från loggens senaste
    tillstånd (samma konto, scenario och förlopp, nästa stapel); dubbla, hoppade, bakåtriktade, främmande och
    post-terminala resultat avvisas. close_points börjar med startpunkten (None, START, 100 000). day_base är E_end
    för dagen före start och är ingen avkastningsdag; day_ends innehåller testdagarna (1 096 för en hel horisont), den
    sista med terminalt kapital.
    """
    state: EngineState                          # senaste tillståndet i förloppet
    close_points: tuple = ()                    # (källstapel, tid känd, E)
    day_base: tuple = ()                        # (2021-12-31, 100 000)
    day_ends: tuple = ()                        # (dag, E_end, likviderad)
    trace: tuple = ()

    def __post_init__(self) -> None:
        _require_issued("RunLog")

    @classmethod
    def begin(cls, state: EngineState) -> "RunLog":
        if not isinstance(state, EngineState) or state != EngineState.start(state.scenario):
            raise EventError("En RunLog börjar bara från startläget EngineState.start(scenario).")
        with _issuing():
            return cls(state=state, close_points=((None, START, INITIAL),),
                       day_base=(START - pd.Timedelta(days=1), INITIAL))

    @property
    def terminated(self) -> bool:
        return self.state.terminated

    def add(self, result: BarResult) -> "RunLog":
        if not isinstance(result, BarResult):
            raise EventError("add kräver ett BarResult.")
        if self.state.terminated:
            raise EventError("Loggen är redan avslutad vid terminal; inga fler resultat.")
        if result.prev_state != self.state:
            raise EventError(f"Resultatet för {result.bar_open} ({result.state.scenario.account_key}/"
                             f"{result.state.scenario.label}) följer inte loggens senaste tillstånd vid "
                             f"{self.state.next_bar} ({self.state.scenario.account_key}/{self.state.scenario.label}): "
                             "dubblett, lucka, bakåtsteg eller främmande förlopp.")
        cps = self.close_points + ((result.close_point,) if result.close_point else ())
        days = self.day_ends + ((result.day_end,) if result.day_end else ())
        if result.terminal_point is not None:
            T, E = result.terminal_point
            cps += ((T, T, E),)
            days += ((T.floor("D"), E, result.state.margin_state.liquidated),)
        with _issuing():
            return replace(self, state=result.state, close_points=cps, day_ends=days, trace=self.trace + result.trace)
