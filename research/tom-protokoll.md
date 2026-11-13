# H-0024: månadsskiftet (turn of the month) i amerikanska aktier

Skrivet och registrerat 2026-11-13, **innan** någon SPY-kurs läses för den här hypotesen och innan någon kod skrivs för den. Ändras inte efter
registreringen: en ändring av regel, parameter, fönster eller period är ett nytt försök med nytt id. Hela protokollet, inklusive avsnittet
"Källverifiering", är skrivet utan att något utfall för hypotesen har setts. Inget test körs i den PR som lägger till filen.

## Idé

Aktiekurser stiger ojämnt över månaden. Det empiriska mönster som prövas är att nästan hela aktiepremien i USA ligger i fyra handelsdagar:
månadens sista handelsdag och de tre första i nästa månad. Hypotesen är att en portfölj som äger SPY **bara** under de fyra dagarna och annars
håller kontanter ger högre Sharpe än köp-och-behåll i SPY efter kostnader, och att det beror på timingen och inte på att man äger aktier.

**H-0024 prövar mönstret, inte en förklaring.** Två förklaringar finns i litteraturen och skiljs åt här (rättat 2026-11-13 efter granskning i PR #132,
se "Rättelse före körning"):

* **(a) Standardiserade betalningar och likviditetsbehov vid månadsskiftet** (löner, utbetalningar, månadsvisa kassaflöden). Ogden (1990) prövar
  enligt SEASTICK:s läsning uttryckligen betalningscykeln som förklaring (andrahandsuppgift, se "Källverifiering").
* **(b) Köptryck vid månadsslutet mätt med handelsvolym eller nettoflöden till aktiefonder.** Enligt SEASTICK:s läsning av artikelns slutsats (s. 62) kunde McConnell och Xus tester
  av volym och fondflöden **varken utesluta payday-förklaringen eller ge stöd för den**. Det är alltså inte belagt att (b) saknar effekt, och inte belagt att (b) förklarar mönstret
  (SEASTICK:s återgivning, ej läst av Claude).

Registerraden för H-0024 skrevs med formuleringen att pengaflöden "skapar köptryck". Den formuleringen gäller inte som hypotes eller belägg. Raden är
append-only och ändras inte; en rättelserad läggs till. Inget beslutskriterium nedan beror på vilken förklaring som stämmer, och inget i testet kan skilja
(a) från (b): ett positivt utfall säger inget om mekanismen. Jag påstår ingenting om vilken som stämmer.

Mekanismen skiljer sig från allt som testats tidigare: ingen kryptomarknad, ingen pris- eller fundingsignal, ingen rankning mellan tillgångar och ingen
trend. Signalen är ren **kalender** (den kräver inget prisdata för att veta när man ska äga).

## Överlapp med tidigare försök (jämförelse mot `research/registry.md` och Agentlab)

| Tidigare | Vad | Överlapp med H-0024 |
|---|---|---|
| H-0001–H-0013 | Tekniska strategier och spelbok på BTC/ETH, 4h | Ingen: annan marknad, signal från pris |
| H-0014, H-0015, H-0018, H-0019 | Tvärsnittsmomentum och funding-carry på Binance-terminer | Ingen: annan marknad och signal |
| H-0020, H-0022, H-0023 | Kassa-och-termin (basis) på BTC/ETH och COIN-M | Ingen: annan marknad, ingen terminskurva |
| H-0021 | Tidsseriemomentum på kryptoterminer | Ingen i signal (trend mot kalender). Båda är långsamma exponeringsregler, annars skilda |
| H-0016, H-0017 | 13F-innehav och Pelosi-affärer mot SPY | **SPY användes bara som jämförelse.** Totalavkastningen för SPY 2014–2024 är känd från de resultaten, men aldrig fönsteravkastningen vid månadsskiftet |
| Agentlab (R001–R004, 16 familjer: `bab`, `donchian`, `ensemble_rank`, `funding_carry`, `funding_fade`, `lowvol`, `ml_xs`, `mtf_trend`, `pairs`, `placebo`, `trend_ma`, `ts_mom`, `vol_regime`, `vol_shock`, `xs_mom`, `xs_rev`) | Pris-, volym- och fundingsignaler på dagliga kryptoperpar | Ingen: ingen familj använder kalender eller aktiemarknad |

