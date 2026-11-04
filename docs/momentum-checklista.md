# Efterföljare till H-0013 – Arbetsplan

**14 av 40 uppgifter verifierade · 8 arbetsområden.**

Metodgranskning · Kontrollerad 2026-11-04 · Granskad kodversion `43b2a4bd26149bb04d77e1ef94113b2b684719a5`.

C5 GODKÄND på exakt 43b2a4b mot aa81472, endast syntetiskt. C5-02/C5-04 stängda; C5-01/C5-03 fortsatt stängda. Ingen publik restore; privat fixturväg godtas endast som testhjälp utan proveniensgaranti. 507 momentumtester, 1060 motorprov, A1, 19 äldre audits och ny revisionslåst audit passerar. C03/C05 done inom huvudmodellens C5-gränser; C04 in_progress för §10.2-bound och 20 %-riskkontroll. A/B/C01/C02 behåller komponentgodkännande. Nästa C-del kan tilldelas; ingen historikkörning/drift/paper/live. 14/40.

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

4/5 verifierade.

- [x] **MOM-C01** Implementera enhetsledger med partial fills, markvärdering och kostnad exakt en gång
  - Underlag: [engine/traderlab/momentum_ledger.py](../engine/traderlab/momentum_ledger.py) — mom-ledger/1.0.0: konto C/q, E = C + qM, exakt §6-lösare, kostnad en gång, normal- och reduce-only-fyllning, E_trade i fas after_trade.
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — 40 syntetiska tester mot orakel O1–O4, O11, O14, O15 och handräkning; 14 riktade felprov fångade.
  - Underlag: [docs/momentum-ledger-C1.md](momentum-ledger-C1.md) — API, bokföringsidentiteter, fel, verifiering och gränser för C1.
  - Underlag: [docs/momentum-C1-granskning-6eba8d6.md](momentum-C1-granskning-6eba8d6.md) — Codex granskar exakt 6eba8d6. Orakel/Decimal stämmer för normala fall, men C1-01 och C1-02 behöver numerisk/API-rättning och regressioner före godkännande. 40 ledgerprov, 629 motorprov godkända.
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — Rättning av C1-01/C1-02 från granskningen av 6eba8d6: kontofält och beräknade belopp ändlighetskontrollerade, vakt för kostnadsfri nämnare, enhetliga skalärtyper. 82 syntetiska tester; 39 nya fäller 6eba8d6.
  - Underlag: [docs/momentum-C1-granskning-6f43505.md](momentum-C1-granskning-6f43505.md) — Codex godkänner exakt C1-revision 6f43505 efter rättade numeriska vakter, 82 ledgerprov/671 motorprov och oberoende Decimal-/före-efterkontroller. Likvidation/riskordning ännu inte verifierade.
  - Underlag: [engine/traderlab/momentum_ledger.py](../engine/traderlab/momentum_ledger.py) — Kompletterad i C2: Account.funding_net och avstämning C = C0 + realized − costs − funding_net − q × avg_price; 82 C1-tester oförändrade och godkända.
  - Underlag: [docs/momentum-C2-granskning-1d9359f.md](momentum-C2-granskning-1d9359f.md) — Codex granskar exakt 1d9359f: C01:s funding_net/avstämning verifierad; C2-01/C2-02 i funding-API återstår. 129 riktade prov/718 motorprov och oberoende Decimal-kontroller passerar.
  - Underlag: [engine/traderlab/momentum_ledger.py](../engine/traderlab/momentum_ledger.py) — Kompletterad i C4: Account.liquidation_adjustment och avstämning C = C0 + realized − costs − funding_net + liquidation_adjustment − q × avg_price; tidigare 82 ledgertester oförändrade och godkända.
  - Underlag: [docs/momentum-C4-granskning-0773f76.md](momentum-C4-granskning-0773f76.md) — Codex omgranskar ledgerkompletteringen på 0773f76: signerad ändlig liquidation_adjustment, 300 egna avstämningsfall och två partial-/fundingförlopp, 200 identiska före/efterfyllningar; 82 ledgertester och 906 motorprov passerar. Marginalfynd C4-01/C4-02 ändrar inte ledgeridentiteten.
  - Underlag: [docs/momentum-C4-granskning-c312dfa.md](momentum-C4-granskning-c312dfa.md) — Ledgern oförändrad mot deb9c8f; återverifierad på c312dfa med 300 avstämningsfall, två partial-/fundingförlopp och 200 identiska normalfyllningar mot ledgern före C4. C4-03 ligger i marginalens satsvalidering och ogiltigförklarar inte ledgergodkännandet.
  - Underlag: [docs/momentum-C4-granskning-d7d2434.md](momentum-C4-granskning-d7d2434.md) — Återöppnad efter C4-05 på d7d2434: befintligt kontrakt om kontrollerade LedgerError bryts av stora heltal i _num. Normala avstämningar och 200 identiska normalfyllningar återverifierade; full integration kvar under C05.
  - Underlag: [engine/traderlab/momentum_ledger.py](../engine/traderlab/momentum_ledger.py) — Rättning av C4-05: _num avvisar reella tal som inte kan bli ändliga flyttal med LedgerError, och felmeddelanden formateras säkert (_show). Regressioner i engine/tests/test_momentum_margin.py; 82 ledgertester oförändrade och godkända.
  - Underlag: [docs/momentum-C4-granskning-4241d0e.md](momentum-C4-granskning-4241d0e.md) — C4 godkänd på exakt 4241d0e: C4-05 stängd med kontrollerade LedgerError; ledgerkomplettering, 300 avstämningar, två partial-/fundingförlopp och 200 identiska normalfyllningar återverifierade. Full integration kvar under C05.
  - C4 godkänd på exakt 4241d0e: C4-05 stängd med kontrollerade LedgerError; ledgerkomplettering, 300 avstämningar, två partial-/fundingförlopp och 200 identiska normalfyllningar återverifierade. Full integration kvar under C05.
