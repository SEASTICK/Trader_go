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

## Rättning D1-01–D1-03 (revision 2)

Underlag: [Codex granskning av 6e6730c](momentum-D1-granskning-6e6730c.md). Codex bekräftade O9-tolkningen (capbrott
vid 0,908 > 0,9).

- **D1-01:** `ComponentSignal` bär nu `earliest_fill`, och varje konstruktion, även direkt, prövar källradens
  konsekvens:
  - dag vid 00:00 UTC och decision_time = earliest_fill = dagen + 1;
  - strikt bool `available` och exakta versioner;
  - delsignaler i {0, 1} och s_main = deras medel;
  - ändlig vol > 0 och cap = min(1, 0,10/vol);
  - s_used = komponentens delsignal och w_target = s_used × cap;
  - otillgänglig rad har bara NaN.

  Codex sex motexempel och sju ogiltiga direktkonstruktioner avvisas, bland annat strängen "False", en sen
  earliest_fill, decision_time på källdagen, s14 = 0,25 i mom7, NaN-vol, 10**5000 och fel adapterversion.
- **D1-02:** `Market` tar egna djupkopior av tabellerna och sparar ett fingeravtryck av innehållet. `run_component`
  och `run_controls` kontrollerar fingeravtrycket före körning, och `run_controls` även efter. Ändringar i
  anroparens tabell efter konstruktionen påverkar inte underlaget, och ändringar i den interna kopian avvisas med
  `ControlError`. Signalberäkningen får en egen kopia.
- **D1-03:** [test_momentum_control_integration.py](../engine/tests/test_momentum_control_integration.py) innehåller:
  - **O5/O5b/O16 genom komponentkompositionen**, från publik start i A och B. Inträdet sker vid första öppningen.
    Minskningen sker nästa midnatt med P = 100,5 ≠ M (ett capbrott, eftersom w 0,5 överstiger cap 0,3). Utgången
    följer dagen efter. Fundingevent ligger exakt vid T, T + 1 ms, T + 30 s, T − 30 s och T − 1 ms. Fasordningen,
    E_trade/E_post och varje belopp räknas med §6-formlerna i Decimal.
  - **Terminalordning** i en full publik komponentkörning med funding vid terminal och terminal + 30 s.
  - **Exakta floatgränser (FIXTUR):** 2 pp-band, capbrott inom band, −2 % och −15 %, med närmaste representerbara
    värden på båda sidor.
  - **Publikt flerdygnsförlopp:** permanent stopp utan nya köp, där ett annat konto på samma priser saknar lås.
  - **Integrerade O6 och O14** (O14 vid båda kostnaderna), samt en O15-analog. O15 självt har s = 1/3; analogen
    visar ett köpbeslut som efter gap blir en försäljning.
  - **Komponentlikvidation** i A/B × båda mmr: gap med negativt prövningskapital och intrastapelträff med olösta
    event. Därtill absorberande noll från likvidation genom midnatt till terminal med oförändrad
    liquidation_adjustment.
  - **Scenarier:** alla åtta etiketter, med identiska L1/L2-spår efter normalisering.
  - **Indatafel:** dubbletter och 10**5000.
- **Reproducerbar felprovsmatris:** [scripts/momentum-d1-mutations.py](../scripts/momentum-d1-mutations.py) inför
  varje fel i en temporär kopia av engine/ och kör D1-proven. Resultatet sparas i
  [docs/momentum-D1-mutationer.json](momentum-D1-mutationer.json), och `--check` kör om och jämför. Utfallet är 26
  fångade, 0 missade, 1 bevisat ekvivalent (observationsdagar, eftersom Market kräver fullständigt raster) och 2 ej
  tillämpliga, med motivering i filen.
- **Verifiering:** 62 D1-tester, 602 momentumtester och 1 155 motortester passerar. A1-oraklet, 23 av 23
  momentum-audits och alla fyra checklistor passerar. Ingen godkänd modul är ändrad.