Det här är därför inte en parameter- eller komponentvariant av en tidigare REJECT. Det är ett första test av en kalenderhypotes på
aktiemarknaden. All historik 2020–2024 på kryptomarknaden är förbrukad i tidigare forskning och är inte ren; det gäller inte direkt här,
men SPY för 2020–2024 ligger i testperioden och 2014–2024 har setts som jämförelse (se "Ren period" nedan).

## Forskningsgrund och vad den inte visar

**Ingen källa är läst i original av mig.** Uppgifterna om innehållet kommer antingen från min kännedom (markerat) eller från SEASTICK:s läsning av de publicerade
abstracten i PR #132 (markerat "andrahandsuppgift"). Ingen av källorna har validerat just den här specifikationen (SPY, de fyra dagarna,
öppning-till-öppning, 10 bp per sida, perioden 2006–2024).

**Fönster- och urvalskälla**

* McConnell och Xu (2008), *Equity returns at the turn of the month*, Financial Analysts Journal 64(2): fönstret **sista handelsdagen i månaden till och med
  tredje handelsdagen i nästa månad**. Fönstrets definition (Table 1-noten, s. 51) och urvalet **1926–2005** (abstract, s. 49) är citerade av SEASTICK i PR #132 (se "Källverifiering"), vilket
  stödjer att 2006 ligger efter deras urval. Artikeln är **ingen källa som visar att mekanism (a) eller (b) gäller**: enligt SEASTICK:s återgivning av slutsatsen på s. 62 gav volym- och fondflödestesterna
  varken stöd för eller möjlighet att utesluta payday-förklaringen.

**Prövar betalningscykeln (mekanism a)**

* Ogden (1990), *Turn-of-month evaluations of liquid profits and stock returns* (titeln ofullständigt återgiven), Journal of Finance 45(4): enligt SEASTICK:s citat ur förlagets abstract en uttrycklig
  prövning av hypotesen att standardiseringen av betalningar vid månadsskiftet förklarar mönstret, med urvalet 1969–1986 (s. 1259–1272). Ogdens urval ligger före 2006 och
  säger inget om perioden 2006–2024.

**Bakgrund, inte belägg** (tillskrivs inget specifikt resultat i detta protokoll; inget kriterium eller val vilar på dem):

* Ariel (1987), *A monthly effect in stock returns*, Journal of Financial Economics 18(1).
* Lakonishok och Smidt (1988), *Are seasonal anomalies real? A ninety-year perspective*, Review of Financial Studies 1(4).
* Etula, Rinne, Suominen och Vaittinen (2020), *Dash for cash: month-end liquidity needs and the predictability of stock returns*, Review of Financial Studies (volym och sidor ej verifierade).

Vad som inte är känt: om effekten finns kvar i USA efter 2005, om den överlever kostnader, och vilken förklaring som stämmer. Det finns ett stort kritiskt fält om
säsongsmönster (datasnokning, kalenderanomalier som försvinner efter publicering). **Huvudperioden** 2006–2024 är vald för att ligga efter McConnell–Xus urval 1926–2005 (citerat av SEASTICK) och Ogdens urval 1969–1986.

## Källverifiering (obligatorisk före körning)

**Status 2026-11-13: ifylld med citat som SEASTICK har läst i originalen och angivit i PR #132; inte läst av Claude.** Jag har inte kunnat öppna källorna själv:
`papers.ssrn.com` och `onlinelibrary.wiley.com` (tillåtna i sessionens miljö) svarar med Cloudflares robotkontroll ("Just a moment…", HTTP 403) på automatiska anrop, och
`business.purdue.edu` (PDF:en med själva artikeln, också tillåten) går att nå men serverns certifikatkedja kan inte valideras ("unable to get local issuer certificate"). Ingen robotkontroll
löses och ingen TLS-kontroll stängs av. Citaten nedan är därför **SEASTICK:s ordagranna återgivning**, kopierad hit utan ändring; sid-/avsnittshänvisningarna är SEASTICK:s egna. Codex
(eller någon som kan öppna originalen) ska ha kontrollerat dem mot källorna innan körning. Tills dess och tills **"Granskad mot original"** nedan är ifylld är H-0024 registrerad men
**får inte köras**. Visar originalen att fönstret, perioden eller riktningen avviker från det som står här, ändras inte detta protokoll i efterhand: det blir ett nytt id.

