# H-0022: datatäckningsgranskning före strategimotor

Datum: 2026-11-12. Uppdrag från Codex efter PR #118 (H-0022 förregistrerad, N = 22). **Ingen basis, avkastning, t-statistik eller beta har beräknats, inga låsta parametrar är ändrade och inga arkiv från 2025-01-01 eller senare har öppnats** (dataperioden stängs vid `2024-10-01` i koden och testas). Rapporten visar *möjlig* täckning: kapital och likviditetstak beror på kassabokens framtida värde, så den visar vad som går att förhandskontrollera och inte vilka positioner som faktiskt skulle tas.

## Slutsats

1. **Data finns och är verifierade.** För alla 91 mynt-cykler som universumet släpper in (7 mynt × 13 cykler; cykel 2 är platt) finns last price (COIN-M), markpris och spot med samma `open_time` på inträdes- och utträdesdagen, volym > 0 på alla fyllningar, staplar för varje hållen dag och nästa öppning efter varje hållen dag. **0 av 91 skulle bli `OGILTIG` på grund av saknade staplar.** Kontraktsstorleken (härledd median) ligger inom 9,5–10,5 för alla 91.
2. **Men datakrav 4 går inte att uppfylla med den registrerade likviditetsregeln.** Protokollet kräver minst 10 av 13 cykler med minst 4 handlade mynt. Högst **9** cykler kan ha fyra mynt, även i det mest generösa fallet (minsta position 10 000 USD, alltså serier med medianvolym över 500 000 USD). Vid startstorleken 20 000 USD är det 5 cykler, och antalet mynt-cykler (45) hamnar under kravet 46.
3. **Det betyder att H-0022 som registrerad inte är ett giltigt test:** en körning som följer protokollet skulle få `OGILTIG` (datakrav 4, ingen beslut) oavsett strategiutfall. Jag säger det utan att köra något, enligt uppdraget.

Orsaken är likviditetstaket (2 % av den inrullade seriens 20-dagars medianvolym). Vid utträdet 7 dagar före förfall är nästa serie den *näst närmaste*, och den handlas mycket tunnare än närmaste serien. Volymen sjunker dessutom kraftigt över tid (20-dagarsmedian: 2021 ofta 10–30 miljoner USD per dag, 2022–2024 ofta under en miljon, se `h0022-datatackning-tabeller.md`).

## Täckning per cykel

Genererade tabeller (`research/universe/h0022-datatackning-tabeller.md`, ur `research/coverage/h0022-datatackning.json`). Utdrag:

| Cykel | Fyllning | Mynt i universum | Data kompletta | Median ≥ 500 000 USD (minsta position) | Median ≥ 1 000 000 USD (startposition) |
|---|---|---|---|---|---|
| 1 | 2021-03-27 | 7 | 7 | 7 | 7 |
| 2 | 2021-06-18 | 0 (platt) | – | – | – |
| 3 | 2021-09-17 | 7 | 7 | 7 | 7 |
| 4 | 2021-12-24 | 7 | 7 | 7 | 7 |
| 5 | 2022-03-18 | 7 | 7 | 5 | 5 |
| 6 | 2022-06-17 | 7 | 7 | 6 | 3 |
| 7 | 2022-09-23 | 7 | 7 | 4 | 1 |
| 8 | 2022-12-23 | 7 | 7 | 3 | 3 |
| 9 | 2023-03-24 | 7 | 7 | 5 | 3 |
| 10 | 2023-06-23 | 7 | 7 | 3 | 2 |
| 11 | 2023-09-22 | 7 | 7 | 2 | 0 |
| 12 | 2023-12-22 | 7 | 7 | 4 | 0 |
| 13 | 2024-03-22 | 7 | 7 | 7 | 6 |
| 14 | 2024-06-21 | 7 | 7 | 1 | 1 |

| Datakrav 4 | Krav | Möjligt vid minsta storlek | Möjligt vid startstorlek |
|---|---|---|---|
| Mynt-cykler handlade (av 91) | minst 46 | 61 | 45 |
| Cykler med minst 4 handlade mynt (av 13) | minst 10 | **9** | **5** |
| Kravet uppfyllt | | **nej** | **nej** |

