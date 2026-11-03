# Efterföljare till H-0013 – Arbetsplan

**11 av 40 uppgifter verifierade · 8 arbetsområden.**

Metodgranskning · Kontrollerad 2026-11-03 · Granskad kodversion `6f4350569f52527d9a156333240b735530e423a6`.

C1 godkänd på 6f43505: C1-01/C1-02 stängda, 82 ledgerprov och 671 motorprov godkända. 250 Decimal-fall, 500 identiska före/efter-fyllningar och egna numeriska gränsfall verifierade. C01 klar; C05 fortsatt in_progress eftersom likvidation/riskordning återstår. 11/40. Nästa avgränsade del C2 är fundingbokföring; ingen verklig historik, H-0017-körning, drift eller lönsamhet verifierad.

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

5/5 verifierade.

- [x] **MOM-A01** Kontrollera Git-läge, projektinstruktioner, tidigare beslut och separat hypotesidentitet
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
- [x] **MOM-A02** Reproducera den sparade H-0013-diagnosen utan nytt marknadstest
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
- [x] **MOM-A03** Färdigställ eventordning, konto, intrastapel-risk och marginalmodell
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
  - Underlag: [docs/momentum-implementationskontrakt-utkast.md](momentum-implementationskontrakt-utkast.md) — Utkast 0.1 till Claude. Kvarstående A-blockerare framgår; inte godkänt som fryst protokoll.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — A1-utkast till Codex: eventordning A/B med klassificering, ledger och storlek, avgränsad korsmarginal, intrastapel-bound även för legacy-stop, jämförelsematris, metodtabell D01–D16. Inte registrerat eller godkänt.
  - Underlag: [docs/momentum-a1-orakel.json](momentum-a1-orakel.json) — Handräknade fall O1–O12 (syntetiska tal), omräknade av scripts/momentum-a1-oracles.py --check. Verifierar formler, inte motorkod.
  - Underlag: [docs/momentum-a1-granskning-cb335ee.md](momentum-a1-granskning-cb335ee.md) — Codex granskning av exakt cb335ee: fyra syntetiskt reproducerade kontraktsfynd. A1 inte godkänd; A2 väntar på rättning och omgranskning.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — Revision 2 efter Codex granskning av cb335ee: reduce-only för riskavsikter (D17), exakt fundingtid utan tolerans (D18), separata faser E_trade/E_post (D19), T-regeln ersatt av scenariogrid A/B × mmr 5 %/0,5 % × legacy L1/L2 med krav i varje scenario (D20); preciserad marginal och DSR. Väntar på omgranskning.
  - Underlag: [docs/momentum-a1-orakel.json](momentum-a1-orakel.json) — Nya syntetiska fall O5b, O13–O16 (kapitalfaser, Sharpe-motexempel, reduce-only vid gap båda riktningar, normalavsikt som byter riktning, exakta fundingtider ±30 s, dagsgräns, första/sista). scripts/momentum-a1-oracles.py --check.
  - Underlag: [docs/momentum-a1-granskning-979fb30.md](momentum-a1-granskning-979fb30.md) — Oberoende omgranskning av 979fb30: ursprungliga fyra fynd rättade; R2-01 och R2-02 behöver precisering och syntetiska orakel före A2.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — Revision 3 efter Codex omgranskning av 979fb30: L1/L2 avgränsad till verkligt okänd ordning, kända öppningsutgångar och likvidation först (R2-01, D18); absorberande nollkonvention efter likvidation (R2-02, D21); textjusteringar i D11, §2 och §10.2. Väntar på omgranskning.
  - Underlag: [docs/momentum-a1-orakel.json](momentum-a1-orakel.json) — Nya syntetiska fall O17 (gapstop +30 s och exakt vid öppning, inträde vid öppning med stop inom stapel) och O18 (likvidation mitt i perioden, på terminaldag, likviderat delkonto i blandning, oförklarad nolla, main-beslut). scripts/momentum-a1-oracles.py --check.
  - Underlag: [docs/momentum-a1-granskning-a25db81.md](momentum-a1-granskning-a25db81.md) — Codex godkänner exakt A1-revision a25db81 för A2 efter oberoende kontroll av O17/O18 och full horisont. Ingen registrering eller motor i granskningsleveransen.
  - Metodkontrakt godkänt på a25db81. Implementation, data och resultat ska verifieras separat i senare leveranser.
