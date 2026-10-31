---
name: hamta-data
description: Använd när historisk marknadsdata ska hämtas från en öppen källa, eller innan data används i ett test. Hämtar, sparar och kontrollerar kvaliteten (luckor, dubbletter, felstaplar, tidszoner).
---

# Hämta och kontrollera data

Dålig data ger backtest som ser bra ut av fel skäl. Ingen data används i en hypotes innan
kontrollerna nedan är körda och resultatet är skrivet i registret.

## Källor

- Börsens publika historik (till exempel Binance eller Bybit, direkt eller via CCXT). Inga
  nycklar behövs för publik data. Använd aldrig en nyckel till att hämta data.
- För terminer behövs också finansieringsränta och, om möjligt, mark price. Säg vilka som
  saknas. Prissätts terminer från spotdata ska det sägas rakt ut.
- Fråga innan en betaltjänst används.

## Spara

- Lägg rådata i `data/raw/` och rensad data i `data/clean/`. Båda ska stå i `.gitignore`.
  Committa i stället ett litet manifest i `data/MANIFEST.md`: källa, marknad, tidsram,
  period, hämtdatum och radantal.
- Rådata skrivs aldrig över. Rensning ger en ny fil.
- Tid lagras i UTC, och staplar märks med öppningstid.

## Kontroller (kör alla, rapportera siffror)

1. **Luckor:** saknade staplar mot förväntad takt. Lista de största.
2. **Dubbletter och ordning:** unika, stigande tidsstämplar.
3. **Felstaplar:** `low <= open, close <= high`, inga negativa eller nollpriser, volym >= 0.
4. **Utstickare:** staplar med ovanligt stor rörelse. Kontrollera mot en annan källa innan de
   tas bort. Äkta kraschar ska vara kvar.
5. **Stillastående pris:** långa serier med oförändrat pris och noll volym tyder på avbrott.
6. **Tidszon och sommartid:** inga hopp eller dubbla timmar.
7. **Andra källan:** jämför en stickprovsperiod mot en annan börs. Stora avvikelser flaggas.
8. **Överlevnad:** kommer marknaderna från dagens lista saknas de som dog. Notera det.

## Regler

- Fyll aldrig luckor med påhittade värden utan att det sägs och märks. Hellre uteslut perioden.
- Tala om hur mycket data som är *ren*, det vill säga inte redan använd för att välja något.
  Det avgör vad som går att testa (se `ny-hypotes`).
- Skriv ned kontrollresultatet i anteckningen för hypotesen (se `forskningslogg`).
