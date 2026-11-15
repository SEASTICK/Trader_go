# Codex granskning av H-0026 (tidigare H-0017), D2

Datum: 2026-11-15. Exakt revision **0668f1035f2d6241c196b669f8d264e2650be8d0**, diffbas **99e96858b460f00818a8f5bfc36ac15f79660242**. Gren `codex/momentum-d2-review`; full HEAD, diffbas och ren arbetskopia verifierades före ändring. Endast syntetiska minnesdata, inga nätverksanrop.

**Beslut: EJ GODKÄND inom D2.** D2-01–D2-03 behöver rättas och granskas på en ny exakt revision. MOM-D01 förblir `in_progress`. MOM-C03/C05 kan återgodkännas inom sina tidigare huvudmodellsgarantier; MOM-C04:s tidigare avgränsade godkännande består. Detta godkänner inte hela kontrollmatrisen eller D2:s publika fullhorisontskontrakt.

Underlag: AGENTS.md, CLAUDE.md, fryst protokoll §6, §8, §9, §11, D07–D21 och O2/O5/O10/O11/O16/O18, D2-uppdraget, Claudes rapport, statuskällan samt faktiska revisionslåsta källor och tidigare revisionsauditer. Rapportens påståenden har prövats självständigt.

## Fynd

### D2-01 [P2] Ogiltigt fullhorisontsunderlag upptäcks efter ekonomiska steg

`run_buy_and_hold`, `engine/traderlab/momentum_benchmark.py:48–65`, förlitar sig på `Market.verified()`. D1:s Market kontrollerar positiva ändliga celler och raster, men saknar fullständig kontroll av mark-OHLC-relationer, fundingreferenser och dubbla funding-id. `verified()` kontrollerar bara att innehållet är oförändrat. Bar och process_bar upptäcker dessa fel först när körningen når dem.

Auditen skapar tre fullständiga syntetiska underlag med fel i stapel 12: low över high, M_ref som avviker från mark_open respektive dubblerat funding-id. Market accepterar samtliga. OHLC-felet avvisas efter **12 redan utförda ekonomiska steg**; fundingfelen avvisas vid det **13:e process_bar-anropet**, efter 12 utförda steg. Ingen partiell retur sker, men kravet att avvisa före första ekonomiska beräkning är brutet (D13/§3 och uppdragets punkt 4).

Fullhorisontsvägen behöver validera hela underlaget före start, med diskriminerande prov som bevisar noll ekonomiska anrop för sent placerade fel. Om Market stärks måste D1:s påverkan redovisas och granskas separat; signalkravet får inte lättas.

### D2-02 [P2] Det publika jämförelsekontot accepterar kostnadsstress

`run_buy_and_hold(..., cost=0.004)` accepteras via `Scenario` och returnerar ett fullständigt buy_and_hold-resultat med stressad kostnad. Auditen reproducerar detta genom den publika fullhorisontsvägen. Uppdragets låsta kostnad är **0,0016 per sida utan kostnadsstress för jämförelsekontot**; D15/§12 lägger kostnadsstress endast på main.

Lås eller validera kostnaden i det publika buy_and_hold-kontraktet och pröva avvisning före ekonomiska steg. Den generiska momentumvägens tillåtna main-stress ska bevaras. Ett valbart avsteg får inte framstå som ett förregistrerat jämförelsekonto.

### D2-03 [P2] Felprovet för delat förlopp delar bara namn och missar verklig loggåteranvändning

Mutationen ”delat kontoförlopp mellan legacy-ordningar”, `scripts/momentum-d2-mutations.py:90–92`, tar bort L1/L2 ur kontonyckeln men kör fortfarande nya oberoende EngineState/RunLog. Den provar identitet, inte uppdragets uttryckliga krav på verkligt delat funding-/kontoförlopp.