- [x] **MOM-A04** Lås exakta jämförelser, försöksräkning, DSR och beslutskriterier
  - Underlag: [docs/momentum-metodgranskning-20261103.md](momentum-metodgranskning-20261103.md) — Inledande granskning på f43c1e7. Git och diagnos verifierade; M01–M08 kräver exakt metodkontrakt och omgranskning före frysning.
  - Underlag: [docs/momentum-implementationskontrakt-utkast.md](momentum-implementationskontrakt-utkast.md) — Utkast 0.1 till Claude. Kvarstående A-blockerare framgår; inte godkänt som fryst protokoll.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — §11–§14: jämförelsematris, sex kriterier i scenario A och B, N-regel (17 → t 2,754268270633685 om H-0017 är ledigt vid A2), DSR med N=17 och N_sok=1 213 som diagnostik.
  - Underlag: [docs/momentum-a1-granskning-cb335ee.md](momentum-a1-granskning-cb335ee.md) — Codex granskning av exakt cb335ee: fyra syntetiskt reproducerade kontraktsfynd. A1 inte godkänd; A2 väntar på rättning och omgranskning.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — Revision 2 efter Codex granskning av cb335ee: reduce-only för riskavsikter (D17), exakt fundingtid utan tolerans (D18), separata faser E_trade/E_post (D19), T-regeln ersatt av scenariogrid A/B × mmr 5 %/0,5 % × legacy L1/L2 med krav i varje scenario (D20); preciserad marginal och DSR. Väntar på omgranskning.
  - Underlag: [docs/momentum-a1-granskning-979fb30.md](momentum-a1-granskning-979fb30.md) — Oberoende omgranskning av 979fb30: ursprungliga fyra fynd rättade; R2-01 och R2-02 behöver precisering och syntetiska orakel före A2.
  - Underlag: [docs/momentum-protokoll-A1.md](momentum-protokoll-A1.md) — Revision 3 efter Codex omgranskning av 979fb30: L1/L2 avgränsad till verkligt okänd ordning, kända öppningsutgångar och likvidation först (R2-01, D18); absorberande nollkonvention efter likvidation (R2-02, D21); textjusteringar i D11, §2 och §10.2. Väntar på omgranskning.
  - Underlag: [docs/momentum-a1-granskning-a25db81.md](momentum-a1-granskning-a25db81.md) — Codex godkänner exakt A1-revision a25db81 för A2 efter oberoende kontroll av O17/O18 och full horisont. Ingen registrering eller motor i granskningsleveransen.
  - Metodkontrakt godkänt på a25db81. Implementation, data och resultat ska verifieras separat i senare leveranser.
- [x] **MOM-A05** Förregistrera ett nytt ledigt id och låt Codex granska leverans A före implementation
  - Underlag: [docs/momentum-a1-granskning-cb335ee.md](momentum-a1-granskning-cb335ee.md) — Codex granskning av exakt cb335ee: fyra syntetiskt reproducerade kontraktsfynd. A1 inte godkänd; A2 väntar på rättning och omgranskning.
  - Underlag: [docs/momentum-a1-granskning-979fb30.md](momentum-a1-granskning-979fb30.md) — Oberoende omgranskning av 979fb30: ursprungliga fyra fynd rättade; R2-01 och R2-02 behöver precisering och syntetiska orakel före A2.
  - Underlag: [docs/momentum-a1-granskning-a25db81.md](momentum-a1-granskning-a25db81.md) — Codex godkänner exakt A1-revision a25db81 för A2 efter oberoende kontroll av O17/O18 och full horisont. Ingen registrering eller motor i granskningsleveransen.
  - Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) — Slutligt protokoll H-0017, momentum-protokoll/1.0.0. §1–§18 byte-identiska med godkänt A1 a25db81 utom länkprefix ../docs/. Låsta värden: N=17, t-krav 2,754268270633685, N_sok=1 213.
  - Underlag: [research/registry.md](../research/registry.md) — En ny rad H-0017 sist; tidigare rader oförändrade (git diff: 1 tillagd, 0 borttagna). registry.count_attempts = 17.
  - Underlag: [docs/momentum-a2-granskning-db7f83b.md](momentum-a2-granskning-db7f83b.md) — Codex verifierar exakt registreringscommit db7f83b: H-0017, N=17, t=2,754268270633685, N_sok=1 213 och oförändrat metodkontrakt. Leverans A godkänd.
  - A2 registrerad och godkänd på db7f83b. B får börja enligt docs/claude-uppdrag-momentum-B.md; ingen historisk körning godkänd.

