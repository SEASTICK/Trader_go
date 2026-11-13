# Vägen till en app som ger positiv avkastning

Ingen kan lova positiv avkastning. Det vi kan styra är att leta på rätt ställen, mäta ärligt och bara
släppa igenom det som klarar varje grind. Läget 2026-11-13: alla 20 avgjorda hypoteser är `REJECT` (H-0001–H-0015, H-0017–H-0020 och H-0023). Tre försök blev `OGILTIGA` och har inget beslut: H-0016 (för många kurser saknas), H-0021 (datahål under hållna positioner) och H-0022 (testets eget datakrav kan inte uppfyllas, ingen körning gjordes). H-0023 (kassa-och-termin med Rullning B) kördes en gång och blev `REJECT`: t 1,37 mot kravet 3,45, CAGR 2,94 % mot kravet över 3 %. Inget av dem ger någon avkastning att lita på.

Produktens faser och den bekräftade målbilden beskrivs i [färdplanen](fardplan.md). Grindarna nedan gäller validering av strategier och ger ingen aktivering av livehandel.

## Grindarna

| # | Grind | Krav för att gå vidare | Status |
|---|---|---|---|
| 1 | Hypotes registrerad | Hypotes, data, kostnader och kriterier i `research/registry.md` före körning | Fungerar |
| 2 | Historiskt test | Spårets kriterier: t ≥ krav (stiger med antal försök), vinst med 2,5 gånger kostnaderna, spårets extra krav | 0 av 19 klarade. Närmast: H-0020 basis (t 2,41 mot 2,81, klarar övriga fyra kriterier) |
| 3 | Slutprov (holdout) | Samma regler på orörd data 2025-01 till 2026-09, körs en gång | Ingen har nått hit |
| 4 | Papper framåt | Fryst strategi på servern minst 3 månader. Utfallet inom ±2 standardfel av testet, ingen regel bruten | Insamlingen går sedan 2026-11-02 (Edwins server) |
| 5 | Liten live | Uttryckligt beslut av er båda (`pengar-grind`). Liten summa, nyckel utan uttag låst till serverns IP, nödstopp och maxförlust per dag | Inte påbörjad, och får inte påbörjas utan beslut |
| 6 | Full live | Liten live i minst 3 månader utan avvikelser mot papper | – |

## Varför det inte har fungerat än, och vad vi gör åt det

1. **För lite statistisk styrka.** Ett mynt i fem år ger få oberoende utfall, och kravet är t ≥ 2,7.
   → **Tvärsnitt över många mynt** (H-0014, H-0015): fler oberoende satsningar per vecka. Resultat: t 1,4 för
   båda, alltså närmare men inte i mål. Universumet blev bara 11 mynt enligt protokollets regel.
   Uppföljningen med 85 terminer (H-0018, H-0019, 25 bp per sida) hjälpte inte: momentum t 0,04 och
   funding-carry t 1,36, och båda förlorar med 2,5 gånger kostnaderna. Fler småmynt betyder högre kostnader,
   och carry-kanten har krympt sedan 2022. Fler mynt är alltså inte vägen framåt för dessa två idéer.
   → **Basis mellan kvartalstermin och spot** (H-0020): nästan riskfri, beta 0, max nedgång −3,7 %, men bara
   4,2 % per år och t 2,41. Kanten är verklig men liten. Den första körningen klarade allt på grund av ett fel
   i kapitalräkningen (gratis belåning), som granskningen hittade före beslut.
2. **Svagt stöd för idéerna.** Enkla indikatorer på ett mynt överlever sällan kostnaderna.
   → Effekter med stöd i forskningen: tvärsnittsmomentum och funding-carry. Parametrar från litteraturen,
   ingen optimering.
3. **Bara uppgång och nedgång i samma riktning som BTC.** När BTC dominerar slår få strategier köp-och-behåll.
   → **Marknadsneutrala** portföljer (spår C): long de starkaste och short de svagaste. De kan tjäna även när marknaden faller.
4. **Kostnaderna äter kanten.** 16 bp per sida är försiktigt räknat.
   → Låg omsättning (ombalansering en gång i veckan). Lägre verkliga avgifter (makers) testas först
   när en strategi klarat grind 3, aldrig för att rädda ett resultat.

