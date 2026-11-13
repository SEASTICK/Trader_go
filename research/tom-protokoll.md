# H-0024: månadsskiftet (turn of the month) i amerikanska aktier

Skrivet och registrerat 2026-11-13, **innan** någon SPY-kurs läses för den här hypotesen och innan någon kod skrivs för den. Ändras inte efter
registreringen: en ändring av regel, parameter, fönster eller period är ett nytt försök med nytt id. Hela protokollet, inklusive avsnittet
"Källverifiering", är skrivet utan att något utfall för hypotesen har setts. Inget test körs i den PR som lägger till filen.

## Idé

Aktiekurser stiger ojämnt över månaden. Om pengaflödena vid månadsskiftet (löner, pensions- och fondsparande, likviditetsbehov och
månadsvisa omviktningar) skapar köptryck, ska nästan hela aktiepremien ligga i fyra handelsdagar: månadens sista handelsdag och de tre första
i nästa månad. Hypotesen är att en portfölj som äger SPY **bara** under de fyra dagarna och annars håller kontanter ger högre Sharpe än
köp-och-behåll i SPY efter kostnader, och att det beror på timingen och inte på att man äger aktier.

Mekanismen skiljer sig från allt som testats tidigare: ingen kryptomarknad, ingen pris- eller fundingsignal, ingen rankning mellan tillgångar
och ingen trend. Signalen är ren **kalender** (den kräver inget prisdata för att veta när man ska äga) och vilar på kassaflöden, inte på
prismönster.

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

**Källorna nedan är angivna efter min kännedom och är INTE verifierade mot originaltexterna.** De ger idén och riktningen. Ingen av dem
har validerat just den här specifikationen (SPY, de fyra dagarna, öppning-till-öppning, 10 bp per sida, perioden 2006–2024).

* Ariel (1987), *A monthly effect in stock returns*, Journal of Financial Economics 18(1): månadsmönster i amerikanska aktieindex.
* Lakonishok och Smidt (1988), *Are seasonal anomalies real? A ninety-year perspective*, Review of Financial Studies 1(4): långt
  historiskt urval av Dow Jones, med månadsskifte som ett av mönstren.
* Ogden (1990), *Turn-of-month evaluations of liquid profits and stock returns*, Journal of Finance 45(4): kassaflödesförklaring.
* McConnell och Xu (2008), *Equity returns at the turn of the month*, Financial Analysts Journal 64(2): fönstret **sista handelsdagen
  i månaden till och med tredje handelsdagen i nästa månad** i flera länder. Det är fönstret som låses här.
* Etula, Rinne, Suominen och Vaittinen (2020), *Dash for cash: month-end liquidity needs and the predictability of stock returns*,
  Review of Financial Studies: likviditetsbehov vid månadsslut som förklaring. Volym och sidor är inte verifierade.

Vad som inte är känt härifrån: de exakta urvalsperioderna i källorna (särskilt när McConnell och Xus urval slutar), om effekten finns kvar
i USA efter publiceringen, och om den överlever kostnader. Det finns ett stort kritiskt fält om säsongsmönster (datasnokning, kalenderanomalier
som försvinner efter publicering). Därför är **huvudperioden** vald efter min kännedom om att McConnell–Xus urval slutar 2005: 2006 och framåt är
då utanför deras urval. Det antagandet är inte verifierat; om det inte stämmer ändras inget i testet, men slutsatsen "utanför urval" faller.

## Källverifiering (obligatorisk före körning)

**Status 2026-11-13: ej verifierad.** Ett försök att läsa originalen från sessionen misslyckades: SSRN, JSTOR och Google ligger utanför sessionens
tillåtna nätverksvärdar (DNS-fel), och Crossref och OpenAlex svarade 403 från proxyn. Inget kringgicks. Därför kan inga exakta citat anges
här, och jag skriver inga i efterhand utifrån minnet.

Före någon körning ska en ny commit fylla i denna tabell med **exakta citat och referenser** ur originalen (abstract, fönstrets definition,
urvalsperiod, siffror för USA) av någon som kan läsa dem, och Codex ska ha granskat att de stämmer. Tills dess är H-0024 registrerad men
**får inte köras**. Om originalen visar att fönstret, perioden eller riktningen avviker från det som står här, ändras inte detta protokoll i
efterhand: det blir ett nytt id.

| Källa | Exakt citat som styrker fönstret | Urvalsperiod enligt källan | Verifierad av/datum |
|---|---|---|---|
| McConnell och Xu (2008) | (att fylla i) | (att fylla i) | (att fylla i) |
| Etula m.fl. (2020) | (att fylla i) | (att fylla i) | (att fylla i) |
| Lakonishok och Smidt (1988) | (att fylla i) | (att fylla i) | (att fylla i) |

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

## Ren period?

Delvis. SPY:s totalavkastning 2014–2024 har setts som jämförelse i H-0016 och H-0017, men aldrig fönsteravkastningen, placebo-fönstren eller något
mått för H-0024. Perioden 2020–2024 ingår och är förbrukad i annan forskning (krypto). 2025-01-01 till 2026-09-30 är orörd.

## Före körning

1. "Källverifiering" ifylld och granskad av Codex (en ny commit, ingen ändring av reglerna ovan).
2. Kod och syntetiska tester i en egen PR, utan kontakt med riktiga SPY-data; test för att data från 2025-01-01 kapas.
3. Datapreflight (täckning enligt datakraven) i en egen PR, utan kurs- eller avkastningsutskrift.
4. Därefter en enda körning och en ny registerrad.
