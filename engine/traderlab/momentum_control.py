"""H-0017 kontrollkonton mom7, mom14 och mom28, mom-control/1.0.0 (research/h0017-protokoll.md §5, §7, §11; uppdrag
docs/claude-uppdrag-momentum-D1.md).

Tre enskilda momentumkonton, vart och ett med 100 000 eget startkapital, ovanpå den godkända eventmotorn
(momentum_event). Inga delkonton, inga överföringar, ingen skalning. Varje konto och scenario körs som ett obrutet
förlopp från EngineState.start genom process_bar och RunLog, med egen risk-, funding- och marginalidentitet.

Signal: komponentens s_h ur B:s signals()-rad (s_h = 1 endast om C_D / C_(D-h) - 1 > 0), med samma vol och
cap = min(1, 0,10 / vol) som main; w_target = s_h × cap. Källraden (main-s, s7, s14, s28, vol, cap, version) behålls
i ComponentSignal; transformationen märks med denna moduls VERSION. Riskmodulen får en SignalInput med s ∈ {0, 1},
som dess oförändrade kontrakt redan accepterar.

Indata är syntetiska minnesdata: kontraktsstaplar (open, close) från uppvärmningen till terminalstapeln, markstaplar
(open, high, low, close) för exakt testhorisonten och fundingevent. Ofullständig horisont, otillgänglig signal på
en beslutsdag, data från 2025 eller fel tidszon/raster avvisas som ControlError (OGILTIG_DATA-underlag) innan något
konto beräknas; ingen fallback till platt eller kortare horisont. Event före START bokförs inte (§8.3) och räknas.
Ingen statistik, inga kriterier och inga ekonomiska beslut här.
"""
from __future__ import annotations

import math
import numbers
from dataclasses import dataclass

import pandas as pd

from . import momentum_event as ev
from . import momentum_funding as fund
from . import momentum_ledger as ledger
from . import momentum_risk as risk
from . import momentum_signal as sigmod
from .momentum_ledger import _show

VERSION = "mom-control/1.0.0"
COMPONENTS = {"mom7": "s7", "mom14": "s14", "mom28": "s28"}
LEGACY_ORDERS = ("L1", "L2")          # ekonomiskt identiska här (ingen legacy-stop), separata identiteter
WARMUP_START = pd.Timestamp("2021-11-01 00:00", tz="UTC")
TEST_BARS = pd.date_range(ev.START, ev.TERMINAL, freq=ev.BAR)
MARK_COLUMNS = ("open", "high", "low", "close")


class ControlError(ev.EventError):
    """Ogiltigt eller ofullständigt underlag för ett kontrollkonto (OGILTIG_DATA-underlag). Inget beräknas."""


def _component(name) -> str:
    if not isinstance(name, str) or name not in COMPONENTS:
        raise ControlError(f"Okänd komponent {_show(name)}; tillåtna {tuple(COMPONENTS)}.")
    return name


@dataclass(frozen=True)
class ComponentSignal:
    """Beslutet för dag D för en komponent, med källraden ur B bevarad och transformationen märkt."""
    component: str
    day: pd.Timestamp
    decision_time: pd.Timestamp
    available: bool
    s_main: float                 # källans medelvärde (main), bara proveniens
    s7: float
    s14: float
    s28: float
    vol: float
    cap: float
    s_used: float                 # komponentens s_h, 0 eller 1
    w_target: float               # s_used × cap
    source_version: str = sigmod.VERSION
    adapter_version: str = VERSION

    def to_input(self) -> risk.SignalInput:
        return risk.SignalInput(day=self.day, decision_time=self.decision_time, available=self.available,
                                s=self.s_used, cap=self.cap, w_target=self.w_target, version=self.source_version)


def component_signals(sig: pd.DataFrame, component: str) -> dict:
    """ComponentSignal per dag ur B:s signals()-tabell. Otillgängliga dagar behålls som otillgängliga (NaN)."""
    component = _component(component)
    if not isinstance(sig, pd.DataFrame) or list(sig.columns) != sigmod.COLUMNS:
        raise ControlError("component_signals kräver en tabell ur momentum_signal.signals() med exakt dess kolumner.")
    if (sig["version"] != sigmod.VERSION).any():
        raise ControlError(f"Signalversionen måste vara {sigmod.VERSION}.")
    key = COMPONENTS[component]
    out = {}
    for day, row in sig.iterrows():
        avail = bool(row["available"])
        s_used = float(row[key]) if avail else math.nan
        if avail and s_used not in (0.0, 1.0):
            raise ControlError(f"{component} {day.date()}: delsignalen {key} = {s_used} är inte 0 eller 1.")
        out[day] = ComponentSignal(component=component, day=day, decision_time=row["decision_time"], available=avail,
                                   s_main=float(row["s"]), s7=float(row["s7"]), s14=float(row["s14"]),
                                   s28=float(row["s28"]), vol=float(row["vol"]), cap=float(row["cap"]), s_used=s_used,
                                   w_target=s_used * float(row["cap"]) if avail else math.nan)
    return out


