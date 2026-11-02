# Utvärdering H-0013 – granskning av PR #72

Granskad PR-head: `efb43fc89932f40e38ad318f1f53d6eb7be51da0`, kod `bbc7181`, metodtolkningar `976c22a`, gren `fas2-utvardering`. PR: https://github.com/SEASTICK/Trader_go/pull/72.

Bara syntetiska data och isolerade tillfälliga resultatfiler har använts. Inget riktigt dataset eller slutprov har lästs, och ingen merge, driftsättning eller publicering görs i denna granskning.

## Fynd före merge

### P1 – direkt permutationstest beräknar regimer innan slutprovsskyddet

`engine/traderlab/fas2_eval.py:136–147`: `permutation_test` anropar `regime.daily(bars)` före kontrollen i `fas2.walk_forward`. Ett direkt anrop med förbjudna staplar kan därför behandla slutprovet, trots att huvudflödet `evaluate` har korrekt kontroll. Med n=0 nås ingen walk-forward-kontroll alls. `regime_results` på rad 118–124 beräknar också regimer direkt utan utvecklingskontroll.

Oberoende prov: syntetiska 4H-staplar 2025-01-01–2025-01-02 skickades till `permutation_test(..., n=1)`. En spion på `regime.daily` avbröt med `RuntimeError: regime calculation called before guard`, i stället för att slutprovskontrollen avvisade indata. Ingen riktig slutprovsdata användes.

Lägg utvecklingskontrollen före all beräkning i de nya publika ingångar som tar staplar/funding/dagslägen. Testa dem direkt med förbjudna staplar, funding och tillförda etiketter där sådana parametrar finns, samt med n=0 för permutationstestet. Bevisa att regim-, statistik- och kandidatberäkning inte anropas vid avvisning. Ändra inte skyddets tillåtna period eller arkivbegränsningen.

### P2 – blandningens position och riskrapportering motsvarar inte dess kapitalvikter

`engine/traderlab/fas2_eval.py:103–115` sätter blandningens position till `0.5 * (a.position + b.position)`, trots att delportföljerna får växa var för sig utan ombalansering. Kurvan och affärsbeloppen blandas däremot korrekt. `summary` på rad 79–94 använder denna felaktiga position för exponering och omsättning.

Oberoende kontrollerade prov:

- En long-delportfölj med kapital 2 och en platt delportfölj med kapital 1 får position 0,5. Nettoposition som andel av det aktuella totalkapitalet är 2/3.
- Två fullt investerade halvor med motsatta riktningar rapporteras som exponering 0 och position 0 överallt. Det kan beskriva nettoriktningen när kapitalen är lika, men döljer att båda delportföljerna har öppna positioner. Det är inte samma exponeringsmått som tid med aktiva affärer eller bruttoexponering.

Behåll den korrekta oombalanserade kurvan och skala positionerna med respektive delportföljs aktuella kapital på samma tidpunkt som positionen avser. Redovisa netto-/bruttoexponering och eventuell tid i marknaden med tydliga definitioner. Räkna omsättning från delportföljernas utförda affärer/omsättning på gemensam kapitalbas, så att motsatta affärer inte tar ut varandra och passiv viktförändring inte felaktigt blir handel. Regressioner ska omfatta olika kapitalutveckling, long/platt, long/short och oförändrade signaler utan ombalansering. Kontrollera att avkastning, Sharpe, affärsbelopp och beslutskriterier inte ändras av rättningen av riskrapporteringen.

### P2 – avbrutna försök tappar alla färdigräknade delresultat

`engine/traderlab/fas2_eval.py:196–242` bygger resultatet först när hela utvärderingen returnerar. `run` på rad 276–288 fångar avbrottet men sparar bara metadata och fel. Därmed uppfylls inte U19:s löfte att spara allt som hunnit räknas.

Oberoende prov: en syntetisk körning avbröts med `KeyboardInterrupt` vid `all_playbooks`, efter att **sju sammanfattningar** (H-0013, stress och fem jämförelser) hade räknats. Den sparade aborted-filen innehöll endast `error`, `evaluation_version`, `hypothesis_id`, `registry_commit`, `run_at` och `status`. Ingen walk-forward, sammanfattning eller jämförelse sparades.

