# Prestanda i TraderGO Universe

Mätt 2026-11-01 på gren `integrate/universe-prestanda`, på en MacBook (arm64). Rapporten skiljer på
uppmätta orsaker och antaganden. Den påstår inte att allt lagg är borta. WebKit i appen kan bete sig
annorlunda än Chromium, där gränssnittet mättes med siffror.

## Vad som kördes

- **Installerad app före:** `/Applications/TraderGO Universe.app`, byggd 2026-11-01 12:55 från `3da121d`.
  I vila använde den 0 % CPU och cirka 52 MB, så det fanns ingen bakgrundsloop.
- **Kartan:** det riktiga projektet har 257 filer (268 noder med grupperna) och 169–173 pilar. Den
  syntetiska kartan, utanför projektet, har 3 000 kort och 4 500 pilar i 40 grupper.

## Bekräftade orsaker

1. **Sökningen monterade om alla synliga kort vid varje tangent.** Varje sökning byggde nya objekt för
   alla noder. React Flow svarade med nya mått via `onNodesChange`, och då byggdes allt om igen, mättes
   om, och kortelementen flyttades i DOM. Uppmätt med en MutationObserver: 5 555 element togs bort och
   lades tillbaka per tangent på den stora kartan.
2. **Statushändelser renderade om hela kartan,** inklusive React Flow och minikartan. Uppmätt: upp
   till 305 ms per händelse på den stora kartan.
3. **Utzoomat ritades tusentals pilar med etiketter, och minikartan ritade alla kort vid varje
   rörelse.** Uppmätt: 3 600 pilar i DOM, och panorering på 284 ms per bildruta.
4. **Backend: att placera nya kort var kvadratiskt eller värre.** För varje ny fil sökte `place()` från
   början av rutnätet mot alla upptagna rutor, och id-kontrollen gick igenom alla noder. Det blev
   ungefär O(N³) vid första indexeringen. Uppmätt: 4 000 filer tog 6,7 s, och 20 000 filer hann inte
   bli klara på över 10 minuter. Det riktiga projektet påverkades knappt (90 ms), men stora Git-
   ändringar och stora mappar gjorde det.
5. **Varje `map-changed` laddade och ritade om hela kartan,** även när innehållet var oförändrat.

**Inte orsaker (uppmätt):**
- **Indexeringen av det riktiga projektet:** 63–90 ms kallt, 12–20 ms per ändring, i en egen tråd.
- **Dubbla lyssnare:** det finns en lyssnare per händelse.
- **Minnesläckor:** minnet planar ut runt 106 MB efter fem omgångar med 300 nya och borttagna filer,
  och trådarna är stabilt 20.

## Ändringar

**Backend** (`src-tauri/src/project_map/canvas.rs`, `mod.rs`):
- Nya kort placeras med ett rutnätsindex och en markör per grupp i stället för en linjär sökning, och
  id:n kontrolleras med en hashmängd. Placeringen blir densamma; de befintliga layouttesterna är gröna.
- Statusen innehåller hur lång tid senaste genomgången tog (`last_duration_ms`), och den visas i
  verktygsfältet.

**Gränssnitt** (`src/ProjectMap.tsx`, `universe.css`):
- Kartan är en egen memoiserad komponent, `MapCanvas`. Status, sökfält och sidopanel renderar inte om
  React Flow.
- Kort återanvänds per id så länge deras grunddata och träffläge är oförändrade, också efter React
  Flows mätningar. Det tar bort ommonteringen.
- Kortkomponenterna är memoiserade, och händelsehanterarna är stabila.
- Sökningen räknas i bakgrunden (`useDeferredValue`). Träffar ramas in i stället för att resten tonas
  ned. Över 500 träffar markeras ingenting på kartan.
- En träfflista hittar också kort som inte är renderade, och ett klick centrerar på kortet.
  Autokomplettering är avstängd.
- Pilarnas etiketter visas från zoom 0,6. På kartor med fler än 1 000 pilar visas genererade pilar
  först från zoom 0,3, med en synlig notis; egna pilar visas alltid.
- Minikartan stängs av över 1 500 kort, med en notis.
- Grupptillhörighet räknas en gång per kartversion.
- Laddningar slås ihop, och en oförändrad karta (samma hash) ritas inte om.

