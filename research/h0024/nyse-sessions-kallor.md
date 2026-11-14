# NYSE-sessionskalendern för H-0024: källor och avstämning

**Status 2026-11-14: delvis verifierad. 85 av 176 stängningar har ett belägg (84 maskinavstämda mot dokument jag läst, 1 läst av Codex i ett dokument jag inte kunnat öppna); 91 återstår overifierade och listas datum för datum i [nyse-unverified-dates.md](nyse-unverified-dates.md), så `tom.evaluate` förblir fail-closed.**
Avstämningen är en maskinavstämning som jag (Claude) gjorde mot dokumenten, inte en mänsklig granskning (`verified_by` säger det). Raden 2018-12-05 är undantaget: den bygger på att Codex har läst NYSE Arca Options RB-18-06 / NYSE American RB-18-176 (2018-12-03), s. 1, som säger "Exchanges will be closed on Wednesday, December 5, 2018 in observance of a National Day of Mourning for President George H. W. Bush." (citat och sida återgivna av SEASTICK i PR #133). nyse.com svarar 403 på automatiska anrop, jag har inte kunnat öppna dokumentet, och raden är markerad så i `verified_by` (ingen maskinavstämning). Dokumenten hämtades 2026-11-14 efter att `www.nyse.com`
tillåtits i sessionens miljö; SHA-256 för varje dokument är låst i `engine/traderlab/nyse_verify.py` (`EVIDENCE`). SHA-256-låset på sessionsfilen och testet mot `generate()` visar fortfarande bara att
CSV:n motsvarar samma kod; det är avstämningen mot dokumenten nedan som är det oberoende beviset, och bara för de rader den täcker.

## Vad som ska verifieras (176 stängningar på vardagar, 2006-01-01..2024-12-31)

Fullständig lista: [nyse-closures-ledger.csv](nyse-closures-ledger.csv), en rad per stängt vardagsdatum med namn, regel och kandidatkälla. Sessionerna är exakt alla vardagar minus ledgerns datum
(kontrolleras av `python -m traderlab.nyse_sessions` och testerna). Raderna fördelar sig så:

| Grupp | Antal | Datum | Kandidatkälla (ej läst av Claude) |
|---|---|---|---|
| Ordinarie helgdagar | 172 | New Year's Day, MLK Day, Washington's Birthday, Good Friday, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas för alla år 2006–2024 samt Juneteenth 2022–2024 (en rad per år och helgdag, ofta flyttad till närmaste vardag) | S1 och S2 |
| Extra stängning 2007-01-02 | 1 | nationell sorgedag efter Gerald Fords död | S4 |
| Extra stängning 2012-10-29 och 2012-10-30 | 2 | stormen Sandy | S3 |
| Extra stängning 2018-12-05 | 1 | nationell sorgedag efter George H. W. Bush död | S4 |

## Vad som är läst och vad det styrker (reproducerbart)

Kommando (kräver nät, `pdftotext`/`pdftoppm` från poppler och Pillow): `cd engine && python -m traderlab.nyse_verify --evidence-dir <katalog> --download` (lägg till `--apply` för att fylla ledgern).
Utan `--apply` skrivs bara avvikelser och antal ut. Dokumenten och deras SHA-256:

| Id | Dokument (publik adress) | SHA-256 | Styrker | Rader |
|---|---|---|---|---|
| NYSE-CAL-2020 | NYSE 2020 Trading Calendar, `nyse.com/publicdocs/NYSE_2020_Trading_Calendar.pdf` | `17109dce…70dac2d` | 2020-01-01, 01-20, 02-17, 04-10, 05-25, **07-03 (4 juli var en lördag, flyttad till fredagen)**, 09-07, 11-26, 12-25 | 9 |
| ICE-HOL-2018-2020 | NYSE Group press release 2017-11-27, "2018, 2019 and 2020 holiday and early closings calendar" (Business Wire; ICE investor-sida, `s2.q4cdn.com/154085107/files/doc_news/archive/27aaa58b-ebcb-4f53-b505-aee992f54968.pdf`) | `b13c0181…89812` | Tabellen över helgdagar (heldagsstängningar) för **2018, 2019 och 2020**: nio rader per år. Fotnoterna anger tidiga stängningar 1:00 p.m. (2018-07-03, 2018-11-23, 2018-12-24; 2019-07-03, 2019-11-29, 2019-12-24; 2020-11-27, 2020-12-24) som **inte** är stängda dagar; avstämningen kontrollerar att de är handelsdagar och saknas i ledgern | 18 (2018 och 2019) |
| ICE-HOL-2019-2021 | NYSE Group press release 2018-12-04, "2019, 2020 and 2021 holiday and early closings calendar" (`s2.q4cdn.com/154085107/files/doc_news/archive/15638cee-2935-4422-bcb4-a3733587eb8b.pdf`) | `bfc91ff0…fb58a` | Tabellen för **2019, 2020 och 2021** (2021: 01-01, 01-18, 02-15, 04-02, 05-31, **07-05**, 09-06, 11-25, **12-24 (jul, flyttad)**); 2019 och 2020 stäms av mot det första pressmeddelandet och mot varandra, och 2020 mot årskalendern. Tidiga stängningar 2021-11-26 m.fl. är handelsdagar | 9 (2021) |
| NYSE-CAL-2022 | NYSE 2022 Trading Calendar, `nyse.com/publicdocs/ICE_NYSE_2022_Yearly_Trading_Calendar.pdf` | `2c2e63b7…985bb6c9` | Dagar fyllda som "Exchange Holiday - Market Closed": 2022-01-17, 02-21, 04-15, 05-30, **06-20 (Juneteenth, flyttad)**, 07-04, 09-05, 11-24, 12-26. Ingen stängning för nyårsdagen 2022 (lördag) | 9 |
| NYSE-CAL-2023 | NYSE 2023 Trading Calendar, `…/ICE_NYSE_2023_Yearly_Trading_Calendar.pdf` | `3d28b46a…542bcfe2` | 2023-01-02, 01-16, 02-20, 04-07, 05-29, 06-19, 07-04, 09-04, 11-23, 12-25 | 10 |
| NYSE-CAL-2024 | NYSE 2024 Trading Calendar, `…/ICE_NYSE_2024_Yearly_Trading_Calendar.pdf` | `02282e73…ccbfd145` | 2024-01-01, 01-15, 02-19, 03-29, 05-27, 06-19, 07-04, 09-02, 11-28, 12-25 | 10 |
| NYSE-RULES | NYSE Rules guide, `nyse.com/publicdocs/nyse/regulation/nyse/NYSE_Rules.pdf` (28 MB) | `b5759294…81939a22` | Information Memo 06-02 (2006-01-12) och 07-05 (2007-01-19), margin extensions holiday schedule: "will be closed on <veckodag>, <datum>" för MLK, Presidents' Day, Good Friday, Memorial Day, 4 juli, Labor Day, Thanksgiving och jul 2006 och 2007; Information Memo 06-88 (2006-12-29): stängt tisdag 2007-01-02 (Gerald Ford) | 8 (2006) + 8 (2007) + 1 |
| SEC-34-70097 | SEC Release No. 34-70097 (2013-08-02), s. 6, `sec.gov/rules/sro/nysearca/2013/34-70097.pdf` | `62d4faad…b76eb2e1` | "On October 29 and 30, 2012 ... all U.S. equities and options markets would be closed for those two days" | 2 |

Avstämningen kontrollerar dessutom att **allt** som kalendrarna 2020 och 2022–2024 och pressmeddelandenas tabeller 2018–2021 visar som stängt finns i ledgern och tvärtom (ingen extra eller saknad stängning de åren). För 2006 och 2007 styrker memona de åtta ordinarie
dagarna per år, men inte nyårsdagen (memona utfärdades efter den) och ingen kompletthet för året.

**Rule 7.2** (adopterad 2015-12-30, ändrad 2017-07-27; PDF-sida 44 i regelboken) och äldre Rule 51 `.10 Holidays` i samma dokument anger helgdagarna (New Year's Day, Martin Luther King Jr. Day, Presidents' Day, Good Friday,
Memorial Day, Independence Day, Labor Day, Thanksgiving Day, Christmas Day) och flyttregeln (lördag → föregående fredag, söndag → följande måndag, "unless unusual business conditions exist, such as the ending of a monthly or yearly
accounting period"). Det styrker **regeln**, inte enskilda datum (regeln anger inte hur "tredje måndagen" räknas, och Juneteenth saknas i den text som ingår). Den ligger bakom att nyårsdagen på lördag inte stänger 31 december,
men 2010-12-31 och 2021-12-31 som sessioner är inte belagda med ett dagsdokument här. Rule 7.2-texten kontrolleras som text i avstämningen; inga rader fylls på den grunden.

## Vad som återstår (91 rader) och varför

Hela listan datum för datum finns i [nyse-unverified-dates.md](nyse-unverified-dates.md) (genereras ur ledgern av `--write-gaps`; ett test kontrollerar att den är i synk). Sammanfattning:

| Rader | Varför de är overifierade | Vad som skulle behövas |
|---|---|---|
| 2008–2017, 89 ordinarie helgdagar (9 per år, 8 för 2011) | Regelboken har dagsdokument (Information Memos) bara för 2004–2007. NYSE:s årskalendrar hittades för 2020 och 2022–2024 och NYSE Group-pressmeddelanden för 2018–2021; för 2008–2017 hittades inget dagsdokument (nyse.com svarar 403 på många okända sökvägar, så ett 403 visar inte att dokumentet saknas) | NYSE:s eller ICE:s helgdagskalendrar eller pressmeddelanden för 2008–2017 (liknande "NYSE announces 20XX holiday calendar"-kungörelser) |
| 2006-01-02 och 2007-01-01 (nyårsdagen) | Marginal-memona utfärdades efter nyår | NYSE-notis eller kalender för nyår 2006 och 2007 |
| 2018-12-05 är **inte** med här | Den har ett belägg (Codex läste RB-18-06 s. 1, citat ovan) men räknas som människoverifierad, inte maskinavstämd, eftersom jag inte kan öppna dokumentet | En maskinavstämning kräver att dokumentet går att hämta automatiskt |

89 + 2 (nyårsdagarna 2006 och 2007) = 91 rader. Siffran och listan genereras ur ledgern, inte för hand.

Källor jag har sökt men som inte gav datumbevis för de raderna: NYSE:s sida "Holidays & Trading Hours" (nuvarande år, 2026–2028), `Trading_Days.pdf` (bara 2026–2028 uppskattade), Rule 7.2 och Rule 51 (regler, inte datum), EDGAR-fulltext (fondprospekt som listar "NYSE holidays" utan dagsdatum).

## Så avstäms och verifieras kalendern (reproducerbart från repot)

1. Kör `cd engine && python -m traderlab.nyse_sessions`. Det skriver ut `ok` (konsistens: sessioner = vardagar − ledger, inga dubbletter, inga helger) och antalet verifierade rader (idag 85 av 176).
2. En granskare läser S1–S4 och fyller i `verified_source` (källa och exakt hänvisning, till exempel dokument, sida eller URL), `verified_by` och `verified_date` på **varje** ledger-rad som källan styrker. Kolumnerna lämnas
   tomma av generatorn. Ändra aldrig `date`, `name` eller `rule` utan att också ändra sessionsfilen (då ändras SHA-256-låset och ett nytt granskningsvarv behövs).
3. `tom.evaluate` kräver att alla 176 rader har källa, person och datum (och att avstämningen är konsistent) innan en körning är giltig. Så länge det inte gäller (idag 85 av 176) returnerar den `OGILTIG` med orsaken, utan kriterier eller mått.
4. Maskinavstämningen (`nyse_verify`) fyller bara rader som ett dokument styrker. Den ersätter inte en mänsklig granskning av att dokumenten och slutsatserna är rätt; en granskare kan ändra `verified_by` efter egen kontroll.

## Vad som är avgjort och vad som inte är det

* Avgjort (kod och test): att sessionsfilen är konsistent med ledgern, att en saknad vanlig session eller månadsslutssession i SPY-serien ger `OGILTIG`, att kalendern är fastlåst, och att 84 stängningar (2006, 2007, 2012-10-29/30, 2018–2024) styrks av namngivna dokument med låsta hashar.
* **Inte avgjort: att kalendern är rätt jämfört med verkligheten.** Det kräver en granskare med åtkomst till S1–S4. Om officiella historiska kalendrar inte täcker hela 2006–2024, ska det sägas uttryckligen i raden och kalendern förbli markerad som ännu ej verifierad.
