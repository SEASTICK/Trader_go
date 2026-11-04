# H-0017 leverans C6 – §10.2-bound mom-bound/1.0.0

Datum 2026-11-04. Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §9, §10.1–§10.2, §13.1–§13.2,
D21, [uppdraget](claude-uppdrag-momentum-C6.md) och [C6-01-tillägget](momentum-C6-01-edwins-beslut.md) (Edwins val H1,
I1, G1 och P1, granskat av Codex: [underlag](momentum-C6-01-granskning-underlag.md),
[beslut](momentum-C6-01-granskning-beslut.md), [tillägg 2](momentum-C6-01-granskning-beslut-2.md) och
[tillägg 3](momentum-C6-01-granskning-beslut-3.md)). Implementationen är för Codex granskning och inte godkänd. Bara
syntetiska staplar, event och signalrader har använts. Ingen marknadshistorik har lästs och ingen H-0017-körning har
startats.

## API

Modul: [engine/traderlab/momentum_bound.py](../engine/traderlab/momentum_bound.py), `VERSION = "mom-bound/1.0.0"`.

| Del | Beskrivning |
|---|---|
| `bar_points(result)` | boundpunkterna för en stapel ur ett `BarResult`, utan peak och drawdown |
| `BoundLog.begin(start_state)` / `add(result)` | §10.2-serien för ett obrutet förlopp. Kedjan kontrolleras av `momentum_event.RunLog`, som avvisar dubbletter, luckor, bakåtsteg, främmande förlopp och tillägg efter terminal. Loggen börjar bara från startläget; replace och direkt konstruktion avvisas |
| `BoundLog.points` | `BoundPoint`: fas, stapel, tid (exakt eller "okänd inom stapeln" för high/low och intrastapelträff), konto/scenario, C/q/E, M och källa, hypotetisk mellanfunding, peak, drawdown och versioner |
| `max_dd_bound` / `max_dd_bound_mag` | negativt minimum respektive positiv magnitud. Kan bli under −1 vid oklippt negativt kapital (I1/G1) |
| `max_dd_close` / `max_dd_close_mag` | §10.1 via den oförändrade `stats.max_drawdown` på closeserien från RunLog, som börjar med 100 000 |

**Ändring i godkänd kod:** `momentum_event.BarResult` får fältet `bar`, den behandlade stapeln, eftersom bounden
behöver mark_high och mark_low. Ändringen är bara ett tillägg, och ingen annan rad i eventmodulen har ändrats. Alla 105
eventtester passerar, liksom de 18 och 16 felproven för eventmodulen. C03/C05 behöver Codex omgodkännande av exakt
revision.

## Punktordning

| Stapel | Punkter |
|---|---|
| levande utan träff | open (E(mark_open) på ingående C/q före A-funding och fyllning), trade (E_trade), post (E_post; i A lika med E_trade), high, low, close |
| terminal | open, trade, post och terminalt kapital, som räknas en gång. Inga extremer med den stängda positionen |
| intrastapelträff (H1, I1, P1) | open, trade, post, high, low, liquidation 0 |
| gapträff (G1, P1) | open, gap_check (prövningskapitalet efter A-funding, bara om A-funding bokfördes), liquidation 0 |
| likviderat konto | en absorbing-nolla per stapel, vid terminal terminalpunkten 0 |

High och low har fundingbasen C_high = C_post − Σmin(p_i, 0) och C_low = C_post − Σmax(p_i, 0), med q efter
öppningen. Utan träff är p_i stapelns bokförda mellanevent. Vid träff är det alla olösta mellanevent, som används enbart
hypotetiskt. Close använder den faktiska ledgern. Peak börjar på 100 000 och uppdateras före varje drawdown. Den
behålls genom likvidationen, och ingen reset sker per dag eller halvår. Utan träff jämförs low med eventlagrets
marginalunderlag inom 1e−12. Negativa värden står kvar oklippta. Punktordningen påstår ingen tidsordning, och bounden
påstås inte vara strängast under −100 % (reservation i C6-01).

## Ingen återkoppling

Bounden läser bara `BarResult`. Den skriver inget till risk-, konto-, funding- eller marginaltillståndet och anropas
inte av `process_bar`. `test_extremes_change_only_the_bound` visar att två förlopp med olika high och low, varav ett med
high över peak och low mer än 20 % ned, har identiska closepunkter, dagsserie, slutkonto, riskstate och eventspår
utanför marginalunderlaget. Bara bounden skiljer sig. Inget stopp utlöses.

## Verifiering

- [engine/tests/test_momentum_bound.py](../engine/tests/test_momentum_bound.py): 32 tester, alla godkända. Facit kommer
  från oraklet, Decimal och en fristående fold i testet:
  - O7: lokala punkter och bound mot oraklet, plus samma tal i float.
  - Ett verkligt sekventiellt förlopp från start med Decimal-löst inträde.
  - Fundingbaser utan träff: A/B × teckenordning × med/utan samtidig funding.
  - B:s skilda E_trade och E_post.
  - Partialförsäljning med q efter öppningen.
  - Ickeinterferens, prefix och löpande peak över midnatt mot fristående fold.
  - O6-reset och O10-terminal i A och B.
  - Full platt horisont: 6 577 closepunkter, 1 096 dagar, 1 + 6 575 × 6 + 4 boundpunkter och noll drawdown.
  - Intrastapelträff enligt C6-01 med positivt och negativt low i båda teckenordningarna, och underlagets fall 4
    (−7/6).
  - Gapträff i A (med gap_check) och B, absorberande nollor och 20 %-gränsen i måttet.
  - Kedje- och konstruktionsvakter.
- Riktade felprov: 18 fel, varav 17 fångade. "Close-peak i bounden" är bevisat ekvivalent: boundens peak innehåller
  alla closepunkter och highs och är därför alltid minst riskmodulens close-peak, och en BoundLog kan bara börja vid
  start. "Peakreset vid midnatt" missades först och fick ett eget prov. Modulen återställdes och jämfördes byte för
  byte.
- Hela verifieringen: 539 momentumtester och 1 092 motortester passerar. A1-oraklet, 20 av 20 momentum-audits och alla
  fyra checklistor passerar. Signal-, ledger-, funding-, risk- och marginalmodulerna är oförändrade, och stats är
  oförändrad.

## Avgränsningar

Bara huvudmodellen long/platt. Ingen legacy-ATR-stop, inga O8-, L1/L2- eller shortregler och ingen 20 %-beslutsmotor
eller boolesk C6. Ingen statistik, inga jämförelsekonton, ingen fundingstress, inget återupptag och ingen
§15-resultatlagring.
