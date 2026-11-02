# Registrerade resultat i Research Lab

Research Lab har två separata vyer:

- **Registrerade resultat:** H-0009–H-0012 från originalfilerna i
  `research/results/`. Besluten kommer från `research/registry.md`. Alla fyra
  är REJECT. Visas utan inloggning eller serveranslutning och uppdateras genom
  en ny appversion.
- **Utforskning:** medlemsinloggning, köning och sparade resultat från Supabase.
  Ger inget registrerat strategibeslut och använder aldrig SIM som reservdata.

Den registrerade vyn visar jämförelse, sökning/sortering, samtliga kriterier,
nyckeltal, equity/drawdown och köp-och-behåll, sex walk-forward-fönster,
månads-/regimresultat, historiska terminscandles och in-/utmarkörer samt
exporterade affärer. På smala fönster visas ytterligare mätvärden i detaljvyn;
breda tabeller går att rulla i sidled. Börsdiagrammet använder samma mörka
utformning som appens befintliga marknadsdiagram i båda app-teman.

En affär utan utträde är öppen vid det aktuella historiska fönstrets slut,
inte en pågående position i dag. Fönster körs separat enligt det ursprungliga
protokollet. Dessa resultat ändrar inga strategier och startar inga nya tester.

## Export och spårbarhet

```sh
PYTHONPATH=engine python -m traderlab fas1-export
```

Den explicita adaptern skriver `app/data/registered-results.json` först när
alla fyra originalresultat är giltiga. Den avvisar SIM, saknade beslut,
felaktiga kriterier och kurvor utanför testperioden. Originalfilens SHA256,
registreringscommit och strategiversion följer med. En reproduktionsaudit
kopplas bara när statistik, kurvor och slutparametrar matchar originalet exakt.
Den äldre `app/data/results.json` ändras inte och dess befintliga resultat
påverkas inte. Fas 1-vyn använder ingen simulerad reservdata.

`app/data/fas1-market.json` innehåller 6 576 stängda UM BTCUSDT 4H-staplar
2022–2024 från det kontrollsummerade femårsdatasetet. Ingen spotdata ersätter
terminer. Baslinjen räknades på samma verifierade data, funding och kostnader;
alla tre ursprungliga baslinjemått matchar exakt. Kurvan väljer baslinjens
faktiska värden vid strategikurvans exakta tider, utan interpolation.
Kontrollrapporten finns i `data/audits/fas1-20261102/market-display-verification.json`.

Det frysta datasetets id är oförändrat. Appens staplar är ett visningsurval,
inte ett nytt forskningsdataset. Slutprovet från 2025 öppnades inte.

## Provning

Exporttester läser samtliga riktiga JSON-filer och kontrollerar originalhashar,
giltighet, oförändrad äldre export samt att trasiga källor inte skriver över
senaste export. Frontendtester kontrollerar periodgräns, komplett 4H-rutnät,
OHLC och samma dataset/baslinje. Webbvyn granskas i ljust och mörkt tema med
sökning, sortering, beslut och verkliga diagram. Desktop-/Windows-provning
redovisas separat efter release; ett godkänt webbtest är inte ett desktoptest.

## Prestanda och plattformar

Två identiska treårskörningar på Ubuntu-dropleten tog 1,90 och 1,61 sekunder,
med toppminne cirka 89 MiB och 4,03 MB materialiserade utdata. Resultaten var
exakt identiska; detta är inte ett belastningstest av samtidiga köjobb.
DigitalOceans do-agent och research-workern var aktiva; disken hade 113 GiB ledigt.

Första Windowsbygget stoppade ett kontrollsummefel orsakat av CRLF-utcheckning.
JSON låses nu till LF via .gitattributes; testet av originalhasharna behålls.
Ingen felaktig version publicerades.

## Publicerad och installerad Stable 0.1.14

Release-körning 41432314601 från `1ed0b31` slutfördes med godkända Mac-/Windows-
byggen. Båda faktiska artefaktsignaturerna verifierades och manipulerade filer
avvisades. Publika filer matchar artefakternas SHA256.

Den installerade Mac-appen uppdaterades 0.1.12 → 0.1.14 via sin egen uppdaterare.
Omstart, versionsnummer, registrerade resultat utan inloggning, Squeeze som
REJECT samt historiska terminspriser/markörer och kontrollen Hela perioden
verifierades i den installerade appen. Första skärmbilden efter programmatisk
rullning var tom; omritningen bekräftades efter interaktion med diagramkontrollen.
Första omritningens tillförlitlighet är inte separat godkänd. Windowsgränssnittet
är inte interaktivt provat. Se `data/audits/fas1-20261102/stable-lab-verification.json`.

Detta är en godkänd delleverans av Research Lab, inte slutgodkännande av Fas 1.
