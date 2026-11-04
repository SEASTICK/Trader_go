# Codex omgranskning av H-0017 leverans C4

Datum: 2026-11-04. Exakt revision: `c312dfacbd3165b7347b78788ec3067eb6eb2226`. Diffbas: `deb9c8fef314f11a1cd1cfbd3e049d5354839f6b`, med [föregående granskning](momentum-C4-granskning-0773f76.md). HEAD, bas och gren `codex/momentum-c4-review` kontrollerade lokalt; arbetskopian var ren före granskningen. Edwin har uttryckligen tillåtit denna syntetiska granskningsrunda. Ingen nätverkskontroll eller ändring av Git-historik utförd.

**C4 är ej godkänd. C4-01 och de tidigare C4-02-reproduktionerna är rättade, men rättningen introducerar C4-03 [P2]: en otillåten stor heltalssats läcker OverflowError.** Normala marginalbeslut och redovisningsidentiteter är återverifierade oberoende av Claudes rapport. API-versionen är fortsatt mom-margin/1.0.0.

## C4-03 [P2] Kontrollerat fel saknas för stor heltalssats

Plats: `engine/traderlab/momentum_margin.py:59`, via `_mnum` på rad 43 och oförändrade ledgerns `_num` på rad 48.

Den nya ordningen i `_mmr` skickar nu varje reellt tal till `_num` innan tillåtna satser prövas. Python-heltal är `numbers.Real`, men `math.isfinite(10**400)` försöker konvertera till float och kastar `OverflowError`. `_mnum` fångar endast LedgerError och `_mmr` endast MarginError. En otillåten sats lämnar därför det dokumenterade kontrollerade felkontraktet. Samma anrop på diffbasen avvisas med MarginError innan konvertering: detta är en ny regression från rättningen.

```python
M.MarginState('main', 'A', 10**400)
dataclasses.replace(M.MarginState('main', 'A', 0.05), mmr=10**400)
M.threshold(L.Account.open(1000), 10**400)
# c312dfa: OverflowError: int too large to convert to float
# deb9c8f: MarginError: Underhållssatsen måste vara exakt en av ...
```

Auditen reproducerar samtliga tre anrop på båda revisionerna och kontrollerar oförändrat konto/tillstånd. Detta är ett syntetiskt valideringsprov, inget påstående om realistisk underhållssats. Giltiga .05/.005 och numpy.float64 fungerar fortsatt; det vanliga träffbeslutet påverkas inte.

**Krävd rättning:** avvisa även reella satser som inte kan representeras som ändliga float med MarginError/LedgerError, före okontrollerad konvertering. Begränsa eventuell undantagshantering till den numeriska valideringen; dölj inte godtyckliga interna fel. Bevara de två tillåtna satserna och typavvisningen från C4-02. Regressioner ska täcka konstruktion, replace och threshold med stor heltalssats och oförändrade indata. Ingen metodändring krävs.

## Stängda tidigare fynd

- **C4-01 [P2], stängt:** de två exakta tidigare kontona, q = −1,75e308 vid .05 och q = −1,795e308 vid .005, ger LedgerError för icke-ändlig nämnare i både threshold och check. Konto och tillstånd förblir identiska. De oberoende 70-siffriga Decimal-trösklarna är fortsatt 0,544217687… respektive 0,554331407…; inget falskt nollpris returneras. Legitim nolltröskel och platt konto → None fungerar.
- **C4-02 [P2], tidigare feltyper stängda:** komplex sats ger MarginError och fel kontotyp avvisas före fältåtkomst i threshold/check_bar. Utökad egen matris ger 44 kontrollerade avvisningar: åtta ogiltiga satser via konstruktion/replace/threshold och fem fel kontotyper via samtliga fyra publika ingångar. Python-float och numpy.float64 vid båda tillåtna satserna fungerar. Den nya heltalsregressionen redovisas separat som C4-03.

## Oberoende verifierade delar

Ny audit: [review.py](../research/audits/momentum-c4-c312dfa/review.py) och [verification.json](../research/audits/momentum-c4-c312dfa/verification.json). Auditens referensprov vidareför de egna proven från föregående granskning. Alla prövade produktionsmoduler läses med `git show` från exakt c312dfa, med matchande revisionslåsta importer. Källornas SHA256 sparas; diffbasen kontrolleras med en exakt tillåten fillista. `--check` räknar om allt och jämför med JSON. PASS innefattar reproducerat C4-03 och är inget godkännande.