## B. Ren signalmodul och tidskontrakt

5/5 verifierade.

- [x] **MOM-B01** Implementera fasta momentumsignaler för 7, 14 och 28 kompletta UTC-dagar
  - Underlag: [engine/traderlab/momentum_signal.py](../engine/traderlab/momentum_signal.py) — mom-signal/1.0.0: ren funktion av stängda 4H-staplar, endast close läses; uttrycklig otillgänglighet med orsak.
  - Underlag: [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py) — 32 syntetiska tester godkända; 14 riktade felprov fångade (docs/momentum-signal-B.md). Horisonter i kalenderdagar, lika pris ger 0, handräknade s = 0, 1/3, 2/3, 1.
  - Underlag: [docs/momentum-signal-B.md](momentum-signal-B.md) — API, tidsregler, otillgänglighet, verifiering och begränsningar för leverans B.
  - Underlag: [docs/momentum-B-granskning-bfdb33b.md](momentum-B-granskning-bfdb33b.md) — Codex granskning av exakt bfdb33b: egna syntetiska avstämningar och tre fångade mutanter; ett P2-fynd för tom signalindata. 32 signaltester och 585 motorprov godkända.
  - Underlag: [docs/momentum-B-granskning-3294e8f.md](momentum-B-granskning-3294e8f.md) — Codex slutgodkänner exakt B-revision 3294e8f: P2 stängt, stabilt tomschema, 17 före/efter-fall identiska och oförändrad beräkningskod. 36 signaltester och 589 motorprov godkända.
  - Leverans B godkänd på 3294e8f, enbart syntetiskt. Konto och utförande återstår i C; ingen historisk körning godkänd.
- [x] **MOM-B02** Implementera 60 dagsavkastningar, ddof=1 och annualisering sqrt(365)
  - Underlag: [engine/traderlab/momentum_signal.py](../engine/traderlab/momentum_signal.py) — mom-signal/1.0.0: ren funktion av stängda 4H-staplar, endast close läses; uttrycklig otillgänglighet med orsak.
  - Underlag: [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py) — 32 syntetiska tester godkända; 14 riktade felprov fångade (docs/momentum-signal-B.md). 60 enkla avkastningar/61 stängningar, ddof=1, sqrt(365); avgränsat mot ddof=0, 59/61, log, prisstd, sqrt(252).
  - Underlag: [docs/momentum-signal-B.md](momentum-signal-B.md) — API, tidsregler, otillgänglighet, verifiering och begränsningar för leverans B.
  - Underlag: [docs/momentum-B-granskning-bfdb33b.md](momentum-B-granskning-bfdb33b.md) — Codex granskning av exakt bfdb33b: egna syntetiska avstämningar och tre fångade mutanter; ett P2-fynd för tom signalindata. 32 signaltester och 585 motorprov godkända.
  - Underlag: [docs/momentum-B-granskning-3294e8f.md](momentum-B-granskning-3294e8f.md) — Codex slutgodkänner exakt B-revision 3294e8f: P2 stängt, stabilt tomschema, 17 före/efter-fall identiska och oförändrad beräkningskod. 36 signaltester och 589 motorprov godkända.
  - Leverans B godkänd på 3294e8f, enbart syntetiskt. Konto och utförande återstår i C; ingen historisk körning godkänd.
