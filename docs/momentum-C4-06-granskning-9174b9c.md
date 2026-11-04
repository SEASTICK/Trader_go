# Codex omgranskning av H-0017 C4-06

Datum: 2026-11-04. Exakt revision: `9174b9c4f1543cefa6793a33d4eb7b853e0a368d`. Diffbas: `6530ca27f06e1c7816b61678f014b26dcf6a5fa5`. Föregående beslut: [granskningen av 4241d0e](momentum-C4-granskning-4241d0e.md). HEAD, diffbas och grenen `codex/momentum-c406-review` kontrollerades först; arbetskopian var ren. Edwin har uttryckligen tillåtit denna avgränsade rättning och oberoende granskning med syntetiska data.

**C4-06 [P2] är stängt på exakt 9174b9c. C2:s fundingmodul och C3:s rena risk-/avsiktsmodul godkänns åter inom sina tidigare komponentgränser. Inga nya fynd.** MOM-C02 återställs till done. Detta är inte ett godkännande av en färdig eventmotor, strategi, historikkörning eller drift. Nästa del väntar på Edwins beslut.

## C4-06 – egen reproduktion och rättning

De åtta ursprungliga vägarna med `10**5000` reproducerar vanligt ValueError på diffbasens egna moduler och egen ledger: funding event_id, time, M_ref_source och config.stress samt risk starttid, available, version och day. Samma fall ger nu FundingError respektive RiskError med meddelanden som kan formateras med str, f-sträng och repr. Heltalsgränsen är 4300 genom hela auditen och ändras aldrig.

Den egna matrisen omfattar **22 vägar**, vardera med positivt och negativt `10**5000`: totalt **44 kontrollerade avvisningar**. Utöver de åtta provas funding M_ref_time, rate, M_ref, price_model, account_key, scenario, processed och phase samt risk initial, decision_time, step-T, bar_open, mark_close och lock_day. Alla befintliga konto-, fundingstate-, event-, signal- och riskstate-värden jämförs efter varje anrop och förblir oförändrade. Konstruktion/replace samt anrop med befintligt konto/state ingår.

På diffbasen läcker **17 av de 22 positiva fallen** ValueError; fem hade redan kontrollerad felhantering. Det skiljer reproducerade brister från redan fungerande numeriska och metadatarelaterade vakter. Nya felmeddelanden ger inga avsikter eller bokningar.

## Diff och integritet

Exakt sju filer skiljer 6530ca2 från 9174b9c: fundingmodulen, riskmodulen, deras två testfiler, Claudes rättningsrapport, momentumstatus och genererad momentumchecklista. Produktionsdiffen ändrar **nio fundingformateringar och fyra riskformateringar**, plus import av ledgerns befintliga `_show` i respektive modul. Inga regler, beräkningar, valideringsvillkor, signaturer eller versionskonstanter ändras.

Auditen verifierar detta på två sätt: AST-jämförelse efter återställning av endast de 13 formateringarna/importerna, och byte-exakt textjämförelse efter samma återställning. Det täcker även kod utanför själva valideringsgrenarna. Kvarvarande interpolerade värden i felmeddelandena har redan kontrollerats som tider, strängar eller ändliga tal; de prövade stora heltalen avvisas tidigare. Den andra källtexten för M_ref nås först efter strängkontroll.

Den exakta fillistan bevisar att ledger, signal, marginal, fryst H-0017-protokoll, register, gamla resultat och samtliga gamla audits är oförändrade mot 6530ca2. Funding/risk på diffbasen är även byte-identiska med 4241d0e. Granskningen ändrar inga implementations- eller testfiler. Claudes rapport har lästs men dess verifieringspåståenden används inte som eget körunderlag.

## Omprövat C2-/C3-godkännande

Ny revisionslåst audit: [review.py](../research/audits/momentum-c406-9174b9c/review.py) och [verification.json](../research/audits/momentum-c406-9174b9c/verification.json). Produktionskällor hämtas med git show från fullständiga låsta revisioner, med matchande ledger- och signalberoenden i minnesmoduler. Källhashar sparas för granskad revision, diffbas och 4241d0e. `--check` räknar om och jämför hela JSON-underlaget.

De tidigare oberoende C2-/C3-referenserna återanvänds i minnet från revisionslåsta auditkällor; gamla auditfiler skrivs inte om. Den giltiga jämförelseversionen sätts till 4241d0e och granskad version till 9174b9c:

- **400 funding-/stressfall** mot 50-siffrig Decimal-referens: long/short/platt, båda räntetecken/noll, betalningsstyrd stress, avstämning och deduplicering. Hela returnerade konto/state/record är exakt identiska mellan 4241d0e och 9174b9c.
- **400 riskbeslut** mot den tidigare fristående beslutstabellen: midnatt/mellangräns, peak, dagskapital, dags-/permanentstopp, lås, cap, platt signal, band och terminalprioritet. Hela returnerade state/record är exakt identiska mellan revisionerna.
- Referensernas övriga kontroller passerar på 9174b9c: **250 C1-Decimalfall**, **15 fas-/tidsfall**, **22 ogiltiga fundingstate-konstruktioner/replace**, fyra återställda samlingstyper med dubbelbokningskontroll, fem felaktiga källtyper och separat scenario; C3:s likviderade terminal-/midnattsförlopp, levande terminal med kostnad 80, **39 ogiltiga signalkontroller** samt Python-/numpy-bool.

Det återställer komponentgodkännandena efter den kända felkontraktsbristen. Full event-/funding-/marginalordning och konservativ intrastapel-bound prövas inte genom denna rättning.

## Körda kontroller

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Båda pytest-körningarna utfördes från `engine/` med `-m pytest -p no:cacheprovider`.

- Fem momentumtestfiler: **402 passerade** (36 signal, 82 ledger, 100 funding, 111 risk, 73 marginal), exit 0, 1,01 s.
- Hela motorsviten: **955 passerade**, exit 0, 97,00 s. En joblib-varning om fysisk CPU-detektering, inga testfel.
- A1-oraklet med `--check`: PASS.
- Samtliga **16 tidigare** `research/audits/momentum-*/review.py --check`: PASS utan ändringar. Den nya auditen med `--check`: PASS. Historiska audits reproducerar avsiktligt sina historiska fynd; deras PASS är inte ett godkännande av felaktig historisk kod.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändring. Momentumchecklistan regenererad med python3; alla fyra kontroller passerar även efter uppdateringen. `git diff --check`: rent.

## Status och avgränsning

MOM-C02 återställs till **done** med nytt revisionslåst underlag för C4-06 och oförändrade giltiga C3-beslut. MOM-C01 behåller sitt tidigare godkännande för oförändrad ledger. MOM-C03/C04/C05 förblir **in_progress**, med uppdaterade reservationer: C4-06 är stängt, men full integration och intrastapel-bound återstår. Checklistan blir **12/40**.

H-0013 förblir REJECT. H-0016:s separata protokoll och status är oförändrade. Ingen marknadshistorik har lästs, inga nätverksanrop gjorts, och ingen registrering, merge, driftsättning, release eller paper/live-start har genomförts. Inget har committats eller pushats. Nästa del väntar på Edwins beslut.
