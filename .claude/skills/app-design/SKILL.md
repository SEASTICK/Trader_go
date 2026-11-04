---
name: app-design
description: Använd när något i Trader_go-appen (app/src) ska byggas eller ändras visuellt, till exempel en ny sida, ett kort, ett diagram eller en text i gränssnittet. Håller färger, komponenter och språk enhetliga och visar bara riktig data.
---

# Design i Trader_go-appen

Stilen bygger på Vinstly Desktop (sidomeny, vita rundade kort, grön primärfärg) med en marknadskänsla som Avanza. Låna stil, aldrig logotyper eller varumärken.

## Grundregler

1. **Bara riktig data.** Appen visar inga påhittade siffror. Resultat kommer från motorn (`app/data/results.json`,
   märkta `HISTORIK`), priser från insamlingen. Saknas data visas en tom vy med förklaring, aldrig en ersättning.
2. **Ingen prognos, inget löfte.** Säg "resultat i test", aldrig "förväntad avkastning".
3. **Svenska, enkelt och utan facktermer** i gränssnittet. Förklara t-värde med "över/under kravet".
4. **Inga externa resurser.** CSP är strikt (`default-src 'self'`). Typsnittet Inter ligger lokalt. Inga CDN:er eller bilder utifrån.

## Färger (`app/src/styles.css`)

Använd variablerna, aldrig hårdkodade färger i komponenter:
`--bg --side --card --line --ink --muted --hover --active --accent --accent-h --on-accent --good --bad --warn --idle --s1 --s2`.
Ljust och mörkt tema definieras båda. Kontrollera alltid båda.

- Upp/vinst: `--good` (klass `up`). Ner/förlust: `--bad` (klass `down`).
- Research-kategorier (`data-group`): krypto orange `#9a6412`, terminer lila `#7a4aa8`, aktier blå `#2b67ad`, makro turkos `#237f7a`, baslinje grå `#566160`. På färgade rutor visas avkastning i ljus bricka.

## Komponenter

| Komponent | Fil | Används till |
|---|---|---|
| `Page` | `components/ui.tsx` | Sidrubrik, undertext, knappar till höger |
| `Segmented` | `components/ui.tsx` | Flikar och filter |
| `StatusDot` | `components/ui.tsx` | Status: Idé, Pågår, REJECT, READY_FOR_PAPER |
| `LineChart`, `Sparkline` | `components/Charts.tsx` | Kurvor, med hover och vattenstämpel |
| `Icon` | `components/icons.tsx` | Enkla linjeikoner |

CSS-klasser: `card`, `pad`, `kpis`/`kpi`, `btn`, `btn accent`, `table-card`, `split`, `footnote`, `callout`, `banner-sim`.

## Innan en ändring är klar

1. `npm --prefix app test` och `npm --prefix app run build`.
2. Skärmbild med Playwright (Chromium finns): ljust och mörkt, den sida som ändrats. Titta på bilden.
3. Säg vad som är provat i webbläsaren och att det inte är provat i Windows-appen.
