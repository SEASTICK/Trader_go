# Fas 2 – Utvecklingsplan

**26 av 40 uppgifter verifierade · 8 arbetsområden.**

H-0013 · Kontrollerad 2026-11-02 · Granskad kodversion `a852aa3`.

PR #72 mergad som d25f444. PR #73 granskad på a852aa3: 513 syntetiska Python-tester och båda lokala PGlite-kötester passerar. Två oberoende fynd före merge: normalstopp tappar försöksfil och SQL accepterar felaktiga kriterier/beslut. Ingen migration, driftsättning eller riktig körning.

## Uppdateringsregler

- `docs/fas2-status.json` är gemensam källa för status. Ändra status där; denna Markdown genereras.
- Efter varje relevant kodändring: kontrollera berörda uppgifter, kör relevanta tester och uppdatera status/underlag i samma leverans.
- Bocka bara av verifierat och granskat arbete. Att en fil finns eller att en commit är pushad räcker inte.
- Spara kod-/testunderlag i `evidence`. Sätt `in_progress` när arbetet pågår och `todo` om en tidigare verifiering inte längre gäller.
- Skilj på lokal kod, mergad kod, driftsättning, publicering och installerat app-test. De har egna kontrollpunkter.
- Håll H-0013 separat från H-0014/H-0015. Ändra inte frysta resultat eller forskningsprotokollet för att få fler bockar.
- Kör `python3 scripts/render-fas2-checklist.py` efter uppdatering och `python3 scripts/render-fas2-checklist.py --check` före commit.
- Chatvyn är en ögonblicksbild. En filändring i en annan session startar inte en verifiering här. Begär en ny kontroll eller uppdatera vyn i nästa leverans.

## 1. Förberedelser och låst forskningsplan

5/5 verifierade.

- [x] **F2-101** Registrera H-0013 före nya forskningskörningar
  - Underlag: [research/registry.md](../research/registry.md) — d88eaac: H-0013 registrerad före implementation.
- [x] **F2-102** Lås marknadslägen, parametrar, kostnader och beslutskriterier
  - Underlag: [research/fas2-protokoll.md](../research/fas2-protokoll.md) — d88eaac: 200 dagar, volatilitet, hysteres, fasta kandidater och fem beslutskriterier dokumenterade.
- [x] **F2-103** Dokumentera fryst dataset och skyddad slutprovsperiod
  - Underlag: [research/fas2-protokoll.md](../research/fas2-protokoll.md) — Fryst dataset 6a84c4f4…; 2020–2024 för utveckling, slutprovet 2025–2026 ska inte läsas.
- [x] **F2-104** Kartlägg återanvändbar motor, kö, worker och Research Lab
  - Underlag: [docs/fas2-inledande-granskning-20261102.md](fas2-inledande-granskning-20261102.md) — 3c2465b: befintlig integration granskad; H-0013 saknar ännu egen motor och köingång.
- [x] **F2-105** Avgränsa H-0013 från tvärsnitt, papper och livehandel
  - Underlag: [docs/fas2-inledande-granskning-20261102.md](fas2-inledande-granskning-20261102.md) — 3c2465b: H-0014/H-0015 är separata; REJECT gäller fortsatt och H-0013 kan inte gå direkt till papper.
  - Underlag: [docs/fardplan.md](fardplan.md) — Edwin bekräftade målbilden automatisk portföljförvaltning 2026-11-02. H-0013 förblir historisk forskning; framtida liveintegration kräver separat uttryckligt beslut.

## 2. Bygg och verifiera regimmodulen

5/5 verifierade.

- [x] **F2-201** Beräkna trend och volatilitet enligt det registrerade protokollet
  - Underlag: [docs/fas2-regim-granskning-69.md](fas2-regim-granskning-69.md) — 866d393 (kod ebc5d38): oberoende slutgranskning godkänd. 253 Python-tester, inklusive 66 regimtestfall, passerar. Tidigare felprov samt nästa-stapel-kontrakt på 1h/4h/1d verifierade.
  - Regimmodulen är mergad via PR #69 i 29e44ec, kod oförändrad mot granskad 866d393. Ej driftsatt eller publicerad.
