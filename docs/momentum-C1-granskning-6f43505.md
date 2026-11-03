# Codex godkännande av H-0017 leverans C1

Datum: 2026-11-03. Godkänd revision **`6f4350569f52527d9a156333240b735530e423a6`**, diffbas `8fc20e2`.

**C1 godkänns. C1-01 och C1-02 är stängda, inga nya blockerande fynd i omgranskningen.** Godkännandet avser den rena ledger-/storleks-/kostnadsgrunden och mekanisk reduce-only-fyllning på syntetiska konton. Det omfattar inte funding, marginal, riskbeslut, eventloop, verklig data eller ekonomiskt resultat. Nästa del av C får börja enligt den separata C2-instruktionen.

## C1-01 – stängt

Account validerar och normaliserar samtliga sex fält vid konstruktion, inklusive dataclasses.replace. NaN, ±inf, bool och text avvisas med LedgerError. Giltig negativ C, legacy-short och realiserad förlust tillåts. Publika kapital-/vikt-/avstämningsvärden och beräknade belopp kontrolleras för ändlighet; den tidigare positiva oändligheten godkänns inte längre som E_trade.

Oberoende kontroll täcker 60 felaktiga konstruktioner/ersättningar och båda fyllningsvägarna för det tidigare overflowfallet. Inget konto/fill returneras vid fel och det inkommande kontot är oförändrat. De ursprungliga NaN-/inf-fynden är därmed avhjälpta.

## C1-02 – stängt

Den kostnadsfria nämnaren kontrolleras före division och q0 måste vara ändligt före likhet/grenval. Python- och numpy-tal normaliseras till samma Python-float-aritmetik. Det tidigare fallet (E=1000, q_old=0, P=200, M=100, w=−1) ger LedgerError för float/int/np.float64/np.int64 med varningar som fel. Ett icke-ändligt q0 från ändliga argument ger också LedgerError. Ingen reservlösare eller ny modellregel har införts; de senare vakterna finns kvar.

## Regression och integritet

- **82 ledgertester godkända**, inklusive de 42 nya regressionerna. De 40 tidigare testfunktionerna/fallen är bevarade i diffen.
- **671 tester godkända i hela motorsviten**, exit 0, antal verifierat genom insamling. Den tidigare joblib-varningen om detektering av fysiska CPU-kärnor förekom i ML-testet utan testfel.
- 250 egna syntetiska fall stämmer med den bevarade oberoende 50-siffriga Decimal-referensen. Före/efter-jämförelse av **500 normal-/riskfyllningar** ger identiska kontofält och fillposter för giltiga vanliga tal.
- A1-orakel, sju äldre Codex-audits och fyra checklistgeneratorer passerar med projektets venv. Ny omgranskningsaudit passerar också. git diff --check för 8fc20e2..6f43505 är rent.
- Arbetskopian var ren före granskningen och lokal/fjärr claude/momentum-c1 verifierades på samma fullständiga hash. Protokoll, register och B-modul är oförändrade mot C1-utgångsläget 1f14a0a.
- Claudes 19 fångade mutanter av 20 är hans redovisning. Codex verifierar rättningen genom egna gränsfall och före/efter-/Decimal-kontroller och påstår inte att hela mutationsserien körts om.

Reproduktion: `engine/.venv/bin/python research/audits/momentum-c1-6f43505/review.py --check`. Skriptet kör två låsta Git-versioner med syntetiska tal och återanvänder den oberoende Decimal-referensen från första C1-granskningen. Källhashar och resultat finns i verification.json. Äldre audit reproducerar fortfarande historiska 6eba8d6 och ska bevaras.

## Status och nästa leverans

MOM-C01 markeras klar för C1 på exakt 6f43505. MOM-C05 får kompletterande verifiering av basis/kostnad/reduce-only men förblir in_progress: likvidation och full riskordning är inte implementerade eller verifierade. C02–C04 är inte klara. Checklistan blir **11/40**; A/B-status bevaras.

Nästa leverans är [C2: fundingbokföring och exakta fundingevent](claude-uppdrag-momentum-C2.md), enbart syntetiskt. Komplettering av ledgerns redovisningsfält för funding kan behöva ändra C1:s kod/identitet. Då ska C01 återöppnas tills den nya ledgerrevisionen granskats, enligt AGENTS.md; detta godkännande täcker bara 6f43505.

Ingen marknadshistorik, skyddad period, H-0017-körning, kö, servermutation, migration, driftsättning eller release har ingått. Börsmodellen, verklig datakvalitet/fundingtäckning, risk- och likvidationsordning, utvärderare och alla ekonomiska resultat återstår. H-0013 REJECT, H-0016 och tidigare Windows-/Gatekeeper-/larm-/temabegränsningar är oförändrade. Ingen paper/live-strategi är godkänd.
