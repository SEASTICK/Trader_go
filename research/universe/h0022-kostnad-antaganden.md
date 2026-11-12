# H-0022: kostnads- och likvidationsmodell och genomförbarhetsbeslut

Datum: 2026-11-12. Uppdrag från Codex efter PR #115. **Ingen hypotes registreras, inget backtest körs, inga data från 2025 eller
senare läses och ingen basis eller avkastning har beräknats på historik.** `research/registry.md` är oförändrad (N = 21). Alla
siffror i testerna är syntetiska. Parametrarna nedan är låsta *förslag* för en senare förregistrering, valda utan avkastningsurval.

## Beslut

**(a) Reglerna för kostnad och likvidation kan låsas.** Ingen kvarvarande lucka i kostnads- eller likvidationsmodellen stoppar en
förregistrering, men tre saker måste stå som uttryckliga antaganden och ett fönster begränsar testet (se "Det som inte kan sägas").
Den största begränsningen är inte kostnaden utan statistisk styrka: det biasfria fönstret ger omkring 14 kvartalscykler.

## Källor och antaganden

| Del | Vad som är daterat (primärkälla) | Osäkert | Låst, konservativt antagande |
|---|---|---|---|
| Kontraktsstorlek | Binance-guide 2020-06-12: altcoin-kontrakt 10 USD, BTC 100 USD; förklaring 2021-07-26: ETH 10 USD. **Datahärledd kontroll** för alla 135 serier (mynt-volym · pris / kontrakt-volym i dagsstaplarna): median 10,00 för alla sju, per serie 9,67–10,42 (p05–p95) | Ingen Binance-källa namnger de sju kontrakten, och datahärledningen är en kontroll, inte en källa | 10 USD. En serie vars härledda median ligger utanför 9,5–10,5 utesluts (0 av 135 idag). Tabell: `coinm-implied-contract-size.json` |
| COIN-M-terminsavgift (vanlig användare) | Ny avgiftsstruktur från 2020-07-17 (meddelande 2020-07-10, siffror ej i texten); 0,015 % maker / 0,040 % taker t.o.m. 2021-04-26 (kolumnen "Before" i meddelandet 2021-04-22); 0,010 % / 0,050 % från 2021-04-27; 0,020 % / 0,050 % från 2023-09-26 | Exakt startdag för 0,040 % (rimligen 2020-07-17); VIP-nivåer och kampanjer (2020-11-16 till 2020-12-31) används inte | Alltid **taker 0,050 %**, aldrig maker, ingen rabatt. Avräkning = takeravgift (leverans-FAQ) |
| Spotavgift | 0,100 % maker och taker, allmän nivå (2017-08-24 och 2018-07-19); 25 % BNB-rabatt förlängd (2021-06-25, 2022-06-30) | Att allmän nivå var oförändrad 2020–2024 är bara belagt genom att inga ändringar hittats i titlarna | **0,100 % per ben**, ingen BNB-rabatt |
| Spread/glidning | Ingen källa: bara dagsstaplar finns, ingen orderbokshistorik | Hela posten | **Antagande: 5 bp per ben** (spot-köp, termin-sälj, terminsutträde och spot-sälj) och **stresstest 2,5×** (12,5 bp per ben). Märkt som antagande, inte som mätning |
| Marginal och likvidation | Marginalformel och exempel (FAQ), kvartalstabeller 2020-12-22 (EOS, ETC, FIL, TRX), 2021-04-05 (BTC, ETH), 2021-04-12 (BNB), 2022-12-29 (maxhävstång för alla sju: 20x → 11x), 2023-05-31 (ADA m.fl.). Högsta underhållsnivåer i tabellerna: 25 % (altcoin) och 50 % (BTC) | Underhållsmarginalen höjdes stegvis 2021-02 till 2021-05 för alla sju (meddelanden 2021-02-22, 03-01); stegen står bara på en Binance-sida som uppdaterades löpande och är inte arkiverad | Hävstång högst 1x (full myntmarginal). Underhållsnivå antas **50 %** för alla serier och perioder. Stopp om marginalkvoten når **80 %** (Binance rekommenderar under 80–90 %) |
| Markpris | Orealiserad PnL på markpris, realiserad på senaste pris (FAQ). Markprisfiler (dagsstaplar) finns i arkivet för alla 135 serier (listningskontroll), och ett prov (ADAUSD_201225, 2020-11) laddades ner med giltig checksumma och rimliga staplar | Innehållet är bara provat på en serie; historisk markprisformel är inte belagd | Marginalkontrollen använder dagens högsta markpris; en saknad markprisdag ger OGILTIG |
| Avräkning | Förfall sista fredagen 08:00 UTC; avräkningskurs ur indexpris | Fönstret: timmesmedel (guide 2020) mot 30 minuter (nuvarande FAQ) | Undvik helt: **förutbestämt utträde 7 kalenderdagar före förfall** (se nedan) |
| Likviditet | Dagsstaplar: närmaste kontrakt, median 0,95–2,9 miljoner USD/dag och P10 78 000–477 000 USD/dag (se tabell) | Ingen orderbok, ingen djupmätning | Positionen får vara högst 2 % av seriens medianvolym över de senaste 20 dagarna, mätt till och med beslutsdagen |
| Finansieringsränta | Daterade terminer har ingen | – | Ingen |
| ADL, försäkringsfond, motpartsrisk | Inte modellerade | Hela posten | Redovisas som utanför modellen |

