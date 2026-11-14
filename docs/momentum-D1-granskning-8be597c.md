# Codex granskning av H-0017 D1-rättning, revision 5

Datum: 2026-11-14. Exakt revision **8be597caf3d0b56bb0721723cbc97df130e2bf4c**, diffbas **02172215a1b0bef4ecc563e314478544a90c5bf3**. Gren `codex/momentum-d1-review`; HEAD, bas och ren arbetskopia verifierade före ändring. Endast syntetiska data, ingen marknadshistorik eller nätverk.

**Beslut: EJ GODKÄND.** D1-08:s tre konkreta motexempel är rättade, men D1-04:s bredare garanti kvarstår som D1-09 P2. Tvillingkontrollen kan ge falsk fångst eftersom den ändrar testföljden. MOM-D01 förblir `in_progress`; D1 ensam slutför inte kontrollmatrisen. A/B/C:s avgränsade godkännanden består.

Underlag: AGENTS.md, CLAUDE.md, D1-uppdraget, tidigare D1-granskningar och audits, metodgranskning och kontraktsutkast, fryst protokoll, Claudes D1-rapport, status och revisionslåsta källor. Claudes rapport behandlas som påståenden att kontrollera.

## Fynd

### D1-09 [P2] – tvillingen tappar föregående prov och kan därför ge falsk FÅNGAD

`scripts/momentum-d1-mutations.py:210–222,236–238`. Mutanten kör ett riktat urval eller hela D1-sviten. Tvillingen kör däremot endast `_node(test_id)` i en ny pytestprocess. Identiska filer innebär inte identiska körförutsättningar: tidigare prov och fixturernas processlokala tillstånd saknas. Ett passerande isolerat prov bevisar därför inte att mutationen orsakade svitens fel.

Egen deterministisk injektion i temporär arbetsyta: två syntetiska prov med en autouse-fixtur vars räknare ökas vid setup. Första provet passerar; andra setup kastar `RuntimeError("synthetic resource exhausted after first test")`. Källändringen är bara en neutral kommentar. `run_one` ger **FÅNGAD**, `1 passed, 1 error`, fas `setup/nedstädning`, tvilling `passerar`. Tvillingen kör bara andra provet och räknaren börjar åter på ett. Samma tvåprovskörning med helt återställd källa ger åter exit 1, `1 passed, 1 error`, samma RuntimeError vid andra setup. Mutationen orsakar alltså inte felet.

Auditen kör först den riktiga gröna 65-provsbaslinjen. Därefter införs injektionen enbart i temporära kopior; inga implementations- eller testfiler i arbetskopian ändras. Detta är ett motexempel mot klassningsgarantin, inte ett påstående att revisionens 31 ordinarie fångster har detta fel. Den neutrala ändringen får varken FÅNGAD eller godkänt mutationsunderlag i denna miljö.

Rättningen behöver bevara relevant urval, ordning och fixturförutsättningar i jämförelsen och verifiera att motsvarande körning utan mutation verkligen är grön. Lägg till ett regressionsprov med sekvensberoende setupfel. En isolerad nods exitkod räcker inte för det utlovade orsakssambandet. Detta preciserar kvarstående D1-04; ingen ny ekonomisk bugg har påvisats.

## Stängda fynd och verifierade delar

- **D1-08:s konkreta motexempel stängda:** FileNotFoundError, RuntimeError och AssertionError från en ovillkorligt felande autouse-fixtur ger nu MILJÖFEL med neutral källändring. Egen injektion via `run_one` verifierar detta utöver Claudes självtest. Den generella setupgarantin är fortfarande öppen enligt D1-09.
- **D1-01/D1-02/D1-05 fortsatt stängda:** sex ursprungliga adapterfel avvisas; earliest_fill bevaras. Anroparens 2025-tillägg isoleras, internt tillägg avvisas före signals, ändrad intern markcell avvisas. Cap `10**5000` och motstridiga dubblettrader ger ControlError.
- **D1-03/D1-06/D1-07 fortsatt stängda inom tidigare gränser:** 31 ordinarie mutationer omkörs individuellt mot sparad matris. Delat förlopp återanvänder faktiskt mom7:s RunLog/slutstate; identitetsmutanten är separat. Körtider ingår inte i jämförelsen.
- **Fallback och missar:** verkligt passerande respektive tomt riktat urval går vidare till hela D1-sviten och fångar main-s-mutanten. Neutral kommentar överlever samtliga 65 prov och blir MISSAD. Ingen dold miss påvisades i dessa fall; D1-09 visar att falska fångster fortfarande är möjliga.
- **Oberoende referenser:** 3 288 Decimal-signaljämförelser med precision 70, alla åtta kombinationer, 1 096 cap<1-dagar och lika-prisfall. Tre fulla publika komponentförlopp jämförs mot eget kapitalfacit, vardera 6 576 staplar, 6 577 closepunkter och 1 096 dagsslut. Separat varierande Decimal-ledger räknar inträde, ökning, minskning med basis, utgång, återinträde och terminal P=100,5/M=100; C/q kontrolleras efter varje stapel och kapital vid varje close/dag. Årsskiftesfacit ger 2023-01-03 04:00 UTC. O9 kräver capminskning trots obrutet band.