- [x] **MOM-C02** Implementera handelsband, avsikter och riskprioritet utan dold ombalansering
  - Underlag: [engine/traderlab/momentum_risk.py](../engine/traderlab/momentum_risk.py) — mom-risk/1.0.0: rena tillståndsövergångar vid 4H-gränser, band 2 pp, dagsbeslut i §7:s ordning, sammanslagning terminal > permanent > dag > cap/platt > normal, dagsreset och lock_day.
  - Underlag: [engine/tests/test_momentum_risk.py](../engine/tests/test_momentum_risk.py) — 61 syntetiska tester mot O6, O14, O15 och handräkning med exakta float-gränser; 17 av 19 riktade felprov fångade, två bevisat ekvivalenta.
  - Underlag: [docs/momentum-risk-C3.md](momentum-risk-C3.md) — API, tillståndsövergångar, gräns mot eventloop, fel, verifiering och gränser för C3.
  - Underlag: [docs/momentum-C3-granskning-d77e353.md](momentum-C3-granskning-d77e353.md) — Codex granskar exakt d77e353: 267 riktade prov/820 motorprov och 400 egna beslutsfall passerar; C3-01 terminal efter likvidation och C3-02 signalkontrakt behöver rättas före godkännande.
  - Underlag: [engine/tests/test_momentum_risk.py](../engine/tests/test_momentum_risk.py) — Rättning av C3-01/C3-02 från granskningen av d77e353: ingen terminalavsikt för likviderat konto, strikt validering av signalens available, version och tider. 101 risktester; 38 nya fäller d77e353; 22 av 24 riktade felprov fångade, två bevisat ekvivalenta.
  - Underlag: [docs/momentum-C3-granskning-8c19618.md](momentum-C3-granskning-8c19618.md) — Codex godkänner exakt C3-revision 8c19618 efter rättad likviderad terminal och strikt signalkontrakt. 307 riktade prov/860 motorprov samt 400 egna oförändrade referensbeslut passerar. Full event-/marginal-/intrastapelintegration återstår.
  - Underlag: [engine/tests/test_momentum_margin.py](../engine/tests/test_momentum_margin.py) — C4-kompatibilitet: riskmodulen oförändrad; 101 risktester passerar med den kompletterade ledgern och nollkontot följer C3:s likvidationsväg inklusive terminal.
  - Underlag: [docs/momentum-C4-granskning-0773f76.md](momentum-C4-granskning-0773f76.md) — Oförändrad C3-källa på 0773f76, 101 risktester och sju egna absorberande gränser över midnatt till terminal passerar med kompletterad ledger. Komponentgodkännande bevaras.
  - Underlag: [docs/momentum-C4-granskning-c312dfa.md](momentum-C4-granskning-c312dfa.md) — Riskmodulen oförändrad mot deb9c8f; 101 risktester och sju egna absorberande gränser över midnatt till terminal återverifierade på c312dfa. Komponentgodkännande bevaras.
  - Underlag: [docs/momentum-C4-granskning-d7d2434.md](momentum-C4-granskning-d7d2434.md) — Komponentgodkännandet på 8c19618 behålls: oförändrad riskmodul, 101 risktester och sju egna absorberande steg återverifierade på d7d2434. C4-05 gäller ledgerns ogiltiga numeriska indata; full eventordning återstår.
  - Underlag: [docs/momentum-C4-granskning-4241d0e.md](momentum-C4-granskning-4241d0e.md) — Återöppnad på 4241d0e för C4-06 P2: riskens metadatafel för stora heltal läcker ValueError mot dokumenterat RiskError. Samma fel reproducerat på diffbasen; ingen C4-regression. Giltiga beslut och sju absorberande steg återverifierade.
  - Underlag: [docs/momentum-C4-06-rattning.md](momentum-C4-06-rattning.md) — Rättning av C4-06: 13 repr-formateringar i funding och risk använder ledgerns _show; 22 regressioner (17 fäller 4241d0e); 12 av 13 felprov fångade, ett ekvivalent. Väntar på Codex granskning.
  - Underlag: [docs/momentum-C4-06-granskning-9174b9c.md](momentum-C4-06-granskning-9174b9c.md) — C4-06 P2 stängt på exakt 9174b9c. C3:s rena risk-/avsiktsmodul åter godkänd: kontrollerade metadatafel, oförändrade indata och 400 giltiga beslut exakt identiska med 4241d0e. Full eventintegration ingår inte.
  - Underlag: [research/audits/momentum-c406-9174b9c/verification.json](../research/audits/momentum-c406-9174b9c/verification.json) — Revisionslåst audit: 44 kontrollerade avvisningar, 17 basläckor inklusive åtta ursprungliga vägar, 400 funding- och 400 riskjämförelser samt oförändrad validering/beräkning/signatur.
  - C4-06 P2 stängt på exakt 9174b9c. C3:s rena risk-/avsiktsmodul åter godkänd: kontrollerade metadatafel, oförändrade indata och 400 giltiga beslut exakt identiska med 4241d0e. Full eventintegration ingår inte.
