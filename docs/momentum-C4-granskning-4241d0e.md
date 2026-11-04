# Codex omgranskning av H-0017 leverans C4

Datum: 2026-11-04. Exakt revision: `4241d0e164db6a7c20250f31fef2695d86e885bb`. Diffbas: `1505d087a1fc22fd47538ed7f3444121813b3714`, med [föregående granskning](momentum-C4-granskning-d7d2434.md). HEAD, diffbas och gren `codex/momentum-c4-review` kontrollerade före arbetet; arbetskopian var ren. Edwin har uttryckligen tillåtit denna syntetiska granskningsrunda. Ingen nätverkskontroll utförd.

**C4 godkänns inom sin avgränsade marginal-/ledgerleverans på exakt 4241d0e. C4-01–C4-05 är stängda med egna reproduktioner. Inga nya regressioner i rättningsytan har påvisats. Ett separat befintligt fel i funding/risk bekräftas som C4-06 [P2]; det hindrar fortsatt komponentgodkännande av risk och återöppnar MOM-C02, men är inte infört av denna C4-rättning.** Detta godkänner inte full eventintegration, intrastapel-bound eller någon körning. Nästa del väntar på Edwins beslut.

## Stängda fynd

- **C4-01 [P2]:** q = −1,75e308 vid .05 och q = −1,795e308 vid .005 ger kontrollerat LedgerError i threshold och check, utan falskt nollpris eller ändrat konto/tillstånd. Oberoende 70-siffriga Decimal-trösklar är 0,544217687… respektive 0,554331407….
- **C4-02 [P2]:** komplex sats och fel kontotyp avvisas med MarginError. Den tidigare egna matrisen med 44 avvisningar passerar via konstruktion/replace/threshold och samtliga fyra publika kontoingångar. Giltiga float/numpy.float64 och båda satserna fungerar.
- **C4-03 [P2]:** 10**400 via konstruktion, replace och threshold ger MarginError. Även de tidigare fyra prisproven med ±10**400 ger MarginError.
- **C4-04 [P2]:** 10**5000 via konstruktion, replace och threshold ger MarginError med skrivbart meddelande. Samma tre fall mot diffbasens egen marginalmodul och egen ledger reproducerar vanligt ValueError. Interpreterns heltalsgräns är 4300 och ändras aldrig. Ny `_show` används även i marginalens metadatafel.
- **C4-05 [P2]:** Account(C=10**400), replace(C=10**400), Account.open(10**400) och equity(10**400) ger LedgerError. Diffbasens egen ledger reproducerar OverflowError i alla fyra vägarna. En egen utökning ger ytterligare 49 kontrollerade avvisningar över positiva/negativa stora heltal, Fraction(10**5000, 3), priser och marginalmetadata. Inkommande konto/tillstånd bevaras.

`_num` fångar OverflowError kring ändlighetsprövningen och avvisar innan floatvärdet används; `_show` skyddar textkonverteringen mot ValueError/OverflowError. Ingen global interpreterinställning eller ekonomisk formel ändras. Testdiffens ändrade meddelandematchning följer den gemensamma ledgertexten; regressionerna behåller kravet på rätt undantagsklass.

## C4-06 [P2] Befintliga metadatafel i funding och risk läcker ValueError

Platser: `momentum_funding.py` i event-/konfigurationsvalidering och `momentum_risk.py` i `_boundary`/`SignalInput.__post_init__`.

Claudes observation är självständigt bekräftad. Exempel med vanliga Python-heltal, utan specialobjekt:

```python
dataclasses.replace(valid_funding_event, event_id=10**5000)
R.RiskState.start(1000, 10**5000)
dataclasses.replace(valid_signal, available=10**5000)
dataclasses.replace(valid_signal, version=10**5000)
# vanligt ValueError från repr, inte FundingError/RiskError
```

Auditen provar åtta vägar: funding event_id, time, M_ref_source och config.stress samt risk starttid, available, version och day. Alla åtta läcker på både 1505d08 och 4241d0e. Modulerna är byte-identiska mot basen. Observationen om samma repr-mönster är alltså korrekt, men kodrättning där hör inte till denna C4-diff. Inga ändringar i dessa moduler beställs eller utförs här. En fundingränta 10**400 har däremot förbättrats genom ledgerberoendet: diffbasen ger OverflowError, granskad revision FundingError.

Detta är ett verifierat motexempel mot modulernas dokumenterade kontrollerade felkontrakt, inte ett påvisat fel i giltiga ekonomiska beräkningar. Precis som för C4-05 räcker ett tidigare godkännande och gröna normalprov inte för att ignorera motexemplet. MOM-C02 återöppnas till in_progress; MOM-C03/C04 förblir in_progress med uttrycklig reservation för funding/risk. Tidigare numeriska verifieringar bevaras som underlag. C4:s avgränsade godkännande gäller marginalmodulen och ledgerkompletteringen, inte ett nytt helhetsgodkännande av C2/C3.