- 600 jämförelser mot fristående 70-siffrig Decimal-referens: long/short, båda satserna, varierande skalor och punkter på båda sidor om gränsen. 12 floatgränsprov med exakt E=MM och grannfloats följer direktvillkoret E≤MM utan epsilon.
- 300 likvidationsavstämningar och två ytterligare förlopp med verkliga syntetiska partialaffärer, kostnader och funding. Bevarade historiska fält; justeringsdelta och mtm+reset jämförda separat. Avstämning relativt beloppsskalan ≤1e−12. Negativt gap-E = −5 000 bevaras med reset +5 000 och mtm −15 000.
- Identiteten är fortsatt `C = deposit + realized − costs − funding_net + liquidation_adjustment − q*avg_price`; likvidationsdelta `−C_old−q_old*avg_price_old`, därefter C=q=avg_price=0. Inga syntetiska fills eller extra likvidationsavgifter. Gammal prövning, fel scenariosats och upprepad likvidation avvisas.
- Fyra öppningskompositioner (A/B × båda satserna) och fyra intrastapelkompositioner (long/short × båda satserna) passerar. A-funding föregår kontroll/fill, B-funding följer fill; ogynnsam extrem prövas efter betald och före mottagen funding. Senare kredit hoppas över efter likvidation. Ingen påhittad tid för extremen.
- Sju C3-gränser över midnatt till terminal bevarar absorberande nollkonto utan avsikter. Ett separat överlevande delkonto kan fortsätta. Full O18-dagsserie och eventloop ingår fortsatt inte i C4.
- 200 normalfyllningar jämförda med ledgern före C4 (`db65a54`): alla tidigare konto-/fillfält exakt identiska, nya justeringen 0. Ledgern är också byte-identisk mot den nuvarande diffbasen deb9c8f.
- 29 tidigare egna ogiltighetsprov passerar utöver de nya feltypsproven och de två nämnarfallen. Fyra egna mutationer i minneskopior fångas: strikt `<`, omvänt villkor, fel shortextrem och tappad justering. Claudes fulla mutationsserie har inte körts om och används inte som eget verifieringsunderlag.

## Körda kontroller och integritet

Projektets interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Båda pytest-körningarna utförda från `engine/` med `-m pytest -p no:cacheprovider`.

- Fem momentumtestfiler: **367 passerade** (36 signal, 82 ledger, 88 funding, 101 risk, 60 marginal).
- Hela motorsviten: **920 passerade**, exit 0, 95,68 s. En joblib-varning om antal fysiska CPU-kärnor, inga testfel.
- A1-oraklet med `--check`: PASS. Samtliga **13 tidigare** `research/audits/momentum-*/review.py --check`: PASS oförändrade. Ny audit: PASS inklusive C4-03.
- Alla fyra checklistgeneratorer med `--check`: PASS före statusändring. Momentumvyn regenererad från statuskällan med python3; alla fyra --check passerar även efter statusändringen. `git diff --check` rent.
- Exakt fem ändrade filer i deb9c8f..c312dfa: marginalmodul, marginaltester, rapport, momentumstatus och momentumchecklista. Ledger, signal, funding, risk, deras tester, frysta protokoll, register, gamla resultat och gamla audits är oförändrade. Detta verifieras av hela diffens fillista, inte enbart utvalda filhashar. Ingen ändring utanför den tillåtna rättningsytan påvisad.

## Status och avgränsning

MOM-C01 och MOM-C02 behåller done: ledger/risk är oförändrade mot basen och kompatibiliteten är omprövad. MOM-C03/C04/C05 förblir in_progress; C05 har verifierat delunderlag men blockeras nu av C4-03 och kvarvarande full integration. Ingen ny punkt blir klar; checklistan kvarstår på **12/40**. C4-01/C4-02:s tidigare reproduktioner är stängda på denna revision, medan C4 som helhet behöver rättning och omgranskning av exakt ny revision. Inget uppdrag för någon senare leverans skrivs.

Endast lokal syntetisk verifiering. Ingen marknadshistorik, nätverksanrop, registrering, historikkörning, merge, driftsättning, release eller paper/live. H-0013 förblir REJECT; H-0016:s protokoll/beslut är orörda. Satserna är frysta forsknings-/stressantaganden, inte verifierade historiska Binance-villkor. Ingen commit eller push utförd.