- [x] **MOM-C03** Implementera funding, dagsreset och första/sista event enligt låst kontrakt
  - Underlag: [engine/traderlab/momentum_funding.py](../engine/traderlab/momentum_funding.py) — mom-funding/1.0.0: exakta fundingevent, betalning q × M_ref × ränta, mark_open-regel, stress bara på betalda belopp, dubbelbokningsskydd per konto och scenario.
  - Underlag: [engine/tests/test_momentum_funding.py](../engine/tests/test_momentum_funding.py) — 47 syntetiska tester mot O5, O5b, O16, O17 och Decimal; 15 riktade felprov fångade.
  - Underlag: [docs/momentum-funding-C2.md](momentum-funding-C2.md) — API, regler, ledgerkomplettering, fel, verifiering och gränser för C2.
  - Underlag: [docs/momentum-C2-granskning-1d9359f.md](momentum-C2-granskning-1d9359f.md) — Codex granskar exakt 1d9359f: C01:s funding_net/avstämning verifierad; C2-01/C2-02 i funding-API återstår. 129 riktade prov/718 motorprov och oberoende Decimal-kontroller passerar.
  - Underlag: [engine/tests/test_momentum_funding.py](../engine/tests/test_momentum_funding.py) — Rättning av C2-01/C2-02 från granskningen av 1d9359f: fas mot exakt eventtid, validerad processed-samling och strängkälla. 88 fundingtester; 27 nya fäller 1d9359f; 20 riktade felprov fångade.
  - Underlag: [docs/momentum-C2-granskning-fcf5cb4.md](momentum-C2-granskning-fcf5cb4.md) — Codex godkänner fundingdelen på exakt fcf5cb4; fas-/tidsvakt, processed-validering och källfeltyp verifierade. 170 riktade prov/759 motorprov samt oberoende Decimal-/regressionsaudit passerar.
  - Underlag: [engine/traderlab/momentum_risk.py](../engine/traderlab/momentum_risk.py) — mom-risk/1.0.0: rena tillståndsövergångar vid 4H-gränser, band 2 pp, dagsbeslut i §7:s ordning, sammanslagning terminal > permanent > dag > cap/platt > normal, dagsreset och lock_day.
  - Underlag: [engine/tests/test_momentum_risk.py](../engine/tests/test_momentum_risk.py) — 61 syntetiska tester mot O6, O14, O15 och handräkning med exakta float-gränser; 17 av 19 riktade felprov fångade, två bevisat ekvivalenta.
  - Underlag: [docs/momentum-C3-granskning-d77e353.md](momentum-C3-granskning-d77e353.md) — Codex granskar exakt d77e353: 267 riktade prov/820 motorprov och 400 egna beslutsfall passerar; C3-01 terminal efter likvidation och C3-02 signalkontrakt behöver rättas före godkännande.
  - Underlag: [docs/momentum-C3-granskning-8c19618.md](momentum-C3-granskning-8c19618.md) — Codex godkänner exakt C3-revision 8c19618 efter rättad likviderad terminal och strikt signalkontrakt. 307 riktade prov/860 motorprov samt 400 egna oförändrade referensbeslut passerar. Full event-/marginal-/intrastapelintegration återstår.
  - Underlag: [docs/momentum-C4-granskning-0773f76.md](momentum-C4-granskning-0773f76.md) — C4 på 0773f76: fyra egna A/B-öppningskompositioner och fyra debit/adverse-kompositioner med båda satserna passerar. Ingen full eventloop eller slutverifierad första/sista-eventintegration.
  - Underlag: [docs/momentum-C4-granskning-c312dfa.md](momentum-C4-granskning-c312dfa.md) — Fyra öppningskompositioner och fyra intrastapelkompositioner återverifierade på c312dfa; full eventordning och integration återstår.
  - Underlag: [docs/momentum-C4-granskning-d7d2434.md](momentum-C4-granskning-d7d2434.md) — Avgränsad C4-komposition återverifierad på d7d2434 med 600 Decimal-fall, fyra öppnings- och fyra adverse-kompositioner samt sju absorberande C3-steg. Full integration/bound inte godkänd.
  - Underlag: [docs/momentum-C4-granskning-4241d0e.md](momentum-C4-granskning-4241d0e.md) — C4:s avgränsade komposition godkänd på 4241d0e; full event-/funding-/marginalintegration återstår. C4-06 P2 bekräftar befintliga metadatafel i funding/risk; tidigare numerisk verifiering bevaras, inget helt komponentgodkännande för felkontraktet.
  - Underlag: [docs/momentum-C4-06-rattning.md](momentum-C4-06-rattning.md) — Rättning av C4-06: 13 repr-formateringar i funding och risk använder ledgerns _show; 22 regressioner (17 fäller 4241d0e); 12 av 13 felprov fångade, ett ekvivalent. Väntar på Codex granskning.
  - Underlag: [docs/momentum-C4-06-granskning-9174b9c.md](momentum-C4-06-granskning-9174b9c.md) — C4-06 stängt på 9174b9c; C2-funding och C3 åter godkända inom komponentgränserna med 400 fundingutfall och 400 riskbeslut identiska med 4241d0e. Full event-/funding-/marginalintegration samt första/sista event återstår.
  - Underlag: [engine/traderlab/momentum_event.py](../engine/traderlab/momentum_event.py) — mom-event/1.0.0: eventkomposition för ett huvudmodellskonto enligt §8.1–§8.4 med första/sista event, §10.1-closepunkter och §4-dagsögonblick; återanvänder godkända moduler.
  - Underlag: [engine/tests/test_momentum_event.py](../engine/tests/test_momentum_event.py) — 62 syntetiska tester mot O3, O5/O5b, O6, O10, O11/O18-snitt, O14–O16 och Decimal; 16 riktade felprov fångade.
  - Underlag: [docs/momentum-event-C5.md](momentum-event-C5.md) — API, fasordning, invarianter, identiteter, horisont, verifiering och avgränsningar för C5.
  - Underlag: [docs/momentum-C5-granskning-b131ff4.md](momentum-C5-granskning-b131ff4.md) — C5 EJ GODKÄND på b131ff4: C5-01 P1 i intrastapel-fundingledger, C5-02 P1 i start-/konto-/riskstate och C5-03 P2 i loggkomposition. Normal A/B, reset och sekventiell horisont verifierade; full integration inte godkänd.
  - Underlag: [research/audits/momentum-c5-b131ff4/review.py](../research/audits/momentum-c5-b131ff4/review.py) — Revisionslåst oberoende git-show-audit: 24 Decimal-inträde/exitfall, två O6, två terminalfall, sex tidsfall, fyra intrastapelfall, 6576 syntetiska staplar/1096 dagar, sju kontrollerade fel och tre reproducerade C5-fynd. Fem egna mutationer fångade. --check jämför verification.json.
  - Underlag: [docs/momentum-C5-01-edwins-beslut.md](momentum-C5-01-edwins-beslut.md) — Rättning av C5-01–C5-03 från granskningen av b131ff4, för Codex omgranskning, inte godkänd: Edwins beslut 2026-11-04 att ingen mellanhändelse i en stapel med intrastapelträff bokförs (olöst, exakt tid och belopp; underlag skilt från ledger); varje event med exakt en fundingkategori.
  - Underlag: [docs/momentum-C5-granskning-3f46aa5.md](momentum-C5-granskning-3f46aa5.md) — Oberoende granskning av exakt 3f46aa5 mot 8e447cb: 503 momentum-/1056 motorprov. Edwins fundingbeslut verifierat, RunLog-kedjan verifierad; restore kan fortfarande ta bort permanent stopp, godta fel kapitalbas/historik och läcka TypeError. C5 EJ GODKÄND.
  - Underlag: [research/audits/momentum-c5-3f46aa5/review.py](../research/audits/momentum-c5-3f46aa5/review.py) — Revisionslåst git-show-audit: 24 Decimal-inträde/exitfall, 32 separata funding-/marginalfall, O6/terminal/tidsfall, full syntetisk horisont 6576/6577/1096, gamla motexempel och verkligt sekventiellt permanent stopp. Fem mutationer fångade; --check jämför verification.json och reproducerar kvarstående fynd.
  - Underlag: [docs/momentum-C5-granskning-43b2a4b.md](momentum-C5-granskning-43b2a4b.md) — Codex godkänner exakt C5-revision 43b2a4b mot aa81472: C5-02/C5-04 stängda, C5-01/C5-03 fortsatt stängda. 507 momentumtester/1060 motorprov; privat testfixtur utanför publikt API. Skalade O14/O15 och marginalprov bevarar facit. §10.2-bound ingår inte.
  - Underlag: [research/audits/momentum-c5-43b2a4b/review.py](../research/audits/momentum-c5-43b2a4b/review.py) — Revisionslåst git-show-audit med verification.json och --check: 24 Decimal-inträde/exitfall, 32 funding/marginalfall, O6/terminal/tidsfall, 6576 staplar/6577 punkter/1096 dagar, publika motexempel avvisade, sex skalade handelsfall/fyra marginalfall och åtta fångade mutationer.
  - Underlag: [engine/traderlab/momentum_event.py](../engine/traderlab/momentum_event.py) — Kompatibilitetsnot C6: BarResult får fältet bar, bara ett tillägg. 105 eventtester och 34 felprov för eventmodulen passerar; omgodkännande av exakt revision behövs.
  - Done inom C5:s huvudmodell: funding, dagsreset, första/sista event och full syntetisk horisont verifierade på 43b2a4b. Ingen publik återställning. Legacy/jämförelsekonton och stress/fördröjning tillhör senare D; ingen historikkörning godkänd.