## Oberoende verifierade delar

Ny revisionslåst audit: [review.py](../research/audits/momentum-c4-4241d0e/review.py) och [verification.json](../research/audits/momentum-c4-4241d0e/verification.json). De egna referensproven från föregående granskning körs om. Produktionskällor hämtas med `git show` från exakt 4241d0e med revisionslåsta importer och SHA256; diffbasens reproduktioner använder också dess egen ledger. `--check` räknar om och jämför hela JSON. PASS innefattar det separat reproducerade C4-06 och innebär inte att funding/risk är felfria.

- **600** fristående 70-siffriga Decimal-jämförelser: long/short, båda satserna, varierande skalor, båda sidor om tröskeln. **12** floatgränsprov med exakt likhet och grannfloats följer direktvillkoret E≤MM utan epsilon.
- **300** likvidationsavstämningar och **två** ytterligare partial-/fundingförlopp bevarar historiska fält och verifierar justeringsdelta samt mtm+reset separat. Avstämning relativt beloppsskalan ≤1e−12. Negativt gap-E = −5 000 bevaras med reset +5 000 och mtm −15 000.
- Identiteten är `C = deposit + realized − costs − funding_net + liquidation_adjustment − q*avg_price`; likvidationsdelta `−C_old−q_old*avg_price_old`, därefter C=q=avg_price=0. Ingen artificiell fill eller extra likvidationsavgift. Gammal prövning, fel scenariosats och dubbel likvidation avvisas.
- **Fyra** A/B-öppningskompositioner och **fyra** long/short-intrastapelkompositioner vid båda satserna passerar. Betald funding föregår adverse-prövningen; senare kredit hoppas över efter likvidation. Ingen påhittad extremtid.
- **Sju** C3-gränser över midnatt till terminal bevarar absorberande nollkonto utan avsikter; separat överlevande delkonto kan fortsätta. Full O18-dagsserie och eventloop ingår fortfarande inte.
- **200** normalfyllningar jämförs mot ledgern före C4 (`db65a54`): tidigare konto-/fillfält exakt identiska, justeringen 0. **29** tidigare ogiltighetsprov passerar utöver särskilda regressioner och typmatriser.
- **Fyra** egna mutationer i minneskopior fångas: strikt `<`, omvänt villkor, fel shortextrem och tappad justering. Claudes fulla mutationsserie används inte som eget verifieringsunderlag.

## Körda kontroller och integritet

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Båda pytest-körningarna utförda från `engine/` med `-m pytest -p no:cacheprovider`.

- Fem momentumtestfiler: **380 passerade**, exit 0 (36 signal, 82 ledger, 88 funding, 101 risk, 73 marginal), 0,96 s.
- Hela motorsviten: **933 passerade**, exit 0, 96,04 s. En joblib-varning om antal fysiska CPU-kärnor, inga testfel.
- A1-oraklet med `--check`: PASS. Samtliga **15 tidigare** `research/audits/momentum-*/review.py --check`: PASS oförändrade. Ny audit med `--check`: PASS.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändring. Momentumvyn regenererad med python3; samtliga fyra --check passerar även efter statusändring. `git diff --check` rent.
- Exakt **sex** ändrade filer i 1505d08..4241d0e: marginalmodul, ledger, marginaltester, rapport, momentumstatus och momentumchecklista. Auditen kräver exakt denna fillista och byte-identisk ledgertext utanför `_num` och nya `_show` (inklusive dess avskiljande blankrader). Signal, funding, risk, deras tester, protokoll, register, gamla resultat och gamla audits är oförändrade mot basen. Ingen ändring utanför rättningsytan påvisad.

## Status och avgränsning

MOM-C01 återställs till done efter verifierad C4-05 och ledgerkomplettering. MOM-C02 sänks till in_progress på grund av C4-06. MOM-C03/C04/C05 förblir in_progress; C4 ger godkänt delunderlag, medan full integration/bound återstår och funding/risk har en känd valideringsbrist. Checklistan är fortsatt **11/40**. Nästa del väntar på Edwins beslut; inget nytt uppdrag skrivs.

Endast lokal syntetisk verifiering. Ingen marknadshistorik, nätverksanrop, historikkörning, registrering, merge, driftsättning, release eller paper/live. H-0013 förblir REJECT; H-0016:s separata protokoll/beslut är orörda. Underhållssatserna är frysta forsknings-/stressantaganden, inte verifierade historiska Binance-villkor. Inga implementations-/testfiler eller gamla audits ändras i denna granskning. Ingen commit eller push utförd.
