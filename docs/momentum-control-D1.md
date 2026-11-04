# H-0017 leverans D1 – kontrollkonton mom7, mom14 och mom28 (mom-control/1.0.0)

Datum 2026-11-04. Underlag: [protokollet](../research/h0017-protokoll.md) §5, §7, §11 och [uppdraget](claude-uppdrag-momentum-D1.md).
Implementationen är för Codex granskning och inte godkänd. Bara syntetiska minnesdata har använts. Ingen
marknadshistorik har lästs och ingen H-0017-körning har startats. **D1 omfattar bara tre fullkapitalkonton. Resten av
MOM-D01–D05 återstår.**

## API

Modul: [engine/traderlab/momentum_control.py](../engine/traderlab/momentum_control.py), `VERSION = "mom-control/1.0.0"`.

| Del | Beskrivning |
|---|---|
| `ComponentSignal` | beslutet för dag D för en komponent. Källradens fält bevaras: `s_main`, `s7`, `s14`, `s28`, `vol`, `cap`, `decision_time`, `available` och `source_version` = mom-signal/1.0.0. Därtill komponentens `s_used` (0 eller 1), `w_target = s_used × cap` och `adapter_version` = mom-control/1.0.0. `to_input()` ger C3:s oförändrade SignalInput med s ∈ {0, 1} |
| `component_signals(signals_table, component)` | ComponentSignal per dag ur `momentum_signal.signals()`. Otillgängliga dagar behålls som otillgängliga |
| `Market(contract, mark, funding)` | syntetiskt gemensamt underlag. Kontraktsstaplar (open, close) i exakt 4H-raster 2021-11-01 00:00–2024-12-31 20:00, markstaplar (open, high, low, close) för exakt testhorisonten och sorterade fundingevent. 2025-data, luckor, fel tidszon, NaN/inf, bool, 10**400 och osorterade event avvisas med `ControlError` innan något beräknas |
| `run_component(market, component, order, mmr, legacy_order, cost)` | ett konto med 100 000 genom hela horisonten. Kontonyckeln är `"{komponent}/{L1|L2}"`. Kör ett obrutet förlopp via `EngineState.start`, `process_bar` och `RunLog`. En saknad eller otillgänglig beslutsdag ger `ControlError` (OGILTIG_DATA-underlag) utan fallback. Event före START bokförs inte och räknas |
| `run_controls(...)` | mom7, mom14 och mom28 i samma scenario och på samma underlag. Ger samma resultat som tre separata `run_component` |
| `ComponentRun` | komponent, legacy-ordning, scenario, RunLog (close-, dags- och eventspår), använda beslut och antal ignorerade event före start |

Ingen godkänd modul är ändrad. Signal, ledger, funding, risk, marginal, event och bound är byte-oförändrade, så alla
äldre godkännanden består.

## Avvikelse från uppdragstexten (för Codex)

Uppdraget säger om O9: "Vid 110: komponentvikt 0,90825688 ger hold mot 0,9". Oraklet anger bara att bandet inte
bryts (`mom7_band: false`), och det verifieras. Men vikten 0,908 överstiger cap 0,9, och enligt §7 och den godkända
C3-modulen gäller capbrott även inom bandet. Resultatet blir alltså en riskavsikt `cap_breach` tillbaka till 0,9,
inte hold. Testet följer protokollet och C3. Codex avgör om uppdragstexten avsåg bara bandet.

## Verifiering

- [engine/tests/test_momentum_control.py](../engine/tests/test_momentum_control.py): 26 tester, alla godkända.
  - **Komponentval:** jämförs mot egna dagscloses, delsignaler, statistics.stdev-vol och cap varje dag
    2021-12-31–2024-12-30. Alla åtta kombinationer förekommer, och komponenten skiljer sig från main.
  - **O12:** målet är 0 eller cap, inte medelvärdet.
  - **O2:** q 998,4025559105431 genom publik start.
  - **O9** med fullt kapital (q = 3 × delkontots q) och två utfall:
    - Vid 110 bryts inte bandet, men capbrott ger återgång till 0,9. Main bryter bandet.
    - Vid 97,7 får komponenten dagsstopp, main inte.
  - **Full horisont per komponent:** 6 577 closepunkter, 1 096 dagar, 1 096 beslut, terminalstängning och q = 0.
    Normalavsikternas vikt efter affär är komponentens w_target.
  - **Isolering:** komponenterna skiljer sig åt, och samlingskörningen är lika med separata körningar.
  - **L1/L2:** ekonomiskt identiska med skilda identiteter.
  - **Funding:** samma event-id bokförs oberoende per konto, och event före start räknas.
  - **Prefix:** senare priser ändrar inte tidigare beslut eller closepunkter.
  - **Indatafel:** tio felaktiga marknader, otillgänglig signal (konstant pris, vol = 0), okända komponenter,
    L3 och flaggan synthetic=False.
- **Riktade felprov:** 14 fel, alla fångade. Felet "2025-data i tabeller" missades först, eftersom rastret avvisade
  samma data med ett annat meddelande. Testet kräver nu att felet uttryckligen gäller 2025. Modulen återställdes och
  jämfördes byte för byte.
- **Hela verifieringen:** 566 momentumtester och 1 119 motortester passerar, liksom A1-oraklet, 22 av 22
  momentum-audits och alla fyra checklistor.

## Inte i D1

- buy_and_hold, ema_legacy och bb_legacy samt no_vol.
- old_mix och new_mix med delkonton, bruttoexponering och oberoende risklås.
- Kontrollkontonas diagnostiska §10.2-bound, som väntar på D1-Q01.
- MOM-D03:s stresser och MOM-D04:s statistik och kriterier.
- D05.

**Öppna frågor till Edwin, via Codex underlag:**
- D1-Q01: gäller C6-01 även komponenternas bound?
- D1-Q02: no_vol:s cap i capbrott och invarianter.
