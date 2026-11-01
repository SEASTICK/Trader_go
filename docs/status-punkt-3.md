# Punkt 3: prisdiagram (candlesticks) i detaljvyerna

Status 2026-11-01, gren `integrate/punkt-3-diagram` (ovanpå PR #36, inte pushad).

## Vad som finns

- **`app/src/components/CandleChart.tsx`**, en gemensam komponent byggd på
  [Lightweight Charts](https://github.com/tradingview/lightweight-charts) 5.2.1 från TradingView
  (Apache-2.0). Appen hade inget diagrambibliotek tidigare; de befintliga diagrammen är handritad SVG
  utan zoom. TradingViews attributionslogga ligger kvar i hörnet, som licensen kräver.
  - **Utseende:** mörk yta med appens mörka färger, gröna och röda staplar med vekar, och volym i en egen
    panel.
  - **Interaktion:** zoom, panorering, crosshair, pris- och tidsaxel, och en rad med tid (UTC), OHLC, volym
    och om stapeln är stängd eller pågående.
  - **Data:** visar instrument, leverantör (Binance spot), tidsram och datastatus (insamlingens läge, och
    en varning när datan inte är färsk eller anslutningen är bruten).
  - **Indikatorer:** SMA 20, SMA 50 och EMA 20, beräknade från stängningspriset. Linjen är tom under
    uppvärmningen, och en text säger hur många staplar som saknas.
  - **Strömmen:** ingen egen anslutning. Staplarna läses med `market_bars`, sidvis bakåt när man
    panorerar, och uppdateras av insamlingens `market-bar`-händelser (punkt 2). Pågående stapel uppdateras
    på plats och en ny läggs till utan att zoomen nollställs. Uppdateringar ritas högst var 250:e ms, och
    alla prenumerationer städas vid byte av instrument eller tidsram.
  - **Märkning:** den pågående stapeln är halvgenomskinlig och märkt "pågående", och fotnoten påminner om
    att strategibeslut tas på stängda staplar. Chipet **REALTIDSDATA** med en förklaring visar att
    realtidspris inte betyder livehandel. Resultatet är fortfarande HISTORIK eller SIM.
  - **Tomt läge med förklaring:** i webbläsaren, för marknader utan datakälla, och för tidsramar som inte
    samlas in. Ingen simulerad ersättning. Tidsramsknapparna visar bara serier som datalagret har.
  - **Markörer:** bara riktiga affärer från registrerade backtest (`recent_trades` i HISTORIK-resultat), på
    stapeln där affären fylldes och där den stängdes. SIM-affärer visas aldrig, och inga mönsteretiketter
    eller dekorativa pilar finns.
- **`ExperimentDetail`:** flikarna **Marknad** (prisdiagrammet) och **Resultat** (kapitalutveckling mot
  baslinjen, oförändrad). Alla rutor i Research öppnar den här vyn, så alla använder samma komponent.
- **Backend:** `market_series`, `market_bars` (bara läsning, WAL) och händelsen `market-bar` från den
  befintliga insamlingen.

## Verifierat

| Vad | Hur |
|---|---|
| Logik | 9 nya tester i `candles.test.ts`: ordning och dubbletter, uppdatering på plats, ny stapel, äldre händelser ignoreras, äldre historik före, UTC, SMA/EMA mot handräkning, uppvärmning, marknad → serie, markörer bara inom datan. Hela gränssnittet: 32/32. |
| Backend | Rust 32/32, 20 körningar i rad gröna. Nytt: sidvis läsning bakåt och pågående stapel bara på första sidan, serielistan, och att stängda, pågående och resync-händelser når diagrammen (dubbletter skickas inte). |
| Rätt OHLCV | En stapel under crosshair (2026-10-17 00:00 UTC) stämmer exakt med databasen och med Binances REST (O 81615,91, H 81677,88, L 81416, S 81573,58, V 1195,3). Databasen: 1000 staplar, unika och stigande. |
| I den körande appen (macOS) | E-01 BTC 4h visar riktiga staplar, volympanel, SMA 20, läget "Ansluten" och den pågående stapeln. Crosshair och tooltip fungerar. Pågående stapel uppdaterades på plats utan att vyn ändrades. Resultat-fliken visar kapitalutveckling och baslinje som förut. E-02 BTC 1d visar tomt läge: "BTCUSDT 1d samlas inte in", med vilka tidsramar som finns. |

## Inte verifierat i appen

- **Klick på tidsrams- och indikatorknapparna, och zoom med mushjulet:** ett annat programs fönster låg
  över den delen av skärmen under provningen. Logiken är testad, men knapparna och mushjulet är inte
  provade för hand.
- **Byte mellan instrument utan gamla prenumerationer:** följer av att diagram, lyssnare och timer städas
  när serien byts (kod granskad). Inget automatiskt test av komponenten (inget testbibliotek för React i
  projektet).
- **Windows:** inte provat.

## Saknade dataanslutningar

- **Historisk OHLCV för backtestperioderna finns inte i appen.** Motorns månadsarkiv (`data/raw/`) ligger
  bara på den dator som hämtade dem. Därför ligger alla 20 affärer från H-0001 (2020–2024) utanför den
  data som finns, och inga markörer ritas. Det står i diagrammets fotnot.
- **Bara BTCUSDT 4h samlas in.** ETH, 1d och andra marknader (terminer, aktier, makro) visar tomt läge.
  Fler serier kräver fler insamlingar (punkt 2: `market/config.json` stöder en serie i taget).
- **Inga paper-händelser finns än**, så det finns inga live-signaler att visa. När paper-körning finns kan
  dess händelser ges till `trades` på samma sätt.
