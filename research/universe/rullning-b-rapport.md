# Rullning B: volym- och datatäckningsgranskning för en möjlig H-0023

Datum: 2026-11-12. Uppdrag från Codex efter PR #120. Kandidattidtabellen och beslutsregeln låstes i `research/rullning-b-kandidat.md` (commit `3be2903`) **före** mätningen. **Ingen H-0023-rad är skriven. Ingen basis, avkastning, t-statistik eller beta har beräknats, och inga arkiv från 2025-01-01 eller senare har öppnats.** Mätningen använder exakt samma kontroller som H-0022:s täckningsgranskning (`h0022_coverage.audit_coin_cycle`, efter PR #119).

## Öppen redovisning: idén valdes efter volymdiagnosen

Kandidaten formades av att H-0022:s volymdiagnos (#119) visade att den inrullade, näst närmaste serien var för tunn. Det är en designfrihet som måste stå i en eventuell H-0023-rad. Den följer inte av avkastning (ingen har räknats), och exakt **en** tidtabell har prövats, men den valdes efter att vi sett att den föregående tidtabellen föll på volym.

## Slutsats enligt den låsta beslutsregeln: ja, men med noll marginal

Beslutsregeln (låst före mätning): ja om tidtabellen vid minsta position 10 000 USD når minst 46 av 91 mynt-cykler **och** minst 10 av 13 cykler med minst 4 handlade mynt, med 0 `OGILTIGA` på grund av saknade staplar.

| Mått | Krav | H-0022 (#119) | Rullning B |
|---|---|---|---|
| Mynt-cykler handlade vid minsta position (av 91) | minst 46 | 61 | **63** |
| Cykler med minst 4 handlade mynt (av 13) | minst 10 | 9 | **10** |
| Mynt-cykler som blir OGILTIGA av saknade staplar | 0 | 0 | **0** |
| Beslutsregeln uppfylld | | nej | **ja** |

**Rullning B klarar alltså datakraven, men exakt på gränsen: 10 av 10.** Det bör inte läsas som ett robust ja.

## Varför marginalen är noll (känslighet)

* Skillnaden mot H-0022 beror på **en enda cykel**: cykel 10 (fyllning 2023-07-01) går från 3 till 4 mynt över gränsen. Det är den som lyfter antalet från 9 till 10. I övriga cykler byter tidtabellen bara plats på ett mynt hit och dit (cykel 6 +1, cykel 9 −1, cykel 12 +1).
* Fyra mynt-cykler ligger inom ±10 % av gränsen 500 000 USD: cykel 9 LINK 495 000 (under), cykel 10 ADA 453 000 (under), cykel 12 LTC 538 000 (över) och XRP 481 000 (under).
* Tre cykler har exakt fyra mynt över gränsen (cykel 7, 9 och 10). I cykel 7 och 9 ligger ett av dem inom 20 % över gränsen (LTC 592 000, ADA 588 000). Skulle något av de fyra mynten i en av cyklerna 7, 9 eller 10 ligga under gränsen skulle antalet cykler med fyra mynt bli 9 och kravet inte uppfyllas.
* Täckningen är en **övre gräns**: kassabokens värde `V` kan sjunka (faller `V/7` under 10 000 USD blir alla platser platta), och positionen begränsas av `min(V/7, tak)`. Siffran "startstorlek 20 000 USD" i tabellen nedan är en strängare tolkning (ett tak på minst 20 000 USD för varje position) som regeln inte kräver, och redovisas bara som information: 48 mynt-cykler och 5 cykler med fyra mynt.
* Volymen är dessutom ojämn över tid: 2021 ofta 10–30 miljoner USD per mynt och dag, från 2022 ofta under en miljon, och i cykel 11 och 14 räcker volymen för högst två respektive ett mynt.

## Kalendern (genererad ur universumtabellen, inga priser)

14 cykler, samma förfall som H-0022. Beslut på föregående förfallsdag (fredag), fyllning nästa dag 00:00 UTC (lördag), utträde sju dagar före seriens förfall (fredag 00:00 UTC). Cykel 2 är platt (0924-serien 2021 saknar daterad annons). Mellan utträdet och nästa inträde ligger portföljen **8 dagar i kontanter** utan ränta i varje cykel, vilket inte påverkar täckningen men sänker avkastningen på det totala kapitalet (ingen avkastning har räknats). Alla beslutsdagar ligger i det biasfria fönstret (sista: 2024-06-28; SOL lanserades 2024-08-14).

Tabeller (genererade, `research/universe/rullning-b-datatackning-tabeller.md`):

| Cykel | Fyllning | Utträde | Data kompletta | Mynt med median ≥ 500 000 USD |
|---|---|---|---|---|
| 1 | 2021-03-27 | 2021-06-18 | 7 | 7 |
| 2 | 2021-06-26 | 2021-09-17 | platt | – |
| 3 | 2021-09-25 | 2021-12-24 | 7 | 7 |
| 4 | 2022-01-01 | 2022-03-18 | 7 | 7 |
| 5 | 2022-03-26 | 2022-06-17 | 7 | 5 |
| 6 | 2022-06-25 | 2022-09-23 | 7 | 7 |
| 7 | 2022-10-01 | 2022-12-23 | 7 | 4 |
| 8 | 2022-12-31 | 2023-03-24 | 7 | 3 |
| 9 | 2023-04-01 | 2023-06-23 | 7 | 4 |
| 10 | 2023-07-01 | 2023-09-22 | 7 | 4 |
| 11 | 2023-09-30 | 2023-12-22 | 7 | 2 |
| 12 | 2023-12-30 | 2024-03-22 | 7 | 5 |
| 13 | 2024-03-30 | 2024-06-21 | 7 | 7 |
| 14 | 2024-06-29 | 2024-09-20 | 7 | 1 |

## Data, luckor och arkiv

* **Alla 91 mynt-cykler har kompletta, verifierade data** med samma kontroller som i #119: exakt gemensam `open_time` 00:00:00 UTC för båda benen på fyllnings- och utträdesdagen, volym på fyllningarna, markpris varje hållen dag och nästa öppning för både termin och spot. 0 OGILTIGA, 0 stapel med avvikande tidsstämpel.
* **Arkiv:** 1 463 filer verifierade mot sparad checksumma (0 fel). Den nya kalendern kräver inga nya nedladdningar, eftersom inträdesdagarna ligger efter H-0022:s och markprisdagarna därför är en delmängd. Augustiluckan 2023 (cykel 10) täcks av samma verifierade dagsfiler och manifest som i #119.
* **Datahål:** inga efter luckfyllnaden.

## Vad rapporten inte säger

* Den säger **inte** att Rullning B skulle ge avkastning eller att H-0023 bör registreras. Den säger bara att ett giltigt test enligt de låsta datakraven **inte är uteslutet** av täckningen, med noll marginal.
* Positionernas faktiska storlek och därmed likviditetstaket beror på kassaboken, så ett verkligt utfall kan hamna under siffrorna ovan.
* Inga nya trösklar, storlekar eller tidtabeller föreslås här. Eventuell registrering av H-0023 är ett separat beslut, med öppen notering om att tidtabellen valdes efter H-0022:s volymdiagnos och att täckningen klarar kravet med exakt noll marginal.

## Reproduktion

```bash
cd engine
.venv/bin/python -m traderlab.h0022_coverage --schedule rullning_b --fetch   # hämtar saknade filer (inga nya behövs) och kör granskningen
.venv/bin/python -m traderlab.h0022_coverage --schedule rullning_b --tables  # tabeller ur JSON-filen
```

Resultat: `research/coverage/rullning-b-datatackning.json` (SHA-256 per fil).
