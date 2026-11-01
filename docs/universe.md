# TraderGO Universe

Universe öppnar direkt på projektkartan: en [JSON Canvas](https://jsoncanvas.org) över hur filerna
i TraderGO-projektet hänger ihop. Den går att panorera, zooma och söka i, har grupper per mapp,
klickbara filer med förhandsvisning och märkta kopplingar. Universe bäddar inte in Obsidian.

## Bara läsning

Universe läser projektmappen och ändrar aldrig något i den: inga filer skapas, ändras, byter namn
eller tas bort, och inga trasiga länkar "repareras". Allt Universe sparar ligger i appens egen
datamapp:

| | Var |
|---|---|
| Kartan (`project-map-<id>.canvas`), kortplaceringar, egna pilar och index | `~/Library/Application Support/com.seastick.tradergo.universe/map/` (macOS), `%APPDATA%\com.seastick.tradergo.universe\map\` (Windows) |
| Vald projektmapp | `universe-settings.json` i samma datamapp |

**Exportera…** sparar en kopia av kartan där du väljer, men vägrar spara inne i projektmappen.
Kartan följer JSON Canvas 1.0 och kan öppnas i Obsidian.

## Hur projektmappen hittas

Se [README](../README.md#så-hittar-universe-projektet). Kort: vald mapp → `TRADERGO_ROOT` →
utvecklingskopian → vanliga platser under hemmappen. Hittas ingen visar Universe **Välj
projektmapp…**. Diagnostikpanelen visar vilken mapp som används och hur den hittades.

## Vad som visas

- Alla filer som Git skulle ta med, utom `.env*`, nycklar och certifikat (`*.key`, `*.pem` …),
  `credentials*`, `secrets*`, `node_modules`, `target`, `dist`, `gen`, cachemappar, `.obsidian`
  och kartans egna filer. Egna undantag: `.tradergomapignore` i projektmappen (samma syntax som
  `.gitignore`).
- Kopplingar: **Länkar** (`[[wikilänk]]`, `![[inbäddning]]`, Markdown-länkar), **Beroenden**
  (import, Rust `mod`, `include_str!`, HTML/CSS-referenser), **Härledda** (sökvägar i backticks)
  och dina **egna pilar**.
- Filer utan koppling hamnar i gruppen **Unconnected / To review**.

## Ändringar syns direkt

En filbevakare ser när filer läggs till, ändras, byter namn eller tas bort, också från Git,
Obsidian eller en editor. Vid start jämförs hela mappen med förra indexet. Ingen LLM och inga
API-anrop används. **Uppdatera** kör en full genomgång direkt.

## Diagnostik

Knappen **Diagnostik** uppe till höger visar:

- projektmappen och hur den hittades (och vilka platser som provades om ingen hittades),
- bevakningens läge och senaste genomgång,
- antal filer, kopplingar per typ och filer utan koppling,
- **trasiga länkar**: wikilänkar och Markdown-länkar som pekar på en fil som inte finns. De rättas
  i Obsidian eller i editorn, inte av Universe.

## Loggar

| | macOS | Windows |
|---|---|---|
| Krascher (`crash.log`) och startfel (`startup-error.log`) | `~/Library/Logs/com.seastick.tradergo.universe/` | `%LOCALAPPDATA%\com.seastick.tradergo.universe\logs\` |

## Kod

`apps/trader-go-universe/` är en egen Tauri-app med eget program-id (`com.seastick.tradergo.universe`),
egen ikon och egen genväg. Den återanvänder Trader_go:s uppdateringsflöde direkt ur
`app/src/features/updates/` (ingen kopia) och har en egen kontroll, `npm test`, som stoppar
mäklar- och orderkod och rättigheter som skulle kunna skriva i filsystemet.

## Data och uppdateringar

Universe uppdaterar sig själv från `universe/latest.json` på den publika uppdateringssidan (se
[release.md](release.md)) och sparar inga inloggningar. Innehållet kommer från din egen kopia av
repot; hämta nytt med Git som vanligt. En appuppdatering rör aldrig projektmappen.
