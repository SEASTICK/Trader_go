# H-0017 leverans C5 – eventkomposition mom-event/1.0.0

Datum 2026-11-04. Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §4, §6–§10, §12, §15, D07,
D17–D21 och [uppdraget](claude-uppdrag-momentum-C5.md). Implementation för Codex granskning, inte godkänd. Endast
syntetiska staplar, event och signalrader; ingen marknadshistorik har lästs och ingen H-0017-körning har startats.
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
| `EngineState` | oföränderligt: scenario, Account, RiskState, FundingState, MarginState, next_bar, prev_mark_close, terminated. Konstruktionen validerar att allt hör till samma konto och scenario; `EngineState.start(scenario)` ger startläget |
| `process_bar(state, bar, events, signal)` | behandlar stapeln vid `state.next_bar` och returnerar `BarResult` |
| `BarResult` | nytt tillstånd, ordnat spår, closepunkt för föregående stapel, dagsögonblick vid 00:00, terminalpunkt, C3:s StepRecord, antal samtidiga, bokförda mellanhändelser och absorberade event |
| `Trace` | fas, exakt tid eller `okänd inom stapeln`, källstapel, konto, scenario, C, q, E, M, P, källa, kostnad, funding, event-id, avsikt med beslutstid och orsak, riskstatus, mmr och modul-/protokollversioner |
| `RunLog` | §10.1-closepunkter (start först), `day_base` (2021-12-31 = 100 000, ingen avkastningsdag) och `day_ends` (testdagarna) |
| `EventError` | underklass till `LedgerError` |

## Ordning inom ett anrop (ett ordnat fasexempel)

För stapeln vid T, scenario B, med ett samtidigt fundingevent och ett mellanliggande:
`close` (föregående stapel, mark_close) → `decision` (C3, även dagsbeslut och reset vid 00:00) → `gap` (q_old vid
mark_open) → [marginal vid gappunkten] → `after_trade` (C3/C1, E_trade) → `funding_B` → `after_funding_B` (E_post) →
[marginal vid mark_low med C efter betald, före mottagen funding] → `funding_interior` i tidsordning.
I scenario A ligger `funding_A` före marginalen och fyllningen, och `after_funding_B` finns inte (E_post = E_trade).
Vid gapträff följer `liquidation` direkt efter gappunkten (A-funding ingår), och avsikten, fyllningen och B-funding
utgår. Vid träff inom stapeln bokförs de betalda mellanhändelserna (exakt prövningsunderlaget), kontot nollställs via
C4 med tiden `okänd inom stapeln`, och de mottagna räknas som absorberade.

## Tillståndsinvarianter

- Funding- och marginaltillståndets (konto, scenario) är scenariots, och marginalens mmr är scenariots.
- `next_bar` är riskmodulens nästa gräns; `terminated` följer riskmodulens terminalstatus.
- Efter likvidation är C = q = 0; riskmodulen får veta det vid nästa close (bara den ordningen tillåts).
- Ostartat tillstånd börjar vid START utan föregående close; därefter krävs `prev_mark_close`.
- q ≥ 0 (huvudmodellen är long eller platt).

## Bokföringsidentiteter

Oförändrade från C1–C4: C = deposit + realized − costs − funding_net + liquidation_adjustment − q × avg_price. E_trade
efter affär före B-funding; E_post efter B-funding; målidentitet och cap gäller E_trade. Vid intrastapelträff består
funding_net av exakt de betalda mellanhändelserna, och liquidation_adjustment tar resten av nollställningen.

## Horisont och punkter

- Första stapeln: ingen close; C3:s första beslut från dagen 2021-12-31. Inga event före START.
- Terminal: C3:s terminalavsikt vid 2024-12-31 20:00 efter gap, A-funding och marginal; därefter avvisas fler staplar.
  Senare event i terminalstapeln bokförs på q = 0 utan ekonomisk effekt. Inga staplar eller event från 2025.
- §10.1: start (None, 2022-01-01 00:00, 100 000), close för staplarna 2022-01-01 00 till 2024-12-31 16 (källstapel och
  tid då closen är känd), terminalt kapital vid 2024-12-31 20.
- §4: E_end per testdag = E_close för dagens 20-stapel vid nästa 00:00 före gap/funding/handel, med likvidationsflagga;
  sista dagen = terminalt kapital. En hel syntetisk horisont ger exakt 1 096 dagar.

## Verifiering

- [engine/tests/test_momentum_event.py](../engine/tests/test_momentum_event.py): 62 tester, alla godkända. Facit från
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

## Avgränsningar

En huvudmodell, long/platt, ett scenario per tillstånd; L1 och L2 är identiska för detta konto och är inte prövade som
grid. Ingen intrastapel-bound, inga drawdownmått eller 20 %-beslut, ingen fundingstress, mark_close-diagnostik eller
fördröjning, inga jämförelsekonton, ingen statistik och inga ekonomiska beslut. Ingen historikläsare, kö, worker,
app, server, release eller paper/live. Endast syntetiskt prövat.
