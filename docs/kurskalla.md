# Kurskälla för amerikanska aktier

Investerarspåret (H-0016, H-0017 och papperportföljen på sidan Investerare) behöver dagliga aktiekurser,
justerade för split och utdelning. Ingen nyckel behövs, och ingen behöver göra något.

| Ordning | Källa | När |
|---|---|---|
| 1 | Tiingo (officiellt API) | Bara om hemligheten `TIINGO_API_KEY` finns. Valfritt. |
| 2 | Yahoo Finance chart-API | Standard. Ingen nyckel. |
| 3 | Stooq | Bara med `PRICE_SOURCE=stooq`. Stooq blockerar molnservrar, och det kringgås inte. |

Koden finns i `engine/traderlab/data/stocks.py`.

## Om Yahoo

- Yahoos API är inofficiellt. Det kan ändras eller strypas utan förvarning.
- Svarar Yahoo med en spärr eller en felsida avbryts körningen (`PriceSourceUnavailable`). Inget kringgås och
  inget felaktigt sparas.
- Kurserna justeras för utdelning med Yahoos justerade stängning, och samma faktor läggs på öppning, hög och låg.
- Avnoterade bolag saknas ofta. Det gör testen för optimistiska, och andelen vikt utan kurs redovisas.
- H-0017:s protokoll anger Stooq som källa. Eftersom Stooq är blockerat används Yahoo för både portfölj och SPY,
  och avvikelsen skrivs i resultatraden.

## Vad som händer

- **Paper 13F** körs varje lördag. Den uppdaterar vad investerarna äger, Pelosis nya affärer och
  papperportföljen på 100 000 USD.
- **Actions → Research 13F → Run workflow** med hypotes `H-0016` eller `H-0017` kör testen. Resultaten hamnar
  på grenen `bot/h-0016-resultat` respektive `bot/h-0017-resultat` och granskas innan de förs in i registret.
