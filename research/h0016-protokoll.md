# H-0016 – fast squeeze-breakout med begränsad risk

Förregistrerad 2026-11-03 före implementation och körning. Ny hypotes i spår B (lägre risk), med ytterligare gräns från Edwins val av cirka 20 % maximal nedgång. Ingen ändring av H-0012 eller H-0013. Ändringar efter registreringen kräver nytt hypotes-id.

## Hypotes

En fast long/platt squeeze-breakout, med små stopbaserade positioner och ett nettobaserat risklager, ger positiv avkastning efter kostnader, positiv stressad avkastning och betydligt mindre drawdown än köp-och-behåll på BTCUSDT under utvecklingsperiodens testdel.

Vald efter att H-0012 och H-0013 setts. BTC 2020–2024 är redan använd. Ingen del av denna period behandlas som orörd bekräftelse. Ingen extern forskningskälla eller ekonomisk kant har verifierats genom detta protokoll; squeeze-signalen är en prövbar idé om fortsatt prisrörelse efter volatilitetskläm.

## Data och jämförelser

- Binance USDⓈ-M BTCUSDT 4H, samma frysta utvecklingsdataset som H-0013, id `6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c` och dess 120 arkiv. SHA/CHECKSUM och inlästa data verifieras före beräkning.
- Endast [2020-01-01, 2025-01-01) UTC får läsas. Skyddet gäller också finansieringsränta. Slutprovet från 2025 förblir oläst.
- 2020–2021 är endast indikatoruppvärmning. Bedömning från 2022-01-01 till 2025-01-01 exklusivt; inga tränade parametrar.
- En sammanhängande testkurva, startkapital 100 000, platt vid start. Sex halvårsbitar redovisas utan omträning, kapitalreset eller nollställning av riskstopp vid gränsen. Ingen ny affär före första signalstängningen i testperioden. Öppna positioner likvideras vid sista tillåtna öppningen 2024-12-31 20:00 UTC och därefter tas inga nya positioner; ingen 2025-stapel används.
- Jämför med long köp-och-behåll 1× och samma fasta long/platt squeeze vid full storlek utan det nya risklagret, på exakt samma staplar och med samma kostnader, funding och slutstängning. Ingen jämförelse får optimera parametrar. Nollavkastning för platt kontantdel; ingen ränta antas.

## Låst signal

Återanvänd squeeze_breakout 1.0.0:s standardparametrar: n=20, bb_k=2,0, kc_k=1,5, atr_n=14, stop_atr=2,0, allow_short=false. Long när Bollingerbanden lämnar Keltnerkanalen efter kläm och stängningen är över mittlinjen. Ut när stängningen är under mittlinjen eller stopp träffas. Ingen take-profit, short, regimväljare, ML eller optimering.

En ny affär kräver en ny squeeze-release efter den föregående affärens utgång. En gammal signal tas inte upp igen efter stop eller dagspaus. Beslut på stängd stapel och fyllning vid nästa öppning. ATR från signalstängningen; stopavståndet är fast i pris under affären och sätts från fyllningspriset. Gap bortom stoppet fylls vid öppningen, kostnader tillkommer.

## Låst risklager (utanför strategin)

| Gräns | Värde | Kontroll och ändring |
|---|---|---|
| Planerad förlust per affär | 0,5 % av aktuellt nettokapital | Storlek vid signalstängningen: q=min(1, 0,005/(stopavstånd/signalpris + 2×kostnad_per_sida)). Negativa/icke ändliga priser/ATR ger platt. Storleken ligger fast, utan löpande ombalansering. Gap vid nästa öppning kan överskrida budgeten. Ändring kräver nytt id. |
| Position och bruttoexponering | Högst 100 % av kapitalet vid inträde, 1 position, hävstång 1× | Ingen short eller pyramidering. Prisrörelser mellan beslut ändrar marknadsvärdet; ingen dold extra handel för att återställa vikten. Ändring kräver nytt id. |
| Inträden per UTC-dygn | Högst 2 | Även stop-utgång följs av ny signal och ny öppning. Ändring kräver nytt id. |
| Dagsförlust | 2 % av dagens ingående nettokapital | Inklusive realiserat/orealiserat resultat, kostnader och funding. Kontroll vid stängning; stäng vid nästa öppning och blockera resten av UTC-dygnet. Nästa dag kräver ny signal. Ändring kräver nytt id. |
| Permanent drawdown-stopp | 15 % från testets högsta nettokapital | Nettokapital vid stapelstängning; stäng vid nästa öppning och förbli platt till testets slut. Toppen uppdateras vid stängningar. Ingen reset mellan halvår. Ändring kräver nytt id. |
| Mål/maximal tillåten uppmätt drawdown | 20 % | Utvärderas även med intrastapel high/low som konservativt riskmått. Ett stop vid 15 % är ingen garanti: gap, slippage och kostnader kan ge större förlust. Överskridande ger REJECT. |
| Databrister | Inga nya positioner | Avvisa dubbletter, felaktiga OHLC, ofullständiga/icke-UTC/feljusterade serier och luckor i testets staplar innan körning. Funding kontrolleras mot fryst manifest. Ingen dold framåtfyllning. |

