# Vägen till en app som ger positiv avkastning

Ingen kan lova positiv avkastning. Det vi kan styra är att leta på rätt ställen, mäta ärligt och bara
släppa igenom det som klarar varje grind. Hittills: alla avgjorda hypoteser `REJECT` (H-0001–H-0015, H-0018–H-0020; H-0016 och H-0017 väntar på kurskälla), läget 2026-11-05.

Produktens faser och den bekräftade målbilden beskrivs i [färdplanen](fardplan.md). Grindarna nedan gäller validering av strategier och ger ingen aktivering av livehandel.

## Grindarna

| # | Grind | Krav för att gå vidare | Status |
|---|---|---|---|
| 1 | Hypotes registrerad | Hypotes, data, kostnader och kriterier i `research/registry.md` före körning | Fungerar |
| 2 | Historiskt test | Spårets kriterier: t ≥ krav (stiger med antal försök), vinst med 2,5 gånger kostnaderna, spårets extra krav | 0 av 18 klarade. Närmast: H-0020 basis (t 2,41 mot 2,81, klarar övriga fyra kriterier) |
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

- **H-0016:** tio kända investerares 13F-innehav (Berkshire m.fl.), `research/13f-protokoll.md`.
- **H-0017:** Nancy Pelosis redovisade affärer, `research/pelosi-protokoll.md`.
- **Papper framåt:** 100 000 USD som följer de tio investerarna från 2026-11-05, sidan Investerare i appen.

Alla tre väntar på en kurskälla, se [kurskalla.md](kurskalla.md). Båda urvalen är gjorda i efterhand, eftersom
investerarna är kända för att ha lyckats. Testen blir därför för optimistiska.

## Nästa idéer i kö (registreras en i taget, aldrig efter att ha sett resultatet)

- Kombination av flera godkända, okorrelerade strategier, först när minst två klarat grind 3.
- Tidsseriemomentum över många mynt (varje mynt long eller short efter sin egen trend), spår A/B.

## Det som inte görs

- Inga riktiga order, inga börsnycklar och ingen hävstång före grind 5 och ett uttryckligt beslut.
- Inga parametrar som väljs efter att ha sett slutprovet.
- Inga misslyckade försök som tas bort ur registret.