## Rättning D1-03–D1-05 (revision 3)

Underlag: [Codex granskning av 720e1f8](momentum-D1-granskning-720e1f8.md).

- **D1-04:** felprovsmatrisen i revision 2 var ogiltig. Skriptet kopierade bara engine/, så proven kraschade vid
  import eftersom oraklet saknades, och varje krasch räknades som "fångad". Inget av de 26 utfallen var en verifierad
  fångst. Det nya skriptet:
  - kopierar även docs/momentum-a1-orakel.json i samma struktur;
  - kör först en oförändrad baslinje, som måste vara grön, annars avbryts allt;
  - stänger av pytest.ini:s `addopts`, som annars döljer sammanfattningen;
  - räknar FÅNGAD bara när proven körde och minst ett prov fallerade utan insamlingsfel, och sparar det första
    fallerande provet;
  - avbryter vid miljöfel.

  Delat state och årsreset är nu riktiga felinjektioner, inte "ej tillämpliga". Resultatet finns i
  [docs/momentum-D1-mutationer.json](momentum-D1-mutationer.json): baslinjen är 65 passerade prov, 30 fel fångas, 0
  missas och 1 är bevisat ekvivalent (observationsdagar). Varje fångst har sitt första fallerande prov angivet.

  Den första ärliga körningen gav tre missar, som är rättade:
  - "Köp efter permanent stopp" kostade inget ekonomiskt, men gav fel beslutsetikett. Provet kräver nu HOLD som
    dagsbeslut.
  - Min mutant för delat state gjorde ingenting och är ersatt av en delad kontoidentitet.
  - Årsreset gick inte att se så länge peak låg på startkapitalet. Årsskiftesprovet höjer nu först peak över
    startkapitalet.

  En årsresetmutant som bröt riskmodulens invariant peak ≥ startkapital gjordes giltig, så att den prövar
  semantiken.
- **Verifiering i revision 3:** 65 D1-tester, 605 momentumtester och 1 158 motortester passerar. A1-oraklet, 24 av
  24 momentum-audits, felprovsskriptet med `--check` och alla fyra checklistor passerar. Ingen godkänd modul är
  ändrad.
- **D1-05:** adaptern prövar index (DatetimeIndex i UTC, unika och sorterade dagar) och numerik med `_real` före all
  aritmetik. Kontrollerade fel gäller nu även cap 10**5000 i en riktig rad, dubblettdagar med motsatt s7 och omvänd
  ordning.
- **D1-03:** två nya prov.
  - `test_independent_full_horizon_capital_path_with_trades_and_terminal_P_ne_M` är ett publikt förlopp genom hela
    horisonten med inträde, ökning (P = 100,4), minskning genom capbrott (P = 99,7), utgång, återinträde och terminal
    med P = 100,5 ≠ M. Varje dagsslut, varje closepunkt efter återinträdet och terminalkapitalet räknas helt
    oberoende i Decimal från startkapitalet, utan motorns mellanresultat.
  - `test_permanent_stop_across_new_year_uses_unbroken_peak` låter priset falla 1,5 % per dag över årsskiftet
    2022/2023. Det permanenta stoppet utlöses exakt där Decimal-facit med obruten peak anger, och ett årsreset skulle
    skjuta upp det.

## Inte i D1

- buy_and_hold, ema_legacy och bb_legacy samt no_vol.
- old_mix och new_mix med delkonton, bruttoexponering och oberoende risklås.
- Kontrollkontonas diagnostiska §10.2-bound, som väntar på D1-Q01.
- MOM-D03:s stresser och MOM-D04:s statistik och kriterier.
- D05.

**Öppna frågor till Edwin, via Codex underlag:**
- D1-Q01: gäller C6-01 även komponenternas bound?
- D1-Q02: no_vol:s cap i capbrott och invarianter.
