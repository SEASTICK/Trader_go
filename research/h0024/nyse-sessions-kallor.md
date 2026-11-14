# NYSE-sessionskalendern för H-0024: källor och avstämning

**Status 2026-11-14: 176 av 176 stängningar har en dokumentbaserad källa (maskinavstämda av Claude mot dokument i sessionen; ingen mänsklig granskning). [nyse-unverified-dates.md](nyse-unverified-dates.md) visar 0 kvar. Begränsningar står längst ned; `tom.evaluate` slutar vara blockerad av kalenderns verifiering, men inget har körts (ingen SPY-data hämtad, ingen preflight, inget backtest, inget registerbeslut).**
Avstämningen är en maskinavstämning som jag (Claude) gjorde mot dokumenten, inte en mänsklig granskning (`verified_by` säger det). Raden 2018-12-05 har två belägg: dels FINRA Regulatory Notice 18-39 (maskinavstämd, se tabellen), dels att Codex har läst NYSE Arca Options RB-18-06 / NYSE American RB-18-176 (2018-12-03), s. 1, som säger "Exchanges will be closed on Wednesday, December 5, 2018 in observance of a National Day of Mourning for President George H. W. Bush." (citat och sida återgivna av SEASTICK i PR #133). nyse.com svarar 403 på automatiska anrop, jag har inte kunnat öppna det dokumentet, och människoläsningen är markerad så i `verified_by` (den är ingen maskinavstämning). Dokumenten hämtades 2026-11-14 efter att `www.nyse.com`
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
| FINRA-IN-2008 … FINRA-IN-2017 | FINRA Information Notices, ett per år (publicerade dec 2007–dec 2016): "20XX Holiday Trade Date, Settlement Date and Margin Extensions Schedule", `finra.org/sites/default/files/…` (exakta adresser och SHA-256 i `EVIDENCE`) | se `EVIDENCE` | Tillsynsmyndighetens schema. Varje helgdag har en egen mening "The securities exchanges will be closed on <veckodag>, <datum>, in observance of …" **och** en tabellrad "Markets Closed" (2013–2017: "N/A") för samma dag. Avstämningen läser meningarna, kräver att mängden för året är exakt lika med ledgerns ordinarie rader (saknat eller extra datum ger avvikelse) och att varje mening har sin tabellrad. Referensen i ledgern anger dokument, sida och meningen. Bank-helgdagar (Columbus Day, Veterans Day) och tidiga stängningar ger inga datum | 89 (2008–2017) |
| NASD-UPC-092-2005 | NASD Uniform Practice Advisory UPC #092-2005 (2005-12-07), `finra.org/sites/default/files/UPCNotice/p015658_0.pdf` | se `EVIDENCE` | "closed on Monday, December 26, 2005 … and Monday, January 2, 2006, in observance of New Year's Day", tabellraden "Jan. 2, 2006 Markets Closed" | 1 (2006-01-02) |
| FINRA-NTM-05-81, FINRA-NTM-06-73 | NASD Notices to Members 05-81 (2006 års schema) och 06-73 (2007 års schema), `finra.org/sites/default/files/NoticeDocument/p015761.pdf` och `…/p018163.pdf` | se `EVIDENCE` | 05-81: stängt "Monday, January 1, 2007, in observance of New Year's Day" (tabellrad "Jan 1, 2007 Market Closed") samt alla ordinarie dagar 2006; 06-73: alla ordinarie dagar 2007 och 2008-01-01. Korskontrolleras mot NYSE-memona (NYSE-RULES) för 2006–2007: de två källorna ska ge samma dagar (undantag: Ford 2007-01-02 kom efter NASD:s schema) | 1 (2007-01-01) + korskontroll |
| FINRA-RN-18-39 | FINRA Regulatory Notice 18-39 (2018-12-03), "Unexpected Close of Securities Markets", `finra.org/sites/default/files/Regulatory-Notice-18-39.pdf` | se `EVIDENCE` | "the securities markets may unexpectedly close for business, for example, on the national day of mourning declared in memory of President George H.W. Bush on December 5, 2018" (s. 1) och "the day of closure … U.S. equity exchanges would be closed" (s. 4). Ett allmänt besked som anger dagen som exempel, **inte** börsernas egen kungörelse; den läste Codex (HUMAN_VERIFIED, NYSE Arca RB-18-06). Båda står på raden | 1 (2018-12-05) |

Avstämningen kontrollerar dessutom att **allt** som kalendrarna 2020 och 2022–2024 och pressmeddelandenas tabeller 2018–2021 visar som stängt finns i ledgern och tvärtom (ingen extra eller saknad stängning de åren). För 2006 och 2007 styrker memona de åtta ordinarie
dagarna per år, men inte nyårsdagen (memona utfärdades efter den) och ingen kompletthet för året.

**Rule 7.2** (adopterad 2015-12-30, ändrad 2017-07-27; PDF-sida 44 i regelboken) och äldre Rule 51 `.10 Holidays` i samma dokument anger helgdagarna (New Year's Day, Martin Luther King Jr. Day, Presidents' Day, Good Friday,
Memorial Day, Independence Day, Labor Day, Thanksgiving Day, Christmas Day) och flyttregeln (lördag → föregående fredag, söndag → följande måndag, "unless unusual business conditions exist, such as the ending of a monthly or yearly
accounting period"). Det styrker **regeln**, inte enskilda datum (regeln anger inte hur "tredje måndagen" räknas, och Juneteenth saknas i den text som ingår). Den ligger bakom att nyårsdagen på lördag inte stänger 31 december,
men 2010-12-31 och 2021-12-31 som sessioner är inte belagda med ett dagsdokument här. Rule 7.2-texten kontrolleras som text i avstämningen; inga rader fylls på den grunden.

## Vad som återstår: inga overifierade rader, men dessa begränsningar gäller

* **Inga overifierade rader.** Listan [nyse-unverified-dates.md](nyse-unverified-dates.md) har 0 rader (genereras ur ledgern av `--write-gaps`; ett test kontrollerar att den är i synk).
* **Källorna för 2006–2017 är tillsynsmyndighetens (FINRA/NASD) scheman, inte NYSE:s egna kalendrar.** De anger att "the securities exchanges" var stängda de dagarna, med en tabellrad per dag. Det är ett maskinläst belägg från en oberoende primär myndighetskälla, men ingen mänsklig har läst dokumenten, och NYSE:s egna kalendrar för 2008–2017 har inte kunnat hämtas (nyse.com/ICE-sidor svarar 403 för dessa; spärrarna är inte kringgångna). 2018–2024 har NYSE:s/ICE:s egna dokument.
* **Kompletthet per år (schemalagda helgdagar):** schemat för ett år listar alla helgdagsstängningar det året, och avstämningen kräver att listan är exakt lika med ledgerns ordinarie rader. En schemalagd stängning som ledgern saknar (eller tvärtom) ger en avvikelse.
  **Oplanerade stängningar** (Ford 2007-01-02, Sandy 2012-10-29/30, Bush 2018-12-05) finns bara i ledgern där ett dokument anger dem; att inga *andra* oplanerade stängningar förekom 2006–2024 är inte belagt av dokumenten (de scheman som lästs utfärdades i förväg) utan bygger på att inga sådana är kända.
* **Tidiga stängningar (1:00 p.m.) för 2008–2017 är inte avstämda separat.** De påverkar inte sessionsmängden (de är handelsdagar); för 2018–2021 är de kontrollerade mot pressmeddelandena. FINRA-schemana anger dem inte som stängningar.
* **2018-12-05:** maskinbeviset (FINRA RN 18-39) är ett allmänt besked; NYSE:s egen kungörelse är läst av Codex, inte av mig.
* Det här är en maskinavstämning av ledgern mot dokument, inte en mänsklig granskning av att slutsatserna är rätt. En granskare kan ändra `verified_by` efter egen kontroll.

Källor jag har sökt men som inte gav bättre datumbevis: NYSE:s sida "Holidays & Trading Hours" (nuvarande år), `Trading_Days.pdf` (bara 2026–2028), Rule 7.2 och Rule 51 (regler, inte datum), EDGAR-fulltext, och ICE:s presssida (`ir.theice.com` svarar 403, inte kringgånget). NYSE Euronext-pressmeddelandena för europeiska marknader (euronext.com) gäller inte USA.

## Så avstäms och verifieras kalendern (reproducerbart från repot)

1. Kör `cd engine && python -m traderlab.nyse_sessions`. Det skriver ut `ok` (konsistens: sessioner = vardagar − ledger, inga dubbletter, inga helger) och antalet verifierade rader (idag 176 av 176).
2. En granskare läser S1–S4 och fyller i `verified_source` (källa och exakt hänvisning, till exempel dokument, sida eller URL), `verified_by` och `verified_date` på **varje** ledger-rad som källan styrker. Kolumnerna lämnas
   tomma av generatorn. Ändra aldrig `date`, `name` eller `rule` utan att också ändra sessionsfilen (då ändras SHA-256-låset och ett nytt granskningsvarv behövs).
3. `tom.evaluate` kräver att alla 176 rader har källa, person och datum (och att avstämningen är konsistent) innan en körning är giltig. Så fort en rad saknar källa (eller avstämningen är inkonsistent) returnerar den `OGILTIG` med orsaken, utan kriterier eller mått; ett test provar det med en ledger där 91 rader har tömts.
4. Maskinavstämningen (`nyse_verify`) fyller bara rader som ett dokument styrker. Den ersätter inte en mänsklig granskning av att dokumenten och slutsatserna är rätt; en granskare kan ändra `verified_by` efter egen kontroll.

## Vad som är avgjort och vad som inte är det

* Avgjort (kod och test): att sessionsfilen är konsistent med ledgern, att en saknad vanlig session eller månadsslutssession i SPY-serien ger `OGILTIG`, att kalendern är fastlåst, och att alla 176 stängningar styrks av namngivna dokument med låsta hashar (2018-12-05 också av Codex människoläsning).
* **Inte avgjort: att kalendern är rätt jämfört med verkligheten i en mänsklig granskning.** Avstämningen är maskinell (se begränsningarna ovan). H-0024 har fortfarande inte körts.
