# Hypotesregister

Facit för alla försök. Se skillen `ny-hypotes`. Regler:

- En ny rad **läggs till sist och committas innan** något körs. Motorn (`engine/`) vägrar köra en hypotes
  som inte finns i den committade versionen av den här filen.
- Rader ändras eller tas aldrig bort. Ett resultat skrivs på en **ny** rad med samma id.
- En ändring av regel, parameter eller feature efter att resultatet setts är ett nytt id.
- Antal försök N räknas som antal olika id. Kravet på t-värde: `python -m traderlab krav N` (i `engine/`).

| id | datum | commit | hypotes (en mening som kan vara fel) | marknad | tidsram | period | modell och features | kostnader | beslutskriterier | ren period? | resultat | beslut |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H-0001 | 2026-11-01 | 428ec5c | En enkel trendregel på BTC (glidande medel 20 över 50 på 4h-staplar, long eller platt) ger positiv avkastning efter kostnader och bättre Sharpe än köp-och-behåll. Vald i förväg som klassisk baslinje, inte efter att ha sett resultat. | Binance spot BTCUSDT | 4h | 2020-01-01 till 2024-12-31. 2025-01 till 2026-09 sparas orörd. | ma_cross fast=20 slow=50, ingen short, ingen ML, inget riskskydd, ingen hävstång | Avgift 10 bp, spread 2 bp, slippage 5 bp per sida. Stress 2,5 gånger. | MORE_RESEARCH om t (Newey-West, dagsavkastning) ≥ kravet 2,0 OCH avkastning med 2,5 gånger kostnaderna > 0 OCH Sharpe > köp-och-behåll. Annars REJECT. | Ja. Ingen data använd för att välja något. | | |