- [x] **MOM-B03** Versionera lika vikt, 10 % målrisk och beteende vid otillräcklig eller ogiltig data
  - Underlag: [engine/traderlab/momentum_signal.py](../engine/traderlab/momentum_signal.py) — mom-signal/1.0.0: ren funktion av stängda 4H-staplar, endast close läses; uttrycklig otillgänglighet med orsak.
  - Underlag: [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py) — 32 syntetiska tester godkända; 14 riktade felprov fångade (docs/momentum-signal-B.md). VERSION mom-signal/1.0.0, lika vikt, 10 % målrisk, cap och w_target; warmup, incomplete_day, missing_day, invalid_vol.
  - Underlag: [docs/momentum-signal-B.md](momentum-signal-B.md) — API, tidsregler, otillgänglighet, verifiering och begränsningar för leverans B.
  - Underlag: [docs/momentum-B-granskning-bfdb33b.md](momentum-B-granskning-bfdb33b.md) — Codex granskning av exakt bfdb33b: egna syntetiska avstämningar och tre fångade mutanter; ett P2-fynd för tom signalindata. 32 signaltester och 585 motorprov godkända.
  - Underlag: [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py) — Rättning av P2 från granskningen av bfdb33b: signals() på tom ram och tomt prefix ger exakt COLUMNS med UTC-index och samma typer; latest_decision ger dokumenterat KeyError. 36 syntetiska tester; tre nya fäller bfdb33b.
  - Underlag: [docs/momentum-B-granskning-3294e8f.md](momentum-B-granskning-3294e8f.md) — Codex slutgodkänner exakt B-revision 3294e8f: P2 stängt, stabilt tomschema, 17 före/efter-fall identiska och oförändrad beräkningskod. 36 signaltester och 589 motorprov godkända.
  - Leverans B godkänd på 3294e8f, enbart syntetiskt. Konto och utförande återstår i C; ingen historisk körning godkänd.
- [x] **MOM-B04** Verifiera dagsstängning, första beslut och nästa öppning med syntetiska gränsfall
  - Underlag: [engine/traderlab/momentum_signal.py](../engine/traderlab/momentum_signal.py) — mom-signal/1.0.0: ren funktion av stängda 4H-staplar, endast close läses; uttrycklig otillgänglighet med orsak.
  - Underlag: [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py) — 32 syntetiska tester godkända; 14 riktade felprov fångade (docs/momentum-signal-B.md). decision_time = earliest_fill = D+1 00:00, bara 20-stapelns close, pågående sista dag, latest_decision vid D 20:00 ger D−1.
  - Underlag: [docs/momentum-signal-B.md](momentum-signal-B.md) — API, tidsregler, otillgänglighet, verifiering och begränsningar för leverans B.
  - Underlag: [docs/momentum-B-granskning-bfdb33b.md](momentum-B-granskning-bfdb33b.md) — Codex granskning av exakt bfdb33b: egna syntetiska avstämningar och tre fångade mutanter; ett P2-fynd för tom signalindata. 32 signaltester och 585 motorprov godkända.
  - Underlag: [docs/momentum-B-granskning-3294e8f.md](momentum-B-granskning-3294e8f.md) — Codex slutgodkänner exakt B-revision 3294e8f: P2 stängt, stabilt tomschema, 17 före/efter-fall identiska och oförändrad beräkningskod. 36 signaltester och 589 motorprov godkända.
  - Leverans B godkänd på 3294e8f, enbart syntetiskt. Konto och utförande återstår i C; ingen historisk körning godkänd.
- [x] **MOM-B05** Granska prefix-/framtidsprov och godkänn exakt signalrevision
  - Underlag: [engine/traderlab/momentum_signal.py](../engine/traderlab/momentum_signal.py) — mom-signal/1.0.0: ren funktion av stängda 4H-staplar, endast close läses; uttrycklig otillgänglighet med orsak.
  - Underlag: [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py) — 32 syntetiska tester godkända; 14 riktade felprov fångade (docs/momentum-signal-B.md). Prefixprov vid hel- och halvdag, ändrade framtida priser och open/high/low ändrar inga kända beslut.
  - Underlag: [docs/momentum-signal-B.md](momentum-signal-B.md) — API, tidsregler, otillgänglighet, verifiering och begränsningar för leverans B.
  - Underlag: [docs/momentum-B-granskning-bfdb33b.md](momentum-B-granskning-bfdb33b.md) — Codex granskning av exakt bfdb33b: egna syntetiska avstämningar och tre fångade mutanter; ett P2-fynd för tom signalindata. 32 signaltester och 585 motorprov godkända.
  - Underlag: [engine/tests/test_momentum_signal.py](../engine/tests/test_momentum_signal.py) — Rättning av P2 från granskningen av bfdb33b: signals() på tom ram och tomt prefix ger exakt COLUMNS med UTC-index och samma typer; latest_decision ger dokumenterat KeyError. 36 syntetiska tester; tre nya fäller bfdb33b.
  - Underlag: [docs/momentum-B-granskning-3294e8f.md](momentum-B-granskning-3294e8f.md) — Codex slutgodkänner exakt B-revision 3294e8f: P2 stängt, stabilt tomschema, 17 före/efter-fall identiska och oförändrad beräkningskod. 36 signaltester och 589 motorprov godkända.
  - Leverans B godkänd på 3294e8f, enbart syntetiskt. Konto och utförande återstår i C; ingen historisk körning godkänd.