- [x] **F2-202** Implementera tre dagars hysteres och omedelbara skyddslägen
  - Underlag: [docs/fas2-regim-granskning-69.md](fas2-regim-granskning-69.md) — 866d393 (kod ebc5d38): oberoende slutgranskning godkänd. 253 Python-tester, inklusive 66 regimtestfall, passerar. Tidigare felprov samt nästa-stapel-kontrakt på 1h/4h/1d verifierade.
  - Regimmodulen är mergad via PR #69 i 29e44ec, kod oförändrad mot granskad 866d393. Ej driftsatt eller publicerad.
- [x] **F2-203** Använd bara föregående stängda dags läge på varje 4H-stapel
  - Underlag: [docs/fas2-regim-granskning-69.md](fas2-regim-granskning-69.md) — 866d393 (kod ebc5d38): oberoende slutgranskning godkänd. 253 Python-tester, inklusive 66 regimtestfall, passerar. Tidigare felprov samt nästa-stapel-kontrakt på 1h/4h/1d verifierade.
  - Regimmodulen är mergad via PR #69 i 29e44ec, kod oförändrad mot granskad 866d393. Ej driftsatt eller publicerad.
- [x] **F2-204** Hantera uppvärmning, ofullständiga dagar, dataluckor och ogiltiga tidsstämplar
  - Underlag: [docs/fas2-regim-granskning-69.md](fas2-regim-granskning-69.md) — 866d393 (kod ebc5d38): oberoende slutgranskning godkänd. 253 Python-tester, inklusive 66 regimtestfall, passerar. Tidigare felprov samt nästa-stapel-kontrakt på 1h/4h/1d verifierade.
  - Regimmodulen är mergad via PR #69 i 29e44ec, kod oförändrad mot granskad 866d393. Ej driftsatt eller publicerad.
- [x] **F2-205** Granska regimkoden och verifiera tester för framtidsläckage och dagsgränser
  - Underlag: [docs/fas2-regim-granskning-69.md](fas2-regim-granskning-69.md) — 866d393 (kod ebc5d38): oberoende slutgranskning godkänd. 253 Python-tester, inklusive 66 regimtestfall, passerar. Tidigare felprov samt nästa-stapel-kontrakt på 1h/4h/1d verifierade.
  - Regimmodulen är mergad via PR #69 i 29e44ec, kod oförändrad mot granskad 866d393. Ej driftsatt eller publicerad.

## 3. Bygg den adaptiva strategiväljaren

5/5 verifierade.

- [x] **F2-301** Inför ett versionshanterat kontrakt för spelbok, läge och målposition
  - Underlag: [docs/fas2-valjare-granskning-70.md](fas2-valjare-granskning-70.md) — db54bbe (kod 9128008): oberoende omgranskning godkänd. 327 Python-testfall, inklusive 74 adaptiva, passerar. Tidigare felaktiga kontrakt avvisas; 81 giltiga round-trips och stabila id verifierade. Handelsfunktionerna är oförändrade.
  - Strategiväljaren är mergad via PR #70 i bcb14c9, kod oförändrad mot godkänd db54bbe. Ej driftsatt eller publicerad.
- [x] **F2-302** Koppla fasta EMA/ADX- och Bollinger/RSI-kandidater samt platt läge
  - Underlag: [docs/fas2-valjare-granskning-70.md](fas2-valjare-granskning-70.md) — db54bbe (kod 9128008): oberoende omgranskning godkänd. 327 Python-testfall, inklusive 74 adaptiva, passerar. Tidigare felaktiga kontrakt avvisas; 81 giltiga round-trips och stabila id verifierade. Handelsfunktionerna är oförändrade.
  - Strategiväljaren är mergad via PR #70 i bcb14c9, kod oförändrad mot godkänd db54bbe. Ej driftsatt eller publicerad.
