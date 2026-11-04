# Codex omgranskning av H-0017 leverans C4

Datum: 2026-11-04. Exakt revision: `d7d2434dd7dbecc70f2267165a02e61296859346`. Diffbas: `35486b885da1cc249b7df97d5c68b9d17f67f53e`, med [föregående granskning](momentum-C4-granskning-c312dfa.md). HEAD, bas och gren `codex/momentum-c4-review` kontrollerade före arbetet; arbetskopian var ren. Edwin har uttryckligen tillåtit denna syntetiska granskningsrunda.

**C4 är ej godkänd. De exakta reproduktionerna C4-01–C4-03 är stängda, men fortsatt felmeddelandeformatering läcker ValueError (C4-04). Ledgerns observerade OverflowError är också verifierad och strider mot dess befintliga felkontrakt (C4-05); MOM-C01 återöppnas.** Normala marginalbeslut och redovisningsidentiteter är återverifierade oberoende av Claudes rapport. API-versionen är fortsatt mom-margin/1.0.0.

## C4-04 [P2] Felmeddelandet för ännu större heltal läcker ValueError

Plats: `engine/traderlab/momentum_margin.py:65`, `_mmr`.

Den snäva fångsten av OverflowError i `_mnum` fungerar. Men `_mmr` ersätter dess MarginError genom att formatera den ursprungliga satsen med `{mmr!r}`. Med projektets interpreter och standardgränsen `sys.get_int_max_str_digits() == 4300` kan Python inte skapa decimalrepresentationen av `10**5000`. Därmed kastar själva felmeddelandet ett vanligt ValueError, som inte är MarginError/LedgerError.

```python
M.MarginState('main', 'A', 10**5000)
dataclasses.replace(M.MarginState('main', 'A', .05), mmr=10**5000)
M.threshold(L.Account.open(1000), 10**5000)
# ValueError: Exceeds the limit (4300 digits) for integer string conversion ...
```

Alla tre ingångar reproduceras i den revisionslåsta auditen. Indata är oförändrade. Detta är en kvarvarande lucka i kontrollerad avvisning, inte ett fel i det normala marginalbeslutet. På diffbasen nådde stora heltal redan en okontrollerad OverflowError; rättningen flyttar för detta större fall läckan till felmeddelandet. Ingen ny ekonomisk beräkningsregression har påvisats.

**Krävd rättning:** gör felmeddelandet säkert även när talet inte kan representeras som text; bevara MarginError och begränsa fångsten till valideringen. Ändra inte interpreterns globala säkerhetsgräns för att få provet grönt. Regressioner behövs för konstruktion, replace och threshold med denna indataklass.

## C4-05 [P2] Ledgerns numeriska validering läcker OverflowError

Plats: `engine/traderlab/momentum_ledger.py:48`, `_num`.

Claudes observation är korrekt, men det kontrollerade felkontraktet finns redan: modulens dokumentation anger LedgerError för felaktig indata och [C1-rapporten](momentum-ledger-C1.md) beskriver reella tal som konverteras till Python-float med kontrollerade fel. Detta kräver inget nytt metodbeslut. `math.isfinite(10**400)` gör en implicit floatkonvertering som läcker OverflowError före LedgerError.

Auditen reproducerar fyra publika vägar: `Account(C=10**400)`, `dataclasses.replace(acct, C=10**400)`, `Account.open(10**400)` och `acct.equity(10**400)`. Inget inkommande konto ändras. Ledgern är byte-identisk mot 35486b8; detta är en redan befintlig C1-brist som nu belagts, inte en ledgerändring eller regression införd av d7d2434.

**Konsekvens:** MOM-C01 återöppnas till in_progress. Normala bokföringsidentiteter och tidigare verifieringsunderlag behålls, men de räcker inte för ett helt komponentgodkännande när det dokumenterade felkontraktet har ett verifierat motexempel. En avgränsad rättning behöver kontrollerade LedgerError och regressioner utan halv uppdatering; den utförs inte i denna granskning. MOM-C02 behåller sitt godkännande eftersom riskmodulen och dess verifierade funktion är oförändrade.

## Stängda tidigare reproduktioner

- **C4-01 [P2], stängt:** båda tidigare kontona, q = −1,75e308 vid .05 och q = −1,795e308 vid .005, ger LedgerError för nämnaroverflow i threshold och check. Inga falska nollpriser; oförändrade konton och tillstånd. De oberoende 70-siffriga Decimal-trösklarna är 0,544217687… respektive 0,554331407….
- **C4-02 [P2], stängt:** tidigare komplex sats och fel kontotyp avvisas med MarginError. Utökad egen matris ger 44 kontrollerade avvisningar via konstruktion/replace/threshold och alla fyra publika kontoingångar. Giltiga Python-float och numpy.float64 vid båda satserna fungerar.
- **C4-03 [P2], exakt tidigare reproduktion stängd:** 10**400 via konstruktion, replace och threshold ger nu MarginError. Samma tre anrop på exakt diffbas ger OverflowError. Fyra extra egna prisprov med ±10**400 i check/check_bar ger MarginError. Det större formateringsfallet redovisas separat som C4-04; detta innebär inget generellt godkännande av all ogiltig indata.