Cykler med minst fyra mynt vid minsta storlek: 1, 3, 4, 5, 6, 7, 9, 12 och 13 (nio). Cykel 8, 10, 11 och 14 har tre, tre, två respektive ett mynt.

## Luckor och hur de hanterades

* **Markpris 2023-08-28..31:** månadsfilerna för de sju 0929-serierna (cykel 10) saknar de fyra dagarna, vilket annars hade gjort sju mynt-cykler `OGILTIGA` (saknad markprisdag under innehavet). Dagarna fylldes ur Binances dagsarkiv för markpris med samma verifiering som i #113: sparad checksumma, SHA-256 mot manifestet `research/coverage/h0022-mark-gap-2023-08.json` (56 filer: sju serier × fyra gapdagar plus fyra grannedagar), giltig tidsstämpel och konsistent OHLC, och **exakt likhet med månadsfilen** för alla 28 grannedagar. Luckfyllnaden är märkt per stapel (`source = daily`) och vägras om något av detta saknas.
* **Last price 2023-08-28..31:** 14 serier (0929 och 1229) fylldes ur de verifierade dagsfilerna från #113 (112 filer).
* **Spot:** inga luckor i månadsfilerna 2021-03 till 2024-09 för de sju mynten (inga dagsfiler behövdes).
* **Övriga luckor:** inga. Samma `open_time` på båda benen vid alla fyllningar och utträden (91 av 91).

## Verifiering och källor

| Källa | Filer verifierade mot sparad checksumma |
|---|---|
| COIN-M last price, månadsfiler (`data.binance.vision`, `futures/cm/monthly/klines`) | 630 |
| COIN-M markpris, månadsfiler (`futures/cm/monthly/markPriceKlines`) | 364 |
| COIN-M markpris, dagsfiler (augusti 2023) | 56 |
| COIN-M last price, dagsfiler (augusti 2023, från #113) | 112 |
| Spot, månadsfiler (`spot/monthly/klines`) | 301 |
| **Totalt** | **1 463** (checksummafel: 0) |

SHA-256 per fil finns i `research/coverage/h0022-datatackning.json`. Datafilerna själva ligger inte i repot (`data/` committas inte). Reproduktion:

```bash
cd engine
.venv/bin/python -m traderlab.h0022_coverage --fetch   # hämtar saknade filer med checksumma och kör granskningen
.venv/bin/python -m traderlab.h0022_coverage --tables  # skriver tabellerna ur JSON-filen
```

## Vad som återstår att kontrollera vid en körning

* Faktisk position per mynt och cykel: `A = min(V/7, tak)` beror på kassabokens värde `V`, som inte går att veta i förväg. Täckningen ovan är därför en övre gräns.
* Att verifierade filer är oförändrade (SHA-256 mot `h0022-datatackning.json` och `h0022-mark-gap-2023-08.json`).
* Att inga arkiv från 2025 eller senare öppnas (test finns i motorn som ska byggas).
* Riskstoppet läser dagligt högsta markpris för varje hållen dag. Alla dagar finns, men stoppets utfall går inte att veta förrän en körning.

## Vad det här betyder (för Codex att bedöma)

H-0022 är fryst och ska inte ändras. Alternativen, som jag lägger fram men inte väljer åt oss:

1. **Köra H-0022 ändå** för att dokumentera `OGILTIG` (datakrav 4). Det ger ingen ny kunskap om idén, men en ärlig registerrad.
2. **Skriva en `OGILTIG`-rad för H-0022 utan körning**, med hänvisning till den här rapporten (datakrav 4 omöjligt), och registrera en ny hypotes (H-0023, N = 23) med en annan rullnings- eller likviditetsregel, till exempel att gå in i den *närmaste* serien efter att den förra löpt ut i stället för i den näst närmaste, eller en annan minsta storlek. Den hypotesen skulle väljas **efter** att vi sett volymtäckningen (volym, inte avkastning), vilket måste stå i registerraden, och t-kravet stiger.
3. **Avstå** från idén: täckningen visar att den *tillgängliga likviditeten* i näst närmaste serie inte räcker för ett test med den här strukturen, och att allt utom de första tre cyklerna är tunt.

Min bedömning: alternativ 2 är mest informativt, men det är en ny hypotes och ett nytt försök, och beslutet är Codex och Philips, inte mitt.
