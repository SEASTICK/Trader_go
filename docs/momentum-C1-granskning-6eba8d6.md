# Codex granskning av H-0017 leverans C1

Datum: 2026-11-03. Granskad revision `6eba8d61cca0df03c3aa6c352a26834011479094`, diffbas `1f14a0a`.

**C1 behöver två avgränsade rättningar före godkännande.** De normala storleks-/kostnadsfallen stämmer med oberoende högprecisionsräkning, men gränssnittet uppfyller inte sitt utlovade felkontrakt för alla indata. Dessa är implementationsfel; ingen ändring av fryst protokoll eller nytt hypotes-id behövs.

## C1-01 [P2] Validera kontot och beräknade belopp, inte bara lösarens inparametrar

Plats: `engine/traderlab/momentum_ledger.py:65–95` och `:165–173`.

Den publika Account-konstruktorn validerar inga fält. Fyllningarna kontrollerar E, q och affärspriser men inte avg_price, realized, deposit eller costs. Därmed kan ett konto med ändligt kapital få NaN i realiserat resultat utan LedgerError:

```python
from traderlab import momentum_ledger as L
import math
bad = L.Account(C=800, q=2, deposit=1000, avg_price=math.nan)
account, fill = L.fill_normal(bad, .1, 100, 100)
# E_trade är cirka 999,84, men account.realized och fill.realized_delta är NaN.
```

Att dataklassen är frozen gör den oföränderlig, inte numeriskt giltig. Konstruktion med metadata behöver fortsatt fungera för syntetiska och senare återställda tillstånd, men ogiltiga tal får inte passera obemärkt. Avstämningsgapet kan annars också bli NaN.

Det finns dessutom ingen ändlighetskontroll på beräknade kontobelopp. Med giltiga ändliga inparametrar kan en multiplikation överflöda och den enda kontrollen E_trade>0 godkänner positiv oändlighet:

```python
account = L.Account(C=800, q=2, deposit=1000, avg_price=100)
after, fill = L.fill_normal(account, 0, 1e308, 100)
# after.C, after.realized och fill.E_trade är +inf; inget LedgerError.
```

Det extrema syntetiska priset är ett numeriskt felprov, inte ett påstående om marknadspriser. Löftet "LedgerError, aldrig NaN" måste också hantera overflow från ändliga tal.

**Krävd rättning:** kontrollera relevanta Account-fält när de konstrueras/används och kontrollera beräknade värden innan Account/Fill eller publika equity/weight/reconciliation-resultat returneras. NaN/inf/bool/icke-numeriska värden ska ge LedgerError där API:t utlovar numeriska belopp. Kontrollera E_trade:s ändlighet, inte bara dess tecken. Underkänn fel utan klippning eller påhittade nollor. Lägg inte till en generell C>0-regel: negativ kontantekvivalent, signerade legacy-enheter och negativt realiserat resultat kan vara giltiga. Koppla inte denna numeriska rättning till nya marginal-/likvidationsregler.

**Regressioner:** NaN/inf i redovisningsfält vid direkt konstruktion och/eller användning, båda publika fyllningsvägarna inklusive no-trade/hold, och overflow med ändliga argument. Kontrollera att inget icke-ändligt konto eller fill lämnas tillbaka och att indata inte ändras vid fel. Bevara giltiga negativa C-/short-/förlustfall.

## C1-02 [P2] Vakta även den första divisionen och gör scalar-typer konsekventa

Plats: `engine/traderlab/momentum_ledger.py:132`, före den befintliga slutliga nämnarkontrollen på rad 138.

`solve_units(1000, 0, 200.0, 100, -1)` ger nämnaren **0 i den kostnadsfria q0-lösningen**. Divisionen sker före vakterna och ger ZeroDivisionError i stället för LedgerError.

Med exakt samma numeriska värden men P=np.float64(200) får man i stället en numpy-varning, q0=−inf och därefter ett returnerat q på cirka **−3125**. Den accepterade scalar-typen ändrar alltså om samma odefinierade första lösningssteg kraschar eller producerar en position. De befintliga tre vakttesterna gäller senare lösningssteg och fångar inte denna division.

**Krävd rättning:** kontrollera att den första divisionen är definierad och att nödvändiga mellanresultat är ändliga innan q0 används för likhet/grenval. Nollnämnaren ska ge LedgerError för både vanliga Python-tal och stödda numpy-skalärer. Låt inte en numpy-varning/inf välja handelsgren, och fånga inte bara det vanliga Python-undantaget. Bevara protokollets matematik och befintliga vakter; definiera ingen ny reservlösare för detta odefinierade fall.

**Regressioner:** ovanstående fall med Python float/int samt np.float64/np.int64, och minst ett fall med ett icke-ändligt mellanresultat trots ändliga argument. Samtliga ska ge kontrollerat LedgerError utan returnerad position. Kontrollera fortsatt att normala numpy-tal stöds och att de tidigare separata nämnar-/grenvakterna fungerar.

## Oberoende verifiering av fungerande delar

- **40 ledgertester godkända**, inklusive oraklen O1–O4, O11, O14 och O15 samt partial-/vändnings-/avstämningsfallen.
- **629 godkända i hela motorsviten**, exit 0; antal verifierat genom insamling. En befintlig joblib-varning om detektering av fysiska CPU-kärnor förekom i ML-testet och gav inget testfel.
- Egen syntetisk referens räknar båda köp-/säljgrenarnas kandidater direkt från C/q-ledgern med **50 Decimal-siffror i 250 fall**, med varierande kapital, signerad position, basis och båda kostnadsnivåerna. Den återanvänder inte produktionslösarens kostnadsfria grenval. Position, E_trade, vikt, normal/risk och avstämning passerar.
- Tre egna avsiktliga fel fångas: dubbel kostnad, ignorerad basis och risk som får öka/vända positionen. Endast källkopior i minnet ändrades. Claudes övriga 14 mutationsprov är hans underlag och påstås inte ha körts om i sin helhet av Codex.
- A1-orakel, sex tidigare audit-script samt fyra checklistgeneratorer passerar med projektets venv. git diff --check är rent.
- H-0017-protokoll, register och B-modul är oförändrade. Diffen innehåller de fem uppgivna nya C1-/statusfilerna. Lokal/fjärr claude/momentum-c1 verifierades på samma revision, med ren arbetskopia före granskning.

Reproduktion: `engine/.venv/bin/python research/audits/momentum-c1-6eba8d6/review.py --check`. Skriptet kör den låsta ledgerkoden från Git-commiten 6eba8d6 på syntetiska tal och sparar kontrollsumma/utfall i verification.json. Det reproducerar denna historiska revision även efter en senare rättning, inte den framtida rättade filen. Inga marknadsarkiv eller verkliga forskningskörningar används.

## Status och nästa leverans

MOM-C01 och C05 förblir in_progress. Inga övriga C-punkter markeras klara. A/B behåller sitt godkännande och checklistan står kvar på **10/40**.

Claude rättar enbart C1-01/C1-02 i ledgern, lägger till oberoende regressioner och uppdaterar API-dokumentationen/status. Bevara detta granskningsdokument och audit som historik. Redovisa exakt ny commit, diffbas, tester och påverkan på tidigare verifiering. Lämna C01/C05 in_progress tills Codex omgranskat rättningen. Ingen nästa C-del, funding, marginal, risk-/eventloop, marknadshistorik, jobb, drift eller release ingår i rättningen. Protokoll, register och B-modul ska vara orörda.