Auditen inför därför en separat beteendemutant i en temporär revisionskopia: L1:s färdiga RunLog sparas och **L2 returnerar exakt samma logg och slutstate**, medan L2:s yttre scenarioetikett behålls. Denna mutant går igenom den deklarerade D2-sviten och klassas **MISSAD**. L1/L2 har lika ekonomi här, men deras kontoförlopp och proveniens ska vara separata. Proven måste kontrollera faktisk logg-/stateidentitet och scenario, samt oberoende processed-state; lika kapital och olika yttre etiketter räcker inte.

Detta är en test- och felprovslucka, inte belägg för att den omuterade implementationen delar state. Den godkända D1-klassningsmekaniken återanvänds korrekt; dess egna kontrollgrenar är inte orsaken till missen.

## Verifierade delar och tidigare C-garantier

- Diffen omfattar exakt åtta filer. **Signal, ledger, funding, risk, marginal, bound, control, stats, fryst protokoll, register, gamla resultat och gamla audits är byte-oförändrade** mot diffbasen. D1:s mutationsskript är också oförändrat. Eventmodulens ändringar har granskats direkt; inga gamla audits ändras i denna leverans.
- Ny modul/API är `mom-bh/1.0.0`; eventmodulen behåller `mom-event/1.0.0` och får det bakåtkompatibla standardfältet `Scenario.policy`. buy_and_hold använder gemensam ledger/fill, funding och marginal, med en särskild policygren för första inträdet, fasta enheter och terminal. Standardpolicyn är momentum. Inga globala riskregler stängs av. Policy ingår i scenarioetiketten och därmed funding-/marginalbindningen; konstruktionsgrinden och RunLogs kedjekontroll består. Signal till buy_and_hold avvisas.
- Oberoende Decimal med precision 70 räknar åtta fulla förlopp, vartdera **6 576 staplar, 6 577 kapitalpunkter och 1 096 dagar**. Varje close och dag jämförs punktvis; O2-storlek, fasta q, blandad funding, exakt första/terminal samtidighet, millisekundsevent, terminal P≠M, kostnader och fundingnetto stäms av. L1/L2-spåren har lika ekonomi efter normalisering. Inga produktionshjälpare eller testfixturer används som referensledger.
- Åtta ytterligare publika fullförlopp (A/B × båda mmr × gap/intrastapel) jämförs mot separat Decimal-underlag: betald funding, adverse-prövning utan räddning från kredit, C5-01:s olösta belopp, bevarad bokföring och justering till totalförlust, senare absorbed och dokumenterad noll till terminal. Ingen statistik eller avkastningsomvandling räknas.
- Momentumregression mot separat laddade git-show-källor från **7345f06b928f25902ab1515008e1c26f99fa7c0c**: main/mom7/mom14/mom28 × A/B × båda mmr, vardera 120 sekventiella staplar med basis, funding, varierande mål/cap och stora prisrörelser. **Hela BarResult**, inklusive StepRecord, tillstånd och ordnade spår, jämförs efter att enbart det nya standardfältet Scenario.policy="momentum" utelämnats ur strukturjämförelsen; även hela ackumulerade BoundLog är lika. Alla oförändrade tidigare momentumtester och revisionsauditer kompletterar dessa jämförelser.
- D1:s Market återanvänds utan ändring och utan lättat signalbehov. Konstant-close accepteras för buy_and_hold, medan komponentvägen fortfarande kräver tillgänglig momentumvol/signal. Fullt oförändrat Market är emellertid inte samma sak som fullständig validering före start; se D2-01.
- **MOM-C03 och MOM-C05 återgår till done inom tidigare huvudmodellsscope** efter omgranskning av eventdiffen, identiska momentumspår, oberoende referenser och regressionerna. **MOM-C04 förblir done inom tidigare huvudmodellsscope**: closebaserade stopp och separat hypotetisk bound består; 20 % styr ingen handel. Ingen buy_and_hold-bound eller full boolesk kriterieprövning godkänns här.

## Revisionsaudit och körda kontroller