## Revisionsaudit och integritet

[review.py](../research/audits/momentum-d1-8be597c/review.py) läser källorna med `git show` från fullständig 8be597c och laddar dem i separat modulrymd. Körningar och injektioner sker i temporära arbetsytor. [verification.json](../research/audits/momentum-d1-8be597c/verification.json) låser SHA-256, diff-fillista, skyddskontroll, Decimal-referenser, omkörda mutationer, fallback, gamla setupmotexempel och D1-09. `--check` reproducerar underlaget inklusive det öppna fyndet; PASS innebär inte godkännande.

Diff 0217221..8be597c omfattar exakt fem filer: mutationsskript, mutations-JSON, D1-rapport, momentumstatus och genererad momentumvy. **Signal, control, ledger, funding, risk, marginal, event, bound, stats, tester, protokoll, register, gamla resultat, gamla audits och gamla granskningar är byte-oförändrade.** Exakt tillåten fillista och separat skyddad git-diff kontrolleras i auditen. Granskningen ändrar endast nytt auditunderlag, detta dokument och momentumstatus/vy.

## Körda kontroller

Interpreter för motor och audits: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest kördes från `engine/` med `-m pytest -p no:cacheprovider -o addopts= -q`.

- Momentum, `tests/test_momentum*.py`: **605 passerade**, exit 0.
- Hela motorsviten: **1 158 passerade**, exit 0; en joblib-varning om fysisk CPU-detektering.
- `python3 scripts/momentum-a1-oracles.py --check`: PASS.
- Alla fyra checklistgeneratorer med `--check`: PASS före statusändring; momentumvyn regenererad och alla fyra kontrollerade igen efter statusändring.
- `git diff --check 0217221 8be597c` och granskningsleveransens `git diff --check`: rena.

- `python3 scripts/momentum-d1-mutations.py --check`: **PASS**, exit 0; **31 FÅNGAD, 0 MISSAD, 1 EKVIVALENT, 0 EJ_TILLÄMPLIG**, med grön **65-provsbaslinje**. Självtestets tre setupfel ger MILJÖFEL och verklig mutation FÅNGAD.
- Ny revisionsaudit genererad med exit 0: alla 31 sparade fångster reproducerade, gamla motexempel och D1-09 verifierade. Separat `--check`: **PASS**, exit 0.
- Samtliga **26 äldre** `research/audits/momentum-*/review.py --check`: **PASS**, exit 0, som historisk reproduktion; deras gamla slutsatser skrivs inte om. Med den nya auditen passerar totalt **27 av 27** momentum-audits.

## Status och nästa steg

MOM-D01 förblir `in_progress`, utan nya done-markeringar. D1-08:s ursprungliga tre motexempel stängs; D1-04:s bredare garanti kvarstår som D1-09. buy_and_hold, legacy, no_vol, blandningar och komponent-bound återstår. D1-Q01/Q02 avgörs inte här. Övriga D-punkter och tidigare avgränsade A/B/C-godkännanden ändras inte. Ny rättning och granskning av exakt revision krävs före godkännande; inget nytt uppdrag skrivs.

Registreringskonflikt enligt Edwins uppgift: origin/main använder sedan 2026-11-04 H-0016 för 13F och H-0017 för Pelosi, medan momentum registrerades som H-0017 på Edwins gren 2026-11-03 och aldrig mergades. Detta är en separat registreringsfråga för Edwin. Inga register, protokoll eller ID ändras i granskningen; fjärrläget har inte hämtats eller verifierats med nätverk.

Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live utförd eller godkänd. H-0013 förblir REJECT. Inget committat eller pushat. Checklistan är en regenererad lokal ögonblicksbild.
