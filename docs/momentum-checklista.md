# Efterföljare till H-0013 – Arbetsplan

**2 av 40 uppgifter verifierade · 8 arbetsområden.**

Metodgranskning · Kontrollerad 2026-11-03 · Granskad kodversion `979fb30f483b856d9210be3591101cd0fb3b3b98`.

Codex omgranskning av A1 revision 2 på 979fb30: de fyra ursprungliga fynden rättade på metodnivå. Två kvarstående kontraktsluckor blockerar A2: L1/L2 efter känd gapstop och avkastning efter total likvidation. 29 tester och syntetiska kontroller passerar; ingen motor, historik, registrering eller drift verifierad. H-0013 REJECT och H-0016 oförändrade.

## Uppdateringsregler

- `docs/momentum-status.json` är gemensam källa för status. Ändra status där; denna Markdown genereras.
- Efter varje relevant kodändring: kontrollera berörda uppgifter, kör relevanta tester och uppdatera status/underlag i samma leverans.
- Bocka bara av verifierat och granskat arbete. Att en fil finns eller att en commit är pushad räcker inte.
- Spara kod-/testunderlag i `evidence`. Sätt `in_progress` när arbetet pågår och `todo` om en tidigare verifiering inte längre gäller.
- Skilj på lokal kod, mergad kod, driftsättning, publicering och installerat app-test. De har egna kontrollpunkter.
- Framåttest kräver READY_FOR_PAPER, fryst strategi och startbeslut. H-0013 förblir REJECT; inga frysta resultat ändras.
- Kör `python3 scripts/render-momentum-checklist.py` efter uppdatering och `python3 scripts/render-momentum-checklist.py --check` före commit.
- Chatvyn är en ögonblicksbild. En filändring i en annan session startar inte en verifiering här. Begär en ny kontroll eller uppdatera vyn i nästa leverans.

## A. Metodkontrakt och förregistrering

2/5 verifierade.

- [x] **MOM-A01** Kontrollera Git-läge, projektinstruktioner, tidigare beslut och separat hypotesidentitet
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
- [x] **MOM-A02** Reproducera den sparade H-0013-diagnosen utan nytt marknadstest
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
- [ ] **MOM-A03** Färdigställ eventordning, konto, intrastapel-risk och marginalmodell **Pågår.**
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
  - Underlag: [docs/momentum-implementationskontrakt-utkast.md](momentum-implementationskontrakt-utkast.md) — Utkast 0.1 till Claude. Kvarstående A-blockerare framgår; inte godkänt som fryst protokoll.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — A1-utkast till Codex: eventordning A/B med klassificering, ledger och storlek, avgränsad korsmarginal, intrastapel-bound även för legacy-stop, jämförelsematris, metodtabell D01–D16. Inte registrerat eller godkänt.
  - Underlag: [docs/momentum-a1-orakel.json](momentum-a1-orakel.json) — Handräknade fall O1–O12 (syntetiska tal), omräknade av scripts/momentum-a1-oracles.py --check. Verifierar formler, inte motorkod.
  - Underlag: [docs/momentum-a1-granskning-cb335ee.md](momentum-a1-granskning-cb335ee.md) — Codex granskning av exakt cb335ee: fyra syntetiskt reproducerade kontraktsfynd. A1 inte godkänd; A2 väntar på rättning och omgranskning.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — Revision 2 efter Codex granskning av cb335ee: reduce-only för riskavsikter (D17), exakt fundingtid utan tolerans (D18), separata faser E_trade/E_post (D19), T-regeln ersatt av scenariogrid A/B × mmr 5 %/0,5 % × legacy L1/L2 med krav i varje scenario (D20); preciserad marginal och DSR. Väntar på omgranskning.
  - Underlag: [docs/momentum-a1-orakel.json](momentum-a1-orakel.json) — Nya syntetiska fall O5b, O13–O16 (kapitalfaser, Sharpe-motexempel, reduce-only vid gap båda riktningar, normalavsikt som byter riktning, exakta fundingtider ±30 s, dagsgräns, första/sista). scripts/momentum-a1-oracles.py --check.
  - Underlag: [docs/momentum-a1-granskning-979fb30.md](momentum-a1-granskning-979fb30.md) — Oberoende omgranskning av 979fb30: ursprungliga fyra fynd rättade; R2-01 och R2-02 behöver precisering och syntetiska orakel före A2.
  - A1 revision 2 omgranskad men inte slutgodkänd. Rätta R2-01/R2-02 före A2; ingen registrering eller leverans B.