### De sju underliggande

| Underliggande | Serier | Härledd kontraktsstorlek (median; p05–p95 över serier) | Maxhävstång kvartal 1230 (2022-12-29) | P10 / median USD per dag, närmaste kontrakt | Daterat marginalunderlag |
|---|---|---|---|---|---|
| ADA | 20 | 10,00; 9,75–10,39 | 11x | 189 592 / 1 307 640 | tabell 2023-05-31 (perp) |
| BCH | 19 | 10,00; 9,75–10,30 | 11x | 92 250 / 1 178 315 | endast maxhävstång |
| BNB | 19 | 10,00; 9,80–10,29 | 11x | 477 104 / 2 925 610 | tabell 2021-04-12 (perp, 0625, 0924) |
| DOT | 19 | 10,00; 9,77–10,32 | 11x | 78 260 / 954 410 | endast maxhävstång |
| LINK | 20 | 10,00; 9,67–10,42 | 11x | 219 438 / 1 105 210 | endast maxhävstång |
| LTC | 19 | 10,00; 9,80–10,29 | 11x | 317 031 / 2 448 995 | endast maxhävstång |
| XRP | 19 | 10,01; 9,71–10,34 | 11x | 224 102 / 1 868 540 | endast maxhävstång |

Serieräkningen är de 135 serier med data före 2025 från `coinm-pit-series.json`.

## Modellen (låst som förslag)

Specifikationen finns som körbar kod med syntetiska tester i `engine/traderlab/basis_costs.py` och `tests/test_basis_costs.py`.
**`pre_expiry_cycle` är förslaget** (utträde 7 dagar före förfall). `hold_cycle` är en **annan modell** (hållen till förfall med avräkning) och ska inte
användas för förslaget.

1. **Hela kapitalet och coin-marginalen räknas** (i `pre_expiry_cycle`, med separata spot- och terminspriser vid in- och utträde). Kapitalet C (USD) köper X mynt på spot (avgift och glidning ingår), mynten läggs
   som marginal, avgiften för att sälja kontrakten dras i **mynt**, och kontraktsantalet avrundas **ned** så att
   `notional ≤ marginal efter öppningsavgift` (effektiv hävstång ≤ 1). Allt bokförs i mynt (PnL = n · storlek · (1/in − 1/ut) för en kort
   position) och slutvärdet i USD tas först när spotbenet säljs (avgift och glidning ingår). Det är motsatsen till H-0020:s förenkling,
   där en förlängning gav hävstång utan att kapitalet räknades. Testerna visar: utan avgifter är avkastningen exakt basis; med avgifter är den
   negativ när det inte finns någon basis (inget "gratis" resultat); effektiv hävstång ≤ 1 även med avgifter.
2. **Likvidation är strukturellt avstängd vid 1x men kontrolleras ändå.** Vid full täckning är marginalkvoten lika med underhållsnivån
   oavsett pris (testad för priser från 0,2× till 20×). Med den antagna nivån 50 % blir kvoten 0,5, under stoppet 0,8. Kontrollen finns kvar
   som skydd mot avrundning och avgiftsdrift och körs på dagens högsta markpris.
3. **Avrundningsresten är en verklig prisexponering vid litet kapital.** Ett kontrakt är 10 USD, alltså ungefär 1 % av 1 000 USD. Testet visar
   att utfallen då skiljer sig mer än 1 procentenhet mellan stigande och fallande pris. Låst regel: restmynt redovisas som mynt
   (inte ignoreras), och positionens värde per underliggande ska vara minst 10 000 USD (ett kontrakt högst 0,1 %).
4. **Kostnadsbudget:** spot-köp 15 bp (10 avgift + 5 glidning), termin-sälj 10 bp, terminsutträde 10 bp, spot-sälj 15 bp = **50 bp per cykel**
   (avgifter 30 bp plus glidning 20 bp). Stresstest 2,5× = **125 bp**. Hållen till förfall: 45 bp, eftersom avräkningen bara kostar
   takeravgift. Siffrorna är kostnader, inte en prognos.
