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


## Omgranskning av rättningarna – 2026-11-03

Granskad head: `08a8966349cfc25137038c747c749615e215ae5f`, rättningskod `fec2e51`, synk av Codex underlag `6cd6649`. Fynden och den ursprungliga bedömningen ovan bevaras som historik; samtliga tre fynd är nu rättade.

- **P1 rättad:** `comparison_curves` kontrollerar utvecklingsperiod och UTC för huvudserien och varje tillförd jämförelse före beräkning. Egna direkta prov med syntetiska datum från 2025 respektive 2019, index utan UTC och en förbjuden jämförelse avvisas med ValueError. Spioner på både `Series.cumprod` och hashfunktionen visar att ingen sådan beräkning nås. Även huvudserie med tom jämförelsesamling kontrolleras.
- **P2 rättad:** appen kräver UTC-format, ändliga tidpunkter på 4H-rutnätet, strikt stigande unika datum och OOS-perioden 2022–2024. Varje utvald tidpunkt kopplas till huvudkurvan; jämförelsediagrammets H-0013-värden kontrolleras mot huvudkurvan med dokumenterad relativ tolerans 1e-6. Fixturens huvud- och jämförelseserie är nu konsekventa. Eget separat Vitest-prov av de fyra ursprungliga axlarna avvisar samtliga och behåller huvudnyckeltalen. Regressionerna täcker även saknad huvudkurva, fel rutnät/tidszon, tidpunkt som saknas i huvudkurvan samt avvikande värden och tillåten avrundning.
- **P3 rättad:** gemensamt jämnt fördelat indexurval reserverar ändpunkterna inom budgeten. Egna prov med 2, 1499, 1500, 1501, 3000 och 10957 staplar ger högst 1500 unika stigande index med första och sista kvar. 3000-fallet ger exakt 1500. Samma urval används för alla kurvor.
- Exakt head körd i isolerad kopia: **553 Python-testfall och 118 frontendtestfall passerar**, och appbygget lyckas. Tidigare ofarliga joblib-/bundlevarningar kvarstår. App check och Engine check är gröna på samma head.
- **Extra integrationsprov utan riktiga data:** motorn kördes på syntetisk utvecklingsdata med fast BB-spelbok för affärer, noll permutationer och tre kontrollspelböcker. Workerns faktiska `result_payload` skapade paketet, som därefter lästes av appens faktiska `readResult`. Alla sex kurvor och deras 1500 punkter accepterades utan tidsaxel- eller värdefel. Det är en lokal kontraktskontroll, inte ett inloggat app–Supabase–worker-test eller ett strategiresultat. Två separata granskningsfall i Vitest passerar utöver projektets 118 tester.
- Chrome: giltigt syntetiskt jämförelsekort i ljust tema samt felmeddelandet för ogiltig tidsaxel i mörkt tema inspekterade. Ingen installerad app, riktig kö eller server ändrades. Den tidigare ljus/mörk-granskningen av själva diagrammet gäller fortsatt.
- Rättningarna ändrar inte `evaluate`, workerns paketering, kandidater, kriterier eller handelslogik jämfört med föregående granskning. Tidigare före/efter-prov och nya passerande regressioner behåller övriga verifieringar.

**PR #78 är kodmässigt godkänd för merge på `08a8966`, med grön CI och bevarad granskad kod.** F2-501 återgodkänns och F2-704 markeras klar: **35 av 40 verifierade**. Inga öppna fynd från granskningen återstår.

Nästa steg är merge med den senaste checklistestatusen bevarad, därefter ett reproducerbart releasepaket och konkret uppdaterad driftsättningsplan för separat driftbeslut. Nuvarande worker `dee88eb` saknar fortfarande kurvorna. Arbetsområde 8 återstår: relevanta slutkontroller, riktigt appflöde, installerad Mac, Stable och slutbedömning. Ingen riktig H-0013-körning, slutprovsåtkomst, merge, driftsättning eller publicering har utförts i denna omgranskning. Inget strategiresultat är godkänt för papper/live.


## Slutpaket och uppgraderingsplan – PR #79

2026-11-03: mergecommiten `b44d3cecaac6e05077c8ce2c74acf73a8455d0d8` är kontrollerad mot godkänd `08a8966`; app-/motorkod är oförändrad. PR #79:s plan granskad på `8d85c10176b5ba28522a522cb567baed2cdf39bb` via hela diffen.

Eget bygge från mergecommiten ger `tradergo-research-b44d3cecaac6.tar.gz`, SHA-256 `015c190c5e9819c0d53795468dc00d551f23edbf78bc094fce34d8d6a46823f0`, identisk med leveransen. Egen uppackning och `verify-research-release.py` verifierar 186 filer och rätt revision.

Mot driftsatt `dee88eb` ändras bara `fas2_eval.py` och `research_engine/h0013.py` bland motorns produktionsfiler. Migrationer, tjänster, beroenden och paketverifierare är oförändrade. Därför behövs ingen SQL-migration eller ändring av den delade venv-miljön. Återgång till `tradergo-research-dee88eb65196` behåller 0005 och samma kökontrakt; äldre kod saknar enbart jämförelsekurvorna.

Planen är godkänd som underlag för Edwins driftbeslut. Före ändring ska faktisk serverrevision, ledig kö/slot, ny verifierad egen export samt senaste lyckade backup kontrolleras. DigitalOcean har enligt tidigare uppgift veckobackup; ett nytt backupdatum samma dag kan därför inte förutsättas. Redovisa faktisk backupålder enligt den befintliga frekvensen. Kontrollera exakt en worker, revision, databaskontrakt och marknadsinsamling efter installation; backa vid misslyckad kontroll. Om en oväntad H-0013-körning finns, avbryt uppgraderingsförberedelserna och rapportera den utan att själv starta eller avbryta forskning.

Ingen server har kontaktats eller ändrats i denna paket-/plangranskning. Detta är inte genomförd uppgradering, inte godkännande att starta H-0013 och inte en Stable-publicering. Status kvarstår på **35/40**.