- [x] **F2-303** Begränsa long till upp-lägen och short till ned-lägen
  - Underlag: [docs/fas2-valjare-granskning-70.md](fas2-valjare-granskning-70.md) — db54bbe (kod 9128008): oberoende omgranskning godkänd. 327 Python-testfall, inklusive 74 adaptiva, passerar. Tidigare felaktiga kontrakt avvisas; 81 giltiga round-trips och stabila id verifierade. Handelsfunktionerna är oförändrade.
  - Strategiväljaren är mergad via PR #70 i bcb14c9, kod oförändrad mot godkänd db54bbe. Ej driftsatt eller publicerad.
- [x] **F2-304** Stäng vid läges- och kandidatbyte utan att återuppta en gammal affär
  - Underlag: [docs/fas2-valjare-granskning-70.md](fas2-valjare-granskning-70.md) — db54bbe (kod 9128008): oberoende omgranskning godkänd. 327 Python-testfall, inklusive 74 adaptiva, passerar. Tidigare felaktiga kontrakt avvisas; 81 giltiga round-trips och stabila id verifierade. Handelsfunktionerna är oförändrade.
  - Strategiväljaren är mergad via PR #70 i bcb14c9, kod oförändrad mot godkänd db54bbe. Ej driftsatt eller publicerad.
- [x] **F2-305** Verifiera nästa öppning, ATR-stop och alla bytesfall med syntetiska tester
  - Underlag: [docs/fas2-valjare-granskning-70.md](fas2-valjare-granskning-70.md) — db54bbe (kod 9128008): oberoende omgranskning godkänd. 327 Python-testfall, inklusive 74 adaptiva, passerar. Tidigare felaktiga kontrakt avvisas; 81 giltiga round-trips och stabila id verifierade. Handelsfunktionerna är oförändrade.
  - Strategiväljaren är mergad via PR #70 i bcb14c9, kod oförändrad mot godkänd db54bbe. Ej driftsatt eller publicerad.

## 4. Träning och walk-forward

5/5 verifierade.

- [x] **F2-401** Välj kandidat per läge enbart på respektive träningsfönster
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — efb43fc: omstrukturerad walk-forward återverifierad med 442 tester och separat 35-affärers jämförelse mot c5068e1. Identiska avkastningar, affärer, kostnader, funding och spelboksval.
  - PR #71 mergad som 793e9f0. Refaktorn i PR #72 återverifierad; fas2.py är oförändrad i rättningen ab97a0a. PR #72 kodmässigt godkänd på a5e8fc3, merge kräver grön CI.
- [x] **F2-402** Kräv minst 20 inledda affärer och positivt t-värde, annars platt
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — efb43fc: omstrukturerad walk-forward återverifierad med 442 tester och separat 35-affärers jämförelse mot c5068e1. Identiska avkastningar, affärer, kostnader, funding och spelboksval.
  - PR #71 mergad som 793e9f0. Refaktorn i PR #72 återverifierad; fas2.py är oförändrad i rättningen ab97a0a. PR #72 kodmässigt godkänd på a5e8fc3, merge kräver grön CI.
- [x] **F2-403** Kör sex halvårsfönster med korrekt uppvärmning och platt start
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — efb43fc: omstrukturerad walk-forward återverifierad med 442 tester och separat 35-affärers jämförelse mot c5068e1. Identiska avkastningar, affärer, kostnader, funding och spelboksval.
  - PR #71 mergad som 793e9f0. Refaktorn i PR #72 återverifierad; fas2.py är oförändrad i rättningen ab97a0a. PR #72 kodmässigt godkänd på a5e8fc3, merge kräver grön CI.
- [x] **F2-404** Sätt ihop testkurvan och spara varje fönsters val, dagar och affärer
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — efb43fc: omstrukturerad walk-forward återverifierad med 442 tester och separat 35-affärers jämförelse mot c5068e1. Identiska avkastningar, affärer, kostnader, funding och spelboksval.
  - PR #71 mergad som 793e9f0. Refaktorn i PR #72 återverifierad; fas2.py är oförändrad i rättningen ab97a0a. PR #72 kodmässigt godkänd på a5e8fc3, merge kräver grön CI.