- [ ] **MOM-C04** Implementera 2 % dagsstopp, 15 % permanent stopp och konservativ 20 %-riskkontroll **Pågår.**
  - Underlag: [engine/traderlab/momentum_risk.py](../engine/traderlab/momentum_risk.py) — mom-risk/1.0.0: rena tillståndsövergångar vid 4H-gränser, band 2 pp, dagsbeslut i §7:s ordning, sammanslagning terminal > permanent > dag > cap/platt > normal, dagsreset och lock_day.
  - Underlag: [engine/tests/test_momentum_risk.py](../engine/tests/test_momentum_risk.py) — 61 syntetiska tester mot O6, O14, O15 och handräkning med exakta float-gränser; 17 av 19 riktade felprov fångade, två bevisat ekvivalenta.
  - Underlag: [docs/momentum-risk-C3.md](momentum-risk-C3.md) — API, tillståndsövergångar, gräns mot eventloop, fel, verifiering och gränser för C3.
  - Underlag: [docs/momentum-C3-granskning-d77e353.md](momentum-C3-granskning-d77e353.md) — Codex granskar exakt d77e353: 267 riktade prov/820 motorprov och 400 egna beslutsfall passerar; C3-01 terminal efter likvidation och C3-02 signalkontrakt behöver rättas före godkännande.
  - Underlag: [engine/tests/test_momentum_risk.py](../engine/tests/test_momentum_risk.py) — Rättning av C3-01/C3-02 från granskningen av d77e353: ingen terminalavsikt för likviderat konto, strikt validering av signalens available, version och tider. 101 risktester; 38 nya fäller d77e353; 22 av 24 riktade felprov fångade, två bevisat ekvivalenta.
  - Underlag: [docs/momentum-C3-granskning-8c19618.md](momentum-C3-granskning-8c19618.md) — Codex godkänner exakt C3-revision 8c19618 efter rättad likviderad terminal och strikt signalkontrakt. 307 riktade prov/860 motorprov samt 400 egna oförändrade referensbeslut passerar. Full event-/marginal-/intrastapelintegration återstår.
  - Underlag: [docs/momentum-C4-granskning-0773f76.md](momentum-C4-granskning-0773f76.md) — C4 på 0773f76: likviderat nollkonto följer C3 över midnatt till terminal utan avsikter. Oförändrad riskmodul; intrastapel-bound och full eventintegration återstår.
  - Underlag: [docs/momentum-C4-granskning-c312dfa.md](momentum-C4-granskning-c312dfa.md) — Absorberande nollkonto och C3-terminal återverifierade på c312dfa; full intrastapel-bound och eventintegration återstår.
  - Underlag: [docs/momentum-C4-granskning-d7d2434.md](momentum-C4-granskning-d7d2434.md) — Avgränsad C4-komposition återverifierad på d7d2434 med 600 Decimal-fall, fyra öppnings- och fyra adverse-kompositioner samt sju absorberande C3-steg. Full integration/bound inte godkänd.
  - Underlag: [docs/momentum-C4-granskning-4241d0e.md](momentum-C4-granskning-4241d0e.md) — Giltiga C3-beslut och absorberande nollkonto återverifierade på 4241d0e. C4-06 P2 i riskens felkontrakt återstår; konservativ intrastapel-bound och full eventintegration återstår.
  - Underlag: [docs/momentum-C4-06-granskning-9174b9c.md](momentum-C4-06-granskning-9174b9c.md) — C4-06 stängt på 9174b9c; C3-komponenten åter godkänd med 400 oförändrade referensbeslut och återkörda terminal-/signalkontroller. Konservativ intrastapel-bound och full eventintegration återstår.
  - Underlag: [engine/traderlab/momentum_event.py](../engine/traderlab/momentum_event.py) — mom-event/1.0.0: eventkomposition för ett huvudmodellskonto enligt §8.1–§8.4 med första/sista event, §10.1-closepunkter och §4-dagsögonblick; återanvänder godkända moduler.
  - Underlag: [engine/tests/test_momentum_event.py](../engine/tests/test_momentum_event.py) — 62 syntetiska tester mot O3, O5/O5b, O6, O10, O11/O18-snitt, O14–O16 och Decimal; 16 riktade felprov fångade.
  - Underlag: [docs/momentum-event-C5.md](momentum-event-C5.md) — API, fasordning, invarianter, identiteter, horisont, verifiering och avgränsningar för C5.
  - Underlag: [docs/momentum-C5-granskning-b131ff4.md](momentum-C5-granskning-b131ff4.md) — C5 EJ GODKÄND på b131ff4: främmande riskstate kan ta bort permanent stopp (C5-02 P1); intrastapelkomposition/logg har C5-01/C5-03. Oförändrad C3-komponent behåller godkännande. §10.2-bound återstår.
  - Underlag: [research/audits/momentum-c5-b131ff4/review.py](../research/audits/momentum-c5-b131ff4/review.py) — Revisionslåst oberoende git-show-audit: 24 Decimal-inträde/exitfall, två O6, två terminalfall, sex tidsfall, fyra intrastapelfall, 6576 syntetiska staplar/1096 dagar, sju kontrollerade fel och tre reproducerade C5-fynd. Fem egna mutationer fångade. --check jämför verification.json.
  - Underlag: [engine/traderlab/momentum_event.py](../engine/traderlab/momentum_event.py) — Rättning av C5-02 från granskningen av b131ff4, för Codex omgranskning, inte godkänd: EngineState skapas bara via start/restore/process_bar; insättning = riskmodulens startkapital, avstämd bokföring, inget risklås med position, inget oförklarat nollkonto, exakt startläge. §10.2-bounden ingår fortfarande inte.
  - Underlag: [docs/momentum-C5-granskning-3f46aa5.md](momentum-C5-granskning-3f46aa5.md) — Oberoende granskning av exakt 3f46aa5 mot 8e447cb: 503 momentum-/1056 motorprov. Edwins fundingbeslut verifierat, RunLog-kedjan verifierad; restore kan fortfarande ta bort permanent stopp, godta fel kapitalbas/historik och läcka TypeError. C5 EJ GODKÄND.
  - Underlag: [research/audits/momentum-c5-3f46aa5/review.py](../research/audits/momentum-c5-3f46aa5/review.py) — Revisionslåst git-show-audit: 24 Decimal-inträde/exitfall, 32 separata funding-/marginalfall, O6/terminal/tidsfall, full syntetisk horisont 6576/6577/1096, gamla motexempel och verkligt sekventiellt permanent stopp. Fem mutationer fångade; --check jämför verification.json och reproducerar kvarstående fynd.
  - Underlag: [docs/momentum-event-C5.md](momentum-event-C5.md) — Revision 3 för Codex omgranskning, inte godkänd: kvarstående C5-02 och C5-04 från granskningen av 3f46aa5 rättade. Ingen publik restore (privat fixturväg för syntetiska prov), låst startkapital 100 000, funding kräver historik, UTC-validering före intervalljämförelse. 105 eventtester/1 060 motortester; 34 av 34 riktade felprov fångade. §10.2-bounden ingår fortfarande inte.
  - Underlag: [docs/momentum-C5-granskning-43b2a4b.md](momentum-C5-granskning-43b2a4b.md) — Codex godkänner exakt C5-revision 43b2a4b mot aa81472: C5-02/C5-04 stängda, C5-01/C5-03 fortsatt stängda. 507 momentumtester/1060 motorprov; privat testfixtur utanför publikt API. Skalade O14/O15 och marginalprov bevarar facit. §10.2-bound ingår inte.
  - Underlag: [research/audits/momentum-c5-43b2a4b/review.py](../research/audits/momentum-c5-43b2a4b/review.py) — Revisionslåst git-show-audit med verification.json och --check: 24 Decimal-inträde/exitfall, 32 funding/marginalfall, O6/terminal/tidsfall, 6576 staplar/6577 punkter/1096 dagar, publika motexempel avvisade, sex skalade handelsfall/fyra marginalfall och åtta fångade mutationer.
  - Underlag: [engine/traderlab/momentum_bound.py](../engine/traderlab/momentum_bound.py) — C6 för Codex granskning, inte godkänd: mom-bound/1.0.0, separat §10.2-bound för huvudmodellen ovanpå eventkompositionen, med C6-01-tillägget (Edwins val H1, I1, G1, P1; Codex: klart för implementation). Ingen återkoppling till handel.
  - Underlag: [docs/momentum-bound-C6.md](momentum-bound-C6.md) — API, punktordning, fundingbaser och verifiering: 32 boundtester, 539 momentumtester/1 092 motortester; 17 av 18 riktade felprov fångade, ett bevisat ekvivalent.
  - C5 godkänd på 43b2a4b: integrerade closebaserade dags-/permanentstopp verifierade, inklusive bevarat permanent stopp genom publika motorsteg. §10.2-bound och konservativ 20 %-riskkontroll återstår; därför fortsatt in_progress.