Ingen manuellt återaktiverad handel efter permanent stopp. Startkapital och riskklocka gäller hela testet. Riskstoppen använder motorns verkliga simulerade nettokapital, inte en separat approximation av strategins bruttorörelser. Eventuell likvidation enligt befintlig terminsmodell ger REJECT; modellen bygger på kontrakts-OHLC och ersätter inte en separat mark-price-modell inför någon framtida drift.

## Kostnader och stresstester

Avgift 10 bp per sida, hel spread 2 bp (1 bp per sida), slippage 5 bp per sida: totalt 16 bp per sida. Betald/mottagen funding ingår. Ingen hävstång eller avkastning på outnyttjat kapital.

Kostnadsstress multiplicerar avgift, spread och slippage med 2,5 (40 bp per sida). Hela risklagret räknas om med de stressade kostnaderna; det kan ge andra storlekar och stopptider. Separat fundingstress: dubbla endast de fundingbetalningar strategin betalar, behåll mottagna belopp oförändrade, och räkna om risklagret. Fundingstressen är redovisning och ändrar inte huvudbeslutet.

## Förregistrerade kriterier

N=16 olika id vid registrering. Newey-West på dagsavkastning, samma estimator som projektets befintliga statistik; låst Bonferroni-krav max(2, norm.ppf(1−0,05/16)) = **2,7343687865331763**. Senare försöksantal redovisas separat.

MORE_RESEARCH endast om samtliga gäller, annars REJECT:

1. Positiv nettoavkastning med normala kostnader.
2. Positiv nettoavkastning med 2,5× handelskostnader.
3. Newey-West t ≥ 2,7343687865331763 på huvudkurvans dagsavkastning.
4. Uppmätt maximal drawdown ≤ 20 %, både på huvudkurvans stapelstängningar och på konservativ intrastapelkurva. Intrastapelvärdet beräknar longpositionens kapital vid stapelns lägsta pris (eller utförd tidigare stop-utgång om stopp ligger före lägsta), från tidigare realiserat kapital, kostnader och funding; ingen påhittad intrastapel prisordning. Vid okänd ordning används det sämre möjliga utfallet.
5. Maximal drawdown på huvudkurvans stapelstängningar minst 40 % lägre i absolutbelopp än samma periods köp-och-behåll (spår B). Om benchmark-drawdown är noll räknas kravet inte som uppfyllt.
6. Ingen likvidation, framtidsdata eller regelöverträdelse; ofullständiga/icke ändliga nyckeltal kan inte godkännas.

Redovisa också affärsantal, exponering, omsättning, alla kostnader/funding, riskstoppens tidpunkter, per halvår/år, bootstrap-osäkerhet och jämförelser. Ingen annan parameteruppsättning väljs om denna misslyckas. Den eventuella slutliga kandidaten har exakt dessa parametrar och versionsmärkt risklager.

## Körning och status

En huvudkörning plus ovan låsta jämförelser/stresser. Inga permutationer, Optuna eller grid search. Alla genomförda och avbrutna försök sparas med kodrevision, dataversion och körnings-id. Syntetiska implementationstester före riktig historik; kodgranskning före körning.

Registreringen ska vara committad före någon H-0016-körning. H-0016 har ännu ingen implementation eller resultatrad och är inte startbar via H-0013:s låsta köingång. Ingen worker eller databas ändras genom registreringen. Ingen riktig körning har startats och ingen framtida avkastning har påvisats. MORE_RESEARCH ger endast underlag för separat beslut om slutprov, aldrig direkt READY_FOR_PAPER eller live.
