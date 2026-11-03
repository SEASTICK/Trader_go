# H-0017 leverans C1 – ledger mom-ledger/1.0.0

Datum 2026-11-03. Rättad efter [Codex granskning av 6eba8d6](momentum-C1-granskning-6eba8d6.md): C1-01 numerisk
validering av kontofält och beräknade belopp, C1-02 vakt för den första divisionen och enhetliga skalärtyper. Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §6, D17 och D19 samt
[uppdraget](claude-uppdrag-momentum-C1.md). Implementation för Codex granskning, inte godkänd. Endast syntetiska tal;
ingen marknadshistorik har lästs och ingen H-0017-körning har startats. Signalmodulen från B är orörd.

## API

Modul: [engine/traderlab/momentum_ledger.py](../engine/traderlab/momentum_ledger.py). `VERSION = "mom-ledger/1.0.0"`,
`COST_NORMAL = 0,0016`, `COST_STRESS = 0,0040`. Alla funktioner är rena: de returnerar ett nytt konto och ändrar inget.

| Del | Beskrivning |
|---|---|
| `Account(C, q, deposit, avg_price, realized, costs)` | oföränderligt konto; `Account.open(kapital)` startar platt |
| `Account.equity(M)`, `Account.weight(M)` | E = C + q × M och q × M / E vid markpris M |
| `Account.reconciliation_gap()` | C − (C0 + realized − costs − q × avg_price); ska vara 0 |
| `solve_units(E, q_old, P, M, w, c)` | exakt q_new enligt §6, gren från den kostnadsfria lösningen |
| `fill_normal(acct, w, P, M, c)` | normalavsikt: exakt målvikt, köp eller sälj beroende på läget vid öppningen |
| `fill_risk(acct, w, P, M, c)` | riskavsikt, reduce-only: ökar aldrig abs(q); annars hold utan affär och kostnad |
| `Fill` | spår per fyllning: kind, w, P, M, c, q_old, q_star, q_new, dq, cost, E_before, E_trade, weight_trade, realized_delta, risk_reduce_only_hold, phase = `after_trade`, version |
| `LedgerError` | ogiltig indata eller ingen konsekvent lösning |

## Bokföringsidentiteter

- En affär Δq vid P: C ← C − Δq × P − c × P × abs(Δq). Kostnaden bokförs en gång; ingen extra spread eller slippage på priset.
- E_trade = E_before + Δq × (M − P) − c × P × abs(Δq), och för en löst fyllning q_new × M / E_trade = w exakt.
- E_trade är kapitalet direkt efter affären. Funding (E_post) läggs till av ett senare eventsteg och ändrar inte E_trade
  eller målidentiteten.
- Vändning är ett Δq med kostnad på abs(Δq) = abs(q_old) + abs(q_new); hela gamla positionen realiseras och nytt
  snittpris blir P. Partialminskning realiserar bara sålda enheter och behåller snittpriset.
- C = C0 + realized − costs − q × avg_price. Kapitalledgern C/q är källan; realized och avg_price är redovisning.

## Typer och numeriskt kontrakt

- Alla tal tas emot som reella tal (Python eller numpy-skalärer), avvisas om de är bool, icke-numeriska, NaN eller
  oändliga, och räknas sedan som Python-float. Samma värden ger därför samma resultat och samma fel oavsett skalärtyp.
- `Account` kontrollerar vid varje konstruktion, även `dataclasses.replace`, att C, q, deposit, avg_price, realized och
  costs är ändliga tal. Inga teckenregler: negativ C, negativ q (legacy-short) och negativt realiserat är giltiga.
- Varje beräknat belopp (E, vikt, avstämningsgap, kostnadsfri nämnare, q0, nämnare, kostnad, realiserat, nya kontofält,
  E_trade och vikt efter affär) kontrolleras för NaN och oändlighet innan något returneras, även när ändliga indata
  ger overflow. Vid fel returneras inget konto eller fill och det inkommande kontot är oförändrat.

## Fel

