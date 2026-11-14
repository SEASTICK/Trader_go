# H-0027, H-0028, H-0029: intradag på BTC-terminer (ungefär en affär om dagen)

Skrivet och registrerat 2026-11-14, **innan** någon kod för strategierna skrivits och innan någon intradagsdata
körts mot en strategi. Ändras inte efter registreringen. Idéerna planerades tillsammans med Codex (read-only,
2026-11-14). Edwin bad om strategier på mindre tidsramar, helst med en affär om dagen, och godkände arbetet.

## Varför det är svårt (skrivet före resultatet)

En affär om dagen kostar mycket. Med kostnaderna nedan (6,05 bp per sida) blir en tur och retur 12,1 bp. Vid
365 affärer om året är det cirka 44 % av beloppet per år. Kravet att avkastningen ska vara positiv med 2,5 gånger
kostnaderna betyder att en strategi med daglig handel behöver tjäna över cirka 30 bp per affär före kostnader.
Ett REJECT här är det mest sannolika utfallet och är ett bra utfall.

## Gemensamt för alla tre

| Del | Val |
|---|---|
| Marknad | Binance USDⓈ-M BTCUSDT (perpetual), data.binance.vision månadsfiler, med finansieringsränta |
| Period | 2020-01-01 till 2024-12-31 (UTC). Utvecklingshistorik som redan använts för 4h och 1d (H-0009–H-0012, H-0025, H-0026); ingen ren period. Slutprovet 2025-01 till 2026-09 **hämtas inte och läses inte**. |
| Utförande | Beslut vid stängd stapel, fyllning vid nästa stapels öppning (motorn `backtest.run`). |
| Storlek | Fast 1× av kapitalet vid inträde, ingen hävstång, ingen påfyllning, inget eget stopp utöver tidsutträdet. Likvidation räknas av motorn med underhållsmarginal 0,5 % (standard i `backtest.run`); en short kan i princip likvideras även vid 1×. |
| Mål utanför regeln | Målpositionen är 0 för alla staplar som inte uttryckligen ges ett mål nedan. |
| Dygn och klockslag | En stapel hör till det dygn (UTC, eller New York för H-0028) där den **öppnar**. Mål sätts bara utifrån stapelns tidsstämpel och data till och med dess stängning. |
| Saknade staplar | Kvalitetskontrollen (`traderlab check`) körs först och antalet saknade staplar redovisas. Målen räknas bara från befintliga staplar; saknas en stapel sker fyllningen vid nästa befintliga stapels öppning (motorns regel). Ingen affär stryks i efterhand på grund av en framtida lucka. |
| Periodens slut | Ingen affär får gå in om dess planerade utträde ligger efter öppningen av datasetets sista stapel (2024-12-31 23:00 UTC för 1h, 23:45 för 15m). Det avgörs av klockan, inte av priser. 2025 och senare läses aldrig. |
| Finansieringsränta | Motorns `_funding_by_bar`: en avräkning vid tid T hör till stapeln [open_i, open_{i+1}) som innehåller T och betalas av positionen under den stapeln. Ett utträde vid öppningen 00:00 betalar alltså inte avräkningen 00:00 (en förenkling i motorns konvention). |
| Jämförelse | Köp-och-behåll på samma BTCUSDT-terminsstaplar med samma kostnader (motorns `_baseline`). |
| Kostnader | `CostModel(fee_bps=5, spread_bps=0.1, slippage_bps=1)` = 6,05 bp per sida: Binance publika taker-avgift 5 bp för vanliga användare, BTCUSDT-spread cirka 0,1 bp, 1 bp glidning för liten storlek. Spread och glidning är antaganden, inte uppmätta. Lägre än de 16 bp som H-0009–H-0012 använde; därför är 2,5 gånger stress (15,1 bp per sida) beslutsgrundande. Finansieringsränta enligt motorn. |
| Spår | B (lägre risk), med tracks.md:s kriterier oförändrade. |
| t-värde | Dagligt Newey-West-t på strategins nettoavkastning per UTC-dygn, alla kalenderdagar inklusive platta dagar (motorns `t_daily_nw`, lags = ⌊4·(n/100)^(2/9)⌋). Kostnader och funding hamnar på det dygn då fyllningen sker. |
| Krav på t | **2,93**: N = 29 räknat med alla id på main (25), H-0024 som är reserverat i öppen PR #132, och de tre nya. Φ⁻¹(1 − 0,05/29) = 2,9247, avrundat uppåt. Motorn räknar bara id i filen (28, krav 2,91); det strängare värdet 2,93 gäller. |

### Beslutskriterier (alla måste uppfyllas, annars REJECT)

1. t ≥ 2,93.
2. Total avkastning med 2,5 gånger kostnaderna > 0.
3. Största fall (stängningsbaserat) minst 40 % mindre än köp-och-behåll BTCUSDT-terminen över samma period.
4. Ingen likvidation, inget fel i look-ahead-kontrollen (`check_no_lookahead`), och slumpkontrollen (motorns `random_label_control`, frö 0, inga kostnader) har |t| < 2.