## C. Utförande och nettobaserad risk

1/5 verifierade.

- [x] **MOM-C01** Implementera enhetsledger med partial fills, markvärdering och kostnad exakt en gång
  - Underlag: [engine/traderlab/momentum_ledger.py](../engine/traderlab/momentum_ledger.py) — mom-ledger/1.0.0: konto C/q, E = C + qM, exakt §6-lösare, kostnad en gång, normal- och reduce-only-fyllning, E_trade i fas after_trade.
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — 40 syntetiska tester mot orakel O1–O4, O11, O14, O15 och handräkning; 14 riktade felprov fångade.
  - Underlag: [docs/momentum-ledger-C1.md](momentum-ledger-C1.md) — API, bokföringsidentiteter, fel, verifiering och gränser för C1.
  - Underlag: [docs/momentum-C1-granskning-6eba8d6.md](momentum-C1-granskning-6eba8d6.md) — Codex granskar exakt 6eba8d6. Orakel/Decimal stämmer för normala fall, men C1-01 och C1-02 behöver numerisk/API-rättning och regressioner före godkännande. 40 ledgerprov, 629 motorprov godkända.
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — Rättning av C1-01/C1-02 från granskningen av 6eba8d6: kontofält och beräknade belopp ändlighetskontrollerade, vakt för kostnadsfri nämnare, enhetliga skalärtyper. 82 syntetiska tester; 39 nya fäller 6eba8d6.
  - Underlag: [docs/momentum-C1-granskning-6f43505.md](momentum-C1-granskning-6f43505.md) — Codex godkänner exakt C1-revision 6f43505 efter rättade numeriska vakter, 82 ledgerprov/671 motorprov och oberoende Decimal-/före-efterkontroller. Likvidation/riskordning ännu inte verifierade.
  - C1 godkänd på 6f43505. Framtida ändring av Account/fundingidentitet kräver återöppning och omgranskning.
- [ ] **MOM-C02** Implementera handelsband, avsikter och riskprioritet utan dold ombalansering
- [ ] **MOM-C03** Implementera funding, dagsreset och första/sista event enligt låst kontrakt
- [ ] **MOM-C04** Implementera 2 % dagsstopp, 15 % permanent stopp och konservativ 20 %-riskkontroll
- [ ] **MOM-C05** Verifiera gap, basis, likvidation och riskordning med handräknade prov och kodgranskning **Pågår.**
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — 40 syntetiska tester mot orakel O1–O4, O11, O14, O15 och handräkning; 14 riktade felprov fångade.
  - Underlag: [docs/momentum-C1-granskning-6eba8d6.md](momentum-C1-granskning-6eba8d6.md) — Codex granskar exakt 6eba8d6. Orakel/Decimal stämmer för normala fall, men C1-01 och C1-02 behöver numerisk/API-rättning och regressioner före godkännande. 40 ledgerprov, 629 motorprov godkända.
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — Rättning av C1-01/C1-02 från granskningen av 6eba8d6: kontofält och beräknade belopp ändlighetskontrollerade, vakt för kostnadsfri nämnare, enhetliga skalärtyper. 82 syntetiska tester; 39 nya fäller 6eba8d6.
  - Underlag: [docs/momentum-C1-granskning-6f43505.md](momentum-C1-granskning-6f43505.md) — Codex godkänner exakt C1-revision 6f43505 efter rättade numeriska vakter, 82 ledgerprov/671 motorprov och oberoende Decimal-/före-efterkontroller. Likvidation/riskordning ännu inte verifierade.
  - C1:s basis-/kostnads-/reduce-only-grund verifierad på 6f43505. Likvidation och full riskordning återstår.

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
