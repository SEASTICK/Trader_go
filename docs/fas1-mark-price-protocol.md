# Förregistrerad teknisk mark-price-kontroll

Kontrollen gäller de fyra redan REJECT-markerade Fas 1-resultaten H-0009–H-0012.
Inga parametrar eller beslut ändras. Inget nytt strategiurval görs.

Källa: Binances publika månadsarkiv för USDⓈ-M BTCUSDT markPriceKlines, 4h,
från 2020-01-01 till exklusivt 2025-01-01. Samtliga 60 arkiv och deras SHA256
kontrolleras. Inget arkiv från 2025 eller senare får öppnas. Kräver exakt samma
10 962 öppningstider som det frysta kontraktsdatasetet och giltig OHLC.

För varje originalfönster reproduceras de frysta parametrarna och Trade-objekten.
En oberoende kontroll räknar isolerad marginalsäkerhet med mark-price-lägsta
för long och högsta för short. Antal enheter = ursprunglig 1x-notional / inträdespris.
Inträdeskostnad och finansiering dras från säkerheten; för betalad finansiering
används mark-stapelns högsta pris och för mottagen dess lägsta (försiktig gräns).
Även hela utträdesstapeln inkluderas när ordningen inom stapeln är okänd.
Öppna affärer stoppas vid respektive walk-forward-fönsters slut.

Krav: redovisa varje möjlig träff där marginalsäkerheten understiger 0,5 % eller
1 % av aktuell mark-notional. En möjlig träff får inte beskrivas som säker
likvidation, eftersom ordningen inom stapeln är okänd. Saknade data, avvikande
originalreproduktion eller en möjlig träff stoppar godkännandet av kontrollen.

Kontrollera separat den analytiska tröskeln från M + q*(P-E) - kostnad - funding
= abs(q)*P*MMR, för både long och short, mot handräknade exempel. Den gamla
motorns tröskel är en förenkling. Detta test får inte märka den som en exakt
Binance-modell: historiska risktrappor, exakt mark price vid avräkning och
likvidationsavgifter saknas. Fas 1-worker tillåter enbart 1x. Högre hävstång och
exakt börsreplikering är inte godkända av detta test.

## Tillägg efter arkivkontroll, före kompletteringshämtning

De 60 verifierade månadsarkiven har 48 saknade staplar på åtta hela UTC-dagar:
2021-07-01, 2021-07-24–27, 2022-07-31, 2022-10-02 och 2023-02-24.
Det misslyckade täckningsresultatet bevaras. Ingen strategispecifik kontroll
eller borttagning av dessa tider tillåts.

Komplettera deterministiskt samtliga saknade tider, endast med verkliga
markPriceKlines från Binance: först publicerade dagsarkiv med CHECKSUM, och
om ett sådant saknas, det publika markPriceKlines-API:t med sparat råsvar och
SHA256. Månadsarkiven ändras aldrig. Endast exakt saknade öppningstider får
läggas till; tidsram, OHLC, dubbletter och full täckning kontrolleras igen.
Om API används hämtas även en angränsande publicerad stapel på vardera sidan;
överlappande OHLC ska stämma inom 1e-8 i absolut pris. Avvikelse eller kvarstående
lucka stoppar godkännande. Ingen interpolering eller kontrakts-/spotersättning.