## Investerarspåret (från 2026-11-04)

Att följa kända investerares redovisade innehav, i stället för egna signaler:

- **H-0016:** tio kända investerares 13F-innehav (Berkshire m.fl.), `research/13f-protokoll.md`. **Ogiltig, inget
  beslut.** Protokollet kräver att minst 90 % av vikten har kurs. Körningen 2026-11-12 hade 14,8 % utan kurs (gräns
  10 %), mest avnoterade och uppköpta bolag som Yahoo inte har. Omkörningen efter rättad kurshämtning gav exakt samma
  siffra: luckorna beror på källan, inte på ett fel i hämtningen. Inga luckor har fyllts med gissningar. Siffrorna i
  registret är bara diagnostik. Täckningsdiagnosen finns i `research/coverage/H-0016-coverage-20261112T113940Z.json`.
- **H-0017:** Nancy Pelosis redovisade affärer, `research/pelosi-protokoll.md`. **REJECT**: t 1,43 mot kravet 2,75,
  och Sharpe 0,97 mot SPY:s 1,01. Mer avkastning än SPY men också mer risk.
- **Papper framåt:** 100 000 USD som följer de tio investerarna från 2026-11-05, sidan Investerare i appen. Det är en
  **observation framåt**, inte ett validerat historiskt test. Den bevisar inget förrän grind 4 (minst 3 månader) är
  uppnådd, och H-0016 är inte godkänd.

Kurserna kommer från Yahoo utan nyckel, se [kurskalla.md](kurskalla.md). Båda urvalen är gjorda i efterhand, eftersom
investerarna är kända för att ha lyckats. Testen blir därför för optimistiska.

## Försök efter H-0020 (läget 2026-11-12)

Alla tre är försök att komma närmare målet, och inget av dem har visat avkastning.

- **H-0021, tidsseriemomentum över många mynt:** `OGILTIG`. I 37 hållna övergångar saknades nästa dags kurs: 32 positioner vid en oförklarad lucka i datan
  (2022-02-26 till 02-28) och 5 serier som tar slut utan en källa som säger varför. Då går testet inte att avgöra, och inga prestandasiffror togs fram.
  Det kan göras om först när luckorna har en förklarande källa.
- **H-0022, kassa-och-termin på sju altcoins:** `OGILTIG`, ingen körning gjordes. Datagranskningen visade att den serie man rullar in i är för tunt handlad: högst
  9 av 13 kvartal kan ha minst fyra mynt, medan testets eget krav var 10. Det är en diagnos av data, inte ett resultat. Ingen avkastning har räknats.
- **H-0023, samma idé med en annan tidtabell (körd 2026-11-13, REJECT):** man går in efter att det förra kontraktet löpt ut, i den då närmaste serien, i stället för
  veckan före. Tidtabellen valdes efter att vi sett H-0022:s volymproblem, och datagranskningen klarar kravet på exakt gränsen: 10 av 13 kvartal (kravet är minst 10 av 13), utan marginal. Testet blev giltigt (63 av 91 mynt-cykler, 10 av 13 kvartal) och gav `REJECT`: t 1,37 mot kravet 3,45 och CAGR 2,94 % mot kravet över 3 %. Nästan hela summan kommer från två kvartal (+5,2 % och +5,3 %), de övriga tolv summerar till ungefär noll efter kostnader. Det är en iakttagelse i efterhand, inte en ny hypotes. H-0020 (samma grundidé på BTC och ETH) är `REJECT`. Se `research/h0023-protokoll.md` och `research/results/H-0023-20261113T110747Z.json`. Ett backtest är ingen prognos och inget löfte ges.

## Nästa idéer i kö (registreras en i taget, aldrig efter att ha sett resultatet)

- Kombination av flera godkända, okorrelerade strategier, först när minst två klarat grind 3.

## Det som inte görs

- Inga riktiga order, inga börsnycklar och ingen hävstång före grind 5 och ett uttryckligt beslut.
- Inga parametrar som väljs efter att ha sett slutprovet.
- Inga misslyckade försök som tas bort ur registret.
