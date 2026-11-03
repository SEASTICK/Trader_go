# H-0017 leverans C3 – avsikter, band och riskstatus mom-risk/1.0.0

Datum 2026-11-03. Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §4, §6–§8, D07, D17, D19 och
[uppdraget](claude-uppdrag-momentum-C3.md). Implementation för Codex granskning, inte godkänd. Endast syntetiska konton
och signaler; ingen marknadshistorik har lästs och ingen H-0017-körning har startats. Protokoll, register och de
godkända modulerna B (signal), C1 (ledger) och C2 (funding) är orörda.

## API

Modul: [engine/traderlab/momentum_risk.py](../engine/traderlab/momentum_risk.py), `VERSION = "mom-risk/1.0.0"`.
Konstanter: `BAND = 0,02`, `DAY_STOP = −0,02`, `PERMANENT_STOP = −0,15`. Drawdowngränsen 20 % är protokollets
utvärderingskrav och finns inte här som handelsstopp.

| Del | Beskrivning |
|---|---|
| `RiskState` | oföränderligt: initial, peak, day_start, next_boundary, started, lock_day, permanent (+ tid), last_decision_day, liquidated, terminated. `RiskState.start(kapital, första_öppning)` |
| `CloseInput(bar_open, account, mark_close, liquidated=False)` | kontot efter allt i stapeln (fyllning, funding) och markpriset vid stapelns close |
| `SignalInput` | B:s rad för dag D; `SignalInput.from_row(signals(...).iloc[i])` |
| `step(state, T, close, signal, terminal=False)` | en 4H-gräns; returnerar nytt tillstånd och `StepRecord` med högst en `Intent` för fyllning vid öppningen T |
| `Intent` | kind, w (fryst vikt), decision_time, fill_time, source_bar, E_decision, mark_decision, w_current, reason, `risk` |
| `StepRecord` | gräns, källstapel, E_close, peak, day_start_used, dagsavkastning, drawdown, utlösta stopp, dagsbeslut, prövade kandidater, avsikt, strukna kandidater med orsak |
| `fill_intent(acct, intent, P, M, c)` | enda kopplingen till C1: risk via `fill_risk` (reduce-only), normal via `fill_normal`, med öppningens P och M |
| `RiskError` | underklass till `LedgerError` |

## Tillståndsövergångar vid gränsen T

1. Kontroller: T är UTC på 4H-rutnätet och exakt `next_boundary`; första steget saknar close, alla senare har en
   close för stapeln som slutar vid T; signal finns vid 00:00 och bara där.
2. E_close = konto.equity(mark_close). Funding och kostnader finns redan i kontot och bokförs inte igen.
   peak = max(peak, E_close), med startkapitalet som utgångsläge.
3. Permanent stopp om E_close/peak − 1 ≤ −0,15; absorberande. Dagsstopp om E_close/day_start − 1 ≤ −0,02;
   lock_day = UTC-dagen för stapeln som stängde. Utträdesavsikter skapas bara om q ≠ 0.
4. Vid 00:00: dagsbeslut för D = T − 1 dag i §7:s ordning: permanent spärr, platt signal med position (risk),
   w_current > cap (risk), abs(w_target − w_current) ≥ 0,02 (normal), annars `hold_units`. Högst ett beslut per dag.
5. Sammanslagning: terminal > permanent > dagsstopp > capbrott/platt > normal. Strukna kandidater loggas. En
   normalavsikt stryks också om fyllningsdagen är lock_day eller permanent stopp gäller.
6. Dagsreset vid 00:00 efter beslutet: day_start = E_close för 20-stapeln, före gap, funding och handel vid T. Den
   gamla köpspärren gäller inte den nya dagen; ett riskutträde från samma close ligger kvar i avsikten. Vid första
   gränsen är day_start startkapitalet.
7. Terminal (`terminal=True`, öppningen 2024-12-31 20:00): avsikt `terminal` med w = 0 före allt annat; därefter
   avvisas fler steg.

Avsikter fryser vikt och typ. Beslutets mark_close sparas i avsikten och är skilt från öppningens priser, som bara
fyllningslagret ser. Det finns ingen kö av gamla avsikter; varje avsikt gäller bara sin fyllningstid T.

