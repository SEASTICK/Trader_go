# Fas 2 – Utvecklingsplan

**16 av 40 uppgifter verifierade · 8 arbetsområden.**

H-0013 · Kontrollerad 2026-11-02 · Granskad kodversion `c5068e1`.

PR #69 och #70 mergade. PR #71 omgranskad och kodmässigt godkänd för merge på c5068e1: periodskydd och gemensam kapitalbas verifierade med 408 syntetiska Python-testfall samt oberoende reproduktionsprov. Ej mergad, driftsatt eller publicerad i denna granskning.

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

1/5 verifierade.

- [ ] **F2-401** Välj kandidat per läge enbart på respektive träningsfönster **Pågår.**
  - Underlag: [docs/fas2-walkforward-granskning-71.md](fas2-walkforward-granskning-71.md) — c5068e1 (kod 7ff0799): oberoende omgranskning godkänd. 408 Python-testfall inklusive 81 fas2 passerar; direkt slutprovsskydd före beräkning och kapital-/affärsavstämning verifierade. Urval och reproducerbarhet fortsatt verifierade.
  - Kod omstrukturerad i bbc7181 (run_window, stitch, tillförda dagslägen för permutationstestet). Beteendet är oförändrat enligt de befintliga fas2-testerna, men den granskade koden c5068e1 täcker inte längre exakt denna version. Behöver omgranskas.
- [x] **F2-402** Kräv minst 20 inledda affärer och positivt t-värde, annars platt
  - Underlag: [docs/fas2-walkforward-granskning-71.md](fas2-walkforward-granskning-71.md) — c5068e1 (kod 7ff0799): oberoende omgranskning godkänd. 408 Python-testfall inklusive 81 fas2 passerar; direkt slutprovsskydd före beräkning och kapital-/affärsavstämning verifierade. Urval och reproducerbarhet fortsatt verifierade.
  - Kodmässigt godkänd för merge i PR #71. Bara syntetisk data; ej mergad, driftsatt eller publicerad i granskningen.
- [ ] **F2-403** Kör sex halvårsfönster med korrekt uppvärmning och platt start **Pågår.**
  - Underlag: [docs/fas2-walkforward-granskning-71.md](fas2-walkforward-granskning-71.md) — c5068e1 (kod 7ff0799): oberoende omgranskning godkänd. 408 Python-testfall inklusive 81 fas2 passerar; direkt slutprovsskydd före beräkning och kapital-/affärsavstämning verifierade. Urval och reproducerbarhet fortsatt verifierade.
  - Kod omstrukturerad i bbc7181 (run_window, stitch, tillförda dagslägen för permutationstestet). Beteendet är oförändrat enligt de befintliga fas2-testerna, men den granskade koden c5068e1 täcker inte längre exakt denna version. Behöver omgranskas.
- [ ] **F2-404** Sätt ihop testkurvan och spara varje fönsters val, dagar och affärer **Pågår.**
  - Underlag: [docs/fas2-walkforward-granskning-71.md](fas2-walkforward-granskning-71.md) — c5068e1 (kod 7ff0799): oberoende omgranskning godkänd. 408 Python-testfall inklusive 81 fas2 passerar; direkt slutprovsskydd före beräkning och kapital-/affärsavstämning verifierade. Urval och reproducerbarhet fortsatt verifierade.
  - Kod omstrukturerad i bbc7181 (run_window, stitch, tillförda dagslägen för permutationstestet). Beteendet är oförändrat enligt de befintliga fas2-testerna, men den granskade koden c5068e1 täcker inte längre exakt denna version. Behöver omgranskas.
- [ ] **F2-405** Versionsmärk slutlig spelbok och verifiera reproducerbarhet utan slutprov **Pågår.**
  - Underlag: [docs/fas2-walkforward-granskning-71.md](fas2-walkforward-granskning-71.md) — c5068e1 (kod 7ff0799): oberoende omgranskning godkänd. 408 Python-testfall inklusive 81 fas2 passerar; direkt slutprovsskydd före beräkning och kapital-/affärsavstämning verifierade. Urval och reproducerbarhet fortsatt verifierade.
  - Kod omstrukturerad i bbc7181 (run_window, stitch, tillförda dagslägen för permutationstestet). Beteendet är oförändrat enligt de befintliga fas2-testerna, men den granskade koden c5068e1 täcker inte längre exakt denna version. Behöver omgranskas.

## 5. Utvärdering och robusthet

0/5 verifierade.

