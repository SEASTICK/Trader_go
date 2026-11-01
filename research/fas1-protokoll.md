# Fas 1-protokoll: fyra regelstrategier med Optuna och walk-forward

Skrivet och registrerat 2026-11-01, **innan** någon av strategierna körts på riktig data. Protokollet ändras inte
efter registreringen. En ändring blir ett nytt protokoll och nya hypoteser.

## Gemensamt för H-0009 till H-0012

| Del | Val |
|---|---|
| Marknad | Binance USDⓈ-M BTCUSDT (terminer), 4h, med finansieringsränta. Terminer eftersom strategierna går både long och short. |
| Utvecklingsperiod | 2020-01-01 till 2024-12-31 (terminsdata finns från 2020-01) |
| Slutprov (holdout) | 2025-01-01 till 2026-09-30. Läses inte in i Fas 1. Används en gång, och bara för en strategi som klarar kriterierna nedan. |
| Optimering | Optuna TPE, frö 0, 40 försök per optimering, målfunktion Sharpe på dagsavkastning efter kostnader (minst 10 affärer) |
| Walk-forward | Växande träningsfönster från 2020-01-01. Testfönster på ett halvår: 2022-01, 2022-07, 2023-01, 2023-07, 2024-01, 2024-07. Parametrarna för varje testfönster väljs bara på data före fönstret. |
| Bedömning | Den ihopsatta kurvan utanför urvalet, 2022-01-01 till 2024-12-31 (3 år) |
| Kostnader | Avgift 10 bp, spread 2 bp, slippage 5 bp per sida. Stresstest 2,5 gånger. Finansieringsränta betalas eller tas emot. |
| Storlek | Hela kapitalet, ingen hävstång (1x), long eller short |
| Stop | ATR-baserad stop-loss enligt strategin, satt vid inträdet |
| Slutliga parametrar | Optimeras på hela utvecklingsperioden och fryses (för slutprov och papper) |
| Stabilitet | Grannar till de slutliga parametrarna, ett steg upp och ned per parameter. Andelen som behåller minst halva Sharpe-värdet ska vara minst 50 %. |

## Beslutskriterier (spår A, research/tracks.md)

`MORE_RESEARCH` om **alla** gäller på perioden utanför urvalet, annars `REJECT`:

1. t (Newey-West, dagsavkastning) ≥ kravet vid körningen: **2,64** med N = 12
2. Avkastning med 2,5 gånger kostnaderna > 0
3. Sharpe > köp-och-behåll på samma terminer och period (med kostnader och finansieringsränta)
4. Stabilitet ≥ 50 %

En strategi med `MORE_RESEARCH` går vidare till slutprovet med frysta parametrar. Först därefter kan den bli
`READY_FOR_PAPER`. Ingenting här säger något om framtida avkastning.

## Kända svagheter, skrivna i förväg

- Perioden 2020–2024 för BTC har vi redan sett i H-0001 till H-0008. Det påverkar valet av strategityper
  (som kommer från Fas 1-planen, inte från våra resultat), men utvecklingsperioden är inte helt ren.
- 40 försök × 7 optimeringar per strategi. Urvalet sker bara på träningsdata, men Deflated Sharpe räknas ändå med
  antalet registrerade försök.
- Stop-loss antas fyllas på stopnivån eller på öppningen vid gap. Verklig glidning vid kraftiga rörelser kan vara större.
