# En forskningsbaserad efterföljare till H-0013

Datum: 2026-11-03. Leverans: nätbaserad litteraturgenomgång och en sammanhängande genomförandeplan. Detta är ett förslag till en ny modell, inte en ändring av det frysta H-0013-protokollet, en registrering eller ett lönsamhetsresultat. Ingen historisk körning, implementation, driftsättning eller publicering ingår.

## Rekommendationen

Bygg en riskstyrd momentummodell för BTCUSDT, med tre fasta tidshorisonter och en gemensam målposition. Återanvänd TraderGO:s dataflöde, resultatsystem, kö, worker och diagram. Ersätt H-0013:s historiskt tränade val mellan EMA, BB/RSI och platt med en fast sammanvägning av trendinformation. Låt risklagret anpassa hur mycket virtuellt kapital som exponeras.

Målet är positivt netto efter realistiska kostnader, bättre riskjusterat utfall än förregistrerade jämförelser och högst cirka 20 % uppmätt drawdown. Forskningen bevisar inte att denna exakta modell klarar målet. Förbättringen får mätas; resultatkraven får inte sänkas för att undvika REJECT.

H-0013 förblir REJECT. H-0016 är en separat förregistrerad squeeze-hypotes och ändras inte till denna modell. Den räknas fortsatt som ett försök även om arbetet här prioriteras först. Ett nytt id och en registreringscommit krävs före en körning av den föreslagna efterföljaren.

## 1. Diagnosen som planen ska lösa

Den sparade H-0013-granskningen visar −10,864 % netto och fem affärer. Bara en av 48 kandidat/läge/fönster-bedömningar kvalificerade sig i träningen; 46 av 48 hade färre än 20 affärer. Kandidatvalen styrdes därför av mycket litet underlag. Bedömningarna överlappar och är inte oberoende försök.

Källa: [den reproducerbara diagnosen](strategiforskning-20261103.md) och [resultatgranskningen](fas2-h0013-granskning-20261103.md).

Planen tar bort själva behovet att uppskatta en vinnare i fyra små delmängder. Den sänker inte H-0013:s affärskrav. Fler signaler eller dagliga datapunkter betyder heller inte fler oberoende observationer eller automatiskt högre statistisk styrka.

## 2. Forskningsunderlag och dess gränser

### Momentum som utgångspunkt