- [x] **F2-405** Versionsmärk slutlig spelbok och verifiera reproducerbarhet utan slutprov
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — efb43fc: omstrukturerad walk-forward återverifierad med 442 tester och separat 35-affärers jämförelse mot c5068e1. Identiska avkastningar, affärer, kostnader, funding och spelboksval.
  - PR #71 mergad som 793e9f0. Refaktorn i PR #72 återverifierad; fas2.py är oförändrad i rättningen ab97a0a. PR #72 kodmässigt godkänd på a5e8fc3, merge kräver grön CI.

## 5. Utvärdering och robusthet

5/5 verifierade.

- [x] **F2-501** Jämför med köp-och-behåll, varje kandidat ensam och en likaviktad blandning
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad som d25f444, utvärderingskod oförändrad mot godkänd a5e8fc3. Bara syntetisk verifiering; full riktig forskningskörning och driftsättning återstår.
- [x] **F2-502** Verifiera kostnadsstress, funding och riskmodell för H-0013
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad som d25f444, utvärderingskod oförändrad mot godkänd a5e8fc3. Bara syntetisk verifiering; full riktig forskningskörning och driftsättning återstår.
- [x] **F2-503** Kör förregistrerad permutation och slumpkontroll med fullständig försöksredovisning
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad som d25f444, utvärderingskod oförändrad mot godkänd a5e8fc3. Bara syntetisk verifiering; full riktig forskningskörning och driftsättning återstår.
- [x] **F2-504** Redovisa osäkerhet, 81 spelböcker, regimresultat och resultat utan bästa året
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad som d25f444, utvärderingskod oförändrad mot godkänd a5e8fc3. Bara syntetisk verifiering; full riktig forskningskörning och driftsättning återstår.
- [x] **F2-505** Bedöm alla fem förregistrerade kriterier och spara även negativa eller avbrutna försök
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad som d25f444, utvärderingskod oförändrad mot godkänd a5e8fc3. Bara syntetisk verifiering; full riktig forskningskörning och driftsättning återstår.

## 6. Supabase och DigitalOcean

1/5 verifierade.