- [ ] **F2-501** Jämför med köp-och-behåll, varje kandidat ensam och en likaviktad blandning **Pågår.**
  - Underlag: [engine/tests/test_fas2_eval.py](../engine/tests/test_fas2_eval.py) — bbc7181 (gren fas2-utvardering): köp-och-behåll, varje kandidat ensam, likaviktad blandning och riskfilter körs genom samma sex fönster och konventioner som H-0013; alla har exakt samma staplar. Blandningen är medelvärdet av två kurvor utan ombalansering. Tolkningar U1–U20 i docs/fas2-utvardering-tolkningar.md (976c22a, före koden). 34 nya tester, hela Python-sviten 442 tester passerar lokalt; nio avsiktliga fel fångas. Endast syntetisk data.
  - Väntar på Codex granskning; ingen riktig data, inget slutprov, ej mergat, driftsatt eller publicerat.
- [ ] **F2-502** Verifiera kostnadsstress, funding och riskmodell för H-0013 **Pågår.**
  - Underlag: [engine/tests/test_fas2_eval.py](../engine/tests/test_fas2_eval.py) — bbc7181: kostnadsstress 2,5 gånger med fönstrens egna spelböcker; riskmodell 1× med finansieringsränta, ATR-stop och backtestmotorns likvidation; stop-utgångar, likvidationer, exponering och omsättning redovisas. Tolkningar U1–U20 i docs/fas2-utvardering-tolkningar.md (976c22a, före koden). 34 nya tester, hela Python-sviten 442 tester passerar lokalt; nio avsiktliga fel fångas. Endast syntetisk data.
  - Väntar på Codex granskning; ingen riktig data, inget slutprov, ej mergat, driftsatt eller publicerat.
- [ ] **F2-503** Kör förregistrerad permutation och slumpkontroll med fullständig försöksredovisning **Pågår.**
  - Underlag: [engine/tests/test_fas2_eval.py](../engine/tests/test_fas2_eval.py) — bbc7181: permutationstest per dygn av kända dagslägen (okänt kvar), frö 0, 200 som standard, hela walk-forward med urval körs om; varje permutations Sharpe och spelböcker sparas, p-värde k/n och (k+1)/(n+1). Slumpkontroll på 2022–2024. Tolkningar U1–U20 i docs/fas2-utvardering-tolkningar.md (976c22a, före koden). 34 nya tester, hela Python-sviten 442 tester passerar lokalt; nio avsiktliga fel fångas. Endast syntetisk data.
  - Väntar på Codex granskning; ingen riktig data, inget slutprov, ej mergat, driftsatt eller publicerat.
- [ ] **F2-504** Redovisa osäkerhet, 81 spelböcker, regimresultat och resultat utan bästa året **Pågår.**
  - Underlag: [engine/tests/test_fas2_eval.py](../engine/tests/test_fas2_eval.py) — bbc7181: block-bootstrap av Sharpe, alla 81 fasta spelböcker genom samma fönster, Deflated Sharpe med 81 försök (standard- och spelboksvarians), resultat per läge, per år och utan bästa året. Tolkningar U1–U20 i docs/fas2-utvardering-tolkningar.md (976c22a, före koden). 34 nya tester, hela Python-sviten 442 tester passerar lokalt; nio avsiktliga fel fångas. Endast syntetisk data.
  - Väntar på Codex granskning; ingen riktig data, inget slutprov, ej mergat, driftsatt eller publicerat.
- [ ] **F2-505** Bedöm alla fem förregistrerade kriterier och spara även negativa eller avbrutna försök **Pågår.**
  - Underlag: [engine/tests/test_fas2_eval.py](../engine/tests/test_fas2_eval.py) — bbc7181: alla fem kriterier med det registrerade t-kravet 2,67 (dagens krav redovisas), MORE_RESEARCH bara om alla gäller; varje körning sparas som ny fil (completed/aborted/invalid) utan överskrivning, avbruten körning sparas och felet visas, och körningen kräver registrerad H-0013. Tolkningar U1–U20 i docs/fas2-utvardering-tolkningar.md (976c22a, före koden). 34 nya tester, hela Python-sviten 442 tester passerar lokalt; nio avsiktliga fel fångas. Endast syntetisk data.
  - Väntar på Codex granskning; ingen riktig data, inget slutprov, ej mergat, driftsatt eller publicerat.

## 6. Supabase och DigitalOcean

0/5 verifierade.

- [ ] **F2-601** Skapa ett separat strikt kökontrakt för H-0013 med autentisering och RLS
- [ ] **F2-602** Anslut H-0013 till samma enda worker med lease och skydd mot dubbla resultat
- [ ] **F2-603** Begränsa dataläsningen till verifierade frysta arkiv innan några filer öppnas
- [ ] **F2-604** Testa avbrott, timeout, återförsök och återhämtning efter workeromstart
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