Liu och Tsyvinski rapporterar tidsseriemomentum i kryptovalutor i sin ursprungliga studie. Det ger en grund för att undersöka fortsättning i prisrörelser, men deras resultat och handelsregel är inte vår föreslagna 7/14/28-dagarsmodell. Studien är historisk och bevisar inte lönsamhet på dagens BTC-marknad. [Risks and Returns of Cryptocurrency, NBER, 2018; publicerad RFS 2021](https://www.nber.org/papers/w24877).

### Anpassa risk utan att passa in framtiden

Moreira och Muir finner förbättringar av volatilitetshanterade portföljer i andra tillgångar. Deras huvudsakliga regel använder invers föregående varians. Vår föreslagna volatilitetsmålsättning nedan använder invers standardavvikelse, en annan konstruktion som måste testas separat. Ingen skalningskonstant får räknas från hela testperioden. [Författarens publicerade artikel, 2017](https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf).

Cederburg med flera finner att volatilitetshantering inte systematiskt slår motsvarande ursprungliga portföljer, och att historiska förbättringar kan utebli utanför urvalet. Därför innehåller planen en obligatorisk jämförelse utan det nya risklagret. [University of Arizona: On the performance of volatility-managed portfolios, 2020](https://experts.arizona.edu/en/publications/on-the-performance-of-volatility-managed-portfolios/).

### Handel måste löna sig efter kostnad

Gârleanu och Pedersen visar hur omsättning och kostnader ska vägas mot signalens förväntade nytta. Deras optimala lösning är inte vårt föreslagna fasta handelsband. Studien ger stöd för att göra kostnadsstyrning till en del av konstruktionen; inte för att just två procentenheter är optimalt. [Dynamic Trading with Predictable Returns and Transaction Costs, publicerad 2013](https://www.nber.org/papers/w15205).

Fieberg, Liedtke och Zaremba finner i en kryptostudie att ekonomiska begränsningar, kostnader och tidsperiod påverkar anomaliernas användbarhet. Resultaten gäller främst tvärsnittsstrategier och är inte en direkt prövning av vår BTC-modell. De motiverar konservativa kostnader och särskild uppföljning på ny data. [Cryptocurrency anomalies and economic constraints, 2024, författararkiv](https://open.icm.edu.pl/handle/123456789/25544).

### Undvik att leta fram ett snyggt backtest

Bailey och López de Prado visar hur urval bland många tester och icke-normal avkastning kan blåsa upp Sharpe. Vi ska därför låsa en huvudmodell och redovisa sökhistorik och Deflated Sharpe, inte optimera tills en variant passerar. [Författarnas artikel, 2014](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf).

### Aktuell litteraturkontroll

Jag granskade även Borri, Liu, Tsyvinski och Wu, [Coming of Age, oktober 2025, preprint](https://arxiv.org/html/2510.14435v1). Den behandlar bland annat få faktorer och stora hopp i kryptopriser. Tvärsnittsfaktorer där är inte bevis för vår enskilda tidsseriestrategi. Artikeln använder också data från 2025: externa aggregerade forskningsresultat har alltså lästs, men TraderGO:s skyddade marknadsarkiv har inte öppnats. Detta ska finnas med i redovisningen av vad som varit känt när nästa hypotes valdes; slutlig bekräftelse bör också kräva verkligt framtida observation efter frysning.

## 3. Den enda föreslagna modellen

Följande siffror är konkreta designval att förregistrera och granska, inte empiriskt bevisade optimala parametrar. Ingen parameterlista eller grid search ingår.

| Del | Föreslagen fast regel |
|---|---|
| Marknad | Binance USDⓈ-M BTCUSDT, long eller platt, ingen short och ingen hävstång över 1× |
| Data | 4H-staplar för utförande; kompletta UTC-dygn för signal och volatilitet |
| Tidshorisonter | 7, 14 och 28 kalenderdagar |
| Delsignal | 1 om dagens stängning är högre än stängningen för h dagar sedan, annars 0 |
| Sammanvägning | Lika vikt: (signal7 + signal14 + signal28)/3 |
| Volatilitet | Standardavvikelse (ddof=1) för de senaste 60 kompletta enkla dagsavkastningarna, annualiserad med sqrt(365) |
| Risknivå | 10 % årlig målrisk som fast skalningsparameter, inte garanterad faktisk volatilitet |
| Målposition | signalmedel × min(1, 0,10/uppmätt årsvolatilitet) |
| Handelsband | Normal ombalansering bara när skillnaden mot aktuell kapitalvikt är minst 2 procentenheter |
| Kostnader | Befintliga 16 bp per sida: avgift 10, halv spread 1 och slippage 5; funding ingår |
| Startkapital | 100 000 virtuella enheter; outnyttjat kapital ger noll ränta |

Ogiltig volatilitet, ofullständiga dagar eller otillräcklig uppvärmning ger ingen ny position. Tre signaler på samma BTC är korrelerade; de är inte tre fristående tillgångar eller tre oberoende bevis.

Exempel: två positiva signaler av tre och 60 % uppmätt årsvolatilitet ger målvikten (2/3) × (10/60) ≈ 11,1 % av kapitalet. Det är ett räkneexempel på exponering, inte en avkastningsprognos.

Modellen väljer därmed kontinuerligt en storlek mellan platt och den tillåtna exponeringen. Den försöker inte hitta en historisk vinnare bland 81 spelböcker. Ingen tre-dagarshysteres eller automatisk full stängning bara för att ett gammalt regimnamn byts ingår. Regimetiketter kan visas som diagnostik men påverkar inte handeln.

## 4. Exakt beslut, utförande och kostnadsbegränsning

1. Vid UTC-dygnets sista 4H-stängning beräknas målvikten från bara färdiga dagar. Första möjliga fyllning är nästa 4H-öppning. Ingen egen dagsstängning används tidigare under dygnet.
2. Den aktuella vikten beräknas från faktiska simulerade enheter och nettokapital. En dag utan handel behåller antalet enheter; konstant målvikt får inte orsaka dold kostnadsfri ombalansering.
3. Om den normala viktförändringen är mindre än 2 procentenheter behålls positionen. Annars handlas skillnaden till målet, inte en full utgång och återöppning. En normal ombalansering per UTC-dygn tillåts.
4. Platt signal, överskriden riskgräns eller vikt över den dagsaktuella volatilitetsgränsen får minska/stänga exponering oavsett handelsband. Bandet får aldrig blockera en säkerhetsåtgärd. Nödstopp stänger aldrig på ett gammalt pris.
5. Eventuell ytterligare riskutgång samma dygn loggas separat; inga nya inträden efter ett dagsstopp. Varje utförd delaffär har kostnad på faktiskt handlat belopp. Funding beräknas på den position som faktiskt finns vid avräkning.
6. Ingen ATR-stop eller take-profit läggs till i detta förslag. Riskutgångarna nedan ingår i stället i den enda låsta modellen. Det är en annan hypotes än H-0016:s stopbaserade squeeze.

## 5. Risklagret

| Gräns | Föreslaget beteende |
|---|---|
| Exponering | Högst 1× vid köp och ytterligare begränsad av volatilitetsregeln; en longposition, inga lånade tillgångar eller pyramidering |
| Dagsförlust | 2 % av dagens ingående nettokapital: nästa möjliga öppning stänger, inga nya positioner resten av UTC-dygnet |
| Permanent stopp | 15 % drawdown från nettokapitalets högsta uppmätta stapelstängning: stäng vid nästa möjliga öppning och förbli platt till forskningskörningens slut |
| Godkännandemål | Högst 20 % maximal uppmätt nedgång, även med konservativ intrastapelkontroll |
| Dataproblem | Blockera nya köp; logga fel. Ingen tyst framåtfyllning eller fyllning på gammalt pris |
| Ändringsrätt | Riskvärden låses före körning. Ingen automatisk riskhöjning; ändrad regel är ett nytt försök |

Dag- och drawdown-kontroller körs vid varje 4H-stängning och inkluderar orealiserat resultat, avgifter och funding. Intrastapelrisk redovisas separat från den beslutsklockan. Vid gap eller större rörelser kan 15 %-stoppet fyllas efter att 20 % passerats. Målvolatilitet och drawdown är olika mått; 10 % målrisk garanterar inte 20 % maximal nedgång.

Terminsmodellen måste granskas mot relevant mark-price, funding och marginalregler. Om nödvändig mark-price-historik saknas är det en uttrycklig begränsning som måste lösas eller avgränsas före godkännande för drift. Inga börsnycklar eller riktiga order behövs för forskningen.

## 6. En reproducerbar validering

### Före körning

- Registrera efterföljaren under ett nytt ledigt id. Behåll H-0013 och H-0016 oförändrade. Frys hela denna modells exakta kontrakt efter kod-/metodgranskning och före marknadsdatautvärdering.
- Räkna N från alla registrerade försök vid registreringen och lås t-kravet då. Dokumentera också tidigare parametersökningar separat; en ny beteckning gör inte forskningens sökhistorik osedd.
- Lås filmanifest och datahash för 2020–2024. Skyddet mot 2025 gäller alla publika ingångar, även jämförelser, volatilitet och funding. Ny mark-price-data får eget tilläggsmanifest; gamla manifest ändras inte.
- Fastställ en slutstängning inom utvecklingsperioden för huvudmodell och samtliga jämförelser. Ingen jämförelse får använda första öppningen från 2025.

### Utvecklingskörning

2020–2021 används för uppvärmning och tekniska kontroller, utan att välja vinnande parametrar. Modellen bedöms på en sammanhängande kurva 2022–2024 med sex halvårsrapporter. Nettokapital, positioner, högvattenmärke och permanent stopp följer med mellan halvår; inga konstgjorda omstarter av riskbudgeten.

Detta är en kausal kronologisk utvärdering av en fast modell, inte sex nytränade modeller. Perioden 2022–2024 är redan sedd i projektet och får inte kallas ren slutvalidering. Fler år från samma redan granskade historia kan inte i efterhand göras orörda.

### Obligatoriska kontrollkörningar

Huvudmodellen jämförs på exakt samma tidpunkter, startkapital och kostnadsmodell med:

- köp-och-behåll;
- de gamla EMA/ADX- och BB/RSI-kandidaterna var för sig samt deras ursprungliga 50/50-blandning;
- var och en av de tre nya momentumsignalerna ensam, med samma grundläggande utförande och riskregler;
- samma fasta signalblandning utan volatilitetsstyrning, men med samma nödstopp och exponeringsgräns;
- en förutbestämd 1/3-blandning av de tre nya komponenterna med separata initiala kapitalandelar utan löpande återställning till lika vikter.

Kontrollerna är till för attribution och jämförelse, aldrig en meny där den efteråt bästa kontrollen utses till ny huvudmodell. De räknas och sparas i försöksloggen. Blandningen utan ombalansering är inte matematiskt identisk med en dagligen sammanvägd målposition; detta måste kontrolleras i implementationen.

Kör huvudmodellen också med 2,5× handelskostnader, med omräknat riskförlopp. Separat fundingstress dubblar betald funding utan att dubbla mottagen funding. En förutbestämd stresstestfördröjning på en extra 4H-stapel redovisar känslighet för försenad fyllning. Stresser används inte för efterhandsval av parametrar.

### Kriterier att låsa före start

Alla nedanstående krävs för MORE_RESEARCH; annars REJECT vid en giltig, fullständig körning:

1. Positivt netto med normala kostnader och med 2,5× handelskostnader.
2. t (Newey-West på dagsavkastning) når det nya försöksantalets Bonferroni-krav, aldrig lägre än H-0013:s 2,67.
3. Sharpe över köp-och-behåll på samma instrument, period och utförandekonventioner.
4. Sharpe över den bästa ensamma kandidaten bland de i förväg listade gamla och nya komponenterna.
5. Sharpe över båda de förregistrerade blandningarna: gamla EMA/BB 50/50 och nya komponenternas fasta 1/3-blandning.
6. Maximal drawdown högst 20 % på huvudkurvan och den konservativa intrastapelkontrollen; ingen likvidation eller riskregelöverträdelse.

Datafel och ofullständiga körningar märks ogiltiga/avbrutna och sparas; de får inte bli MORE_RESEARCH eller presenteras som ekonomiskt bevis för/ emot strategin. Det är ingen sänkning av H-0013:s krav och inget försök att flytta den till ett lättare spår efter resultatet. Den nya modellens riskgräns är ett ytterligare villkor.

Redovisa dessutom bootstrap-intervall, DSR med dokumenterad hantering av testernas beroende, årliga resultat, resultat utan bästa året, exponering, omsättning och kostnadsbidrag. Vid alltför lite effektivt underlag krävs längre observation, inte fler konstgjorda affärer eller ett sänkt t-krav.

### Slutprov och framåttest

Bara efter ett granskat MORE_RESEARCH tas ett separat beslut om ett enda fryst slutprov. Ny kod får inte användas för att förhandsläsa den skyddade perioden. Den slutliga bekräftelsen behöver dessutom ett fryst framåttest i minst tre månader och tillräckligt antal affärer enligt en i förväg angiven slutregel. Tre månader är ett minimum för driftobservation, inte en garanti för tillräckligt statistiskt underlag.

## 7. Genomförande i TraderGO, i ordning

1. **Metodkontrakt:** lås regler, referensportföljer, riskdefinitioner, försöksräkning och gränser; registrera nytt id. Leverans: förregistrerat protokoll och granskningsbar commit.
2. **Ren signalmodul:** implementera 7/14/28-dagars signaler, 60-dagars volatilitet och lika vikter; ingen marknadskörning. Leverans: versionerat kontrakt och syntetiska tids-/lookahead-tester.
3. **Utförande och risk:** implementera enhetsbaserade delaffärer, band, nettokapital och stopp. Återanvänd befintlig kärna där semantiken stämmer; befintligt risk_overlay på bruttoserie får inte återanvändas oförändrat. Leverans: handräknade prov för gap, kostnader, funding, band och samtidiga riskhändelser.
4. **Utvärderare:** alla jämförelser och stresser, gemensamma perioder, resultatkontrakt och oberoende avstämning. Leverans: tester som skiljer huvudmodell från matematiskt liknande blandningar.
5. **Körväg:** separat registrerad jobbtyp med korrekta gränser i kö och worker, granskad migration om en behövs, versionsmärkt paket och återgång. H-0013:s låsta RPC får inte användas under fel id. Ingen sådan driftåtgärd ingår i denna planleverans.
6. **En låst utvecklingsutvärdering:** spara även fel och avbrott, granska alla kriterier och redovisa utfallet utan parameterändring efteråt.
7. **Granskat nästa beslut:** REJECT bevaras vid underkänt; MORE_RESEARCH kan gå till separat slutprovsbeslut och först därefter eventuell READY_FOR_PAPER. Fas 3:s pilot startar inte genom att denna plan skrivs.

En ny modell kan fortfarande bli REJECT. Den konkreta förbättringen i konstruktionen är mindre beroende av små historiska delgrupper, direkt kostnadsstyrning och ett explicit riskmål. Om detta också förbättrar nettot är den fråga experimentet ska besvara.