- [ ] **F2-601** Skapa ett separat strikt kökontrakt för H-0013 med autentisering och RLS **Pågår.**
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — a852aa3 (kod cd9701d): Medlemsåtkomst och fast jobb verifierade; SQL:s resultatkontrakt behöver exakta booleska kriterier, konsekvent beslut och booleskt holdout_loaded.
  - Underlag: [scripts/test-h0013-queue.mjs](../scripts/test-h0013-queue.mjs) — 2160c6e (PR #73): research_h0013_result_ok kräver exakt de fem namngivna kriterierna som JSON-booleans, MORE_RESEARCH exakt när alla är sanna annars REJECT, och booleskt holdout_loaded = false; avvisning lämnar körning, resultat och slot oförändrade, och ett korrekt resultat kan sedan publiceras med samma lease. PGlite: test-h0013-queue.mjs passerar med 27 ogiltiga resultat; fem avsiktliga SQL-fel fångas; befintliga test-research-queue.mjs passerar. Python: hela sviten 521 passerar, varav 8 tester med riktiga spawn-processer och signaler. Migrationen är inte applicerad och inget är driftsatt.
  - Rättat i 2160c6e efter granskning av a852aa3. Väntar på Codex omgranskning; 0005 inte applicerad, inget driftsatt.
- [ ] **F2-602** Anslut H-0013 till samma enda worker med lease och skydd mot dubbla resultat **Pågår.**
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — a852aa3 (kod cd9701d): Samma worker och globala slot, två timmars H-0013-timeout, lease/fencing och skydd mot andra publiceringar verifierade lokalt. Verklig konkurrens/drift återstår.
  - Underlag: [engine/tests/test_research_worker_spawn.py](../engine/tests/test_research_worker_spawn.py) — 2160c6e (PR #73): workerns stopp ändrat; slotten släpps fortfarande först när processen är borta, inget publiceras efter avbrott, förlorad lease eller tidsgräns, och fencing är oförändrad. PGlite: test-h0013-queue.mjs passerar med 27 ogiltiga resultat; fem avsiktliga SQL-fel fångas; befintliga test-research-queue.mjs passerar. Python: hela sviten 521 passerar, varav 8 tester med riktiga spawn-processer och signaler. Migrationen är inte applicerad och inget är driftsatt.
  - Workerns stoppväg ändrad i 2160c6e; tidigare verifiering täcker inte längre exakt koden. Behöver omgranskas.
- [x] **F2-603** Begränsa dataläsningen till verifierade frysta arkiv innan några filer öppnas
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — a852aa3 (kod cd9701d): Exakta manifestnamn före arkivläsning, SHA256 och CHECKSUM samt stapel-/fundinghash verifierade på syntetiska 120 arkiv; 2019/2025 öppnas inte.
  - Lokal syntetisk verifiering och PGlite. PR #73 ej godkänd för merge; 0005 inte applicerad och ingen worker driftsatt.
- [ ] **F2-604** Testa avbrott, timeout, återförsök och återhämtning efter workeromstart **Pågår.**
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — a852aa3 (kod cd9701d): SQL-leaseåterförsök och FakeProcess-stopp passerar, men riktig spawn-process slutar med SIGTERM -15 och sparar 0 försöksfiler vid normalt worker.stop.
  - Underlag: [engine/tests/test_research_worker_spawn.py](../engine/tests/test_research_worker_spawn.py) — 2160c6e (PR #73): SIGTERM blir WorkerStop i beräkningsprocessen så att H-0013 sparar aborted-post med delresultat vid normalt stopp, användaravbrott, förlorad lease och tidsgräns, provat med riktiga spawn-processer; en process som inte svarar dödas efter högst 20 s och rapporteras som att delresultat kan saknas; Fas 1 och utforskning stoppas också kontrollerat innan slotten släpps. PGlite: test-h0013-queue.mjs passerar med 27 ogiltiga resultat; fem avsiktliga SQL-fel fångas; befintliga test-research-queue.mjs passerar. Python: hela sviten 521 passerar, varav 8 tester med riktiga spawn-processer och signaler. Migrationen är inte applicerad och inget är driftsatt.
  - Rättat i 2160c6e efter granskning av a852aa3. Väntar på Codex omgranskning; 0005 inte applicerad, inget driftsatt.
- [ ] **F2-605** Driftsätt verifierad kod med loggar, resursgränser och dokumenterad återgång

## 7. Visa Fas 2 i Research Lab

0/5 verifierade.

- [ ] **F2-701** Visa H-0013 separat från Fas 1 och tvärsnittshypoteserna
- [ ] **F2-702** Visa registrerade parametrar och förbered en fast forskningskörning
- [ ] **F2-703** Visa köstatus, förlopp, fel och möjlighet att avbryta
- [ ] **F2-704** Visa marknadslägen, kandidatval och jämförelsekurvor med spårbara källor
- [ ] **F2-705** Visa kriterier, osäkerhet, historik och REJECT/MORE_RESEARCH utan SIM som verkliga resultat

## 8. Sluttest och godkännande

0/5 verifierade.

- [ ] **F2-801** Kör relevanta Python-, frontend-, Rust- och databaskontroller
- [ ] **F2-802** Verifiera hela flödet från app till worker och sparat H-0013-resultat
- [ ] **F2-803** Kontrollera Mac, anslutningsfel och att befintliga Fas 1-funktioner fungerar
- [ ] **F2-804** Publicera granskad Stable och verifiera installerad kodversion samt uppdaterad checklista
- [ ] **F2-805** Dokumentera Fas 2-godkännande och fatta separat beslut om eventuellt slutprov; ingen automatisk paper- eller liveaktivering