@dataclass(frozen=True)
class Market:
    """Syntetiskt underlag gemensamt för alla konton som jämförs."""
    contract: pd.DataFrame        # open, close; index 4H UTC från WARMUP_START till TERMINAL
    mark: pd.DataFrame            # open, high, low, close; index exakt TEST_BARS
    funding: tuple = ()           # FundingEvent, sorterade, M_ref = mark_open i innehållande stapel
    synthetic: bool = True

    def __post_init__(self) -> None:
        if self.synthetic is not True:
            raise ControlError("Endast syntetiskt underlag accepteras i D1.")
        for name, df, cols in (("contract", self.contract, ("open", "close")), ("mark", self.mark, MARK_COLUMNS)):
            if not isinstance(df, pd.DataFrame) or not set(cols) <= set(df.columns):
                raise ControlError(f"{name} måste vara en tabell med kolumnerna {cols}.")
            idx = df.index
            if not isinstance(idx, pd.DatetimeIndex) or idx.tz is None or str(idx.tz) != "UTC":
                raise ControlError(f"{name} måste ha ett DatetimeIndex i UTC.")
            if len(idx) and idx.max() >= ev.END:
                raise ControlError(f"{name} innehåller data från {ev.END.date()} eller senare; avvisas före beräkning.")
            for c in cols:
                vals = df[c]
                if vals.dtype == bool or not all(isinstance(v, numbers.Real) and not isinstance(v, bool)
                                                 for v in vals.tolist()):
                    raise ControlError(f"{name}.{c} måste vara reella tal.")
                try:
                    f = vals.to_numpy(dtype=float)
                except (OverflowError, ValueError, TypeError):
                    raise ControlError(f"{name}.{c} innehåller tal som inte kan representeras som float.") from None
                if not (pd.notna(f).all() and (abs(f) < math.inf).all() and (f > 0).all()):
                    raise ControlError(f"{name}.{c} måste vara ändliga tal > 0.")
        if not self.mark.index.equals(TEST_BARS):
            raise ControlError("Markstaplarna täcker inte exakt testhorisonten 2022-01-01 00:00–2024-12-31 20:00 "
                               "utan luckor, dubbletter eller extra staplar.")
        expected = pd.date_range(WARMUP_START, ev.TERMINAL, freq=ev.BAR)
        if not self.contract.index.equals(expected):
            raise ControlError("Kontraktsstaplarna täcker inte exakt 2021-11-01 00:00–2024-12-31 20:00 i 4H-raster.")
        last = None
        for e in self.funding:
            if not isinstance(e, fund.FundingEvent):
                raise ControlError(f"Fel typ för fundingevent: {type(e).__name__}.")
            if e.time >= ev.END:
                raise ControlError(f"Fundingevent {e.event_id} vid {e.time} är från 2025; avvisas före beräkning.")
            if last is not None and e.time < last:
                raise ControlError("Fundingevent måste vara sorterade efter tid.")
            last = e.time


@dataclass(frozen=True)
class ComponentRun:
    component: str
    legacy_order: str
    scenario: ev.Scenario
    log: ev.RunLog                # obrutet förlopp: close-, dags- och eventspår
    decisions: tuple              # använda ComponentSignal per beslutsdag
    ignored_pre_start: int        # fundingevent före START, inte bokförda (§8.3)
    version: str = VERSION

    @property
    def day_ends(self) -> tuple:
        return self.log.day_ends


def run_component(market: Market, component: str, order: str, mmr: float, legacy_order: str = "L1",
                  cost: float = ledger.COST_NORMAL) -> ComponentRun:
    """Ett komponentkonto med 100 000 genom hela testhorisonten i ett scenario."""
    if not isinstance(market, Market):
        raise ControlError("run_component kräver ett Market.")
    component = _component(component)
    if not isinstance(legacy_order, str) or legacy_order not in LEGACY_ORDERS:
        raise ControlError(f"Legacy-ordning måste vara L1 eller L2, fick {_show(legacy_order)}.")
    scenario = ev.Scenario(f"{component}/{legacy_order}", order, mmr, cost)
    try:
        table = sigmod.signals(market.contract[["close"]])
    except ValueError as exc:
        raise ControlError(f"Signalunderlaget är ogiltigt: {exc}") from None
    sigs = component_signals(table, component)
    # Alla beslutsdagar måste vara tillgängliga innan något konto beräknas (ingen fallback).
    needed = [T for T in TEST_BARS if T == T.floor("D")]
    for T in needed:
        cs = sigs.get(T - pd.Timedelta(days=1))
        if cs is None or not cs.available:
            raise ControlError(f"{component}: signalen för {(T - pd.Timedelta(days=1)).date()} saknas eller är "
                               "otillgänglig; OGILTIG_DATA, ingen fallback.")
    by_bar: dict = {}
    pre = 0
    for e in market.funding:
        if e.time < ev.START:
            pre += 1
            continue
        by_bar.setdefault(e.time.floor("4h"), []).append(e)
    state = ev.EngineState.start(scenario)
    log = ev.RunLog.begin(state)
    decisions = []
    c, m = market.contract, market.mark
    for T in TEST_BARS:
        signal = None
        if T == T.floor("D"):
            cs = sigs[T - pd.Timedelta(days=1)]
            decisions.append(cs)
            signal = cs.to_input()
        bar = ev.Bar(T, float(c.at[T, "open"]), float(m.at[T, "open"]), float(m.at[T, "high"]),
                     float(m.at[T, "low"]), float(m.at[T, "close"]))
        r = ev.process_bar(state, bar, by_bar.get(T, ()), signal)
        log, state = log.add(r), r.state
    if not state.terminated or len(log.day_ends) != 1096:
        raise ControlError("Intern inkonsekvens: förloppet nådde inte terminal med 1 096 dagar.")
    return ComponentRun(component=component, legacy_order=legacy_order, scenario=scenario, log=log,
                        decisions=tuple(decisions), ignored_pre_start=pre)


def run_controls(market: Market, order: str, mmr: float, legacy_order: str = "L1",
                 cost: float = ledger.COST_NORMAL) -> dict:
    """mom7, mom14 och mom28 i samma scenario och på samma underlag; samma som tre separata run_component."""
    return {k: run_component(market, k, order, mmr, legacy_order, cost) for k in COMPONENTS}
