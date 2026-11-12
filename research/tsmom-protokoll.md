# H-0021: tidsseriemomentum över många kryptoterminer

Skrivet och registrerat 2026-11-12, **innan** någon ny körning och innan någon kod för strategin skrivits. Ändras inte
efter registreringen. Detta dokument är bara förregistreringen: inget test, ingen motorkod och inga nya data.

## Idé

Varje mynt bedöms mot **sin egen** historia, inte mot de andra: går myntet upp över de senaste fyra veckorna är
positionen long, annars short. Storleken sätts så att varje mynt bidrar lika mycket risk. Skillnaden mot H-0014/H-0018
(tvärsnittsmomentum) är att portföljen inte är marknadsneutral: när hela marknaden trendar kan den vara långt mer
long än short, och tvärtom. Frågan är om trendföljande över många mynt ger bättre riskjusterad avkastning än
köp-och-behåll i BTC, efter kostnader, och inte bara följer marknaden.

## Forskningsgrund (parametrar bestäms av litteraturen, optimeras inte)

Källorna anges efter min kännedom och har inte kunnat kontrolleras mot originaltexterna härifrån. Granskaren bör
göra det.

- Moskowitz, Ooi och Pedersen (2012), *Time series momentum*, Journal of Financial Economics: positionens tecken
  följer tecknet på den egna avkastningen över tidigare period, och positionen skalas efter förväntad volatilitet så
  att varje tillgång bidrar lika mycket risk.
- Hurst, Ooi och Pedersen (2017), *A century of evidence on trend-following investing*: samma idé över mycket lång
  historia och många marknader.
- Liu, Tsyvinski och Wu (2022), *Common risk factors in cryptocurrency*, Journal of Finance: momentum i krypto på
  horisonter om cirka 1 till 4 veckor.

Av det följer valen nedan. Lookback 28 dagar är densamma som i H-0014 och H-0018 och fastställdes redan 2026-11-02,
alltså före den här hypotesen. Ingen annan lookback testas.

## Regler (låsta)

| Del | Val |
|---|---|
| Universum | Samma som H-0018 (`research/xs-stort-protokoll.md`): Binance USDⓈ-M-terminer mot USDT med en månadsfil (1d) för 2021-01, utom BTCDOMUSDT, DEFIUSDT, BLUEBIRDUSDT och FOOTBALLUSDT. Avnoterade kontrakt ingår tills datan tar slut. |
| Valbarhet | Samma som H-0018: minst 60 dagars historik, en stängd stapel samma dag, och median av daglig omsättning (stängning × volym) de senaste 30 dagarna minst 10 miljoner USD. |
| Period | Signaldata från 2020-11-01 (uppvärmning). Test 2021-01-01 till 2024-12-31. **Slutprov 2025-01-01 och framåt läses inte in**, och alla läsare skickar periodgränser så att arkiv från slutprovet aldrig öppnas. |
| Data | Dagsstaplar (1d) och finansieringsränta per kontrakt ur Binances arkiv (data.binance.vision). |
| Signal | Avkastning över 28 dagar där senaste dagen hoppas över: `stängning(t−1) / stängning(t−29) − 1`, där t är beslutsdagen. Positivt ger long, negativt ger short. Exakt noll eller saknat värde ger ingen position. |
| Volatilitet | σ = standardavvikelsen av dagsavkastning (stängning mot stängning) över de 60 dagar som slutar dagen före beslutsdagen. Minst 40 giltiga dagar, annars ingen position i myntet. |
| Positionsstorlek | w = tecken / σ, normaliserat så att summan av absolutvikterna är exakt 1 (brutto 1×, ingen hävstång). Ingen enskild vikt över 10 %: överskottet fördelas proportionellt på övriga, och upprepas tills ingen överskrider. Färre än 10 valbara mynt med signal ger platt. Nettoexponeringen varierar fritt mellan −1 och +1. |
| Ombalansering | Varje söndag (UTC) vid stängning, fyllning vid måndagens öppning. Mellan ombalanseringar driver vikterna med priset. |
| Kostnader | 25 bp per sida på omsatt belopp (avgift 10, halv spread 5, glidning 10), samma som H-0018. Stress 2,5 gånger. Finansieringsränta per kontrakt betalas eller tas emot på hållen position. |
| Likvidation och konkurs | **Förenklat likvidationsstopp (ett eget antagande, inte Binances underhållsmarginal).** Definitioner: vid veckans ingång (måndagens öppning, kurs P0) har varje position insatsen I = w × kapital och ingångsnotional N0 = I (1× per position, ingen hävstång). Positionens equity är insatsen plus orealiserad vinst eller förlust: **short** `I + N0·(1 − P/P0) = N0·(2 − P/P0)`, **long** `I + N0·(P/P0 − 1) = N0·P/P0`. Positionen stoppas när dess equity har fallit till **5 % av ingångsnotional** (N0), alltså `short: P ≥ 1,95 × P0` och `long: P ≤ 0,05 × P0`. Gränserna är härledda ur just den definitionen. Kontrollen använder dagsstapelns **high** för short och **low** för long. Vid stopp antas, konservativt, att **hela insatsen I förloras** (även de sista 5 % tas av avgifter och glidning i en klämma) och att positionen stängs för resten av veckan utan möjlighet att återhämta sig; den öppnas på nytt först vid nästa söndagsombalansering. En position som inte stoppas stängs mot insats plus resultat. Marginalen återställs varje vecka. Avgifter och finansieringsränta räknas på notional utöver detta. Konkurs (kapital ≤ 0) är slutgiltig. Antal stopp och förlusten av dem redovisas. |
| Jämförelse 1 | Köp-och-behåll i BTCUSDT spot (1d) över samma dagar, enligt spår A. |
| Jämförelse 2 (skärpning) | Likaviktad **long-only**-korg av samma valbara mynt med samma söndagsombalansering och samma kostnader. Den visar om trendföljandet tillför något utöver att vara long marknaden. |
| Slumpkontroll | Samma portfölj med slumpade tecken (fast frö 0). t ska ligga nära noll. |

