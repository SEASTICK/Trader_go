# Codex omgranskning av H-0017 leverans C5

Datum: 2026-11-04. Exakt revision: **`43b2a4bd26149bb04d77e1ef94113b2b684719a5`**. Diffbas: **`aa81472178c293cb59ed941cf3c39fa0076b1a3e`**, granskningsleveransen för 3f46aa5. HEAD, diffbas och grenen `codex/momentum-c5-review` kontrollerades först; arbetskopian var ren. Endast syntetiska data.

**C5 är GODKÄND inom uppdragets avgränsning. C5-02 [P1] och C5-04 [P2] stängs. C5-01/C5-03 förblir stängda. Inga nya fynd.** Nästa C-del kan tilldelas; inget nytt uppdrag skrivs här. Godkännandet gäller eventkomposition för ett huvudmodellskonto, inte hela leverans C eller ett ekonomiskt strategiresultat.

## Stängda fynd

**C5-02 [P1]: stängt genom borttagen publik återställning.** Den tidigare publika `EngineState.restore` finns inte längre. De publika fabriksmetoderna på EngineState består enbart av `start`; `process_bar` skapar fortsättningen under modulens privata konstruktionsgrind. Direkt konstruktion och `dataclasses.replace` avvisas. Kodgranskningen visar ingen kvarvarande publik fabrik som sammanfogar fristående Account/RiskState. Det låsta startläget, oföränderliga delobjekt och cursorvalideringen bevarar kedjan vid normal API-användning.

Den egna auditen återupprepar det starkare förloppet från föregående granskning: två konton körs genom sex vanliga staplar. Det första får permanent stopp efter close 300 och 220, stänger och har C=159 696,24300559552. Det andra är platt utan stopp. Den gamla publika restore-vägen för riskbytet saknas, replace avvisas och det riktiga nästa steget behåller q=0. Även det tidigare fixturbaserade riskbytet, de tre felaktiga startkontona, kapitalbas 200 000 och funding utan historik kontrolleras. Kapitalbas och historik avvisas dessutom av de privata fixturinvarianterna. Deposit och risk.initial måste båda vara 100 000; ett icke-noll funding_net kräver processed-id.

**Privat fixturväg är acceptabel inom denna avgränsning.** `_fixture` är uttryckligen dokumenterad som privat, endast för syntetiska prov och utanför API:t. Den bevisar inte gemensam proveniens. Auditen visar öppet att ett avsiktligt anrop till denna privata hjälp fortfarande kan blanda riskdelar och ge köp; detta räknas inte som en säker återställning eller som verifierad proveniens. Ett sådant tillstånd kan inte börja en RunLog. Skillnaden mot den underkända revisionen är att användbar offentlig återställning inte längre erbjuds. Python-privathet är en API-gräns, ingen säkerhetsbarriär mot anrop av privata hjälpare, ändring av modulglobaler eller kringgående av frozen-objekt. C5 godkänner ingen sådan användning. Framtida publikt återupptag kräver ett eget förseglat, granskat format; namnbyte tillbaka till publik restore återöppnar fyndet.

**C5-04 [P2]: stängt.** Den gamla publika restore-ingången saknas även för naiv tid. I den kvarvarande privata testvägen körs `_bar_time` före intervalljämförelsen. Naiv Timestamp, NaT och en UTC-tid en millisekund utanför 4H-gränsen ger kontrollerad EventError, utan TypeError och utan ändrade indata. Det är både en borttagen publik felväg och en verifierad rättning av valideringsordningen.

**C5-01 [P1]: fortsatt stängt enligt Edwins dokumenterade tillägg.** Samma 32 oberoende Decimal-fall som i föregående audit har körts mot den nya revisionen: A/B × båda mmr × båda teckenordningarna × med/utan samtidig funding × två low-priser; 16 träffar och 16 utan träff. Separat adverse-underlag, kronologisk bokföring utan träff, olösta mellanhändelser vid träff, historisk funding 500, öppningsfunding och nollställningsjustering stämmer. Okänd träfftid anges utan fabricerad händelseordning. Absorberande noll kontrolleras över midnatt och med privat terminalfixtur. Edwins beslut och det frysta protokollet har inte ändrats.

**C5-03 [P2]: fortsatt stängt inom den publika loggkedjan.** Åtta egna avvisningar omfattar dubblett, lucka, bakåtsteg, främmande konto/scenario, fixturresultat efter start, fixturstart, replace och tillägg efter terminal. Full sekventiell syntetisk horisont verifieras mot separat kalender: **6 576 staplar, 6 577 kapitalpunkter, 1 096 dagar**. Varje källstapel, känd-tid och dag jämförs; start är ingen extra dag.