Behåll en progress-/resultatsnapshot under utvärderingen och spara genomförda steg när den avbryts, inklusive färdiga kontrolliterationer om avbrottet sker i en sådan loop. Märk genomförda/ofullständiga steg och spara körningskonfigurationen. Ett avbrutet eller misslyckat försök får fortsatt inget beslut. Regressionstesta avbrott efter huvudresultat, efter jämförelser och mitt i en kontroll, samt att en befintlig fil inte skrivs över. Detta kräver ingen riktig data eller ändring av forskningskriterierna.

## Verifierat och accepterat

- Exakt PR-head kördes i en isolerad arkivkopia: **442 Python-testfall passerar**, inklusive **34 utvärderingstestfall**. CI Engine check är grön på samma head. Lokal joblib-varning om identifiering av fysiska CPU-kärnor påverkar inte testutfallet.
- PR #71 är mergad som `793e9f0`, med `fas2.py` och dess tester oförändrade mot godkänd `c5068e1`.
- Omstruktureringen av walk-forward behåller periodkontroller, sex halvårsfönster, träning före test, platt start, dokumenterad slutstängning, kapital-/affärsavstämning, versionsmärkning och reproducerbarhet. Gamla regressioner passerar.
- Ett separat jämförelseprov mellan `c5068e1` och `efb43fc`, med samma syntetiska data och fast BB-spelbok, ger 35 affärer och exakt samma SHA256 `997697be09c65ba5d6f375906af524ec522a1ba8f0052147d7acd2ef947cb97e` för serialiserad avkastning, affärer, kostnader, funding, slutlig spelbok och fönstrens val. Det är en kontrollerad kodregression, inte ett strategiresultat.
- Jämförelsernas avkastningsserier har exakt samma stapelindex som H-0013. Köp-och-behåll och ensamma kandidater använder uttalade fönsterkonventioner. Blandningens kurva är korrekt medelvärde av de två separata kapitalkurvorna, utan ombalansering.
- Stressen återanvänder de normalt valda spelböckerna med 2,5 gånger avgift/spread/slippage och oförändrad funding. Riskmodellen använder befintlig motor, standard 1× och kandidatens ATR-stop. Det är inte ny validering av börsens exakta mark-price-/likvidationsmodell.
- Bootstrap, Deflated Sharpe med 81 försök, uppräkning av de 81 fasta spelböckerna, regimattribution, år och utan bästa året är implementerade. Tester använder mindre kontrollmängder; ingen full körning med 200 permutationer/81 spelböcker mot riktig data har gjorts eller godkänts här. Runtimeuppskattningen fem minuter är inte mätt i granskningen.
- De fem kriterierna använder registrerat t >= 2,67, strikt positiv stressavkastning och strikt högre Sharpe än de tre jämförelserna. Dagens försökskrav rapporteras separat. Permutationer flyttar kända dagslägen, bevarar okänt, använder frö 0 och kör om urvalet i walk-forward; p-värdet är rapport, inte beslut.
- Normalflödets slutprovsskydd, registreringskrav, exklusiv filskapning och borttaget beslut för avbrutet försök fungerar. Fyndet gäller att delresultaten går förlorade.

Metodtolkningarna U1–U18 kan behållas med ovanstående rättning av riskmått och direkta ingångar. Hela utvecklingsperiodens etiketter används i den förregistrerade permutationens nollmodell; det är ingen kausal produktionsfunktion och får inte användas som en utvärdering av verklig framtida handel. U19 är ännu inte uppfylld. Före riktig serverkörning behöver körningsposten även ha faktisk kodrevision och identifierad dataversion: `registry_commit` identifierar registret, inte körd kod eller använda data. Detta är en spårbarhetskontroll inför den senare jobb-/dataintegrationen.

## Checklista och beslut

F2-401 och F2-403–405 återverifieras efter omstruktureringen. F2-502 och F2-504 är kodmässigt verifierade på syntetisk data. F2-501, F2-503 och F2-505 är `in_progress` för fynden ovan. Gemensam status: **22/40 verifierade**.

**PR #72 är inte godkänd för merge ännu.** Nästa kontroll är rättade direkta dataingångar, kapitalviktad och tydligt definierad riskrapportering samt bevarade delresultat vid avbrott. Inget strategiresultat har bedömts och inget godkänns för papper/live.
