# Marknadsdata i TraderGO

TraderGO samlar in publik marknadsdata för **BTCUSDT spot, 4h** från Binance och sparar den lokalt.
Inga nycklar, inget konto, inga order. Allt är historik och papper.

## Källa

| | Adress | Dokumentation |
|---|---|---|
| REST (bara marknadsdata) | `https://data-api.binance.vision/api/v3/klines`, `/api/v3/time` | [Market data only](https://developers.binance.com/docs/binance-spot-api-docs/faqs/market_data_only) |
| WebSocket (bara marknadsdata) | `wss://data-stream.binance.vision:443/ws/btcusdt@kline_4h` | [WebSocket streams](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams) |

Regler som koden följer:
- `klines`: högst 1000 per anrop, vikt 2. Gräns 6000 vikt per minut. Vid HTTP 429 eller 418 väntar
  insamlingen så länge som `Retry-After` anger, och den pausar självmant när använd vikt närmar sig 4800.
- Strömmen skickar ungefär varannan sekund. Servern pingar var 20:e sekund och kopplar ner om ingen
  pong kommer inom en minut. En anslutning lever högst 24 timmar, och `serverShutdown` varnar för
  planerade avbrott.
- Tider är millisekunder i UTC. Mikrosekunder (värden över 10^14) räknas om till ms.

Kan källan inte nås visar Status felet. Insamlingen byter aldrig källa i tysthet och faller aldrig
tillbaka på simulerad data.

## Hur det fungerar

Koden finns i `app/src-tauri/src/market/` och körs i appens egen process, så det behövs ingen Python
eller andra utvecklingsverktyg i den installerade appen.

1. **Uppstart:** strömmen ansluts först, så att händelser som kommer under hämtningen väntar i
   socketbufferten. Sedan hämtas historiken via REST, från senaste sparade stängda stapel. Vid första
   start hämtas uppvärmningen, `warmup_bars`, standard 1000. Det räcker inte garanterat för en strategi:
   behovet ska räknas ut från strategins längsta fönster när en strategi körs live.
2. **Ihopslagning:** varje stapel har nyckeln leverantör, marknad, symbol, tidsram och öppningstid.
   Upprepade och felordnade meddelanden ändrar ingenting. Den pågående stapeln sparas separat
   (`live_bar`) och är aldrig analysunderlag. En stapel blir stängd när strömmen säger `x: true`, eller
   när REST visar att dess sista millisekund har passerat enligt serverns klocka.
3. **Luckor:** hoppar strömmen över en stapel, eller saknas staplar efter ett avbrott, hämtas de via
   REST innan datan markeras redo. Det som källan själv saknar sparas som en bekräftad lucka och fylls
   aldrig med påhittade värden.
4. **Rättelser:** en sparad stängd stapel skrivs aldrig över. Kommer den senare med andra värden sparas
   båda versionerna i `corrections`, och Status visar antalet. En människa avgör vad som gäller.
5. **Robust anslutning:** återanslutning sker med exponentiell backoff (1 s upp till 60 s, halva väntan
   slumpad). Följande räknas som avbrott, och efter varje avbrott hämtas missade staplar via REST:
   - strömmen tystnar i 30 s (justera med `stale_after_secs`);
   - väggklockan hoppar mot den monotona klockan, vilket betyder att datorn har sovit;
   - en stängd stapel har inte kommit inom tidsramen plus 2 minuter;
   - anslutningen närmar sig 24 timmar.
6. **Ett exemplar:** appen startar bara en gång. Dessutom finns `collector.lock`, så att två insamlare
   aldrig skriver samtidigt.
7. **Avslut:** när appen avslutas stängs anslutningen och läget blir `stopped`.

## Var datan sparas

| | Mapp |
|---|---|
| macOS | `~/Library/Application Support/com.seastick.tradergo/market/` |
| Windows | `%APPDATA%\com.seastick.tradergo\market\` |

| Fil | Innehåll |
|---|---|
| `market-data.sqlite` | Stängda staplar (`bars`), pågående stapel, rättelser, bekräftade luckor och hämtningslogg. Schema: `app/src-tauri/src/market/schema.sql`. |
| `status.json` | Maskinläsbar status, skriven atomiskt. |
| `config.json` | Valfri. Till exempel `{"provider":"binance","market":"spot","symbol":"BTCUSDT","interval":"4h","warmup_bars":1000}`. Stöds: BTCUSDT och ETHUSDT; 1m, 5m, 15m, 1h, 4h och 1d. Ett fel i filen ger läget `error`, ingen tyst standard. |
| `collector.lock` | Lås mot dubbla insamlare. |

Inget av detta ligger i Git, i appen eller i installationsmappen, och det finns kvar när appen uppdateras.

**Lagring och storlek:**
- Staplar sparas tills vidare. 4h-staplar är ungefär 2200 per år, några hundra kB.
- Hämtningsloggen behåller de senaste 5000 raderna.
- Bara en pågående stapel sparas per serie.

## Status

Status har följande lägen: `starting`, `syncing`, `connected`, `reconnecting`, `gap`, `stale`, `stopped` och
`error`. `ready` är sant bara i `connected`, alltså när historiken är komplett och strömmen är färsk.

Datorns mottagningstid (`last_received_at`) och serverns händelsetid (`last_event_time`) sparas var för sig.
Statusen syns under **Status → Marknadsdata** i appen och finns i `status.json`. Universe, eller andra
program, kan läsa den filen utan att röra databasen.

## Från motorn

```python
from traderlab.data import live
from traderlab import quality
bars = live.load()                 # stängda staplar, samma format som binance.load
print(quality.check(bars, "4h").to_markdown())
```

`live.load` öppnar databasen bara för läsning. De befintliga månadsarkiven i `data/raw/` rörs inte och
läses som förut med `binance.load`.

## Det här är inte

- **Ingen gemensam server.** Edwins och Philips datorer samlar in var för sig. Det är alltså två lokala
  insamlingar, inte en gemensam papperssession.
- **Inga strategisignaler eller diagram ännu.** Det är punkt 3.
