# Fas 2 – Utvecklingsplan

**33 av 40 uppgifter verifierade · 8 arbetsområden.**

H-0013 · Kontrollerad 2026-11-03 · Granskad kodversion `db9a4ec`.

PR #78 granskad på db9a4ec (kod e42c534): 541 Python-/105 frontendtester och bygge passerar. Ny direkt kurvingång saknar slutprovsskydd, läsaren godkänner felaktiga tidsaxlar och urvalet kan ge 1501 punkter. Ej godkänd för merge. Tidigare nyckeltal återverifierade med identiskt före/efter-resultat; ingen riktig körning eller driftsättning.

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

4/5 verifierade.

- [ ] **F2-501** Jämför med köp-och-behåll, varje kandidat ensam och en likaviktad blandning **Pågår.**
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - Underlag: [docs/fas2-jamforelsekurvor-granskning-78.md](fas2-jamforelsekurvor-granskning-78.md) — db9a4ec: befintliga jämförelseutfall identiska mot de70580, men nya comparison_curves saknar utvecklingskontroll vid direkt anrop (P1).
  - Återöppnad för ny oskyddad jämförelseingång. Kriterier och tidigare jämförelseberäkningar oförändrade; bara syntetisk verifiering.
- [x] **F2-502** Verifiera kostnadsstress, funding och riskmodell för H-0013
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad, kod verifierad syntetiskt och nu del av driftsatt worker dee88eb. Ingen full H-0013-forskningskörning är startad.
- [x] **F2-503** Kör förregistrerad permutation och slumpkontroll med fullständig försöksredovisning
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad, kod verifierad syntetiskt och nu del av driftsatt worker dee88eb. Ingen full H-0013-forskningskörning är startad.
- [x] **F2-504** Redovisa osäkerhet, 81 spelböcker, regimresultat och resultat utan bästa året
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad, kod verifierad syntetiskt och nu del av driftsatt worker dee88eb. Ingen full H-0013-forskningskörning är startad.
- [x] **F2-505** Bedöm alla fem förregistrerade kriterier och spara även negativa eller avbrutna försök
  - Underlag: [docs/fas2-utvardering-granskning-72.md](fas2-utvardering-granskning-72.md) — a5e8fc3 (kod ab97a0a): oberoende omgranskning godkänd. 478 Python-testfall inklusive 70 utvärderingstestfall passerar. Direkt slutprovsskydd, kapitalviktade riskmått, omsättning och bevarade delresultat vid avbrott verifierade med egna reproduktionsprov.
  - PR #72 mergad, kod verifierad syntetiskt och nu del av driftsatt worker dee88eb. Ingen full H-0013-forskningskörning är startad.

## 6. Supabase och DigitalOcean

5/5 verifierade.

- [x] **F2-601** Skapa ett separat strikt kökontrakt för H-0013 med autentisering och RLS
  - Underlag: [docs/fas2-drift-granskning-74.md](fas2-drift-granskning-74.md) — e0c41ca (kod d01dccd): kökontrakt återverifierat efter ny kontroll under advisory lock. Båda ordningarna för köning/återgång passerar i lokal PostgreSQL; kö- och rättighetstester passerar.
  - 0005 är aktiv och rena kontraktsprov samt anon-nekanden verifierade på servern. Authenticated-grants och riktigt medlemstest är fortfarande skilda kontroller; se driftutfallsgranskning.
- [x] **F2-602** Anslut H-0013 till samma enda worker med lease och skydd mot dubbla resultat
  - Underlag: [docs/fas2-drift-granskning-74.md](fas2-drift-granskning-74.md) — eb15650: utbrutet workerlås och revisionslogg återverifierade med riktiga processer. 532 Python-tester och lokal PostgreSQL-samtidighet passerar; en reservation/publicering och fencing verifierade.
  - Worker dee88eb verifierad på dropleten 2026-11-03: exakt en worker, PID 24061, lås och revision stämmer, 0 omstarter.
- [x] **F2-603** Begränsa dataläsningen till verifierade frysta arkiv innan några filer öppnas
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — a852aa3 (kod cd9701d): Exakta manifestnamn före arkivläsning, SHA256 och CHECKSUM samt stapel-/fundinghash verifierade på syntetiska 120 arkiv; 2019/2025 öppnas inte.
  - Arkivkontrollen är oförändrad i 2160c6e och fortsatt verifierad på syntetiska arkiv. PR #73 kodmässigt godkänd på 445178d; ingen riktig datakörning eller driftsättning.
- [x] **F2-604** Testa avbrott, timeout, återförsök och återhämtning efter workeromstart
  - Underlag: [docs/fas2-ko-granskning-73.md](fas2-ko-granskning-73.md) — 445178d (kod 2160c6e): oberoende omgranskning godkänd. 521 Python-tester, 8 riktiga signal-/processtester och båda PGlite-kösviterna passerar. Tidigare SIGTERM-felprov sparar nu försöket; felaktiga SQL-kriterier och beslut avvisas utan ändrad lease.
  - PR #73 mergad som d6f2eae, med godkänd kod 445178d. Lokalt verifierad. Faktiska Supabase-/driftkontroller återstår i F2-605.
