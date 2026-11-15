"""H-0026 (tidigare H-0017) kontrollkonto buy_and_hold, mom-bh/1.0.0 (research/h0017-protokoll.md §6, §11; uppdrag
docs/claude-uppdrag-momentum-D2.md).

Ett konto med 100 000 eget startkapital som vid första testöppningen köper till vikt 1 efter kostnad på E_trade (§6)
och sedan håller fasta enheter till terminal eller likvidation: ingen momentumsignal, cap, band, dags- eller
permanentstopp, ingen återinvestering av funding och ingen ombalansering (§11). Kontot körs som ett obrutet förlopp
från EngineState.start genom process_bar och RunLog i eventlagrets buy_and_hold-väg (Scenario.policy), med samma
gap-, funding-, marginal- och likvidationskedja som huvudmodellen.

Underlaget är D1:s validerade momentum_control.Market (syntetiska minnesdata, låst med fingeravtryck). buy_and_hold
behöver ingen signal, så ett konstant kontraktspris som ger momentumvol 0 avvisas inte här; marknadskontrollerna
(raster, priser, fundingordning, 2025) gäller oförändrat. Ingen statistik, inga kriterier och inga ekonomiska beslut.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import momentum_control as ctl
from . import momentum_event as ev
from . import momentum_ledger as ledger
from .momentum_ledger import _show

VERSION = "mom-bh/1.0.0"


@dataclass(frozen=True)
class BenchmarkRun:
    policy: str
    legacy_order: str
    scenario: ev.Scenario
    log: ev.RunLog                # obrutet förlopp: close-, dags- och eventspår
    ignored_pre_start: int        # fundingevent före START, inte bokförda (§8.3)
    rule: str = ev.BH_RULE
    version: str = VERSION

    @property
    def day_ends(self) -> tuple:
        return self.log.day_ends


def run_buy_and_hold(market: ctl.Market, order: str, mmr: float, legacy_order: str = "L1",
                     cost: float = ledger.COST_NORMAL) -> BenchmarkRun:
    """buy_and_hold med 100 000 genom hela testhorisonten i ett scenario."""
    if not isinstance(market, ctl.Market):
        raise ctl.ControlError("run_buy_and_hold kräver ett Market.")
    market = market.verified()
    if not isinstance(legacy_order, str) or legacy_order not in ctl.LEGACY_ORDERS:
        raise ctl.ControlError(f"Legacy-ordning måste vara L1 eller L2, fick {_show(legacy_order)}.")
    scenario = ev.Scenario(f"buy_and_hold/{legacy_order}", order, mmr, cost, policy=ev.BUY_AND_HOLD)
    by_bar: dict = {}
    pre = 0
    for e in market.funding:
        if e.time < ev.START:
            pre += 1
            continue
        by_bar.setdefault(e.time.floor("4h"), []).append(e)
    state = ev.EngineState.start(scenario)
    log = ev.RunLog.begin(state)
    c, m = market.contract, market.mark
    for T in ctl.TEST_BARS:
        bar = ev.Bar(T, float(c.at[T, "open"]), float(m.at[T, "open"]), float(m.at[T, "high"]),
                     float(m.at[T, "low"]), float(m.at[T, "close"]))
        r = ev.process_bar(state, bar, by_bar.get(T, ()), None)
        log, state = log.add(r), r.state
    market.verified()                                       # underlaget oförändrat under hela körningen
    if not state.terminated or len(log.day_ends) != 1096:
        raise ctl.ControlError("Intern inkonsekvens: förloppet nådde inte terminal med 1 096 dagar.")
    return BenchmarkRun(policy=ev.BUY_AND_HOLD, legacy_order=legacy_order, scenario=scenario, log=log,
                        ignored_pre_start=pre)