**Mätverktyg** (nytt, påverkar inte appen):
- `perf/` kör gränssnittet i en vanlig webbläsare med en låtsas-backend. Den använder den riktiga
  kartan (`?canvas=real`, kopierad från appens datamapp) eller en syntetisk (`?n=3000`).
- `src/tauri.ts` använder låtsas-backenden bara om den finns och appen inte körs i Tauri.
- `project_map/perf.rs` innehåller backend-mätningar:
  `cargo test --release perf_ -- --ignored --nocapture`, där `PERF_FILES=4000` styr storleken.

## Före och efter

### Backend (release, `perf.rs`)

| Struktur | Kall start före | Kall start efter | En ändrad fil efter |
|---|---|---|---|
| Riktiga projektet (254 filer) | 90 ms | 63 ms | 12 ms |
| Syntetisk 1 000 filer | 183 ms | 55 ms | 31 ms |
| Syntetisk 2 000 filer | 951 ms | 80 ms | 41 ms |
| Syntetisk 4 000 filer | 6 742 ms | 129 ms | 61 ms |
| Syntetisk 20 000 filer | över 10 min (avbruten) | 1 922 ms | 269 ms |

### Gränssnitt (Chromium, produktionsbygge, visningsyta 1 400×900, samma skript)

Värdena är tid per bildruta: median, med sämsta värdet där det anges. För sökning är det svarstid per
tangent i realistisk takt (ett tryck per 100 ms).

| | Riktig karta före | Riktig karta efter | 3 000 kort före | 3 000 kort efter |
|---|---|---|---|---|
| Zoom | 10,7 ms | 9,4 ms | 266 ms | 13,7 ms |
| Panorering | 12,6 ms | 12,3 ms | 284 ms | 28 ms * |
| Sökning per tangent, median / sämsta | 22 / 28 ms | 8,9 / 13,7 ms | 996 / 1 193 ms | 13,6 / 21 ms |
| Statushändelse, median / sämsta | 8 / 10 ms | 8 / 10 ms | 49 / 305 ms | 11 / 15 ms |
| Långa uppgifter vid zoom och panorering | 0 | 0 | 6,2 s | 0 |
| DOM-element flyttade per sökning | – | 0 | 5 555 | 0 |

\* Vid den utzoomade startvyn döljs pilarna på den stora kartan, så panoreringen där mäts utan pilar.

### Installerad app efter (macOS, WebKit)

- Startar via `open` och visar kartan med diagnostiken "Bevakar".
- 300 nya filer syntes på kartan inom 0,9 s, ett namnbyte registrerades, och borttagning syntes inom
  0,9 s. `git status` var oförändrad efteråt, så appen skrev inget i projektet.
- Sökningen visar en träfflista, och ett klick väljer filen och centrerar kartan på den.
- En full uppdatering tar 20 ms.
- Första genomgången direkt efter en nyinstallation tog en gång 3,5 s. Orsaken är inte bekräftad:
  troligen kall filcache, eller att macOS kontrollerade det nysignerade bygget.

## Kvarstående begränsningar

- **Siffrorna för gränssnittet kommer från Chromium.** I appen (WebKit) är funktionen provad för hand,
  men det finns inga bildrutetider därifrån.
- **Ett tomt fönster sågs en gång** när appen startades direkt efter att paketet bytts ut. Det gick inte
  att återskapa.
- **Indexeringen går fortfarande igenom hela mappen vid varje ändring,** i en egen tråd: 12 ms i det
  riktiga projektet och 269 ms vid 20 000 filer. Ändringar indexeras alltså inte en och en. Det
  lämnades eftersom mätningarna inte visade att det låser gränssnittet.
- **Rådata och stora loggar visas inte som sammanfattade noder.** De är redan undantagna från kartan:
  `data/raw/` står i `.gitignore`, och appens databaser ligger i appens datamapp. Det står i
  diagnostikpanelen, men antal och storlek visas inte.
- **Windows** är inte provat.

## Testa själv

Öppna **TraderGO Universe** från Launchpad eller `/Applications/TraderGO Universe.app` (byggd
2026-11-01 14:41 från den här grenen). Panorera, zooma och sök, till exempel efter "updater".
Verktygsfältet visar hur lång tid senaste genomgången tog.
