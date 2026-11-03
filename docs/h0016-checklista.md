# H-0016 – Arbetsplan

**5 av 40 uppgifter verifierade · 8 arbetsområden.**

H-0016 · Kontrollerad 2026-11-03 · Granskad kodversion `e65012e`.

Protokoll och registrering committade i e65012e före implementation. Förberedelserna nedan är verifierade som dokumenterade; signaler, risklager, körning och resultat är ännu inte verifierade. H-0013 förblir REJECT. Slutprovet är oläst och ingen paper/live-aktivering ingår.

## Uppdateringsregler

- `docs/h0016-status.json` är gemensam källa för status. Ändra status där; denna Markdown genereras.
- Efter varje relevant kodändring: kontrollera berörda uppgifter, kör relevanta tester och uppdatera status/underlag i samma leverans.
- Bocka bara av verifierat och granskat arbete. Att en fil finns eller att en commit är pushad räcker inte.
- Spara kod-/testunderlag i `evidence`. Sätt `in_progress` när arbetet pågår och `todo` om en tidigare verifiering inte längre gäller.
- Skilj på lokal kod, mergad kod, driftsättning, publicering och installerat app-test. De har egna kontrollpunkter.
- Framåttest kräver READY_FOR_PAPER, fryst strategi och startbeslut. H-0013 förblir REJECT; inga frysta resultat ändras.
- Kör `python3 scripts/render-h0016-checklist.py` efter uppdatering och `python3 scripts/render-h0016-checklist.py --check` före commit.
- Chatvyn är en ögonblicksbild. En filändring i en annan session startar inte en verifiering här. Begär en ny kontroll eller uppdatera vyn i nästa leverans.

## 1. Förregistrering och mål

5/5 verifierade.

- [x] **H16-101** Registrera H-0016 och committa protokollet före implementation och körning
  - Underlag: [research/h0016-protokoll.md](../research/h0016-protokoll.md) — Förregistrerat i e65012e; endast dokumenterat kontrakt godkänt, inte implementerat beteende.
  - Underlag: [docs/strategiforskning-20261103.md](strategiforskning-20261103.md) — Registrering verifierad av motorn: N=16, inget resultatbeslut; äldre REJECT bevarade.
- [x] **H16-102** Lås BTCUSDT 4H, utvecklingsperiod 2020–2024 och skyddat slutprov från 2025
  - Underlag: [research/h0016-protokoll.md](../research/h0016-protokoll.md) — Förregistrerat i e65012e; endast dokumenterat kontrakt godkänt, inte implementerat beteende.
  - Underlag: [docs/strategiforskning-20261103.md](strategiforskning-20261103.md) — Registrering verifierad av motorn: N=16, inget resultatbeslut; äldre REJECT bevarade.
- [x] **H16-103** Lås squeeze-standardparametrar, long/platt och förbud mot optimering
  - Underlag: [research/h0016-protokoll.md](../research/h0016-protokoll.md) — Förregistrerat i e65012e; endast dokumenterat kontrakt godkänt, inte implementerat beteende.
  - Underlag: [docs/strategiforskning-20261103.md](strategiforskning-20261103.md) — Registrering verifierad av motorn: N=16, inget resultatbeslut; äldre REJECT bevarade.
- [x] **H16-104** Dokumentera riskbudget 0,5 %, dagsstopp 2 %, permanent stopp 15 % och drawdown-mål 20 %
  - Underlag: [research/h0016-protokoll.md](../research/h0016-protokoll.md) — Förregistrerat i e65012e; endast dokumenterat kontrakt godkänt, inte implementerat beteende.
  - Underlag: [docs/strategiforskning-20261103.md](strategiforskning-20261103.md) — Registrering verifierad av motorn: N=16, inget resultatbeslut; äldre REJECT bevarade.
- [x] **H16-105** Lås kostnader, jämförelser och de sex beslutskriterierna, inklusive t ≥ 2,7343687865331763
  - Underlag: [research/h0016-protokoll.md](../research/h0016-protokoll.md) — Förregistrerat i e65012e; endast dokumenterat kontrakt godkänt, inte implementerat beteende.
  - Underlag: [docs/strategiforskning-20261103.md](strategiforskning-20261103.md) — Registrering verifierad av motorn: N=16, inget resultatbeslut; äldre REJECT bevarade.

## 2. Data och skydd

