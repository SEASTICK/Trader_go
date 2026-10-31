# Hypotesregister

Facit för alla försök. Se skillen `ny-hypotes`. Regler:

- En ny rad **läggs till sist och committas innan** något körs. Motorn (`engine/`) vägrar köra en hypotes
  som inte finns i den committade versionen av den här filen.
- Rader ändras eller tas aldrig bort. Ett resultat skrivs på en **ny** rad med samma id.
- En ändring av regel, parameter eller feature efter att resultatet setts är ett nytt id.
- Antal försök N räknas som antal olika id. Kravet på t-värde: `python -m traderlab krav N` (i `engine/`).

| id | datum | commit | hypotes (en mening som kan vara fel) | marknad | tidsram | period | modell och features | kostnader | beslutskriterier | ren period? | resultat | beslut |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