- [ ] **MOM-A04** Lås exakta jämförelser, försöksräkning, DSR och beslutskriterier **Pågår.**
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
  - Underlag: [docs/momentum-implementationskontrakt-utkast.md](momentum-implementationskontrakt-utkast.md) — Utkast 0.1 till Claude. Kvarstående A-blockerare framgår; inte godkänt som fryst protokoll.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — §11–§14: jämförelsematris, sex kriterier i scenario A och B, N-regel (17 → t 2,754268270633685 om H-0017 är ledigt vid A2), DSR med N=17 och N_sok=1 213 som diagnostik.
  - Underlag: [docs/momentum-a1-granskning-cb335ee.md](momentum-a1-granskning-cb335ee.md) — Codex granskning av exakt cb335ee: fyra syntetiskt reproducerade kontraktsfynd. A1 inte godkänd; A2 väntar på rättning och omgranskning.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — Revision 2 efter Codex granskning av cb335ee: reduce-only för riskavsikter (D17), exakt fundingtid utan tolerans (D18), separata faser E_trade/E_post (D19), T-regeln ersatt av scenariogrid A/B × mmr 5 %/0,5 % × legacy L1/L2 med krav i varje scenario (D20); preciserad marginal och DSR. Väntar på omgranskning.
  - Underlag: [docs/momentum-a1-granskning-979fb30.md](momentum-a1-granskning-979fb30.md) — Oberoende omgranskning av 979fb30: ursprungliga fyra fynd rättade; R2-01 och R2-02 behöver precisering och syntetiska orakel före A2.
  - A1 revision 2 omgranskad men inte slutgodkänd. Rätta R2-01/R2-02 före A2; ingen registrering eller leverans B.
- [ ] **MOM-A05** Förregistrera ett nytt ledigt id och låt Codex granska leverans A före implementation
  - Underlag: [docs/momentum-a1-granskning-cb335ee.md](momentum-a1-granskning-cb335ee.md) — Codex granskning av exakt cb335ee: fyra syntetiskt reproducerade kontraktsfynd. A1 inte godkänd; A2 väntar på rättning och omgranskning.
  - Underlag: [docs/momentum-a1-granskning-979fb30.md](momentum-a1-granskning-979fb30.md) — Oberoende omgranskning av 979fb30: ursprungliga fyra fynd rättade; R2-01 och R2-02 behöver precisering och syntetiska orakel före A2.
  - A1 revision 2 omgranskad men inte slutgodkänd. Rätta R2-01/R2-02 före A2; ingen registrering eller leverans B.

## B. Ren signalmodul och tidskontrakt

0/5 verifierade.

- [ ] **MOM-B01** Implementera fasta momentumsignaler för 7, 14 och 28 kompletta UTC-dagar
- [ ] **MOM-B02** Implementera 60 dagsavkastningar, ddof=1 och annualisering sqrt(365)
- [ ] **MOM-B03** Versionera lika vikt, 10 % målrisk och beteende vid otillräcklig eller ogiltig data
- [ ] **MOM-B04** Verifiera dagsstängning, första beslut och nästa öppning med syntetiska gränsfall
- [ ] **MOM-B05** Granska prefix-/framtidsprov och godkänn exakt signalrevision

## C. Utförande och nettobaserad risk

0/5 verifierade.