Dokumenterat likvidationstillstånd: en close med `liquidated=True` kräver E = C = q = 0, gör tillståndet absorberande
och ger inga fler avsikter. En nolla eller negativt kapital utan detta tillstånd är fel. Likvidationsbokföringen
finns inte här.

## Gräns mot kommande eventloop

Eventloopen ska vid varje T anropa `step` med kontot efter stapelns händelser, skicka avsikten till `fill_intent` vid
öppningen (efter gap, scenario A-funding och marginalkontroll), bokföra B-funding och mellanhändelser med C2 och
avgöra första/sista event, intrastapel-bound och likvidation. Fördröjningsstressens kö finns inte här.

## Fel

RiskError (eller LedgerError från ledgern) utan ändrat tillstånd: fel typ, icke-UTC, naiv eller felplacerad tid, tid
som inte är `next_boundary` (dubblett eller lucka), close för fel stapel, saknad eller felplacerad signal, signal för
fel dag, otillgänglig signal (OGILTIG_DATA, ingen ersättning), w_target ≠ s × cap, dubbelt dagsbeslut, q < 0,
E ≤ 0 utan likvidationstillstånd, icke-ändliga värden och overflow, ogiltigt tillstånd, steg efter terminal.

## Verifiering

- [engine/tests/test_momentum_risk.py](../engine/tests/test_momentum_risk.py): 61 tester, alla godkända. Facit från
  [orakelfilen](momentum-a1-orakel.json) (O6, O14, O15) och handräkning. Faktiska gränsvärden (inga epsilon):
  - band uppåt vid w_current 0,3: cap 0,32 ger diff 0,020000000000000018 (normal), grannen 0,31999999999999995 ger
    0,019999999999999962 (hold); nedåt motsvarande; exakt 0,04 − 0,02 = 0,02 ger normal, så bandet är inkluderande;
  - permanent stopp: E = 85 000 ger −0,15000000000000002 (utlöst), nästa float 85 000,00000000001 ger
    −0,1499999999999998 (ej utlöst);
  - dagsstopp med day_start 101 000: E = 98 980 ger −0,020000000000000018 (utlöst), nästa float −0,019999999999999907.
  - Övrigt: capbrott och platt signal trots litet bandavstånd och utan position, sammanfallande villkor, prioritet
    terminal > permanent > dag > cap, O6 med dagsstopp vid 20-stapeln där riskutträdet behålls över reset och
    normalavsikten stryks, day_start som inte flyttas av gap/funding efter midnatt, lock_day inom dygnet, permanent
    stopp över 24 gränser, beslut bara vid 00:00, O14 och O15 komponerade med C1, ingen gammal normalavsikt efter
    riskfyllning, prefix och ändrade framtida värden, oförändrade indata, 18 ogiltiga anrop, ogiltiga close-indata och
    tillstånd, overflow, likvidationstillstånd och en riktig rad från B:s `signals()`.
- Alla momentumtester (signal, ledger, funding, risk): 267 godkända.
- Riktade felprov: 19 avsiktliga fel infördes ett i taget. 17 fångades: band med epsilon, band strikt `>`, dagsstopp mot
  peak, dag före permanent, normal före risk, capbrott före platt signal, capbrott ignorerat inom bandet, reset till
  gammal day_start, reset till peak, riskutträde som tappas vid midnatt, permanent stopp som återställs, avsikt som
  fryser enheter (fyllning till beslutets pris), borttagen lock_day-spärr, dubbelt dagsbeslut, otillgänglig signal som
  blir platt, peak som inte uppdateras och borttagen tidsordningskontroll. Två är bevisat ekvivalenta: `<` i stället
  för `≤` i permanent- och dagsstoppet. För kvoter i [0,5; 1] räknas E/peak − 1 exakt och hamnar på rutnätet 2⁻⁵³, där
  varken −0,15 eller −0,02 ligger, så likhet kan inte inträffa; ett test visar detta. Två felprov (band `>` och
  tidsordning) missades först och fick riktade tester. Modulen återställdes och jämfördes byte för byte.

## Utanför C3

Ingen eventloop, marginal eller likvidationsbokföring, intrastapel-bound, första/sista event-integration,
fördröjningsstress, jämförelser, statistik eller historisk körning. Hela C02–C05 blir inte klara genom denna modul.
Endast syntetiskt prövat.
