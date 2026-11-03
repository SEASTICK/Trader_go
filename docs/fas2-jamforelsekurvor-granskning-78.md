# Jämförelsekurvor H-0013 – granskning av PR #78

Granskad head: `db9a4ec1866e0727510abbc3101ebd2620fc56d0`, kod `e42c534`, gren `fas2-jamforelsekurvor`.
PR: https://github.com/SEASTICK/Trader_go/pull/78. Granskning 2026-11-03, i en isolerad kopia av exakt denna commit.

## Fynd

### P1 – den nya publika kurvingången saknar utvecklingskontroll

`engine/traderlab/fas2_eval.py:178–195`: `comparison_curves` kontrollerar bara att serierna har samma index. Därefter beräknar den kapital, kontrollsummor och exporterade kurvor även för slutprovsperioden. Detta öppnar åter ett direkt anrop utan modulens dokumenterade skydd före beräkning. Normalflödet via `evaluate` har fortsatt kontroll; fyndet gäller den nya direkta ingången.

Oberoende prov med enbart syntetiska avkastningar `[0.1, 0.2, 0.3]` på tre 4H-tidpunkter från 2025-01-01 UTC gav kapitalkurvan `[1.1, 1.32, 1.716]` i stället för avvisning. Samma sak hände med datum från 2019 respektive ett tidsindex utan UTC. Ingen riktig slutprovsdata användes.

Använd den befintliga utvecklingskontrollen först, för huvudserien och varje tillförd jämförelse, innan kapital eller hash räknas. Behåll den tillåtna perioden. Testa direkt med syntetiska förbjudna datum, index utan UTC och tom jämförelsesamling; verifiera med spion att ingen beräkning sker när indata avvisas.

### P2 – läsaren godkänner ogiltiga och missvisande tidsaxlar

`app/src/features/research-engine/h0013.ts:103–125`, anropet på rad 197: tidsaxeln måste bara innehålla minst två strängar. Datumen tolkas inte och varken ordning, dubbletter, UTC eller tillåten testperiod kontrolleras. Samma antal värden som datum räcker för att en kurva ska beskrivas som på samma staplar.

Ett separat Vitest-prov ändrade endast `payload().curves.comparisons.t` i PR:ens syntetiska fixtur. Alla dessa fyra axlar accepterades av `readResult` med sex kurvor utan problem:

- `["x", "y", "z"]`;
- tre identiska UTC-tidpunkter;
- tre giltiga UTC-datum i fallande ordning;
- tre UTC-datum i januari 2025, trots `holdout_loaded=false`.

Den befintliga testningen av ogiltig tidsaxel provar bara saknat fält, fel typ och en lista med en enda punkt. Det fångar inte exemplen ovan. Dessutom jämförs inte tidsaxeln med resultatets ordinarie H-0013-kurva. PR:ens fixtur har redan jämförelsedatum som inte finns i dess ordinarie kurva; den kan därför inte verifiera kopplingen mellan dem.

Validera faktiska UTC-tidpunkter, strikt stigande och unika, inom de tillåtna OOS-fönstren och på rätt stapelrutnät. Kontrollera att de utvalda tidpunkterna motsvarar huvudresultatets staplar, samt att jämförelsediagrammets H-0013-värden stämmer med huvudkurvan vid dessa tidpunkter med dokumenterad avrundningstolerans. Hantera fel som saknade kurvor med förklaring, utan att dölja övriga giltiga nyckeltal. Rätta fixturen så att dess två representationer faktiskt är samma serie.

### P3 – gränsen 1 500 punkter kan överskridas

`engine/traderlab/fas2_eval.py:185–189`: urvalet kan redan ha 1 500 punkter innan slutpunkten läggs till. Ett oberoende prov med 3 000 syntetiska 4H-avkastningar från 2022 gav **1 501 punkter** med standardgränsen. Det avviker från J3 och leveransbeskrivningen. Det nya testets tillåtna `<=1501` låser inte det utlovade kontraktet.

Reservera plats för slutpunkten eller använd ett begränsat gemensamt urval. Testa precis vid gränserna och behåll första/sista punkt, samma index för alla serier samt högst 1 500 punkter. Detta är ett mindre storleksfel och påverkar inte kriterierna.

## Oberoende verifiering

- **541 Python-testfall passerar** på exakt head. Ofarlig lokal joblib-varning om identifiering av fysiska CPU-kärnor kvarstår.
- **105 frontendtestfall passerar**, och `npm --prefix app run build` lyckas. Vite rapporterar befintlig varning om stor huvudbundle.
- Både App check och Engine check är gröna på samma head. Grön CI fångar inte fynden ovan.
- PR #77 är mergad i `de70580`; dess app-/motorkod är oförändrad jämfört med godkänd `677752f`.
- De fem jämförelserna beräknas från samma fönster och avkastningsindex som huvudresultatet. Urval och SHA-256 bygger på hela respektive avkastningsserie. Slutvärden och befintliga hash-/pakettester passerar.
- Separat före/efter-prov körde utvärderingen från `de70580` och `db9a4ec` på samma syntetiska utvecklingsdata, fast BB-spelbok för att få affärer, noll permutationer och tre kontrollspelböcker. Bortsett från det nya fältet `comparison_curves` var hela serialiserade resultatet identiskt: SHA-256 `0159f807d84d865ff0513a454eb397f2be43976a9ea1139f434aef0aac4c0595`. Detta är kodregression, inget strategiresultat.
- AST-jämförelse visar att befintliga funktioner i `fas2_eval.py` är oförändrade utom de uttryckliga tilläggen i `evaluate`. I `h0013.py` ändras bara `result_payload`, genom tillägg av jämförelsekurvor och borttagning av den duplicerade kopian. Befintliga avbrotts-, slutprovsskydds-, kriterie- och workertester passerar.
- Lokal Chrome-förhandsvisning av jämförelsekortet, tydligt märkt syntetisk: ljus/mörk vy inspekterad och byte från köp-och-behåll till likaviktad blandning fungerar. SVG saknar NaN/Infinity. Detta är inte test i installerad Mac-/Windows-app eller mot riktig inloggad kö.
- Ingen riktig data eller skyddat slutprov lästes. Inget jobb köades, ingen merge eller driftsättning gjordes och inget publicerades. Protokoll, frysta resultat, REJECT och H-0014/H-0015 är orörda.

## Checklista och beslut

**Inte godkänd för merge ännu.** Rätta P1 och P2; rätta även den lilla avvikelsen mot J3 i samma leverans.

F2-501 återöppnas för den nya oskyddade jämförelseingången. F2-704 förblir `in_progress`. De övriga verifierade punkterna i arbetsområde 5–6 behålls efter diffgranskning, före/efter-prov och passerande regressioner. Det är inte ett blanketgodkännande av nytillkomna funktioner. Gemensam status: **33 av 40 verifierade**.

F2-605 beskriver den tidigare verifierade driftsättningen `dee88eb`, som saknar jämförelsekurvorna. En framtida release behöver granskas och driftsättas separat före användning av den nya exporten. Ingen riktig H-0013-körning eller strategi har godkänts för papper/live. Nästa kontroll är omgranskning av rättade dataingångar och kurvkontrakt på syntetiska data.