Klarar en hypotes alla fyra blir beslutet `MORE_RESEARCH` (granskning och sedan slutprov och papper), aldrig
direkt `READY_FOR_PAPER`.

## H-0027: reversering efter extrem timme

**Hypotes.** När BTC rör sig extremt under en timme, ofta på grund av tvångsstängningar, går en del av rörelsen
tillbaka under de närmaste timmarna, tillräckligt för att täcka kostnaderna.

**Regler (1h-staplar).**
- Timavkastning r_t = close_t / close_{t−1} − 1.
- σ_t = standardavvikelsen för de 720 föregående timavkastningarna (r_{t−720} … r_{t−1}, inte r_t).
- σ_t räknas med ddof = 1 och kräver 721 sammanhängande timstaplar (720 föregående avkastningar utan lucka);
  annars ingen signal den timmen.
- Signal: den **första** stapeln (efter öppningstid) under ett UTC-dygn där |r_t| > 3·σ_t. Position =
  −tecken(r_t), alltså mot rörelsen. Senare extrema timmar samma dygn ignoreras, även om den första inte ger
  någon affär.
- Inträde vid öppningen av nästa timme. Utträde vid öppningen av timme t+4 eller vid nästa 00:00 UTC, det som
  kommer först. Om inträde och utträde blir samma öppning (signal i stapeln som öppnar 23:00) blir det ingen
  affär. Målet är −tecken(r_t) för staplarna t … t+2 (eller fram till och med stapeln som öppnar 22:00) och 0
  därefter.
- Förväntat cirka 30–100 affärer per år (planeringsskattning, inte uppmätt).

**Grund.** Caporale och Plastun (2019) beskriver överreaktioner i kryptopriser; de har inte validerat just den här
timregeln. 3σ, 720 timmar och tre timmar är fasta designval utan sökning.

**Fälla.** Fortsättning i krascher, och att fyllningar mitt i en chock i verkligheten blir dyrare än antaget.

## H-0028: utbrott ur USA-öppningens intervall

**Hypotes.** Information och flöden kring USA-sessionens öppning ger en prisrörelse som fortsätter efter det
första handelsintervallet.

**Regler (15m-staplar, klockslag i America/New_York med sommartid).**
- Bara måndag till fredag i New York-tid. Ingen helgdagskalender (krypto handlas ändå).
- Intervallet: högsta high och lägsta low för staplarna som öppnar 09:30, 09:45, 10:00 och 10:15 (alltså
  09:30–10:30).
- Alla fyra intervallstaplar måste finnas, annars ingen affär den dagen.
- Signal: den första stapeln som öppnar 10:30–11:45 (alltså stänger 10:45–12:00) vars close ligger över
  intervallets high (long) eller under dess low (short). Högst en affär per dag.
- Inträde vid nästa stapels öppning. Målet hålls till och med stapeln som öppnar 15:30 och är 0 vid stängningen
  av stapeln som öppnar 15:45, så utträdet sker vid öppningen 16:00 New York-tid.
- Förväntat cirka 150–240 affärer per år.

**Grund.** Gao, Han, Li och Zhou (2018), *Market intraday momentum*, visar sessionsmomentum på amerikanska
aktieindex; det är inte validerat för krypto eller för utbrott. Klockslagen är fasta designval.

**Fälla.** Fel i sommartid, och att USA-öppningen inte är en riktig öppning för krypto.

## H-0029: tidiga UTC-timmar förutsäger sena

**Hypotes.** BTC:s avkastning under dygnets första sex UTC-timmar förutsäger riktningen under de sista sex,
på grund av att information sprids med fördröjning.

**Regler (1h-staplar).**
- Signal s = tecken(close för stapeln som öppnar 05:00 / open för stapeln som öppnar 00:00 − 1), samma UTC-dygn.
  s = 0 ger ingen affär.
- Position s från öppningen 18:00 UTC till öppningen 00:00 UTC nästa dygn. Alltså mål s för staplarna som
  öppnar 17:00–22:00 och mål 0 vid stängningen av stapeln som öppnar 23:00.
- Saknas någon av de sex tidiga staplarna (00:00–05:00) det dygnet: ingen affär. Luckor senare hanteras enligt
  den gemensamma regeln om saknade staplar.
- Förväntat cirka 365 affärer per år.

**Grund.** Gao m.fl. (2018), en extrapolering från aktier. Sex timmar och 18:00 är fasta designval.

**Fälla.** Godtyckliga dygnsgränser, och för liten bruttokant över sex timmar.

## Rapport

Resultaten sparas som vanligt i `research/results/` och förs in på nya rader i registret. Alla tre redovisas,
även de som misslyckas. Ranking efter antal affärer, avkastning och t-värde görs först när alla tre är körda,
och ingen hypotes justeras efter att resultatet setts. En ändrad regel är ett nytt id.

## Kända svagheter

- Samma prisdata (BTC 2020–2024) har redan använts för många hypoteser, om än på 4h och 1d.
- Kostnadsantagandet är lägre än tidigare; stressen på 2,5 gånger är därför avgörande.
- Klockslag och trösklar är designval. Andra val testas inte, så ett negativt utfall utesluter inte varianter.
