# Data- och genomförbarhetsgranskning: oberoende uppföljning av kassa-och-termin (basis)

Skriven 2026-11-12 på uppdrag av granskaren (Codex, PR #110/#111). **Inget backtest är kört, inga avkastningar eller
basisnivåer är beräknade, och slutprovet 2025+ är inte hämtat.** Det enda som mätts är kontraktslistor, månadsfilernas
täckning, luckor och daglig volym. H-0020 är fortfarande `REJECT` (t 2,41 mot 2,81) och dess låsta trösklar är orörda.

## Svar

**Ja, men bara i begränsad mening, och med tre villkor.**

- **Ja** för ett *delvis* oberoende test: dagsdata för daterade COIN-M-terminer finns gratis för sju underliggande
  tillgångar som H-0020 aldrig använde (ADA, BCH, BNB, DOT, LINK, LTC, XRP), 19 till 20 kontrakt vardera med data före
  2025 (förfall sedan 2020-09 respektive 2020-12), utan saknade månadsfiler, med spot-referens för alla.
- **Nej** för ett *helt* oberoende test: ingen gratiskälla ger en annan period eller annan börs med historik (se källprov).
  Samma börs, samma period och samma marknads belåningsutbud gör att baserna på olika mynt hänger ihop. Sju
  underliggande är inte sju oberoende satsningar.
- **Villkor 1, kostnader:** inga historiska spreadar eller orderböcker finns gratis. Kostnaderna måste därför bestämmas
  i förväg som en konservativ regel som beror på volymen, och kan inte kalibreras mot verkliga spreadar.
- **Villkor 2, datalucka:** alla COIN-M-kontrakt som levde 2023-08-28 till 2023-08-31 saknar dessa fyra dagar. Binance
  officiella API svarar 451 från GitHubs servrar och kan inte fylla dem (kringgås inte). Ett protokoll måste före
  körning ange hur en lucka behandlas. Annars blir körningen `OGILTIG` enligt den fail-closed-regel som infördes i
  PR #111.
- **Villkor 3, kapacitet:** de sju har ungefär 0,9 till 2,9 miljoner USD i mediandagsvolym i närmaste kontrakt och
  78 000 till 477 000 USD på sämsta tiondelen av dagarna. Ett test är genomförbart bara med små belopp.

## Vald riktning (en)

**Myntmarginerad kassa-och-termin över de sju nya underliggande på Binance COIN-M (daterade kvartalsterminer), med
spot-referens, 2020-12 till 2024-12 och slutprovet 2025+ orört.**

Ekonomisk motivering: en daterad termin som handlas över spot ersätter dem som vill ha belånad exponering, och
premien försvinner vid förfall. En myntmarginerad säkring (äg myntet, sälj terminen) är deltaneutral i myntets egen
enhet och behöver inget stabilmyntsben, och förfallet är avtalat, så inga avnoteringar uppstår som i H-0021.
H-0020:s problem var få satsningar och låg avkastning efter kostnader, och fler underliggande ger fler cykler.
Vad som inte avgörs här: tröskel för att gå in, positionsstorlek, kostnadsregel och hantering av luckan. De ska
bestämmas i ett protokoll före körning, av extern grund och inte utifrån H-0020:s utfall.

Inte vald: COIN-M BTC och ETH (samma underliggande och period som H-0020, alltså inte oberoende), BTC/ETH i USDⓈ-M
(redan använda), och alla andra källor (se nedan).

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
| Binance API (för att fylla luckan) | **Inte nåbar.** 451 (spärrad plats) från GitHubs servrar. |
| Bitstamp | Spot-historik för BTC/USD från 2011-09, men det finns ingen gratis terminshistorik att para med. |
| FRED (statsväxelränta) | **Inte nåbar** från GitHubs servrar (tidsgräns). H-0020:s fasta tröskel på 3 % per år har ingen extern källa i den här granskningen. |

## Kostnader och marginal: vad som inte gick att verifiera

Följande är **inte hämtat och inte verifierat härifrån** och ska kontrolleras mot Binances dokumentation före ett protokoll:
avgifter för spot och COIN-M (grundnivå), kontraktsstorlekar (BTC 100 USD och övriga 10 USD är antaget i volymmåttet),
marginalkrav och likvidationsregler för COIN-M, och eventuella begränsningar för användare i vissa länder (API:et gav 451
från GitHubs servrar, vilket också visar att tillgängligheten beror på plats). Spreadar och orderböcker finns inte gratis
för historiska daterade kontrakt. Volym i USD är därför det enda handelsbarhetsmåttet, och det säger inget om hur stor
glidningen blir.

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
- Inte mätt: avkastning, basis, signaler eller något som liknar ett backtest.
- Inget av detta ändrar H-0020, H-0021 eller något protokoll.
