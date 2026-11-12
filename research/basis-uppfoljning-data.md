# Data- och genomförbarhetsgranskning: oberoende uppföljning av kassa-och-termin (basis)

Skriven 2026-11-12 på uppdrag av granskaren (Codex, PR #110/#111). **Inget backtest är kört, inga avkastningar eller
basisnivåer är beräknade, och slutprovet 2025+ är inte hämtat.** Det enda som mätts är kontraktslistor, månadsfilernas
täckning, luckor och daglig volym. H-0020 är fortfarande `REJECT` (t 2,41 mot 2,81) och dess låsta trösklar är orörda.

**Rättelse (2026-11-12, efter granskning av PR #112):** en första version påstod att säkringen är ”deltaneutral i
myntets egen enhet” och att ett avtalat förfall gör att ”inga avnoteringar uppstår”. Båda påståendena var för starka och
är ersatta nedan. En COIN-M-short har invers PnL i mynt, så säkringen låser **USD-värdet** och inte antalet mynt, och
arkivet visar att Binance har upphört att lista nya kvartalskontrakt för flera underliggande.

## Svar

**Ja, men bara i begränsad mening, och med fyra villkor.**

- **Ja** för ett *delvis* oberoende test av en **USD-säkrad** kassa-och-termin: dagsdata för daterade COIN-M-terminer
  finns gratis för sju underliggande som H-0020 aldrig använde (ADA, BCH, BNB, DOT, LINK, LTC, XRP), 19 till 20 kontrakt
  vardera med data före 2025, utan saknade månadsfiler, med spot-referens för alla.
- **Nej** för ett *helt* oberoende test: ingen gratiskälla ger en annan period eller annan börs med historik (se källprov).
  Samma börs och period gör att baserna på olika mynt hänger ihop. Sju underliggande är inte sju oberoende satsningar.
- **Villkor 1, kostnader:** inga historiska spreadar finns gratis, och avgifterna är inte verifierade mot primär källa.
  Kostnaderna måste därför bestämmas i förväg som en konservativ regel som beror på volymen.
- **Villkor 2, datalucka:** alla COIN-M-kontrakt som levde 2023-08-28 till 2023-08-31 saknar dessa fyra dagar. Binance
  API svarar 451 från GitHubs servrar och kan inte fylla dem (kringgås inte). Ett protokoll måste före körning ange hur
  en lucka behandlas, annars blir körningen `OGILTIG` enligt fail-closed-regeln från PR #111.
- **Villkor 3, kapacitet:** de sju har ungefär 0,9 till 2,9 miljoner USD i mediandagsvolym i närmaste kontrakt och
  78 000 till 477 000 USD på sämsta tiondelen av dagarna. Ett test är genomförbart bara med små belopp.
- **Villkor 4, förtida upphörande:** produktlinjer har upphört i arkivet (se Risker). Ett protokoll måste ange vad som
  gäller om ett kontrakt inte kan rullas eller avslutas, utan efterhandsurval av underliggande.

## Säkringens ekonomi (rättad)

**Primära källor (lästa).** Binances egna hjälpartiklar om PnL och om marginal, hämtade från Binances publika
artikel-API på GitHubs servrar (de två sidor som granskaren länkade till). Utdragen finns i
`research/coverage/basis-sources-runner5-*.json` (`faq_pnl`, `faq_margin_liquidation`). Sidorna visar inget datum i texten.

- ”A BTC COIN-M Futures contract is denominated, collateralized, and settled in Bitcoin … Each BTC COIN-M contract represents 100 USD and as such, USD is the counter currency.”
- ”Unrealized PNL = Contract Size * Contract Multiplier * Absolute value of Position * Direction of Order * (1 / Entry Price - 1 / Mark Price)”
- Binances eget exempel för en short: ”((1 / Futures Entry Price) - (1 / Futures Exit Price)) * (Contract Size * -1) ((1/50,000) - (1/45,500)) * (100 contracts * 100 USD * -1) = 0.0198 BTC”. Kursen faller och shorten **ökar antalet mynt**.
- ”unrealized profit and loss are calculated based on the Mark Price, while realized profit and loss are calculated based on the Last Price.”
- ”In Cross Margin Mode, margin can only be shared with the same type of asset. For example, all BTC in the COIN-M Futures Wallet can be used for all BTC-based contracts (including perpetual and delivery) within Cross Margin Mode.” Initial Margin Rate = 1 / Leverage.
- ”All of your margin balance may be liquidated in the event of adverse price movement.”

**Vad det betyder.** En invers short har resultatet n · kontraktsstorlek · (1/F1 − 1/F0) i **mynt**. Att äga X mynt (som
också är marginalen) och sälja n kontrakt med n · storlek = X · F0 låser alltså **USD-värdet X · F0**, medan antalet
mynt ändras med kursen. Det är en USD-säkring (och därmed en lås-in av premien i USD), inte en konstant myntposition.
Matematiken stämmer under antaganden som exemplet visar: konvergens vid förfall (F1 = S1), heltalskontrakt, inga
avgifter (inte verifierade) och ingen förtida likvidation. Utfallen beror på hur väl kontrakten täcker positionen.

**Numeriskt exempel** (beräknat av `traderlab.basis_example`, testat): spot 100, terminspris 102 (premie 2 %).

| Fall | Kurs vid förfall | Mynt vid förfall | USD-värde | Avkastning på spot-kostnaden | Marginalkvot |
|---|---|---|---|---|---|
| 10 mynt, 102 kontrakt (exakt säkring) | 150 | 6,800 | 1020,00 | 2,00% | 1,000 |
| 10 mynt, 102 kontrakt (exakt säkring) | 100 | 10,200 | 1020,00 | 2,00% | 1,000 |
| 10 mynt, 102 kontrakt (exakt säkring) | 50 | 20,400 | 1020,00 | 2,00% | 1,000 |
| 7 mynt, 71 kontrakt (heltalsavrundning) | 150 | 4,773 | 715,88 | 2,27% | 1,008 |
| 7 mynt, 71 kontrakt (heltalsavrundning) | 100 | 7,139 | 713,92 | 1,99% | 1,006 |
| 7 mynt, 71 kontrakt (heltalsavrundning) | 50 | 14,239 | 711,96 | 1,71% | 1,003 |

- Exakt säkring: USD-värdet blir 1 020 oavsett kurs (premien 2 % på spot-kostnaden 1 000), men antalet mynt är 6,8, 10,2
  eller 20,4. Marginalkvoten (equity i mynt delat med positionens värde i mynt) är 1,0 i alla fall, vilket är 1× täckning.
- Heltalsavrundning: 7 mynt kräver 71,4 kontrakt, och 71 lämnar en rest. USD-utfallet följer då kursen något (715,88 mot
  711,96 mellan kurserna 150 och 50). Små positioner i dyra kontrakt (10 USD per kontrakt) ger relativt stor avrundning.
- En halv säkring skulle följa kursen kraftigt (testat). Hedge-kvoten är alltså en parameter som ett protokoll måste låsa.

## Vald riktning (en)

**USD-säkrad kassa-och-termin över de sju nya underliggande på Binance COIN-M (daterade kvartalsterminer), med
spot-referens, 2020-12 till 2024-12 och slutprovet 2025+ orört.**

Ekonomisk motivering: en daterad termin som handlas över spot ersätter dem som vill ha belånad exponering, och premien
konvergerar mot noll vid förfall. Säkringen i exemplet låser premien i USD vid ingången, och mer än ett par underliggande
ger fler cykler än H-0020. **Det är en motivering, inte ett belägg:** premiens storlek efter kostnader är exakt det som
inte är mätt här och som testet ska pröva. Vad som inte avgörs här: tröskel för att gå in, positionsstorlek och hedge-kvot,
kostnadsregel, hantering av luckan och av förtida upphörande. De ska bestämmas i ett protokoll före körning, av extern
grund och inte utifrån H-0020:s utfall.

Inte vald: COIN-M BTC och ETH (samma underliggande och period som H-0020, alltså inte oberoende), BTC/ETH i USDⓈ-M
(redan använda), och alla andra källor (se nedan).

## Risker som ett protokoll måste hantera utan efterhandsurval

| Risk | Belägg | Vad protokollet måste ange i förväg |
|---|---|---|
| **Förtida upphörande av produktlinje** | I arkivet har EOS, ETC, FIL och TRX bara två kontrakt (2020-12-25 och 2021-03-26), och ADA, BCH, DOT, LINK och LTC har inget kontrakt med förfall efter 2025-09-26, medan BTC, ETH, BNB och XRP fortsätter till 2026-12. Orsaken är **inte verifierad** mot någon primär källa (utvecklardokumentationen gav 0 tecken). | Vilka underliggande som ingår bestäms av en regel före körning (till exempel minst ett visst antal kontrakt i arkivet vid beslutstillfället), aldrig av vad som senare hänt. Hur ett kontrakt som inte kan rullas stängs, och att en sådan händelse inte får värderas med en kurs som inte gick att handla till (jämför H-0021, PR #111). |
| **Basisrisk före förfall** | Orealiserat resultat räknas på Mark Price och realiserat på Last Price (Binance). Terminspriset kan avvika från spot innan förfall. | Hur positionen värderas under livet (mark mot spot), och att utfallet bara redovisas vid förfall eller rullning enligt en förhandsregel. |
| **Marginal och likvidation** | Binance använder en ”Maintenance Margin model” med nivåer på sidan ”Leverage & Margin”, som **inte är läst**. Likvidationsregeln och underhållsmarginalen är därför inte verifierade. | Ett eget, konservativt likvidationsantagande med tydlig etikett (som i H-0021:s protokoll), eller en bedömning av avståndet till likvidation vid 1× täckning. Exemplets marginalkvot 1,0 är min egen räkning och **inte verifierad** mot Binances regler. |
| **Heltalskontrakt** | Kontraktsstorlek är 100 USD för BTC (bekräftad). Övriga **10 USD är inte bekräftat**. | Hur många kontrakt som säljs (avrundning) och att resten redovisas som kvarvarande prisexponering. |
| **Datalucka 2023-08-28 till 2023-08-31** | Alla COIN-M-kontrakt som levde då saknar fyra dagar. Binance API svarar 451. | Hur positioner som hålls över luckan värderas, utan att fylla med sista kända värde. Annars `OGILTIG`. |
| **Staplar efter förfall** | Kontrakt har staplar med noll volym efter förfallodagen (till exempel BTCUSD_230929 till 2023-10-05). | Att staplar efter förfallodagen ignoreras. |
| **Börs- och platsrisk** | API:et svarade 451 från GitHubs servrar. Motpartsrisk finns inte i ett backtest. | Att resultatet inte säger något om en viss användares tillgång eller om motparten. |

## Vad som redan setts

| Data | Använd i | Status |
|---|---|---|
| BTC- och ETH-kvartalsterminer i USDⓈ-M, 2021-02 till 2024-12 | H-0020 | sedd |
| BTC och ETH spot, alla perioder | H-0001 till H-0021 | sedd |
| Spot- och evighetsterminspriser för ADA, BCH, DOT, LINK, LTC m.fl., 2021–2024 | H-0014, H-0015, H-0018, H-0019, H-0021 | **sedda** (som USDⓈ-M-evighetsterminer) |
| Daterade COIN-M-terminspriser (alla underliggande) | ingen | **osedda**: bara antal staplar, luckor och volym är mätta, inga avkastningar eller basis |
| 2025-01 och framåt | ingen | **orört**: inga filer från 2025 eller senare är hämtade |

Alltså: själva baspriserna på de sju är osedda, men prisrörelserna i deras underliggande är sedda.

## Källor och täckning (genererade tabeller)

Tabellerna skapas av `python -m traderlab.data.basis_report` (från `engine/`) ur rapportfilerna i
`research/coverage/`. Rapportfilerna skapas av `python -m traderlab.data.basis_sources` (Binance, från Claudes sandlåda) och av
workflowet `.github/workflows/basis-data-survey.yml` (övriga källor, på GitHubs servrar).

## Källprov

| Källa | Nåbar | Vad som svarade |
|---|---|---|
| binance | ja | USDⓈ-M: 3 underliggande, COIN-M: 14 underliggande (detaljer nedan) |
| deribit | ja | BTC: 1 utgånget kontrakt via API; ETH: 1 utgånget kontrakt via API |
| bitmex | nej | HTTPError: HTTP Error 403: Forbidden |
| bybit | ja | 2033 symboler listade, 789 med datum i namnet (affärsfiler) |
| bitstamp | ja | tomt svar (första provet hade fel startdatum) |
| fred | nej | TimeoutError: The read operation timed out |
| okx | ja | 11 aktiva BTC-USD-terminer, 0 dagsstaplar för utgånget kontrakt |
| bitmex_files | ja | 20170331: nej (HTTPError: HTTP Error 403: For), 20200327: nej (HTTPError: HTTP Error 403: For), 20241227: nej (HTTPError: HTTP Error 403: For) |
| bitstamp | ja | BTC/USD dagsstaplar från 2011-09-13 |
| fred_text | nej | TimeoutError: The read operation timed out |
| bitmex_api | nej | HTTPError: HTTP Error 403: Forbidden |
| binance_api | ja | BTCUSD_230929: HTTPError: HTTP Error 451: ; ETHUSD_230929: HTTPError: HTTP Error 451:  |
| fred_text | nej | TimeoutError: The read operation timed out |
| binance_docs | ja | delivery_api_docs: läsbar (64 tecken); faq_pnl: läsbar (18625 tecken); faq_margin_liquidation: läsbar (17192 tecken) |
| binance_docs | ja | developers_exchange_information: läsbar (0 tecken); faq_pnl: läsbar (5312 tecken); faq_margin_liquidation: läsbar (4618 tecken) |

## Daterade terminer hos Binance

| Marknad | Underliggande | Kontrakt | Första förfall | Sista förfall | Kontrakt med saknade månader | Spot-referens (USDT) från |
|---|---|---|---|---|---|---|
| USDⓈ-M | BTC | 25 | 2021-03-26 | 2027-03-26 | 0 | 2017-08 |
| USDⓈ-M | BTCB | 2 | 2021-01-29 | 2021-02-26 | 0 | – |
| USDⓈ-M | ETH | 25 | 2021-03-26 | 2027-03-26 | 0 | 2017-08 |
| COIN-M | ADA | 21 | 2020-09-25 | 2025-09-26 | 0 | 2018-04 |
| COIN-M | BCH | 20 | 2020-12-25 | 2025-09-26 | 0 | 2019-11 |
| COIN-M | BNB | 25 | 2020-12-25 | 2026-12-25 | 0 | 2017-11 |
| COIN-M | BTC | 26 | 2020-09-25 | 2026-12-25 | 0 | 2017-08 |
| COIN-M | DOT | 20 | 2020-12-25 | 2025-09-26 | 0 | 2020-08 |
| COIN-M | EOS | 2 | 2020-12-25 | 2021-03-26 | 0 | 2018-05 |
| COIN-M | ETC | 2 | 2020-12-25 | 2021-03-26 | 0 | 2018-06 |
| COIN-M | ETH | 26 | 2020-09-25 | 2026-12-25 | 0 | 2017-08 |
| COIN-M | FIL | 2 | 2020-12-25 | 2021-03-26 | 0 | 2020-10 |
| COIN-M | LINK | 21 | 2020-09-25 | 2025-09-26 | 0 | 2019-01 |
| COIN-M | LTC | 20 | 2020-12-25 | 2025-09-26 | 0 | 2017-12 |
| COIN-M | SOL | 10 | 2024-09-27 | 2026-12-25 | 0 | 2020-08 |
| COIN-M | TRX | 2 | 2020-12-25 | 2021-03-26 | 0 | 2018-06 |
| COIN-M | XRP | 25 | 2020-12-25 | 2026-12-25 | 0 | 2018-05 |

## Handelsbarhet, COIN-M (närmaste kontrakt med mer än 14 dagar kvar, volym i USD)

| Underliggande | Kontrakt med data före 2025 | Dagsstaplar | Saknade dagar | Dagar med närmaste kontrakt | Median USD/dag | P10 USD/dag | Andel nollvolym |
|---|---|---|---|---|---|---|---|
| BTC | 20 | 3320 | 8 | 1579 | 137 065 900 | 27 827 860 | 0.0% |
| ETH | 20 | 3320 | 8 | 1579 | 76 528 040 | 15 108 420 | 0.0% |
| ADA | 20 | 3315 | 8 | 1579 | 1 307 640 | 189 592 | 0.0% |
| BCH | 19 | 3024 | 8 | 1486 | 1 178 315 | 92 250 | 0.0% |
| BNB | 19 | 3082 | 8 | 1515 | 2 925 610 | 477 104 | 0.0% |
| DOT | 19 | 3082 | 8 | 1515 | 954 410 | 78 260 | 0.0% |
| LINK | 20 | 3315 | 8 | 1579 | 1 105 210 | 219 438 | 0.0% |
| LTC | 19 | 3028 | 8 | 1488 | 2 448 995 | 317 031 | 0.0% |
| XRP | 19 | 3030 | 8 | 1489 | 1 868 540 | 224 102 | 0.0% |

## Tolkning av källproven

| Källa | Slutsats |
|---|---|
| Binance USDⓈ-M | Bara BTC och ETH har kvartalsterminer (från 2021-03-26). De är H-0020:s data. Två BUSD-marginerade månadskontrakt (januari och februari 2021) finns också (underliggande `BTCB`). |
| Binance COIN-M | **Användbar.** Nio underliggande har minst 20 kontrakt (BTC och ETH samt sju nya: BNB, ADA, BCH, DOT, LINK, LTC och XRP). EOS, ETC, FIL och TRX har bara två kontrakt och SOL börjar 2024-09: för korta. |
| Deribit | **Inte genomförbar gratis.** Det publika API:et listar bara ett utgånget kontrakt per valuta, alltså ingen historik. |
| OKX | **Inte genomförbar.** Inga dagsstaplar för utgånget kontrakt via det publika API:et. |
| Bybit | **Inte tillräcklig.** Bara affärsfiler (inga dagsstaplar). Provet visade 789 symboler med datum i namnet, men inte hur långt bak historiken går, så ingen längre historik kan antas. |
| BitMEX | **Inte nåbar.** Både API och publika datafiler svarade 403 från GitHubs servrar. Det kringgås inte. |
| Binance FAQ (PnL, marginal) | **Läsbar** via Binances publika artikel-API från GitHubs servrar (5 312 och 4 618 tecken). Det är källan till formlerna nedan. Utvecklardokumentationen (kontraktsstorlek, förfallsfält, avnotering) gav 0 tecken (sidan bygger på JavaScript) och är **inte läst**. |
| Binance API (för att fylla luckan) | **Inte nåbar.** 451 (spärrad plats) från GitHubs servrar. |
| Bitstamp | Spot-historik för BTC/USD från 2011-09, men det finns ingen gratis terminshistorik att para med. |
| FRED (statsväxelränta) | **Inte nåbar** från GitHubs servrar (tidsgräns). H-0020:s fasta tröskel på 3 % per år har ingen extern källa i den här granskningen. |

## Verifierat och inte verifierat

| Uppgift | Status |
|---|---|
| COIN-M är denominerad, säkrad med marginal och avräknad i mynt; BTC-kontrakt är 100 USD | **Verifierat** (Binances hjälpartikel) |
| PnL-formel för invers kontrakt, inklusive exempel för en short | **Verifierat** (samma artikel) |
| Orealiserat resultat på Mark Price, realiserat på Last Price | **Verifierat** |
| Korsad marginal delas mellan kontrakt av samma mynt, Initial Margin Rate = 1 / hävstång | **Verifierat** |
| Kontraktsstorlek för övriga mynt (10 USD) | **Inte verifierat** (bara BTC står i artikeln). Antaget i volymmåttet. |
| Avgifter för spot och COIN-M (grundnivå) | **Inte verifierat.** Avgiftssidan är inte läst. |
| Underhållsmarginalnivåer, likvidationsregel, hävstångstrappor | **Inte verifierat.** Sidan ”Leverage & Margin” är inte läst. |
| Avräkningspris, förfallotid, och regler för att Binance kan avsluta eller avnotera kontrakt | **Inte verifierat.** Utvecklardokumentationen gav 0 tecken. |
| Historiska spreadar och orderböcker för daterade kontrakt | **Inte tillgängligt gratis** |
| Statsväxelränta (FRED) | **Inte nåbar** från GitHubs servrar |

Det som inte är verifierat måste läsas från Binances primära sidor, av någon med åtkomst till dem, innan ett protokoll låser
kostnader, marginal eller kontraktsstorlekar. Sidorna blockeras för Claudes webbhämtare (DNS) och från Claudes sandlåda.

## Datakvalitet värd att veta

- **Lucka 2023-08-28 till 2023-08-31:** gemensam för alla COIN-M-kontrakt som levde då (kontrakten med förfall
  2023-09-29 och 2023-12-29, 4 dagar var). Det är samma sorts lucka som drabbade H-0021 (2022-02-26 i USDⓈ-M-evighetsterminer).
- **Staplar efter förfall med noll volym** finns (till exempel BTCUSD_230929 till och med 2023-10-05). Ett protokoll måste
  säga att staplar efter förfallodagen ignoreras.
- Att alla månadsfiler finns betyder inte att dagarna är kompletta: luckorna ovan hittades på dagsnivå.

## Avgränsning och reproducerbarhet

- Nedladdade data: COIN-M 1d-staplar för de nio underliggande med minst 20 kontrakt, månader 2020-08 till 2024-12
  (1 118 filer, inga från 2025 eller senare). De är checksummeverifierade av `binance.fetch` och noterade i `data/MANIFEST.md`.
- Mätt: antal staplar, saknade dagar, nollvolymdagar och volym i USD för närmaste kontrakt med mer än 14 dagar kvar.
- Inte mätt: avkastning, basis, signaler eller något som liknar ett backtest. Exemplet ovan är algebra med påhittade
  priser och använder ingen data.
- Inget av detta ändrar H-0020, H-0021 eller något protokoll.
