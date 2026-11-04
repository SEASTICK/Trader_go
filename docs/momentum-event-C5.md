# H-0017 leverans C5 – eventkomposition mom-event/1.0.0

Datum 2026-11-04. Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §4, §6–§10, §12, §15, D07,
D17–D21 och [uppdraget](claude-uppdrag-momentum-C5.md). Implementation för Codex granskning, inte godkänd. Endast
syntetiska staplar, event och signalrader; ingen marknadshistorik har lästs och ingen H-0017-körning har startats.
Revision 2 rättar C5-01–C5-03 från [Codex granskning av b131ff4](momentum-C5-granskning-b131ff4.md); C5-01 följer
[Edwins beslut](momentum-C5-01-edwins-beslut.md).
De godkända modulerna signal (B), ledger (C1), funding (C2), risk (C3) och marginal (C4) är oförändrade och
återanvänds; inga formler är kopierade. Drawdown-bounden (§10.2) ingår inte.

## API

Modul: [engine/traderlab/momentum_event.py](../engine/traderlab/momentum_event.py), `VERSION = "mom-event/1.0.0"`,
`PROTOCOL = "momentum-protokoll/1.0.0"`, `START = 2022-01-01 00:00`, `TERMINAL = 2024-12-31 20:00`,
`END = 2025-01-01 00:00`, `INITIAL = 100 000`.

| Del | Beskrivning |
|---|---|
| `Scenario(account_key, order, mmr, cost)` | ett komplett scenario: ordning A eller B, mmr 0,05 eller 0,005, kostnad 0,0016 eller 0,0040; `label` identifierar det i funding- och marginaltillstånd |
| `Bar(open_time, contract_open, mark_open, mark_high, mark_low, mark_close, synthetic=True)` | syntetisk 4H-stapel med validerad mark-OHLC |
| `EngineState` | oföränderligt: scenario, Account, RiskState, FundingState, MarginState, next_bar, prev_mark_close, terminated. Skapas bara via `start(scenario)` (exakt startläge), `restore(...)` (uttrycklig syntetisk återställning efter minst en stapel, före terminal) eller `process_bar`; `dataclasses.replace` och direkt konstruktion avvisas. Varje konstruktion prövar invarianterna nedan |
| `process_bar(state, bar, events, signal)` | behandlar stapeln vid `state.next_bar` och returnerar `BarResult` |
| `BarResult` | föregående och nytt tillstånd, stapeltid, ordnat spår, closepunkt för föregående stapel, dagsögonblick vid 00:00, terminalpunkt, C3:s StepRecord, antal samtidiga, bokförda mellanhändelser, absorberade event, olösta event `(id, tid, belopp, i underlaget)` och marginalunderlaget `(C, E, MM, mark_low)`. Skapas bara av `process_bar` |
| `Trace` | fas, exakt tid eller `okänd inom stapeln`, källstapel, konto, scenario, C, q, E, M, P, källa, kostnad, funding, event-id, avsikt med beslutstid och orsak, riskstatus, mmr och modul-/protokollversioner |
| `RunLog` | `begin(start_state)` och `add(result)`: §10.1-closepunkter (start först), `day_base` (2021-12-31 = 100 000, ingen avkastningsdag) och `day_ends` (testdagarna). Bunden till sitt senaste tillstånd: tar bara emot resultatet som behandlades från det, avvisar dubbletter, luckor, bakåtsteg, främmande konton/scenarier/förlopp och tillägg efter terminal; börjar bara från startläget |
| `EventError` | underklass till `LedgerError` |

## Ordning inom ett anrop (ett ordnat fasexempel)

För stapeln vid T, scenario B, med ett samtidigt fundingevent och ett mellanliggande:
`close` (föregående stapel, mark_close) → `decision` (C3, även dagsbeslut och reset vid 00:00) → `gap` (q_old vid
mark_open) → [marginal vid gappunkten] → `after_trade` (C3/C1, E_trade) → `funding_B` → `after_funding_B` (E_post) →
`margin_basis` (prövningsunderlag vid mark_low med C efter betald, före mottagen funding; ingen ledgerpost) →
`funding_interior` i tidsordning.
I scenario A ligger `funding_A` före marginalen och fyllningen, och `after_funding_B` finns inte (E_post = E_trade).
Vid gapträff följer `liquidation` direkt efter gappunkten (A-funding ingår), och avsikten, fyllningen och B-funding
utgår; senare event i stapeln får `funding_absorbed`. Vid träff inom stapeln (Edwins beslut för C5-01) bokförs ingen
mellanhändelse: var och en får `funding_unresolved` med exakt tid, belopp och om den ingick i underlaget, och
`liquidation` har tiden `okänd inom stapeln`. Varje event i en stapel får exakt en kategori: `funding_A`, `funding_B`,
`funding_interior`, `funding_absorbed` eller `funding_unresolved`.