## Verifierade delar och skalning

Den nya [auditen](../research/audits/momentum-c5-43b2a4b/review.py) bygger vidare på föregående oberoende syntetiska facit, laddar samtliga sex momentumkällor och lokala beroenden med `git show` från fullständig 43b2a4b till separat minnespaket och sparar [verification.json](../research/audits/momentum-c5-43b2a4b/verification.json). Källhashar omfattar även protokoll, register, uppdrag, orakel, beslutsdokument, ordningsnotering, eventtester och status. Exakt diff-fillista krävs. `--check` kör om allt och jämför hela JSON-underlaget. Inga gamla audits ändras.

Utöver ovanstående: **24 Decimal-inträde/exitfall** med A/B, båda mmr, båda kostnaderna och tre basispriser; **två O6-reset/riskutträden**, **två terminalfall**, **sex fundingtidsfall**, gaplikvidation före tänkt räddande fill och **sju kontrollerade grundfelprov** med oförändrat state. E_trade, E_post, målidentitet, avgifter, funding och avstämning stämmer.

O14/O15:s skalning ×100 ändrar varken priser, vikt, band, stoppkvoter, mmr eller kostnadssats. C, q, deposit, peak och day_start skalas tillsammans; storlekslösningen och kostnaderna är homogena i kapital och q. Testernas q-facit är oraklets q ×100 med samma relativa tolerans, och Decimal-formlerna är omräknade. Den egna auditen verifierar **sex skalade handelsfall** (hold, riskreduktion och normal som byter riktning vid båda kostnaderna), samt deras normalisering till ursprunglig skala. Hold kräver fortfarande noll kostnad. Ingen assertionsgren har tagits bort.

Nära-likvidationsfixturen skalar C, q, deposit, realized, peak och day_start ×10, med samma priser. E/MM-kvoten och avståndet till riskstoppen består. Den egna auditen verifierar **fyra skalade marginalfall** vid priser 55 och 62 för båda mmr mot Decimal och originalskalan. Negativt gapkapital/reset i Claudes regression är korrekt omräknat från −5 000/+5 000 till −50 000/+50 000; mellanfunding och adverse-facit har samma faktor. Skalningen försvagar inte proven. De ursprungliga komponenttesterna och oraklen är dessutom byte-oförändrade.

**Åtta egna mutationer fångade, noll missade:** återinförd publik restore, borttagen låsning till 100 000, borttagen fundinghistorikvakt, borttagen A-funding, B på gamla q, reset från framtida open, borttagen startpunkt och borttagen terminalpunkt. Claudes rapporterade mutationsantal används inte som eget verifieringsantal.

## Körda kontroller och integritet

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Båda pytest-körningarna utfördes från `engine/` med `-m pytest -p no:cacheprovider`.

- Momentumtesterna: **507 passerade**, exit 0, 5,58 s; därav 105 eventtester.
- Hela motorsviten: **1 060 passerade**, exit 0, 100,97 s. En joblib-varning om fysisk CPU-detektering, inga testfel.
- A1-oraklet med `--check`: PASS.
- Samtliga **19 äldre** revisionslåsta momentum-audits med `--check`: PASS, inklusive historisk reproduktion av äldre fynd. Ny audit med `--check`: PASS.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusuppdatering. Momentumvyn regenereras och kontrolleras efter uppdateringen; övriga tre statuskällor ändras inte.
- `git diff --check aa81472 43b2a4b` och granskningsleveransens `git diff --check`: rena.

Diffen aa81472..43b2a4b har exakt fem filer: eventmodul, eventtester, Claudes rapport, momentumstatus och momentumvy. Signal, ledger, funding, risk, marginal, deras tester, protokoll, register, gamla resultat och gamla audits är därmed byte-oförändrade. De tidigare komponentgodkännandena kvarstår. Denna leverans ändrar endast den nya auditen, detta granskningsdokument och momentumstatus/vy.

## Status och nästa steg

**MOM-C03 och MOM-C05 är done inom sina angivna huvudmodell-/C5-gränser:** funding, reset, första/sista event, gap, basis, marginal och integrerad riskordning är nu oberoende granskade och verifierade. Detta godkänner inte legacy-orkestrering, jämförelsekonton eller ett helt scenariogrid. **MOM-C04 förblir in_progress:** closebaserade 2 %/15 %-stopp är verifierade men §10.2:s konservativa bound och 20 %-riskkontroll återstår. A/B samt MOM-C01/C02 behåller godkännande. Checklistan blir **14/40**.

Nästa C-del kan tilldelas. Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live godkänns. H-0013 förblir REJECT; H-0016 är oförändrat. Ingen marknadshistorik eller nätverk har använts. Inget har committats eller pushats.