[review.py](../research/audits/momentum-d2-0668f10/review.py) läser källor med `git show` från full revisionshash och laddar separata modulrymder för D2 respektive 7345f06. [verification.json](../research/audits/momentum-d2-0668f10/verification.json) innehåller källhashar, exakt fillista/skyddskontroll, Decimal-facit, momentumregressioner och egna motexempel. `--check` räknar om underlaget; PASS innebär reproduktion även av öppna fynd.

Motor och audits kördes med `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest kördes från `engine/` med `-m pytest -p no:cacheprovider` och projektets `-q`.

- Momentumtesterna, `tests/test_momentum*`: **629 passerade**, exit 0.
- Hela motorsviten: **1 182 passerade**, exit 0; en joblib-varning om fysisk CPU-detektering.
- A1-oraklet, `python3 scripts/momentum-a1-oracles.py --check`: **PASS**, exit 0.
- D1-felprovsskriptets `--check`: **PASS**, **31 FÅNGAD / 0 MISSAD / 1 EKVIVALENT / 0 EJ_TILLÄMPLIG**, grön **65-provsbaslinje**.
- Ny revisionsaudit genererad och separat körd med `--check`: **PASS**, exit 0. Åtta fulla Decimal-ledgrar och åtta fulla likvidationsförlopp; 1 920 kompletta momentumsteg och 9 624 ordnade spårrader samt ackumulerad BoundLog lika mot 7345f06.
- Egen neutral felinjektion i D2-harnessen: första-användningsfel i ett testanrop ger **MILJÖFEL**, RuntimeError, och kontrollgrenen fallerar också. Egen verklig beteendemutant som delar L1/L2-logg ger **MISSAD efter 155 passerade prov**; se D2-03.
- D2-felprovsskriptets `--check`: **PASS**, **23 FÅNGAD / 0 MISSAD / 0 EKVIVALENT / 0 EJ_TILLÄMPLIG**, grön **155-provsbaslinje**. Nio självtestutfall: sju MILJÖFEL, kvarlämnad resurs MISSAD och verklig mutation FÅNGAD. Detta reproducerar den deklarerade matrisen, inte den saknade delat-förlopp-mutationen i D2-03.
- Samtliga **30 äldre** `research/audits/momentum-*/review.py --check`: **PASS**, exit 0, som historisk reproduktion. A–C:s 22 audits och D1:s åtta audits har kontrollerats; med den nya auditen passerar **31 av 31**. Gamla slutsatser och underlag är orörda.
- Alla **fyra** checklistgeneratorer med `--check`: **PASS före och efter statusändringen**. Momentumvyn regenererad med `python3 scripts/render-momentum-checklist.py` och därefter kontrollerad med `--check`.
- `git diff --check 99e9685 0668f10` och granskningsleveransens `git diff --check`: rena. Merge-base är exakt diffbasen. HEAD och gren oförändrade. Endast C03/C05 ändrar uppgiftsstatus; bara C03/C04/C05/D01 får nytt uppgiftsunderlag. D2:s implementation, tester och skript samt alla gamla audits är orörda.

## Status och nästa steg

MOM-D01 är fortsatt `in_progress`: D2 är inte godkänd och kan inte ensam slutföra kontrollmatrisen. Legacy, no_vol, blandningar och kontrollkontonas diagnostiska bound återstår. MOM-D02–D05 och E–H förblir todo. D1-Q01/Q02 avgörs inte här. C03/C05:s återgodkännande är uttryckligen begränsat till tidigare huvudmodellsgarantier; C04 består inom samma tidigare avgränsning.

Rätta D2-01–D2-03 och lämna en ny exakt revision för omgranskning. Inget nytt uppdrag skrivs. H-0013 förblir REJECT, H-0016:s protokoll och status ändras inte. Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live har utförts eller godkänts. Inget committat eller pushat. Checklistan är en lokalt regenererad ögonblicksbild.
