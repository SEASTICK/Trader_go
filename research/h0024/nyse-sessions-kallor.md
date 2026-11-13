# NYSE-sessionskalendern för H-0024: källor och avstämning

**Status 2026-11-13: ej verifierad mot någon officiell källa.** Kalendern (`nyse-sessions-2006-2024.csv`, 4 781 sessioner) är genererad av `engine/traderlab/nyse_sessions.py` ur
helgdagsregler och fyra extra stängningar som jag skrev efter min kännedom, utan att ha kunnat öppna någon officiell NYSE- eller myndighetskälla från den här miljön
(nätspärr: nyse.com, Federal Register och SEC:s dokumentarkiv ligger utanför tillåtna värdar eller svarar med robotkontroll; inget kringgicks). SHA-256-låset och testet mot
`generate()` visar bara att CSV:n motsvarar samma kod. De hårdkodade årsantalen (`EXPECTED_PER_YEAR`) är också mina och bevisar ingenting oberoende. `tom.evaluate` är därför
**fail-closed**: standardkörningen blir `OGILTIG` tills varje stängning nedan är markerad som verifierad av en granskare.

## Vad som ska verifieras (176 stängningar på vardagar, 2006-01-01..2024-12-31)

Fullständig lista: [nyse-closures-ledger.csv](nyse-closures-ledger.csv), en rad per stängt vardagsdatum med namn, regel och kandidatkälla. Sessionerna är exakt alla vardagar minus ledgerns datum
(kontrolleras av `python -m traderlab.nyse_sessions` och testerna). Raderna fördelar sig så:

| Grupp | Antal | Datum | Kandidatkälla (ej läst av Claude) |
|---|---|---|---|
| Ordinarie helgdagar | 172 | New Year's Day, MLK Day, Washington's Birthday, Good Friday, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas för alla år 2006–2024 samt Juneteenth 2022–2024 (en rad per år och helgdag, ofta flyttad till närmaste vardag) | S1 och S2 |
| Extra stängning 2007-01-02 | 1 | nationell sorgedag efter Gerald Fords död | S4 |
| Extra stängning 2012-10-29 och 2012-10-30 | 2 | stormen Sandy | S3 |
| Extra stängning 2018-12-05 | 1 | nationell sorgedag efter George H. W. Bush död | S4 |

## Kandidatkällor som en granskare ska läsa (jag har inte läst någon)

| Id | Källa | Vad den förväntas styrka | Känd begränsning |
|---|---|---|---|
| S1 | NYSE:s regel om helgdagar och handelstider (i nuvarande regelbok "Rule 7.2 Holidays"; äldre regelbok kan ha annat nummer, ej kontrollerat) | Vilka helgdagar börsen stänger för och flyttregeln (lördag → fredag, söndag → måndag, nyårsdagen på lördag undantagen) | Beskriver regeln, inte varje enskilt datum; historiska versioner av regeln måste jämföras |
| S2 | NYSE:s sida "Holidays & Trading Hours" (nyse.com/markets/hours-calendars) | Datumen för ordinarie helgdagar för de år sidan visar | Täcker troligen inte hela 2006–2024; det är oklart och måste anges av granskaren |
| S3 | SEC:s och/eller NYSE:s offentliga meddelande om att börserna höll stängt 2012-10-29 och 2012-10-30 | De två extra stängningarna 2012 | Exakt dokument ej identifierat av mig |
| S4 | Presidentens order om stängning av federala myndigheter vid nationell sorgedag (Federal Register) samt NYSE:s meddelande om stängning, för 2007-01-02 och 2018-12-05 | De två sorgedagarna | Exakta dokument ej identifierade av mig |

Jag anger ingen dokumentbeteckning, sida eller citat som jag inte har läst. Finns ingen officiell källa för ett visst år eller datum ska granskaren lämna raden som overifierad och skriva det i
`verified_source` som "saknas" (raden räknas då som overifierad; det bryter inte ledgern men håller `evaluate` stängd), och frågan går tillbaka till Codex/SEASTICK.

## Så avstäms och verifieras kalendern (reproducerbart från repot)

1. Kör `cd engine && python -m traderlab.nyse_sessions`. Det skriver ut `ok` (konsistens: sessioner = vardagar − ledger, inga dubbletter, inga helger) och antalet verifierade rader.
2. En granskare läser S1–S4 och fyller i `verified_source` (källa och exakt hänvisning, till exempel dokument, sida eller URL), `verified_by` och `verified_date` på **varje** ledger-rad som källan styrker. Kolumnerna lämnas
   tomma av generatorn. Ändra aldrig `date`, `name` eller `rule` utan att också ändra sessionsfilen (då ändras SHA-256-låset och ett nytt granskningsvarv behövs).
3. `tom.evaluate` kräver att alla 176 rader har källa, person och datum (och att avstämningen är konsistent) innan en körning är giltig. Så länge det inte gäller returnerar den `OGILTIG` med orsaken, utan kriterier eller mått.

## Vad som är avgjort och vad som inte är det

* Avgjort (kod och test): att sessionsfilen är konsistent med ledgern, att en saknad vanlig session eller månadsslutssession i SPY-serien ger `OGILTIG`, och att kalendern är fastlåst.
* **Inte avgjort: att kalendern är rätt jämfört med verkligheten.** Det kräver en granskare med åtkomst till S1–S4. Om officiella historiska kalendrar inte täcker hela 2006–2024, ska det sägas uttryckligen i raden och kalendern förbli markerad som ännu ej verifierad.
