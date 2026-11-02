# Tvärsnittsprotokoll: momentum och funding-carry över många terminer

Skrivet och registrerat 2026-11-02, **innan** data för universumet hämtats och innan något körts.
Protokollet ändras inte efter registreringen.

## Varför

Hittills har alla 12 hypoteser (ett mynt i taget, mest BTC) fått REJECT. Ett mynt under fem år ger få
oberoende utfall, så även en verklig kant når sällan t-kravet. Här jämförs i stället många mynt samtidigt,
long i de starkaste och short i de svagaste. Det ger fler oberoende satsningar, och portföljen är nära
marknadsneutral (spår C). Båda idéerna är dokumenterade i forskningen om kryptomarknader (tvärsnittsmomentum:
till exempel Liu och Tsyvinski 2021; funding-carry: premien som longsidan betalar på terminer). Parametrarna
nedan är standardval från den litteraturen och **optimeras inte**.

## Gemensamt för H-0014 och H-0015

| Del | Val |
|---|---|
| Universum | Binance USDⓈ-M-terminer mot USDT som har en månadsfil för 2020-01 bland kandidaterna BTC, ETH, BCH, XRP, EOS, LTC, TRX, ETC, LINK, XLM, ADA, XMR, DASH, ZEC, XTZ, BNB, ATOM, ONT, IOTA, BAT, VET, NEO, QTUM, IOST. Universumet bestäms av den regeln, inte av senare resultat. Mynt som avnoteras ligger kvar tills datan tar slut, och positionen stängs då på sista öppningen. |
| Data | Dagsstaplar (1d) och finansieringsränta från data.binance.vision |
| Period | 2020-01-01 till 2024-12-31 (hela perioden är test, eftersom inget optimeras). Slutprov 2025-01-01 till 2026-09-30 läses inte in. |
| Valbarhet | Minst 60 dagars historik och en stängd stapel samma dag |
| Datafel | Ett mynt med fel enligt `quality.check` (inte bara varningar) tas bort ur universumet och redovisas i resultatet. |
| Ombalansering | Varje söndag (UTC) vid stängning, fyllning vid måndagens öppning. Mellan ombalanseringar driver vikterna med priset. |
| Portfölj | Long de 5 högst rankade och short de 5 lägst, lika vikt (±10 %), brutto 100 %, netto 0. Färre än 10 valbara mynt ger platt. |
| Kostnader | 16 bp per sida på omsatt belopp (avgift 10, halv spread 1, slippage 5), stress 2,5 gånger. Finansieringsränta betalas eller tas emot per mynt och avräkning. |
| Ingen hävstång | Brutto 1x av kapitalet |

### H-0014: tvärsnittsmomentum
Rang = avkastning från stängningen 29 dagar före till stängningen dagen före ombalanseringen (28 dagar, där
den senaste dagen hoppas över för att undvika kortsiktig återgång). Long högst, short lägst.

### H-0015: funding-carry
Rang = medelvärdet av de finansieringsräntor som avräknats under de senaste 7 dagarna, strikt före stängningen
(en avräkning exakt vid stängningen räknas inte, eftersom beslut och fyllning sker i samma ögonblick).
Short högst ränta (longsidan betalar mest), long lägst.

## Beslutskriterier (spår C, research/tracks.md)

`MORE_RESEARCH` om **alla** gäller, annars `REJECT`:

1. t (Newey-West, dagsavkastning) ≥ kravet vid körningen: **2,71** (N = 15)
2. Avkastning med 2,5 gånger kostnaderna > 0
3. |beta mot BTCUSDT spot 1d| ≤ 0,2

`MORE_RESEARCH` betyder slutprov på 2025–2026 med samma regler. Först därefter kan det bli papper framåt.

## Kända svagheter, skrivna i förväg

- Universumet är litet (cirka 24 mynt) jämfört med studierna, och korrelationen mellan altcoins är hög.
- Blankning antas alltid möjlig till terminspris. Avnoterade mynt kan ha sämre likviditet än kostnadsmodellen antar.
- 2020–2024 är sedd för BTC i tidigare hypoteser, men inte för tvärsnitten.
