# H-0020: kassa-och-termin (basis) på BTC och ETH

Skrivet och registrerat 2026-11-05, **innan** någon kursdata för kvartalsterminerna har hämtats. Bara listan över
vilka kontrakt som finns i Binances arkiv har lästs. Protokollet ändras inte efter registreringen.

## Idé

En kvartalstermin handlas ofta över spotpriset, och skillnaden (basis) försvinner vid förfall. Köper man spot och
säljer terminen blankt med samma belopp, tjänar man basis oavsett vart priset går. Detta är en känd effekt som inte
bygger på någon prognos. Frågan är om den räcker efter kostnader och slår räntan på kontanter.

## Regler

| Del | Val |
|---|---|
| Instrument | Binance spot BTCUSDT och ETHUSDT (1d) och Binance USDⓈ-M kvartalsterminer `BTCUSDT_ÅÅMMDD`, `ETHUSDT_ÅÅMMDD` (1d) |
| Period | 2021-01-01 till 2024-12-31. Slutprovet 2025-01-01 och framåt läses inte in. |
| Aktivt kontrakt | Varje dag: kvartalsterminen med närmast förfall som har **mer än 14 dagar** kvar |
| Basis | b = (terminens stängning / spotens stängning − 1) × 365 / dagar kvar till förfall |
| Gå in | Platt och b ≥ 5 % per år: köp spot och sälj det aktiva kontraktet blankt med samma belopp |
| Gå ur | b ≤ 0: stäng båda benen |
| Rulla | När det hållna kontraktet inte längre är aktivt (14 dagar kvar): stäng terminen. Är b för det nya kontraktet ≥ 5 % säljs det nya blankt och spoten behålls, annars säljs spoten också. |
| Fyllning | Beslut på dagens stängning, fyllning på nästa dags öppning för båda benen |
| Kapital | Hälften per tillgång. Inom en tillgång går 2/3 till spot och 1/3 ligger kvar som säkerhet för terminen (terminen har då 50 % säkerhet). Avkastning räknas på hela kapitalet. Oanvänt kapital ger ingen ränta. |
| Kostnader | Avgift 10, spread 2 och glidning 5 bp per sida och ben, som H-0008. Stress 2,5 gånger. Kvartalsterminer har ingen finansieringsränta. |

## Beslutskriterier (spår C)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t (Newey-West, dagsavkastning) ≥ kravet vid registreringen: **2,81** (N = 20)
2. Avkastning med 2,5 gånger kostnaderna > 0
3. |beta mot BTCUSDT spot 1d| ≤ 0,2
4. Årlig avkastning (CAGR) > 3 %, ungefär snittet för amerikanska 3-månadersväxlar 2021–2024. Annars är
   kontanter bättre, och ett högt t betyder bara låg svängning.
5. Ingen likvidation. Säkerheten fylls på varje dag från spotbenet. Under en öppen säkring får terminens högsta
   pris under en dag aldrig ligga 45 % eller mer över föregående dags stängning, för då hade säkerheten på 50 %
   inte räckt. Största sådana uppgång redovisas.

## Kända svagheter, skrivna i förväg

- Idén liknar H-0008 (säkrad finansieringsränta på evighetsterminen), som fick REJECT. Den gick av och på ofta.
  Här är tröskeln högre och utgången sker först vid negativ basis, för att inte göra om samma misstag.
- Basis var hög 2021 och lägre senare. Resultatet kan bero mest på 2021.
- Spot och termin fylls på öppningen samma dag. I verkligheten är det två order som inte sker exakt samtidigt.
- Motpartsrisken mot börsen (FTX 2022) finns inte i ett backtest.
