# Efterföljare till H-0013 – Arbetsplan

**2 av 40 uppgifter verifierade · 8 arbetsområden.**

Metodgranskning · Kontrollerad 2026-11-03 · Granskad kodversion `f43c1e7`.

Inledande metodgranskning klar som underlag: Git/status och sparad diagnos verifierade. Kontraktsutkast 0.1 och leverans A till Claude förberedda. Metodkontraktet är inte godkänt eller förregistrerat; inga nya signaler, historiska körningar eller driftkontroller genomförda. H-0013 REJECT och H-0016 oförändrade.

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
- [ ] **MOM-A04** Lås exakta jämförelser, försöksräkning, DSR och beslutskriterier **Pågår.**
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
  - Underlag: [docs/momentum-implementationskontrakt-utkast.md](momentum-implementationskontrakt-utkast.md) — Utkast 0.1 till Claude. Kvarstående A-blockerare framgår; inte godkänt som fryst protokoll.
- [ ] **MOM-A05** Förregistrera ett nytt ledigt id och låt Codex granska leverans A före implementation

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