## Oberoende verifierade delar

Ny audit: [review.py](../research/audits/momentum-c4-d7d2434/review.py) och [verification.json](../research/audits/momentum-c4-d7d2434/verification.json). De egna tidigare referensproven vidareförs och körs om. Produktionskällor läses med `git show` från exakt d7d2434, med revisionslåsta importer och SHA256. Diffbasens marginalmodul och ledgern före C4 läses också revisionslåst. `--check` räknar om och jämför hela JSON. PASS innefattar reproducerade C4-04/C4-05 och är inget godkännande.

- 600 fristående 70-siffriga Decimal-jämförelser: long/short, båda satserna, varierande skalor och båda sidor om tröskeln. 12 floatgränsprov följer E≤MM utan epsilon, inklusive exakt likhet och grannfloats.
- 300 likvidationsavstämningar och två ytterligare syntetiska partial-/fundingförlopp. Historiska fält bevaras; justeringsdelta och mtm+reset kontrolleras separat med tolerans relativt beloppsskalan ≤1e−12. Negativt gap-E = −5 000 bevaras med reset +5 000 och mtm −15 000.
- Identiteten är `C = deposit + realized − costs − funding_net + liquidation_adjustment − q*avg_price`; likvidationsdelta `−C_old−q_old*avg_price_old`, därefter C=q=avg_price=0. Ingen artificiell fill eller extra likvidationsavgift. Gammal prövning, fel scenariosats och upprepad likvidation avvisas.
- Fyra A/B-öppningskompositioner och fyra long/short-intrastapelkompositioner vid båda satserna passerar. Betald funding föregår adverse-prövningen, mottagen följer; senare kredit hoppas över efter likvidation. Ingen påhittad extremtid.
- Sju C3-gränser över midnatt till terminal bevarar absorberande nollkonto utan avsikter; ett separat överlevande delkonto kan fortsätta. Full O18-dagsserie och eventloop ingår fortfarande inte i C4.
- 200 normalfyllningar jämförda mot ledgern före C4 (`db65a54`): alla tidigare konto-/fillfält exakt identiska, justeringen 0. 29 tidigare egna ogiltighetsprov passerar utöver de särskilda regressions- och typmatrisproven.
- Fyra egna mutationer i minneskopior fångas: strikt `<`, omvänt villkor, fel shortextrem och tappad justering. Claudes rapporterade fulla mutationsserie används inte som eget verifieringsunderlag.

## Körda kontroller och integritet

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Båda pytest-körningarna utförda från `engine/` med `-m pytest -p no:cacheprovider`.

- Fem momentumtestfiler: **371 passerade** (36 signal, 82 ledger, 88 funding, 101 risk, 64 marginal).
- Hela motorsviten: **924 passerade**, exit 0, 96,75 s. En joblib-varning om antal fysiska CPU-kärnor, inga testfel.
- A1-oraklet med `--check`: PASS. Samtliga **14 tidigare** `research/audits/momentum-*/review.py --check`: PASS oförändrade. Ny audit: PASS med reproducerade C4-04/C4-05.
- Alla fyra checklistgeneratorer med `--check`: PASS före och efter statusändring. Momentumvyn regenererad från statuskällan med python3 och kontrollerad med `--check`. `git diff --check` rent.
- Exakt fem ändrade filer i 35486b8..d7d2434: marginalmodul, marginaltester, rapport, momentumstatus och momentumchecklista. Ledger, signal, funding, risk, deras tester, frysta protokoll, register, gamla resultat och gamla audits är oförändrade. Hela diffens exakta tillåtna fillista kontrolleras även av auditen. Ingen ändring utanför rättningsytan har införts av Claude.

## Status och avgränsning

MOM-C01 sänks från done till in_progress på grund av C4-05. MOM-C02 behåller done med ny kompatibilitetsevidens. MOM-C03/C04/C05 förblir in_progress; ingen ny punkt markeras klar. Checklistan blir **11/40**. De tidigare fyndens exakta reproduktioner är stängda på d7d2434, medan C4 som helhet behöver rättning och omgranskning av exakt ny revision. Inget uppdrag för någon senare leverans skrivs.

Endast lokal syntetisk verifiering. Ingen marknadshistorik, nätverksanrop, registrering, historikkörning, merge, driftsättning, release eller paper/live. H-0013 förblir REJECT; H-0016:s protokoll/beslut är orörda. Satserna är frysta forsknings-/stressantaganden, inte verifierade historiska Binance-villkor. Inga implementations- eller testfiler, frysta protokoll, register, gamla resultat eller gamla audits har ändrats i denna granskning. Ingen commit eller push utförd.
