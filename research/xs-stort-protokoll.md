# Tvärsnitt med stort universum: momentum och funding-carry över alla likvida terminer

Skrivet och registrerat 2026-11-05, **innan** någon kursdata för universumet hämtats. Bara listan över vilka
kontrakt som finns i Binances arkiv har lästs. Ändras inte efter registreringen.

## Varför

H-0014 och H-0015 (11 mynt) var marknadsneutrala och lönsamma även med 2,5 gånger kostnaderna, men nådde bara
t 1,4. Ett större universum ger fler oberoende satsningar per vecka. Det är samma idéer, med fler mynt, strängare
kostnader och ett likviditetsfilter. Parametrarna bestäms här och optimeras inte.

## Gemensamt för H-0018 och H-0019

| Del | Val |
|---|---|
| Universum | Alla Binance USDⓈ-M-terminer mot USDT som har en månadsfil (1d) för 2021-01, utom indexkontrakt (BTCDOMUSDT, DEFIUSDT, BLUEBIRDUSDT, FOOTBALLUSDT). Avnoterade kontrakt ingår tills datan tar slut. |
| Period | 2021-01-01 till 2024-12-31. Slutprov 2025-01-01 och framåt läses inte in. |
| Valbarhet | Minst 60 dagars historik, en stängd stapel samma dag, och median av daglig omsättning (stängning × volym) de senaste 30 dagarna minst 10 miljoner USD |
| Ombalansering | Varje söndag (UTC) vid stängning, fyllning vid måndagens öppning. Mellan ombalanseringar driver vikterna med priset. |
| Portfölj | Long den översta tiondelen, short den nedersta (minst 5 per sida), lika vikt, brutto 1x, netto 0. Färre än 10 valbara ger platt. |
| Kostnader | 25 bp per sida på omsatt belopp (avgift 10, halv spread 5, glidning 10), högre än för de 11 stora mynten. Stress 2,5 gånger. Finansieringsränta per mynt. |

### H-0018: momentum
Rang = avkastning över 28 dagar, där senaste dagen hoppas över (som H-0014).

### H-0019: funding-carry
Rang = medel av finansieringsräntor avräknade de senaste 7 dagarna strikt före stängningen (som H-0015).
Short högst ränta, long lägst.

## Beslutskriterier (spår C)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t (Newey-West, dagsavkastning) ≥ kravet vid körningen: **2,79** (N = 19)
2. Avkastning med 2,5 gånger kostnaderna > 0
3. |beta mot BTCUSDT spot 1d| ≤ 0,2

## Kända svagheter, skrivna i förväg

- **Idéerna är valda efter H-0014 och H-0015**, som såg lovande ut men fick REJECT. Det är en uppföljning, inte ett
  oberoende test. Därför räknas båda som nya försök, och kravet stiger.
- Altcoins kan ha större glidning än 10 bp, särskilt vid kraftiga rörelser. Blankning antas möjlig till terminspris.
- Kontrakt som avnoteras faller ofta kraftigt före avnoteringen. Det ingår, men stängningen sker på sista öppningen.