## Datakrav (annars `OGILTIG`, inget beslut)

1. Finansieringsränta finns för varje hållen position och dag (`portfolio.funding_gaps` ger inga luckor).
2. Inga arkiv från slutprovet har öppnats (kontrolleras av test).
3. Minst 30 valbara mynt som median över söndagarna.
4. Likvidationsstoppet ovan är implementerat i motorn och varje hållen position har dagsstaplar med high och low under hela veckan. Saknas modellen eller någon stapel är körningen `OGILTIG` och kan **aldrig** ge `MORE_RESEARCH`. En simulering som låter en likviderad short överleva godkänns alltså inte.

Luckor fylls aldrig med sista kända värde eller ersättare. Ogiltig körning redovisas som en ny rad, och försöket räknas.

## Beslutskriterier (spår A med skärpta krav, som H-0013)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t (Newey-West, dagsavkastning) ≥ kravet vid registreringen: **2,82** (N = 21)
2. Avkastning med 2,5 gånger kostnaderna > 0
3. Sharpe > köp-och-behåll i BTC (spår A)
4. Sharpe > den likaviktade long-only-korgen (skärpning, bestämd här)

Godkänt betyder bara att idén får granskas och sedan testas på den orörda perioden och på papper. Det betyder inte att
strategin tjänar pengar framåt. Redovisas även om kriterierna klaras eller inte: beta mot BTC, genomsnittlig
nettoexponering, omsättning per år, kostnader och finansieringsränta, avkastning per år, deflated Sharpe, bootstrap-
intervall för Sharpe och slumpkontrollens t.

## Kända svagheter, skrivna i förväg

- **Samma prisdata är redan sedd** i H-0014, H-0015, H-0018 och H-0019. Signalen är en variant av H-0014 och förväntas
  vara korrelerad med den. Idén valdes efter att tvärsnittsvarianterna fått REJECT, så den är en uppföljning och inte
  ett oberoende test. Därför räknas den som ett nytt försök och kravet stiger.
- Perioden 2021–2024 innehåller en stark uppgång (2021), en lång nedgång (2022) och en återhämtning. Resultatet kan
  bero på få regimer och på ett fåtal tillfällen.
- Nettoexponeringen följer marknaden: portföljen kan vara kraftigt long i en toppfas och förlora när trenden vänder.
- Shortpositioner i småmynt kan ha större glidning än 10 bp och kan klämmas (short squeeze). Blankning antas möjlig
  till terminspris. Likvidation modelleras med ett förenklat stopp (se tabellen) som är ett eget antagande: verklig
  marginal hos Binance beror på kontrakt, storlek och marginalläge (korsad eller isolerad), och likvidationen sker till
  en kurs som inte är exakt gränsen. Reglerna kan ha ändrats under perioden. Stoppet kallas därför inte
  underhållsmarginal.
- Kontrakt som avnoteras faller ofta kraftigt före avnoteringen. Det ingår, men stängningen sker på sista
  öppningen (Edwins fynd P2 är inte åtgärdat).
- Yahoo och aktiekurser berörs inte. All data kommer från Binances arkiv.

## Rättelse före registrering (2026-11-12)

Ett första utkast av raden "Likvidation och konkurs" sa att högst 10 % per mynt gör att ingen enskild position kan
tömma kontot på en vecka. Det stämde inte för en short: den förlorar hela sin insats om priset stiger mer än cirka
10 gånger, och en termin kan likvideras dessförinnan av marginalreglerna. Brutto 1× utesluter inte risken. Granskningen
(Codex, PR #108) påpekade felet. Raden är ersatt av det låsta likvidationsstoppet ovan, och datakrav 4 gör att
resultatet inte kan godkännas på en simulering som låter en likviderad short överleva. Rättelsen gjordes före merge
och före någon körning. H-0021 har inte körts.

## Före körning

Motorkoden skrivs i en separat PR och granskas innan något körs. Den ska återanvända `portfolio.py` (konkurs är
absorberande, `funding_gaps` stoppar körningen) och läsare med periodgränser, och ha test för look-ahead, för
slutprovsskyddet och för vikterna (brutto 1, tak 10 %). Dessutom riktade syntetiska test av stoppet, mot just
definitionen ovan: (1) en short vars high når 2,0 × P0 under veckan och som sedan faller tillbaka ska ge förlust av
hela insatsen I och ingen återhämtning, (2) en short vars high stannar på 1,90 × P0 ska inte stoppas, och en short på
exakt 1,95 × P0 ska stoppas, (3) en long vars low når 0,05 × P0 ska stoppas och en long på 0,06 × P0 inte, (4) ett
stopp i en vecka ska inte hindra ny position vid nästa söndagsombalansering.