## Tillståndsinvarianter

Prövas vid varje konstruktion (start, restore och process_bar):

- Funding- och marginaltillståndets (konto, scenario) är scenariots, och marginalens mmr är scenariots.
- `next_bar` är riskmodulens nästa gräns; `terminated` följer riskmodulens terminalstatus.
- Ostartat tillstånd är exakt startläget: `Account.open(100 000)`, `RiskState.start(100 000, START)`, inga
  behandlade event, ingen likvidation, START och inget föregående close.
- Kontots insättning är riskmodulens startkapital (inga tillskott, D21), och bokföringen stämmer av.
- Efter likvidation är C = q = avg = 0; riskmodulen får veta det vid nästa close (bara den ordningen tillåts).
- Startat och levande konto: `prev_mark_close` > 0 och E > 0 vid den (inget oförklarat nollkonto). Permanent stopp
  eller dagslås för den senast behandlade stapelns dag kräver q = 0.
- q ≥ 0 (huvudmodellen är long eller platt).

`restore` är en uttrycklig väg för syntetiska prov. Anroparen intygar att delarna hör till samma förlopp, och modulen
prövar det som går att pröva enligt ovan. Delar som inte går att skilja åt, till exempel ett risktillstånd utan lås
från ett annat platt konto, kan inte upptäckas. Ett återställt förlopp kan därför inte börja en RunLog.

## Bokföringsidentiteter

Oförändrade från C1–C4: C = deposit + realized − costs − funding_net + liquidation_adjustment − q × avg_price. E_trade
efter affär före B-funding; E_post efter B-funding; målidentitet och cap gäller E_trade. Vid intrastapelträff är
funding_net oförändrad från kontot efter öppningen. C4 nollställer prövningsunderlaget (dess post dokumenterar
underlaget). Ledgerns justering = C4:s `adjustment_delta` − underlagets betalningar = −C_open − q × avg, alltså hela
kontot efter öppningen. Avstämningen och C = q = 0 kontrolleras mot C4:s utfall.

## Horisont och punkter

- Första stapeln: ingen close; C3:s första beslut från dagen 2021-12-31. Inga event före START.
- Terminal: C3:s terminalavsikt vid 2024-12-31 20:00 efter gap, A-funding och marginal; därefter avvisas fler staplar.
  Senare event i terminalstapeln bokförs på q = 0 utan ekonomisk effekt. Inga staplar eller event från 2025.
- §10.1: start (None, 2022-01-01 00:00, 100 000), close för staplarna 2022-01-01 00 till 2024-12-31 16 (källstapel och
  tid då closen är känd), terminalt kapital vid 2024-12-31 20.
- §4: E_end per testdag = E_close för dagens 20-stapel vid nästa 00:00 före gap/funding/handel, med likvidationsflagga;
  sista dagen = terminalt kapital. En hel syntetisk horisont ger exakt 1 096 dagar.

## Verifiering

- [engine/tests/test_momentum_event.py](../engine/tests/test_momentum_event.py): 62 tester i revision 1 (101 i revision 2), alla godkända. Facit från
  [orakelfilen](momentum-a1-orakel.json), Decimal och handräkning:
  - O5/O5b: inträde och utgång i A och B med samtidig funding, E_trade och vikt 0,5 före B, E_post efter B; samtidigt
    event på platt konto bokförs en gång.
  - O6: dagsstopp vid 20-stapeln samtidigt med normalavsikt, reset till 97 900, riskutträde med O6:s belopp i A och B,
    ingen normalavsikt resten av dagen; permanent stopp över flera dagar.
  - O10: terminalens gapvärde, kostnad och kapital i A och B, B-funding och senare event på q = 0, inga steg efter
    terminal; inga event eller staplar före start eller från 2025; första beslutet från uppvärmningen; en hel syntetisk
    horisont (6 576 staplar) med 1 096 dagar, startpunkt, sista close 2024-12-31 16 och terminalpunkt.
  - O14/O15 med båda kostnadsnivåerna mot Decimal-formel och orakel; O3:s basis i kompositionen.
  - O16: T, T ± 1 ms och T ± 30 s med rätt stapel, dag, q och fas i A och B; utgång vid öppning följd av mellanhändelse.
  - O11/O18-snitt: gaplikvidation före en avsikt (struken, ingen fill eller B-funding, negativt E −5 000 och reset
    +5 000), absorberande nollkonto över midnatt, båda satserna vid gappunkten, intrastapelmarginal med betald före
    mottagen i båda tidsordningarna och båda satserna, likviderat konto genom midnatt och terminal.
  - Isolering av fyra scenarier med samma event-id, avvisade felkopplade tillstånd, prefix och ändrade framtida priser,
    att high och low aldrig ändrar closebeslut eller closepunkter, otillgänglig signal och fel signaldag, ordningsfel,
    fem felaktiga eventlistor, tolv felaktiga staplar och åtta felaktiga scenarier (även 10**400 och 10**5000),
    oförändrade indata och spårets proveniens.
