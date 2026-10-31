# Projektkarta

En karta över hur projektets filer hänger ihop, i fliken **Projektkarta** i datorprogrammet.
Kartan sparas som `Project Map.canvas` (öppet [JSON Canvas](https://jsoncanvas.org)-format) i
projektmappen och kan öppnas i Obsidian. Uppdateringar sker lokalt och deterministiskt: inga
LLM-anrop, inga API-nycklar, inget nätverk.

## Kom igång

1. Starta Trader_go och öppna fliken **Projektkarta** (finns bara i datorprogrammet).
2. Klicka **Välj projektmapp…** och välj t.ex. `Trader_go`-repot.
3. Kartan byggs direkt och hålls sedan uppdaterad medan appen är öppen.

## Vad som händer automatiskt

- En filbevakare ser när filer läggs till, ändras, byter namn eller tas bort, även via
  `git pull` eller synk. Händelser samlas i 0,7 s; filer som nyss skrivits kontrolleras igen
  efter 2 s.
- Vid start jämförs hela mappen med förra indexet, så ändringar medan appen var stängd kommer med.
- Är mappen borta (t.ex. en frånkopplad disk) visas ett fel och appen försöker igen var 5:e sekund.
- **Uppdatera** kör en full genomgång direkt.

## Kopplingar

| Typ | Kommer från | Utseende |
|---|---|---|
| Länkar | `[[wikilänk]]`, `![[inbäddning]]`, `[text](sökväg)` i Markdown | grön |
| Beroenden | `import ... from "./x"`, `require("./x")`, Rust `mod x;`, `include_str!`, HTML `src`/`href`, CSS `@import` | blå |
| Härledda | En sökväg i backticks i text, t.ex. `` `research/registry.md` ``, som finns | gul, streckad |
| Egna pilar | Dra från kanten på ett kort till ett annat | orange, tjock |

Bara referenser som pekar på en fil som finns blir en koppling. En wikilänk som matchar flera
filer med samma namn kopplas inte alls. Filer utan kopplingar hamnar i gruppen
**Unconnected / To review**.

## Layout

- Nya kort läggs i sin mappgrupp utan att något annat flyttas.
- Ett kort du har flyttat ligger kvar där du lade det.
- Egna pilar, textkort och fält som appen inte känner till sparas oförändrade.
- Byter en fil namn behåller kortet sin plats och sina pilar. Tas filen bort försvinner kortet
  och alla pilar till det.
- Stora kartor: sök (Enter zoomar till träffarna), filtrera kopplingstyper, fäll ihop grupper.

## Vad som aldrig kommer med

Alltid undantaget, oavsett inställningar: `.git`, `node_modules`, `target`, `dist`, `gen`,
`.obsidian`, cachemappar, `.env*`, nycklar och certifikat (`*.key`, `*.pem`, `*.p12` …),
`credentials*`, `secrets*` och kartans egna filer (`Project Map*.canvas`).

Dessutom följs `.gitignore`. Egna undantag läggs i `.tradergomapignore` i projektmappen, med
samma syntax som `.gitignore`:

```gitignore
research/TraderGO/09 Archive/
*.csv
```

Förhandsvisningen visar högst 64 kB text, döljer värden som ser ut som nycklar eller lösenord,
och kan bara läsa filer som finns på kartan. Binärfiler (bilder, PDF) visas som kort men tolkas
inte. Inget i projektet körs: **Visa i Finder** visar bara filen, och **Öppna i Obsidian**
använder Obsidians egen länk.

## Obsidian

- **Öppna i Obsidian** fungerar när Obsidian är installerat och projektmappen (eller en mapp
  ovanför) är ett valv i Obsidian. Valv hittas i Obsidians egen konfiguration.
- Kortens sökvägar är relativa till projektmappen. Öppnar du `research/` som valv men väljer
  hela repot som projektmapp hittar Obsidian inte filerna utanför `research/`. Välj samma mapp
  på båda ställena.
- Redigerar du kartan i Obsidian medan Trader_go är öppet läses ändringen in. Har du samtidigt
  osparade ändringar i Trader_go skrivs ingenting över. Du får välja **Ladda om från disk**
  eller **Spara mina ändringar som kopia**.

### Begränsningar i rundresan

- Obsidian kan ta bort fält det inte känner till när det sparar.
- Grupper i Trader_go flyttar inte sina kort när gruppen dras (i Obsidian gör de det).
- Kopplingstypen syns på pilens id (`g-e-`, `g-d-`, `g-i-`); Obsidian visar bara etikett och färg.
- Länknoder och textkort visas som ren text, utan Markdown-formatering.

## Data

- Kartan: `Project Map.canvas` i projektmappen. Commit den om ni vill dela layouten.
- Index och layoutminne: appens datamapp (`project-map-<id>.json`), inte i repot. Tar du bort
  filen byggs indexet om vid nästa start; kort som redan finns på kartan ligger kvar.