LedgerError, aldrig klippning, påhittade nollor eller NaN: icke-ändliga eller icke-numeriska tal (även bool), ogiltiga
kontofält, E ≤ 0, P ≤ 0, M ≤ 0, c < 0, abs(w) > 1, kostnadsfri nämnare M − w(M − P) = 0, slutlig nämnare ≤ 0,
lösning som motsäger vald köp-/säljgren eller har fel tecken, icke-ändligt mellanresultat eller belopp,
startkapital ≤ 0 och E_trade ≤ 0. Ingen reservlösare för odefinierade fall.

## Verifiering

- [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py): 82 tester, alla godkända. De 42
  nya regressionerna för granskningen täcker NaN, ±inf, bool och text i varje kontofält vid konstruktion och replace,
  giltiga negativa C/short/förlustfall, overflow med ändliga argument i båda fyllningsvägarna (oförändrat konto),
  no-trade- och hold-vägarna, publika värden, nollnämnaren med Python float/int och np.float64/np.int64 under
  varningar-som-fel, icke-ändligt q0 från ändliga argument och samma resultat för numpy- och Python-tal. 39 av dem
  fäller den granskade revisionen 6eba8d6. De tidigare 40 testerna är oförändrade. Facit från
  [orakelfilen](momentum-a1-orakel.json) och handräknade uttryck, aldrig från produktionslösaren: O1, O2, O3 (basis en
  gång), O4 (partialköp/partialsälj med snittpris och realiserat), O11 (legacy-short w = −1), O14 (hold vid gap ned,
  exakt minskning vid gap upp), O15 (normalavsikt byter riktning), ingen affär utan kostnad, full stängning med w = 0 i
  båda avsiktstyperna, vändning long→short och short→long, riskavsikt köper aldrig från platt eller byter tecken,
  skalning med konstant, spårpost utan funding, kostnadsstress, 16 ogiltiga lösarindata, tre lösarfall där varje vakt
  ensam måste fånga felet, ogiltigt startkapital, numpy-skalärer och en lång sekvens med avstämning.
- Riktade felprov efter rättningen: de 14 tidigare och 6 nya fel (oövervakad första nämnare, q0 utan
  ändlighetskontroll, ovaliderade kontofält, numpy kvar som numpy, ingen overflowkontroll i E, ingen kontroll av
  realiserat). 19 fångas. Det sista är ekvivalent: ett oändligt realiserat resultat stoppas ändå av kontots fältkontroll
  när det nya kontot byggs; vakten behålls som försvar på djupet.
- Riktade felprov i första leveransen: 14 avsiktliga fel infördes ett i taget och testfilen kördes. Alla 14 fångades: kostnad två gånger,
  storlek före kostnad, ignorerad basis, riskavsikt som får öka q, partialsälj som realiserar hela positionen, vändning
  som behåller gammalt snittpris, kostnad på abs(q_old) + abs(q_new) i stället för abs(Δq), kostnad 0,01 % för hög,
  w = 0 som behåller innehavet, E_trade till kontraktspris, tyst klippning av w, inkonsekvent gren godkänd,
  nämnarkontroll borttagen och hold som ändå handlar. Två lösarvakter missades först eftersom testfallet utlöste båda;
  därför finns nu fall där bara den ena vakten slår till. Ett första felprov (w = 0 utan tidig retur) var ekvivalent,
  eftersom formeln då ändå ger 0, och ersattes. Modulen återställdes och jämfördes byte för byte.

## Utanför C1

Ingen eventloop, funding, marginal eller likvidation, UTC-dagsreset, handelsband eller signalbeslut, dags- eller
permanent stopp, intrastapel-bound, jämförelser eller statistik. Gränserna i uppdraget (cap efter affär, band 2 pp,
dagsstopp 2 %, permanent stopp 15 %, drawdown 20 %) implementeras i senare delar. Gap kan överskrida stoppnivåer; inget
här är en garanti om maximal förlust. Endast syntetiskt prövat.