5. **Förutbestämt utträde (`pre_expiry_cycle`):** stäng båda benen vid dagens slut **7 kalenderdagar före förfall**. Terminen köps tillbaka till
   terminens senaste pris den dagen (`fut_exit`, inte en avräkningskurs) och spotbenet säljs till spotpriset den dagen (`spot_exit`), alla fyra
   ben med takeravgift och glidning. PnL i mynt = n · storlek · (1/`fut_exit` − 1/`fut0`), utträdesavgiften dras i mynt på notionellt värde vid
   `fut_exit`. Rulla till nästa serie bara om den är valbar enligt `universe_at` den dagen. Utträdesdagen är fastlagd av kalendern, inte av pris.
   **Test:** utan avgifter är avkastningen exakt `(fut0/spot0) · (spot_exit/fut_exit) − 1` för olika prisvägar, och vid noll basis är den bokförda
   kostnaden 50 bp (stress 2,5× ger 124,2 bp; budgeten är additiv och därför en övre gräns inom 1 bp).
   **Förfallsvarianten (`hold_cycle`) är en annan modell** med ett slutpris (avräkning) och 45 bp; den används inte av förslaget. Vill en senare
   förregistrering hålla till förfall kan avräkningskursen beräknas både som timmesmedel och som 30-minutersmedel ur indexpris-minutstaplar för
   förfallodagen, och det sämre utfallet gäller. Det är ett eget, större arbete.

### Fail-closed (OGILTIG, inte MORE_RESEARCH)

* Ingen verifierad handelsstapel för serien på inträdes- eller utträdesdagen (inklusive spotbenet).
* Saknad markprisdag, saknad spotstapel, eller en luckfyllnad som inte verifierats.
* Härledd kontraktsstorlek utanför 9,5–10,5 för serien.
* Marginalkvot ≥ 0,8 på någon dag, eller effektiv hävstång över 1,0.
* Position över 2 % av medianvolymen, eller under 10 000 USD per underliggande.
* Beslutsdag utanför det biasfria fönstret 2021-03-26 till 2024-08-13 (se `coinm-pit-rapport.md`).

## Det som inte kan sägas

* **Statistisk styrka:** fönstret är cirka 3,4 år, alltså omkring 14 kvartalscykler, och de sju underliggande rör sig ihop. Det effektiva antalet
  oberoende utfall är litet. Ett nytt försök ger N = 22 och t-kravet 2,84 (nu 2,82). Ett positivt resultat vore svårt att skilja från slump, ett REJECT eller
  MORE_RESEARCH är det sannolika utfallet. Det är ett argument för att ändå registrera och se, inte för att hoppa över kravet.
* **Basisnivåerna är inte undersökta här.** Om kostnaderna (50 bp, stress 125 bp per cykel) är små eller stora i förhållande till basis vet jag
  inte, och får inte undersöka det före en registrering.
* **Spread och glidning är ett antagande.** Stresstestet ska visa om slutsatsen vänder vid 2,5× kostnad.
* **Motpart och exekvering:** inget om börsrisk, uttagsstopp, ADL eller att Binance ändrar regler.
* **H-0020 är REJECT:** samma period och börs är delvis sedda. Det här är ett nytt försök, inte en räddning av H-0020:s trösklar.

## Kvarvarande luckor (avgränsade)

1. Underhållsnivåerna per underliggande 2021-02 till 2021-05 (inte arkiverade). Täcks av det konservativa antagandet 50 %.
2. Avgiftens exakta startdag för 0,040 %. Täcks av 0,050 %.
3. Spotavgiften 2020–2024 för allmän nivå är inte belagd år för år. Täcks av 0,100 % utan rabatt.
4. Markprisfilernas innehåll är provat på en serie, inte alla 135. Ska kontrolleras (checksumma, giltiga staplar, luckor) i datasteget före en körning.
5. 0924-serien 2021 saknar daterad annons (kvarstår från PR #115) och används inte.

## Filer

* `engine/traderlab/basis_costs.py`: avgifter, kostnadsbudget, kontraktsstorlek ur data, `pre_expiry_cycle` (förslaget), `hold_cycle` (annan modell), `margin_ratio`.
* `engine/tests/test_basis_costs.py`: tester med syntetiska tal.
* `research/universe/coinm-implied-contract-size.json`: kontraktsstorlek härledd per serie (före 2025).
* `research/coverage/basis-sources-cost1-*.json`, `…cost2-*.json`: rådata från Binance-meddelandena (avgifter, marginaltabeller, spotavgifter).
