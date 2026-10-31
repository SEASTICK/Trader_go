---
name: ny-hypotes
description: Använd när vi vill testa en ny tradingidé, strategi, signal, feature eller parameter, innan någon kod körs mot historik. Registrerar hypotesen och räknar försöket.
---

# Ny hypotes

Antalet försök är siffran som lättast glöms. Prövar man tjugo idéer på samma historik ser
någon bra ut av ren slump. Därför skrivs varje idé ned innan resultatet finns.

## Gör så här

1. **Formulera idén som en mening som kan vara fel.** Vad tjänar pengar, och varför finns
   kanten kvar? Går det inte, stanna och reda ut det.
2. **Skriv en ny rad sist i `research/registry.md`.** Skapa filen om den saknas. Ändra eller
   ta aldrig bort tidigare rader.
   - id (`H-0001`, `H-0002` och så vidare), datum och commit
   - hypotes, marknader, tidsram, period
   - modell, features och kostnader
   - beslutskriterier, bestämda nu
   - om perioden är ren eller redan använd
3. **Commita raden före körningen.** Commiten är beviset på att reglerna fanns först.
4. **Räkna kravet.** `N` är alla rader i registret. Kravet är Bonferroni, ensidigt:
   `t >= norm.ppf(1 - 0.05 / N)`, och aldrig under 2,0. Det är ungefär 2,6 vid 10 försök och
   3,3 vid 100.
5. **Efter körningen:** skriv resultat och beslut på en ny rad, enligt kriterierna. Besluten
   är `REJECT`, `MORE_RESEARCH` eller `READY_FOR_PAPER`.

## Regler

- En ändring av regel, parameter eller feature efter att resultatet setts är ett **nytt
  försök med nytt id**.
- Ett försök som överges räknas ändå.
- En idé som hittades genom att titta på ett resultat måste märkas så.
- Kör `granska-backtest` innan beslutet skrivs.