- Riktade felprov: 16 avsiktliga fel infördes ett i taget. Alla 16 fångas: fill före gapmarginal, A på nya q,
  B-funding före fyllning (gamla q och i målidentiteten), mellanfunding flyttad till gräns, close värderad med nya
  öppningen (reset efter gap), riskutträde som tappas vid midnatt, dubbel mellanfunding, kredit före adverse-prövning,
  kredit som räddar ett likviderat konto, terminal fördröjd, terminal som kan behandlas igen, startpunkt borttagen,
  terminalpunkt borttagen, high/low som styr closebeslut, M_ref-värdet okontrollerat och likvidation som inte stryker
  avsikten. Felet med high/low missades först och fick ett eget test. "Återupplivad normalavsikt" är inte tillämpligt:
  kompositionen håller ingen kö, varje avsikt gäller bara sin fyllningstid. Modulen återställdes och jämfördes byte
  för byte.

## Rättning C5-01–C5-03 (revision 2)

- **C5-01:** Ingen mellanhändelse i en stapel med intrastapelträff bokförs (Edwins beslut). Underlaget hålls skilt i
  `margin_basis` och i C4:s post. Ledgerjusteringen räknas fram ur C4:s utfall. Regression
  `test_intrabar_hit_books_no_interior_funding_and_keeps_basis_separate` täcker 32 fall: A/B × båda mmr × båda
  teckenordningarna × med/utan samtidig funding. Varje fall har två betalningar, två krediter och ett nollevent. Facit
  är oberoende och räknat i Decimal: underlags-C, E_low, MM, olösta id, tider, belopp och underlagsflaggor,
  funding_net, liquidation_adjustment, avstämning, inga processed-id från mellanhändelserna och absorberande noll i
  fyra följande staplar. Utan träff: kronologiska C per post. `test_gap_liquidation_lists_each_absorbed_event_once`
  visar en kategori per event vid gaplikvidation.
- **C5-02:** EngineState skapas bara via start/restore/process_bar och prövar invarianterna ovan. Proven omfattar
  Codex fyra motexempel (200 000, position före start, nollkonto och främmande risklås via replace), ett startkonto
  med ändrad bokföring och startinvarianten bakom grinden. Dessutom tretton felaktiga återställningar, som alla ger
  kontrollerat fel utan ändrade indata, och giltiga oberoende återställningar nära terminal och mitt i horisonten.
- **C5-03:** RunLog är bunden till sitt senaste tillstånd. Proven omfattar dubblett, lucka, bakåtsteg, främmande
  konto/scenario, ett giltigt alternativt nästa steg, begin från ett återställt tillstånd, direkt konstruktion och
  replace, samt tillägg efter terminal. Den hela syntetiska serien har fortfarande exakt 1 096 dagar och 6 577
  kapitalpunkter.
- Riktade felprov i revision 2: 15 nya fel (5 för C5-01, 7 för C5-02, 3 för C5-03), alla fångade. De 16 ursprungliga
  felen kördes om med mönster anpassade till den nya koden och samma avsikt; alla fångades. Startkontrollen missades
  först, eftersom grinden maskerade den, och fick ett eget prov bakom grinden. Modulen återställdes och jämfördes
  byte för byte.
- Verifiering: 101 eventtester, 503 momentumtester och 1 052 motortester passerar. Signal-, ledger-, funding-, risk-
  och marginalmodulerna och deras tester är oförändrade.

## Avgränsningar

En huvudmodell, long/platt, ett scenario per tillstånd; L1 och L2 är identiska för detta konto och är inte prövade som
grid. Ingen intrastapel-bound, inga drawdownmått eller 20 %-beslut, ingen fundingstress, mark_close-diagnostik eller
fördröjning, inga jämförelsekonton, ingen statistik och inga ekonomiska beslut. Ingen historikläsare, kö, worker,
app, server, release eller paper/live. Endast syntetiskt prövat.