- [x] **F2-605** Driftsätt verifierad kod med loggar, resursgränser och dokumenterad återgång
  - Underlag: [docs/fas2-drift-granskning-74.md](fas2-drift-granskning-74.md) — e0c41ca: godkänt underlag efter omgranskning, 538 Python-tester och lokala SQL-/samtidighetstester passerar. Paket SHA256 11dd7a0faabd24f8939ec2c64ea3d59b0d2a33787f0c710e3833d702e7b7378b; 186 filer verifierar.
  - Underlag: [docs/fas2-drift-granskning-74.md](fas2-drift-granskning-74.md) — Slutpaket dee88eb: Engine check grön, 651 788 byte och SHA256 62c7d8e482ef6a1755d670f74a7631c221469e61259a09b285f32627936c8575. Eget bygge byteidentiskt; 186 filer verifierar.
  - Underlag: [docs/fas2-driftutfall-granskning-76.md](fas2-driftutfall-granskning-76.md) — 2026-11-03: oberoende drift-/kontraktskontroller och privat export verifierade. Edwin redovisar DO veckobackup från 1 dag sedan och Supabase-backup 2026-11-03 06:47:12 UTC; skärmbild visar auth_enqueue=true, auth_result_ok=false, auth_finish=false.
  - Driftsättning godkänd inom dokumenterad avgränsning. Riktigt medlemstest, appens E2E och JWT-samtidighet är inte verifierade av grantkontrollen. Inget H-0013-jobb startat.

## 7. Visa Fas 2 i Research Lab

4/5 verifierade.

- [x] **F2-701** Visa H-0013 separat från Fas 1 och tvärsnittshypoteserna
  - Underlag: [docs/fas2-research-lab-granskning-77.md](fas2-research-lab-granskning-77.md) — f36a3ee (kod 62cc4bb): Separat H-0013-flik och avgränsning mot Fas 1, tvärsnitt och utforskning verifierade.
  - PR #77 mergad i de70580 med app-/motorkod oförändrad mot godkänd 677752f. PR #78:s nya kurvor granskas separat. Ingen riktig köning eller installerad app/publicering verifierad.
- [x] **F2-702** Visa registrerade parametrar och förbered en fast forskningskörning
  - Underlag: [docs/fas2-research-lab-granskning-77.md](fas2-research-lab-granskning-77.md) — f36a3ee (kod 62cc4bb): Låsta parametrar matchar protokoll/migration/motor; fast köanrop och tvåstegsförberedelse med aktiv/resultatblockerare verifierade lokalt.
  - PR #77 mergad i de70580 med app-/motorkod oförändrad mot godkänd 677752f. PR #78:s nya kurvor granskas separat. Ingen riktig köning eller installerad app/publicering verifierad.
- [x] **F2-703** Visa köstatus, förlopp, fel och möjlighet att avbryta
  - Underlag: [docs/fas2-research-lab-granskning-77.md](fas2-research-lab-granskning-77.md) — 677752f (kod a883094): Eget payloadfel, automatisk återhämtning och manuell knapp verifierade med DOM-tester. Eget Chrome-prov ger andra payload-anropet och resultat, utan köning.
  - PR #77 mergad i de70580 med app-/motorkod oförändrad mot godkänd 677752f. PR #78:s nya kurvor granskas separat. Ingen riktig köning eller installerad app/publicering verifierad.
- [ ] **F2-704** Visa marknadslägen, kandidatval och jämförelsekurvor med spårbara källor **Pågår.**
  - Underlag: [docs/fas2-research-lab-granskning-77.md](fas2-research-lab-granskning-77.md) — 677752f (kod a883094): Platt kapital och noll-drawdown nu visuellt verifierade i ljust/mörkt tema med ändlig SVG. Jämförelsekurvor saknas fortfarande i payload och uppgiften förblir öppen.
  - Underlag: [docs/fas2-jamforelsekurvor-granskning-78.md](fas2-jamforelsekurvor-granskning-78.md) — db9a4ec: kurvor implementerade och visuellt provade i ljus/mörk Chrome-vy. Ogiltiga tidsaxlar accepteras (P2); 1500-gränsen kan överskridas (P3). 105 frontendtester och bygge passerar.
  - Öppen i väntan på rättade kurvkontroller. Driftsatt dee88eb saknar kurvorna; inget riktigt jobb eller installerat app-test.
- [x] **F2-705** Visa kriterier, osäkerhet, historik och REJECT/MORE_RESEARCH utan SIM som verkliga resultat
  - Underlag: [docs/fas2-research-lab-granskning-77.md](fas2-research-lab-granskning-77.md) — 677752f (kod a883094): Saknad/feltypad logg, ogiltiga rader, avvikande antal och faktiskt tom logg skiljs åt och redovisas. Tidigare egna felprov och DOM-regressioner passerar.
  - PR #77 mergad i de70580 med app-/motorkod oförändrad mot godkänd 677752f. PR #78:s nya kurvor granskas separat. Ingen riktig köning eller installerad app/publicering verifierad.

## 8. Sluttest och godkännande

0/5 verifierade.

- [ ] **F2-801** Kör relevanta Python-, frontend-, Rust- och databaskontroller
- [ ] **F2-802** Verifiera hela flödet från app till worker och sparat H-0013-resultat
- [ ] **F2-803** Kontrollera Mac, anslutningsfel och att befintliga Fas 1-funktioner fungerar
- [ ] **F2-804** Publicera granskad Stable och verifiera installerad kodversion samt uppdaterad checklista
- [ ] **F2-805** Dokumentera Fas 2-godkännande och fatta separat beslut om eventuellt slutprov; ingen automatisk paper- eller liveaktivering
