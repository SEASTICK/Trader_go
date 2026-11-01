# Rekommendation 3: verklig marknadsdata i TraderGO

Status 2026-11-01, gren `integrate/rek-3-marknadsvy` (ovanpå PR #40, inte pushad). Bygger på punkt 2
([marknadsdata.md](marknadsdata.md), [status-punkt-2.md](status-punkt-2.md)) och punkt 3
([status-punkt-3.md](status-punkt-3.md)). Ingen bred ombyggnad: det mesta fanns redan.

**Kan markeras klar på macOS när PR #40 är sammanslagen.** Den installerade Mac-appen visar riktig
BTCUSDT spot 4h med candlesticks, volym, tider och status. Windows-bygget och Rust-testerna går i CI,
men ingen har kört appen på en Windows-dator.

## Inventering: vad som redan fanns

| Krav | Var | Status |
|---|---|---|
| Datalager och insamling | `app/src-tauri/src/market/` (punkt 2) | Verifierat: mocktester, riktigt nät, paketerad app, Rust-tester på Windows i CI (#36) |
| Brygga motor ↔ app | Insamlingen i Rust skriver SQLite i appens datamapp; motorn läser med `traderlab.data.live` | Verifierat (5 Python-tester, `quality.check` på appens data) |
| Ingen Python i installerad app | Insamlingen körs i appens egen process | Verifierat: appen startar och samlar utan terminal eller Python |
| Gemensamt prisdiagram | `components/CandleChart.tsx` under fliken Marknad (punkt 3) | Verifierat i appen; OHLC stämmer mot Binance |
| Resultatvyn kvar | Fliken Resultat i `ExperimentDetail` | Verifierat i appen |

## Typade meddelanden (app ↔ gränssnitt)

| Meddelande | Typ (Rust → TS) | Kanal |
|---|---|---|
| Historiska staplar | `BarsPage { bars, live, has_more }` | kommandot `market_bars` (sidvis bakåt) |
| Pågående stapel | `BarEvent { kind: "live", bar }` | händelsen `market-bar` |
| Stängd stapel | `BarEvent { kind: "closed", bar }` | händelsen `market-bar` |
| Läs om efter REST-ikappkörning | `BarEvent { kind: "resync" }` | händelsen `market-bar` |
| Status | `Status { state, ready, last_received_at, last_event_time, last_closed_open_time, … }` | händelsen `market-status`, kommandot `market_status`, filen `market/status.json` |
| Fel | `Status { state: "error", message }`; kommandon ger `Err(String)` | som status |

Typerna finns i `market/runner.rs`, `market/store.rs` och `market/status.rs`, och i
`src/lib/candles.ts` och `features/market/useMarketStatus.ts`.

## Ändrat i den här omgången

- **`lib/barSubscription.ts`** (ny), prenumerationen på `market-bar` utbruten ur diagrammet:
  - filtrerar på serie;
  - samlar händelser och ritar högst var 250:e ms, och läser om vid `resync`;
  - städar garanterat, också om man lämnar vyn innan lyssnaren hunnit kopplas in.

  Diagrammet använder den.
- **Diagrammet** visar *senast mottagen händelse* och *senaste stängda stapel* var för sig, i UTC, och
  lokal tid är märkt "(lokal tid)". Vid avbrott ligger senast kända data kvar under en tydlig varning.
- **Status-sidan** märker lokal tid.

## Märkning

| Märke | När |
|---|---|
| SIM | Påhittade rutor och demonstrationer. |
| HISTORIK | Backtest på historisk data. |
| REALTIDSDATA | Diagrammet under Marknad (aktuell feed från datalagret). Säger uttryckligen att det inte är livehandel. |
| PAPER | Används inte än: det finns ingen paper-session kopplad till marknadsdatan. Philips Papper-sida loggar pappersaffärer för hand, och den märkningen ändras inte här. |

## Verifiering

| | Vad | Resultat |
|---|---|---|
| Mocktester | Gränssnitt: 38/38. Nytt: 5 prenumerationstester (serie, takt, resync, städning, städning före inkoppling, byte av tidsram). Rust i #40: 44 plus 4 signaturtester, fmt och clippy rena. | Gröna |
| Riktig dataanslutning | Den installerade appen är `connected`, redo, 1000 stängda staplar, 0 återanslutningar | OK |
| Paketerad app (macOS) | Byggd från den här grenen och installerad. Startar, och Philips Papper-sida finns i menyn. | OK |
| Visuell granskning | Tidigare omgång (punkt 3): diagram, volym, crosshair, tooltip, Resultat-fliken och tomt läge granskade. Den här omgångens nya rad är inte granskad: skärmen låstes. | Delvis |
| Windows | CI bygger och kör Rust-testerna (#36 grön, #40 körs). Ingen Windows-dator provad. | Ej verifierat i appen |

## Återstående blockerare

1. **PR #40 måste slås ihop** för att detta ska finnas på `main` (och nå Philip via en release).
2. **En release med Mac-fil** behövs för att Edwins installerade app ska uppdatera sig själv.
3. **Windows på riktig dator** är inte provat.
4. **Historisk OHLCV för backtestperioderna saknas i appen**, så backtest-markörer syns sällan (se status-punkt-3).

## Starta

- **Installerad app:** öppna TraderGO och gå till Research, välj en ruta (till exempel BTC 4h) och sedan
  fliken **Marknad**. Status → Marknadsdata visar insamlingens läge.
- **Från källkod:** `npm --prefix app ci && npm --prefix app run tauri dev`.
- **Data:** macOS `~/Library/Application Support/com.seastick.tradergo/market/`, Windows
  `%APPDATA%\com.seastick.tradergo\market\`.
