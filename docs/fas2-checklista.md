# Fas 2 – Utvecklingsplan

**29 av 40 uppgifter verifierade · 8 arbetsområden.**

H-0013 · Kontrollerad 2026-11-02 · Granskad kodversion `445178d`.

PR #73 omgranskad på 445178d (kod 2160c6e): båda fynd rättade. 521 Python-tester inklusive 8 riktiga processtester och båda PGlite-sviterna passerar; egna signal- och SQL-felprov verifierade. Kodmässigt godkänd för merge när CI är grönt. Ingen migration, driftsättning eller riktig körning.

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

4/5 verifierade.

- [x] **F2-601** Skapa ett separat strikt kökontrakt för H-0013 med autentisering och RLS
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — 445178d (kod 2160c6e): oberoende omgranskning godkänd. 521 Python-tester, 8 riktiga signal-/processtester och båda PGlite-kösviterna passerar. Tidigare SIGTERM-felprov sparar nu försöket; felaktiga SQL-kriterier och beslut avvisas utan ändrad lease.
  - Kodmässigt verifierad lokalt. PR #73 godkänd för merge när CI är grönt; faktisk Supabase-samtidighet och driftverifiering återstår i F2-605.
- [x] **F2-602** Anslut H-0013 till samma enda worker med lease och skydd mot dubbla resultat
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — 445178d (kod 2160c6e): oberoende omgranskning godkänd. 521 Python-tester, 8 riktiga signal-/processtester och båda PGlite-kösviterna passerar. Tidigare SIGTERM-felprov sparar nu försöket; felaktiga SQL-kriterier och beslut avvisas utan ändrad lease.
  - Kodmässigt verifierad lokalt. PR #73 godkänd för merge när CI är grönt; faktisk Supabase-samtidighet och driftverifiering återstår i F2-605.
- [x] **F2-603** Begränsa dataläsningen till verifierade frysta arkiv innan några filer öppnas
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — a852aa3 (kod cd9701d): Exakta manifestnamn före arkivläsning, SHA256 och CHECKSUM samt stapel-/fundinghash verifierade på syntetiska 120 arkiv; 2019/2025 öppnas inte.
  - Arkivkontrollen är oförändrad i 2160c6e och fortsatt verifierad på syntetiska arkiv. PR #73 kodmässigt godkänd på 445178d; ingen riktig datakörning eller driftsättning.
- [x] **F2-604** Testa avbrott, timeout, återförsök och återhämtning efter workeromstart
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — 445178d (kod 2160c6e): oberoende omgranskning godkänd. 521 Python-tester, 8 riktiga signal-/processtester och båda PGlite-kösviterna passerar. Tidigare SIGTERM-felprov sparar nu försöket; felaktiga SQL-kriterier och beslut avvisas utan ändrad lease.
  - Kodmässigt verifierad lokalt. PR #73 godkänd för merge när CI är grönt; faktisk Supabase-samtidighet och driftverifiering återstår i F2-605.
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