| Källa | Vad som styrks | Citat och hänvisning (återgivet av SEASTICK, PR #132, 2026-11-13) | Granskad mot original |
|---|---|---|---|
| McConnell och Xu (2008), *Financial Analysts Journal* 64(2), s. 49–64. [Artikel-PDF](https://business.purdue.edu/faculty/mcconnell/publications/Equity-Returns-at-the-Turn-of-the-Month.pdf), [SSRN 1135217](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1135217) | Urvalsperiod | Abstract, s. 49: urvalet anges som “1926–2005 period”. | (att granska) |
| samma | Fönstrets definition | Table 1-noten, s. 51: intervallet definieras med frasen “last trading day of the month … third trading day of the following month”. | (att granska) |
| samma | Vad volym- och fondflödestesterna visar | Slutsatsen, s. 62 (återgiven i sak, inget ordagrant citat lämnat): testerna kunde varken utesluta payday-förklaringen eller ge stöd för den. | (att granska; ordagrant citat saknas) |
| Ogden (1990), *Journal of Finance* 45(4), s. 1259–1272. [Wiley, förlagets abstract](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1990.tb02435.x) | Att artikeln prövar betalningscykeln | Förlagets abstract: artikeln “presents and tests a hypothesis that the standardization of payments in the United States at the turn of each calendar month” (citatet är återgivet som det lämnades, meningen fortsätter i originalet). | (att granska) |
| samma | Urvalsperiod | Samma abstract: urvalet är 1969–1986 (återgivet i sak, inget ordagrant citat lämnat). | (att granska) |
| Ariel (1987), Lakonishok–Smidt (1988), Etula m.fl. (2020) | Inget: bakgrund | Tillskrivs inget specifikt resultat | – |

## Regler (låsta)

| Del | Val |
|---|---|
| Instrument | SPY (SPDR S&P 500 ETF Trust), dagliga staplar |
| Datakälla | Yahoo Finance chart-API via `engine/traderlab/data/stocks.py` (`load_prices`), öppning och stängning justerade för utdelning och split (`adj`-faktor). Stooq används inte (spärr). Kontantränta (sekundärt mått): ^IRX från samma källa. |
| Handelsdag | Dag med stapel i SPY-serien. Dag `T0` = sista handelsdagen i kalendermånad `M`, `T1`, `T2`, `T3` = första, andra och tredje handelsdagen i `M+1`, `T4` = fjärde handelsdagen i `M+1`. Datumen följer av börskalendern och är kända i förväg. |
| Position | 100 % SPY under fönstret, annars kontanter. Ingen hävstång, inget blankat. Kontanter ger 0 % (konservativt mot hypotesen i år med hög ränta; se sekundärt mått). |
| Utförande (primärt, A) | Projektets standard: beslut på stängd stapel, fyllning vid nästa öppning. Köp vid **öppningen `T0`**, sälj vid **öppningen `T4`**. Dagsavkastningen för dag `t` är `open(t+1) / open(t) − 1` för `t = T0..T3`, annars 0. Alla serier (strategi och köp-och-behåll) räknas öppning-till-öppning. |
| Utförande (sekundärt, B) | Marknad-vid-stängning: köp vid stängningen dagen före `T0`, sälj vid stängningen `T3`. Dagsavkastning `close(t)/close(t−1) − 1` för `t = T0..T3`. Redovisas, men **påverkar inte beslutet** (kalenderregeln har ingen information vid beslutet, så detta är genomförbart, men A är standard). |
| Kostnader | 10 bp per sida på omsatt belopp (två sidor per fönster), stress 2,5 gånger (25 bp per sida). |
| Period, primär | 2006-01-01 till 2024-12-31 (förhandsregel: efter McConnell–Xus urval enligt min, ej verifierad, kännedom). |
| Period, sekundär | 1993-02-01 (första fulla månaden efter SPY:s start) till 2005-12-31. Kan ligga inom källornas urval. Redovisas, avgör inget. |
| Slutprov | 2025-01-01 till 2026-09-30 (orört; läses inte, hålls orört tills hela den historiska grinden är klar). Serien kapas vid 2025-01-01 innan någon beräkning. |
| Jämförelse | (1) Köp-och-behåll SPY, öppning-till-öppning, samma period. (2) Konstant exponering `c` (andelen fönsterdagar av alla handelsdagar i perioden, ungefär 0,19, beräknad ur kalendern). |
| Antal försök | N = 24 (H-0024 är det 24:e id:t). Krav `t ≥ 2,87` (`python -m traderlab krav 24`). |

## Mått och beslutskriterier (spår A: slå marknaden)

Per dag `t`: `d_t = r_strategi,t − c · r_KoB,t`, där `r_strategi` är strategins nettodagsavkastning (efter kostnader, 0 utanför fönstret) och `r_KoB` är
köp-och-behåll öppning-till-öppning. `d_t` mäter vad timingen ger utöver att bara äga aktier en konstant andel `c` av tiden. Dagarna summeras
per kalendermånad: `D_m`. Det blir cirka 228 månader.

Beslut `MORE_RESEARCH` kräver **alla** punkter. Annars `REJECT`. Datakravet nedan har företräde: uppfylls det inte blir utfallet `OGILTIG`
utan beslut.

1. `t(D_m) ≥ 2,87` (vanligt t-värde för medelvärdet av `D_m` mot noll, `stats.t_stat`; N=24).
2. Med 2,5 gånger kostnaderna är medelvärdet av `D_m` > 0.
3. Sharpe (årsvis, 252 dagar, utan kontantränta) för strategin > Sharpe för köp-och-behåll, daglig öppning-till-öppning, samma period.
4. **Placebo-fönster:** samma fönster förskjutet `u` handelsdagar för `u ∈ {−10, …, −1, +1, …, +10}` (20 alternativ, samma kostnader och samma `c`).
   Det verkliga fönstrets (`u = 0`) medelvärde av `d_t` ska vara det **högsta av de 21**. Det motsvarar en exakt p-värdesgräns på 1/21 ≈ 0,048 och
   visar att just månadsskiftet är särskilt och inte vilken fyradagarsperiod som helst.
5. **Stabilitet:** medelvärdet av `D_m` > 0 i både 2006-01 till 2014-12 och 2015-01 till 2024-12.

`MORE_RESEARCH` betyder bara att idén får granskas vidare och sedan prövas en gång på den orörda perioden 2025-01 till 2026-09 och på
papper. Det är ingen prognos och ingen avkastningslöfte. Ingenting lämnar papper utan ett uttryckligt, separat beslut.

**Sekundära mått, redovisas men avgör inget:** utförande B; period 1993–2005; Sharpe på överavkastning över ^IRX för både strategi och
köp-och-behåll (om ^IRX går att hämta, annars utelämnas måttet utan påverkan på beslutet); största nedgång; andel månader med positiv
fönsteravkastning; fönstrets andel av köp-och-behålls totala log-avkastning.

## Datakrav (annars `OGILTIG`, inget beslut)

1. Justerad öppning och stängning för SPY finns för alla handelsdagar 2006-01-01 till 2024-12-31, utan saknade värden i dessa fält, och antalet
   handelsdagar per kalenderår ligger mellan 249 och 253 (NYSE har haft 250–253 under perioden).
2. Varje kalendermånad 2006-01 till 2024-12 har minst 15 handelsdagar i serien, och fönstrets fyra dagar plus `T4` finns för varje cykel.
3. Inga värden från 2025-01-01 eller senare används, skrivs ut eller sparas i något resultat. Observera att `load_prices` hämtar historiken till
   idag och cachar hela svaret; läsningen ska därför kapas före första beräkningen, och ett test ska visa att koden vägrar eller kapar data
   från 2025-01-01. Ingen siffra för slutprovet beräknas.
4. Kostnader och utförande enligt tabellen; ingen parameter (fönster, förskjutning, kostnad, period) ändras efter att resultatet setts.

## Stoppregler

* En körning, en gång, från mergad main efter granskning av koden och efter att "Källverifiering" är ifylld. Inga varianter (andra fönsterlängder,
  andra dagar, andra instrument) körs som val. De 20 förskjutna fönstren är **placebo i beslutet**, inte kandidater.
* Skulle koden visa ett fel som ändrar ett resultat, rättas det i en separat PR och körningen görs om som ny rad med samma id, med allt
  redovisat. Rättelsen får inte ändra regler eller kriterier.
* Blir utfallet `REJECT` eller `OGILTIG` redovisas det som sådant. Det är ett bra utfall.

## Kända svagheter, skrivna i förväg

1. **Datasnokning och publiceringsförfall.** Kalendermönster är en av de mest kartlagda och mest tvivlade delarna av litteraturen. Effekten kan ha
   handlats bort efter publiceringen. Huvudperioden 2006–2024 är vald för att ligga efter urvalet i källan om min kännedom stämmer.
2. **Samma underliggande index.** SPY är ett enda instrument; ett positivt utfall är en historia, inte flera oberoende marknader. De utländska
   resultaten i litteraturen används inte här.
3. **Kassa 0 %.** Kontanter ger 0 % i huvudmåttet. I år med hög ränta (2006–2007, 2023–2024) gynnar det köp-och-behåll; sekundärt mått med ^IRX redovisas.
4. **Fönstret är lånat från litteraturen**, inte optimerat här, men det är fortfarande ett val på ett känt mönster. Placebo-testen (punkt 4)
   begränsar det men ersätter det inte.
5. **Utförande A missar nattens avkastning dagen före `T0`** (köp vid öppningen `T0`, inte vid stängningen dagen före). Om effekten ligger i
   den natten kan A bli sämre än B, och beslutet bygger ändå på A.
6. **Överlapp med tidigare prisdata är begränsat men inte noll:** SPY 2014–2024 har setts som jämförelse. Därför markeras perioden som delvis förbrukad.
7. **Yahoo-data är inofficiella** och kan ändras. Samma källa gav `OGILTIG` för H-0016 på grund av avnoterade bolag; SPY har inget sådant problem men
   källans justeringar för utdelning kan skilja sig från en officiell totalavkastningsserie.

8. **Förklaringen är obekräftad.** Betalningscykeln (mekanism a) prövas av Ogden på 1969–1986; enligt SEASTICK:s återgivning kunde McConnell–Xus volym- och fondflödestester (mekanism b)
   varken utesluta payday-förklaringen eller ge stöd för den. H-0024 kan inte skilja dem åt; ett positivt utfall är inget belägg för någon av dem.

## Rättelse före körning (2026-11-13, efter granskning i PR #132)

Ändrat: mekanismformuleringen i "Idé" och källbeskrivningen i "Forskningsgrund" och "Källverifiering", så att prövning av mönster skiljs från förklaringar och så att källor utan verifierat
resultat markeras som bakgrund. **Oförändrat:** instrument, fönster, utförande, kostnader, perioder, jämförelser, kriterier, N=24, t-krav och datakrav. Registerraden för H-0024 (som
säger "eftersom pengaflöden … skapar köptryck") ändras inte; en rättelserad med samma id läggs till sist. Det är inget nytt försök.

**Andra rättelsen (2026-11-13, efter SEASTICK:s kontroll av primärkällorna):** (1) Formuleringen att McConnell–Xu "inte" finner att volym och fondflöden förklarar mönstret var för kategorisk och
står i konflikt med artikelns slutsats (s. 62, enligt SEASTICK): testerna kunde varken utesluta payday-förklaringen eller ge stöd för den. Den är ersatt i "Idé", "Forskningsgrund" och "Källverifiering".
(2) Källverifieringstabellen är ifylld med SEASTICK:s citat och hänvisningar (McConnell–Xu s. 49, 51 och 62, Ogden s. 1259–1272 med urvalet 1969–1986); de är inte lästa av Claude och kräver granskning mot original.
**Oförändrat:** alla låsta regler, kriterier, N=24, t-krav och datakrav. En andra rättelserad med samma id läggs till i registret. Det är inget nytt försök.

## Ren period?

Delvis. SPY:s totalavkastning 2014–2024 har setts som jämförelse i H-0016 och H-0017, men aldrig fönsteravkastningen, placebo-fönstren eller något
mått för H-0024. Perioden 2020–2024 ingår och är förbrukad i annan forskning (krypto). 2025-01-01 till 2026-09-30 är orörd.

## Före körning

1. "Källverifiering" ifylld och granskad av Codex (en ny commit, ingen ändring av reglerna ovan).
2. Kod och syntetiska tester i en egen PR, utan kontakt med riktiga SPY-data; test för att data från 2025-01-01 kapas.
3. Datapreflight (täckning enligt datakraven) i en egen PR, utan kurs- eller avkastningsutskrift.
4. Därefter en enda körning och en ny registerrad.