- [ ] **MOM-C01** Implementera enhetsledger med partial fills, markvärdering och kostnad exakt en gång
- [ ] **MOM-C02** Implementera handelsband, avsikter och riskprioritet utan dold ombalansering
- [ ] **MOM-C03** Implementera funding, dagsreset och första/sista event enligt låst kontrakt
- [ ] **MOM-C04** Implementera 2 % dagsstopp, 15 % permanent stopp och konservativ 20 %-riskkontroll
- [ ] **MOM-C05** Verifiera gap, basis, likvidation och riskordning med handräknade prov och kodgranskning

## D. Utvärderare och jämförelser

0/5 verifierade.

- [ ] **MOM-D01** Implementera de förregistrerade kontrollkontona på gemensam horisont och kapitalbas
- [ ] **MOM-D02** Verifiera 50/50- och 1/3-blandningar, bruttoexponering och oberoende risklås
- [ ] **MOM-D03** Implementera 2,5× kostnader, fundingstress, fördröjning och låst ordningskänslighet
- [ ] **MOM-D04** Verifiera statistik, osäkerhet, DSR och sex booleska kriterier från fullständiga serier
- [ ] **MOM-D05** Godkänn utvärderingsrevisionen efter oberoende avstämning utan verklig historikkörning

## E. Registrerad körväg och dataskydd

0/5 verifierade.

- [ ] **MOM-E01** Verifiera frysta utvecklingsarkiv och separat kompletterande mark-/marginalunderlag
- [ ] **MOM-E02** Avvisa skyddad data innan läsning och beräkning i samtliga ingångar
- [ ] **MOM-E03** Skapa separat strikt jobb- och resultatkontrakt med behörigheter och registerkoppling
- [ ] **MOM-E04** Verifiera lease, fencing, avbrott, återförsök och bevarade försöksresultat
- [ ] **MOM-E05** Granska eventuell ny migration och kompatibilitet med befintlig kö och app

## F. Infrastruktur och driftsättningsunderlag

0/5 verifierade.

- [ ] **MOM-F01** Kontrollera aktuellt serverpaket, exakt en worker, köläge och tjänsteanvändare läsande
- [ ] **MOM-F02** Bygg reproducerbart revisionsmärkt paket och verifiera varje fils kontrollsumma
- [ ] **MOM-F03** Förbered backup, verifierad återställning och säker migrations-/återgångsordning
- [ ] **MOM-F04** Genomför endast uttryckligen godkänd driftsättning och eventuell migration
- [ ] **MOM-F05** Omverifiera worker, revision, lås, behörigheter och insamling efter ändringen

## G. Godkänd historisk utvärdering

0/5 verifierade.

- [ ] **MOM-G01** Dokumentera Edwins uttryckliga beslut om den exakta registrerade körningen
- [ ] **MOM-G02** Verifiera kod/data/konfiguration och att inga otillåtna jobb eller arkiv används
- [ ] **MOM-G03** Genomför den låsta körningen och dess förregistrerade kontroller utan parameterändring
- [ ] **MOM-G04** Spara även fel och avbrott, med delresultat där kontraktet kräver det
- [ ] **MOM-G05** Verifiera ett spårbart resultat och tom aktiv slot utan sen eller dubbel publicering

## H. Oberoende resultatgranskning och beslut

0/5 verifierade.

- [ ] **MOM-H01** Räkna om netto, kapital, affärer, kostnader och riskmått från sparade fullständiga serier
- [ ] **MOM-H02** Kontrollera kriterier, jämförelser, försöksräkning och kvarstående modellbegränsningar
- [ ] **MOM-H03** Registrera granskat REJECT eller MORE_RESEARCH utan att ändra gamla registerrader
- [ ] **MOM-H04** Dokumentera separat slutprovsbeslut endast vid granskat MORE_RESEARCH
- [ ] **MOM-H05** Överlämna till fortsatt forskning eller senare READY_FOR_PAPER utan automatisk paper/live-start