- [x] **MOM-C05** Verifiera gap, basis, likvidation och riskordning med handräknade prov och kodgranskning
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — 40 syntetiska tester mot orakel O1–O4, O11, O14, O15 och handräkning; 14 riktade felprov fångade.
  - Underlag: [docs/momentum-C1-granskning-6eba8d6.md](momentum-C1-granskning-6eba8d6.md) — Codex granskar exakt 6eba8d6. Orakel/Decimal stämmer för normala fall, men C1-01 och C1-02 behöver numerisk/API-rättning och regressioner före godkännande. 40 ledgerprov, 629 motorprov godkända.
  - Underlag: [engine/tests/test_momentum_ledger.py](../engine/tests/test_momentum_ledger.py) — Rättning av C1-01/C1-02 från granskningen av 6eba8d6: kontofält och beräknade belopp ändlighetskontrollerade, vakt för kostnadsfri nämnare, enhetliga skalärtyper. 82 syntetiska tester; 39 nya fäller 6eba8d6.
  - Underlag: [docs/momentum-C1-granskning-6f43505.md](momentum-C1-granskning-6f43505.md) — Codex godkänner exakt C1-revision 6f43505 efter rättade numeriska vakter, 82 ledgerprov/671 motorprov och oberoende Decimal-/före-efterkontroller. Likvidation/riskordning ännu inte verifierade.
  - Underlag: [engine/traderlab/momentum_risk.py](../engine/traderlab/momentum_risk.py) — mom-risk/1.0.0: rena tillståndsövergångar vid 4H-gränser, band 2 pp, dagsbeslut i §7:s ordning, sammanslagning terminal > permanent > dag > cap/platt > normal, dagsreset och lock_day.
  - Underlag: [engine/tests/test_momentum_risk.py](../engine/tests/test_momentum_risk.py) — 61 syntetiska tester mot O6, O14, O15 och handräkning med exakta float-gränser; 17 av 19 riktade felprov fångade, två bevisat ekvivalenta.
  - Underlag: [docs/momentum-C3-granskning-d77e353.md](momentum-C3-granskning-d77e353.md) — Codex granskar exakt d77e353: 267 riktade prov/820 motorprov och 400 egna beslutsfall passerar; C3-01 terminal efter likvidation och C3-02 signalkontrakt behöver rättas före godkännande.
  - Underlag: [docs/momentum-C3-granskning-8c19618.md](momentum-C3-granskning-8c19618.md) — Codex godkänner exakt C3-revision 8c19618 efter rättad likviderad terminal och strikt signalkontrakt. 307 riktade prov/860 motorprov samt 400 egna oförändrade referensbeslut passerar. Full event-/marginal-/intrastapelintegration återstår.
  - Underlag: [engine/traderlab/momentum_margin.py](../engine/traderlab/momentum_margin.py) — mom-margin/1.0.0: direktvillkor E <= mmr|q|m, gap och ogynnsam extrem, atomisk absorberande nollställning via liquidation_adjustment.
  - Underlag: [engine/tests/test_momentum_margin.py](../engine/tests/test_momentum_margin.py) — 46 syntetiska tester mot O11, O18 och Decimal; 16 riktade felprov fångade.
  - Underlag: [docs/momentum-margin-C4.md](momentum-margin-C4.md) — API, bokföringsidentiteter, tillstånd, gräns mot eventloop, verifiering och påverkan för C4.
  - Underlag: [docs/momentum-C4-granskning-0773f76.md](momentum-C4-granskning-0773f76.md) — C4 ej godkänd på 0773f76: C4-01 P2 shorttröskelns overflow ger felaktigt nollpris; C4-02 P2 feltyper läcker TypeError/AttributeError. 353 momentum-/906 motorprov passerar; egen revisionslåst audit reproducerar fynden och verifierar 600 Decimal-jämförelser, 300 resetidentiteter och avgränsad komposition.
  - Underlag: [engine/tests/test_momentum_margin.py](../engine/tests/test_momentum_margin.py) — Rättning av C4-01/C4-02 från granskningen av 0773f76: nämnaren i trösklarna kontrolleras före division; sats och kontotyp valideras före konvertering och fältåtkomst. 60 marginaltester; 8 nya fäller 0773f76; 19 riktade felprov fångade.
  - Underlag: [docs/momentum-C4-granskning-c312dfa.md](momentum-C4-granskning-c312dfa.md) — C4 ej godkänd på c312dfa: C4-01 och tidigare C4-02-feltyper ger kontrollerade fel; nytt P2-fynd C4-03 ger OverflowError för 10**400 via konstruktion/replace/threshold, medan diffbasen gav MarginError. 367 momentumtester/920 motorprov och egen revisionslåst audit passerar inklusive reproducerat fynd. 600 Decimal-fall och 300 resetidentiteter återverifierade.
  - Underlag: [engine/tests/test_momentum_margin.py](../engine/tests/test_momentum_margin.py) — Rättning av C4-03 från omgranskningen av c312dfa: reellt tal som inte kan bli ändlig float (10**400) ger MarginError i marginalmodulens validering; ledgern oförändrad. 64 marginaltester; 3 nya fäller c312dfa; 20 riktade felprov fångade.
  - Underlag: [docs/momentum-C4-granskning-d7d2434.md](momentum-C4-granskning-d7d2434.md) — C4 ej godkänd på exakt d7d2434. Exakta C4-01–C4-03-reproduktioner stängda, men C4-04/C4-05 P2 kvarstår. Normala marginal-/resetfall och avgränsad komposition återverifierade syntetiskt; full event-/riskordning återstår. Ingen senare leverans beställd.
  - Underlag: [engine/tests/test_momentum_margin.py](../engine/tests/test_momentum_margin.py) — Rättning av C4-04/C4-05 från omgranskningen av d7d2434: säkra felmeddelanden för heltal som inte kan skrivas som text och LedgerError för reella tal som inte blir ändliga flyttal. 73 marginaltester; 7 fäller d7d2434; 22 riktade felprov fångade.
  - Underlag: [docs/momentum-C4-granskning-4241d0e.md](momentum-C4-granskning-4241d0e.md) — C4 godkänd inom marginal-/ledgerleveransen på exakt 4241d0e: C4-01–C4-05 stängda; 600 Decimal-fall och 300 avstämningar. C4-06 P2 i funding/risk ligger utanför rättningsytan och är dokumenterad. Full event-/riskordning återstår. Nästa del väntar på Edwins beslut.
  - Underlag: [docs/momentum-C4-06-granskning-9174b9c.md](momentum-C4-06-granskning-9174b9c.md) — Tidigare avgränsat C4-godkännande på 4241d0e bevaras för oförändrad marginal/ledger. C4-06 i funding/risk stängt på 9174b9c; giltiga C2/C3-utfall och felkontrakt återverifierade syntetiskt. Full event-/riskordning återstår. Nästa del väntar på Edwins beslut.
  - Underlag: [engine/traderlab/momentum_event.py](../engine/traderlab/momentum_event.py) — mom-event/1.0.0: eventkomposition för ett huvudmodellskonto enligt §8.1–§8.4 med första/sista event, §10.1-closepunkter och §4-dagsögonblick; återanvänder godkända moduler.
  - Underlag: [engine/tests/test_momentum_event.py](../engine/tests/test_momentum_event.py) — 62 syntetiska tester mot O3, O5/O5b, O6, O10, O11/O18-snitt, O14–O16 och Decimal; 16 riktade felprov fångade.
  - Underlag: [docs/momentum-event-C5.md](momentum-event-C5.md) — API, fasordning, invarianter, identiteter, horisont, verifiering och avgränsningar för C5.
  - Underlag: [docs/momentum-C5-granskning-b131ff4.md](momentum-C5-granskning-b131ff4.md) — C5 EJ GODKÄND på b131ff4: C5-01/C5-02 P1 och C5-03 P2 reproducerade oberoende. 24 Decimal-kompositioner, O6/terminal, gap/intrastapel och full syntetisk horisont verifierade inom dokumenterade gränser; integration/bound återstår.
  - Underlag: [research/audits/momentum-c5-b131ff4/review.py](../research/audits/momentum-c5-b131ff4/review.py) — Revisionslåst oberoende git-show-audit: 24 Decimal-inträde/exitfall, två O6, två terminalfall, sex tidsfall, fyra intrastapelfall, 6576 syntetiska staplar/1096 dagar, sju kontrollerade fel och tre reproducerade C5-fynd. Fem egna mutationer fångade. --check jämför verification.json.
  - Underlag: [engine/tests/test_momentum_event.py](../engine/tests/test_momentum_event.py) — Rättning av C5-01–C5-03 från granskningen av b131ff4, för Codex omgranskning, inte godkänd: 101 eventtester (Decimal-facit för olösta event i A/B × båda mmr × teckenordning × med/utan samtidig funding), RunLog bunden till förloppet; 31 av 31 riktade felprov fångade.
  - Underlag: [docs/momentum-C5-granskning-3f46aa5.md](momentum-C5-granskning-3f46aa5.md) — Oberoende granskning av exakt 3f46aa5 mot 8e447cb: 503 momentum-/1056 motorprov. Edwins fundingbeslut verifierat, RunLog-kedjan verifierad; restore kan fortfarande ta bort permanent stopp, godta fel kapitalbas/historik och läcka TypeError. C5 EJ GODKÄND.
  - Underlag: [research/audits/momentum-c5-3f46aa5/review.py](../research/audits/momentum-c5-3f46aa5/review.py) — Revisionslåst git-show-audit: 24 Decimal-inträde/exitfall, 32 separata funding-/marginalfall, O6/terminal/tidsfall, full syntetisk horisont 6576/6577/1096, gamla motexempel och verkligt sekventiellt permanent stopp. Fem mutationer fångade; --check jämför verification.json och reproducerar kvarstående fynd.
  - Underlag: [docs/momentum-C5-granskning-43b2a4b.md](momentum-C5-granskning-43b2a4b.md) — Codex godkänner exakt C5-revision 43b2a4b mot aa81472: C5-02/C5-04 stängda, C5-01/C5-03 fortsatt stängda. 507 momentumtester/1060 motorprov; privat testfixtur utanför publikt API. Skalade O14/O15 och marginalprov bevarar facit. §10.2-bound ingår inte.
  - Underlag: [research/audits/momentum-c5-43b2a4b/review.py](../research/audits/momentum-c5-43b2a4b/review.py) — Revisionslåst git-show-audit med verification.json och --check: 24 Decimal-inträde/exitfall, 32 funding/marginalfall, O6/terminal/tidsfall, 6576 staplar/6577 punkter/1096 dagar, publika motexempel avvisade, sex skalade handelsfall/fyra marginalfall och åtta fångade mutationer.
  - Underlag: [engine/tests/test_momentum_event.py](../engine/tests/test_momentum_event.py) — Kompatibilitetsnot C6: eventtesterna är oförändrade och passerar på revisionen med BarResult.bar.
  - Done inom C5:s huvudmodell: gap, basis, likvidation och riskordning granskade mot oberoende Decimal-/kalenderfacit på 43b2a4b. C5-01–C5-04 stängda. Inget godkännande av legacy/grid, §10.2-bound, ekonomiskt resultat eller drift. Nästa C-del kan tilldelas.

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
