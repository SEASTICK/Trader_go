---
name: granska-backtest
description: Använd när ett backtest ska granskas, när ett resultat ser för bra ut, eller före ett beslut om en hypotes. Letar efter look-ahead, läckage, saknade kostnader, short-risker och slumpfynd.
---

# Granska backtest

Utgå från att resultatet är fel tills motsatsen är visad. Gå igenom listan, ange fil och rad
för varje fynd, och kör kontrollerna i stället för att bara läsa koden. Metodik finns också
i `backtest-expert`.

## Look-ahead och läckage

- Fylls ordern vid nästa stapels öppning, och inte på stängningen som gav signalen?
- Använder någon feature data från framtiden, till exempel normalisering över hela perioden?
- Är träning och test åtskilda med gallring när etiketten tittar framåt?
- Valdes tröskel eller parameter på testdatan?
- Kontroll: ger slumpade etiketter ett resultat nära noll **före kostnader**? Efter kostnader
  mäter testet bara omsättning.

## Kostnader

- Finns avgift, spread och slippage på varje sida?
- Hur ser det ut vid en stressad kostnad, ungefär 2,5 gånger den normala?
- Beräkna omsättningen per år. Hög omsättning kan äta upp en signal som ser bra ut gratis.

## Short och terminer

- Finns verklig finansieringsränta med, och betalas den av den som håller positionen vid
  avräkningen?
- Simuleras likvidation från stapelns högsta och lägsta pris?
- Prissätts terminer från spotdata? Säg i så fall att skillnaden ignoreras.
- Krypto har ofta stigit över tid. Jämför alltid short mot en short utan modell.

## Är det verkligt?

- **t-värde** med Newey-West på dagliga avkastningar, mot kravet för antalet försök i
  `research/registry.md`.
- Sharpe med **osäkerhetsintervall** från block-bootstrap. Visa aldrig Sharpe ensam.
- Kommer vinsten från ett enda år eller en enda marknad? Ta bort den bästa och räkna om.
- Håller resultatet på en annan börs med egen data?
- Slår det en enkel baslinje, som köp-och-behåll och en trendregel?
- Är urvalet överlevnadsbiased? Kommer marknaderna från dagens lista saknas de som dog.
- Är perioden redan använd för att välja något? Då är testet inte rent.

## Svara så här

Lista fynden efter allvar. Avsluta med en mening: går resultatet att lita på, och vad är
nästa kontroll? Säg `REJECT` rakt ut när kriterierna säger det.