0/5 verifierade.

- [ ] **H16-201** Verifiera att arkivnamn, SHA-256 och CHECKSUM motsvarar det frysta datasetet
- [ ] **H16-202** Kontrollera OHLC, UTC, 4H-rutnät, ordning, dubbletter och luckor
- [ ] **H16-203** Verifiera fundingserien och kontrollsumman för inlästa data
- [ ] **H16-204** Avvisa data från 2025 innan filer öppnas eller beräkningar börjar
- [ ] **H16-205** Skilj uppvärmning 2020–2021 från den sammanhängande testperioden 2022–2024

## 3. Implementera signalerna

0/5 verifierade.

- [ ] **H16-301** Återanvänd squeeze_breakout 1.0.0 med de låsta standardparametrarna
- [ ] **H16-302** Tillåt endast long eller platt och avvisa short, ML och parameteroptimering
- [ ] **H16-303** Kräv en ny squeeze-release efter utgång, stop eller dagspaus
- [ ] **H16-304** Verifiera beslut vid stängning, fyllning vid nästa öppning och fast ATR-stop
- [ ] **H16-305** Testa uppvärmning, signalbyten och framtidsläckage med syntetiska data

## 4. Implementera risklagret

0/5 verifierade.

- [ ] **H16-401** Beräkna positionsstorlek från 0,5 % riskbudget inklusive kostnader för in- och utträde
- [ ] **H16-402** Begränsa till en position, högst 1× exponering vid inträde och två inträden per UTC-dygn
- [ ] **H16-403** Implementera dagsstopp vid 2 % nettoförlust och krav på ny signal efter pausen
- [ ] **H16-404** Implementera permanent stopp vid 15 % nettodrawdown utan reset mellan halvår
- [ ] **H16-405** Testa riskgränser mot verkligt simulerat nettokapital, gap och ogiltiga indata

## 5. Backtest och redovisning

0/5 verifierade.

- [ ] **H16-501** Behåll fast positionsstorlek under affären utan dold ombalansering
- [ ] **H16-502** Verifiera avgifter, spread, slippage, funding och gap för varje affär
- [ ] **H16-503** Bygg en sammanhängande kurva med startkapital 100 000 och utan framtida slutstapel
- [ ] **H16-504** Beräkna konservativ intrastapel-drawdown samt drawdown vid stapelstängning
- [ ] **H16-505** Stäm av affärslogg, nettokapital, kostnader, funding och eventuella likvidationer

## 6. Jämförelser och stresstester

0/5 verifierade.

- [ ] **H16-601** Implementera köp-och-behåll och fast squeeze utan nytt risklager på exakt samma staplar
- [ ] **H16-602** Kör 2,5× kostnadsstress med omräknade positioner och riskstopp
- [ ] **H16-603** Implementera separat fundingstress enligt protokollet
- [ ] **H16-604** Beräkna netto, t-värde, osäkerhet, drawdown och resultat per år och halvår
- [ ] **H16-605** Testa alla sex beslutskriterier och avvisa ofullständiga eller icke ändliga resultat

## 7. Granskning och registrerad körning

0/5 verifierade.

- [ ] **H16-701** Granska kod och protokolltolkningar före riktig historik; registrera nya regler som nytt id
- [ ] **H16-702** Kör relevanta automatiska tester och verifiera identiska resultat vid återspelning
- [ ] **H16-703** Förbered separat H-0016-körväg, versionsmärkt paket och verifierade data
- [ ] **H16-704** Genomför den registrerade historiska körningen med låsta jämförelser och stresser
- [ ] **H16-705** Spara resultat och avbrutna försök med kodrevision, datahash och körnings-id

## 8. Resultatgranskning och nästa beslut

0/5 verifierade.

- [ ] **H16-801** Räkna oberoende om netto, kostnader och de sex kriterierna från sparat resultat
- [ ] **H16-802** Granska affärer, riskstopp, intrastapel-risk och terminsmodellens begränsningar
- [ ] **H16-803** Registrera REJECT eller MORE_RESEARCH på ny registerrad utan att ändra gamla beslut
- [ ] **H16-804** Dokumentera separat slutprovsbeslut vid MORE_RESEARCH; öppna inget vid REJECT
- [ ] **H16-805** Överlämna nästa steg till Fas 3 först efter READY_FOR_PAPER, annars dokumentera fortsatt forskning
