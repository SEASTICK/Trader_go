# Codex granskning av H-0017 D1-rättning, revision 8

Datum: 2026-11-15 (påbörjad 2026-11-14). Exakt revision **7345f06b928f25902ab1515008e1c26f99fa7c0c**, diffbas **e148199a4306b08ef9d9cb01853d30e6e2df42b1**. Gren `codex/momentum-d1-review`; HEAD, full diffbas och ren arbetskopia verifierade före ändring. Endast syntetiska data; inga nätverksanrop eller marknadshistorik.

**Beslut: GODKÄND inom D1.** D1-11 och D1-04 stängs; inga nya fynd. MOM-D01 förblir `in_progress`; D1 ensam slutför inte kontrollmatrisen. A/B/C:s tidigare avgränsade godkännanden består.

Underlag: AGENTS.md, CLAUDE.md, D1-uppdraget, samtliga tidigare D1-granskningar och deras revisionsauditer, metodgranskning, kontraktsutkast, fryst protokoll, Claudes rapport, momentumstatus och revisionslåsta källor. Rapportens påståenden har prövats självständigt.

## Fynd och stängda fynd

**Inga nya fynd (D1-12 och framåt).** Följande tidigare fynd stängs inom den syntetiska D1-matrisens avgränsning:

- **D1-11 [P2] stängt:** `_run_flow` tar `mutant_hela`, `kontroll_riktade` och `kontroll_hela` före första `_pytest`. Det riktade provet använder den ursprungliga mutantarbetsytan och sin kontroll; fallback använder två andra, orörda kopior. Båda jämförelserna behåller samma TESTS, `-k` och ordning, och kontrollen återställer bara den avsiktliga källmutationen. Ingen jämförelse ärver en tidigare provkörnings filändringar.
- **Eget ursprungligt D1-11-motexempel:** neutral kommentar plus `test_resource`, som skapar en markör och fallerar om den redan finns. `run_one` ger nu **MISSAD**, `2 passed`, `hela D1-sviten`. Två färska omuterade fullkörningar passerar också. De gamla omuterade tvåstegskontrollerna (riktat följt av fullsvit i samma arbetsyta) fallerar fortfarande med RuntimeError; auditen bevisar därmed både den gamla felmekanismen och att den nya vägen undviker den.
- **D1-04 [P2] stängt, inklusive preciseringarna D1-08–D1-11:** egna neutrala injektioner med FileNotFoundError, RuntimeError och AssertionError vid setup ger **MILJÖFEL**, liksom det processlokala andra-provet-felet och de tre första-användningsfelen i setup/anrop/nedstädning. De sistnämnda har dessutom sex färska omuterade negativa kontroller som fallerar som väntat. Insamlingsfel blir MILJÖFEL; orörd kontroll måste passera hela samma provurval innan en fångst godtas. Den ursprungliga saknade-orakelfilen är fortsatt rättad och baslinjen är grön.
- **Ytterligare egna fallbackinjektioner:** riktat prov som raderar en befintlig resurs vid nedstädning ger **MISSAD** med neutral källändring när den färska fullkörningen passerar. Ett setupfel som uppstår först vid andra provet i fullsviten ger **MILJÖFEL**, `1 passed, 1 error`, och kontrollen fallerar också. Ett fel vid insamling ger **MILJÖFEL**, inte en fångst.
- **D1-03/D1-06/D1-07 fortsatt stängda inom tidigare gränser:** alla 31 sparade fångster reproduceras individuellt med grön kontrollgren. Verkligt passerande respektive tomt riktat urval faller vidare till hela sviten och fångar main-s-mutanten där. Neutral kommentar i oförstörd miljö blir MISSAD efter samtliga 65 prov. Ingen ny miss eller falsk fångst har påvisats.

Stängningen gäller uppdragets syntetiska, isolerade testmiljö och de granskade felmekanismerna.

## Verifierade delar

- API/version `mom-control/1.0.0` och de tre fullkapitalkontona mom7/mom14/mom28 är oförändrade. Källans main-s skiljs från komponentens s_used; earliest_fill samt käll- och adapterversion bevaras. Varje konto börjar med eget kapital 100 000 och eget obrutet eventförlopp; D1 inför inga delkonton eller blandningar.
- Oberoende referenser räknas om från den granskade revisionen: 3 288 Decimal-signaljämförelser vid precision 70, alla åtta komponentkombinationer, 1 096 cap<1-dagar och lika-prisfall. Kalenderlag, 60 avkastningar, ddof=1-vol, cap och komponentmål räknas utan produktionsutdata som facit.
- Tre fulla publika komponentförlopp jämförs med eget kapitalfacit, vardera 6 576 staplar, 6 577 closepunkter och 1 096 dagsslut. Separat varierande Decimal-ledger räknar inträde, ökning, minskning med basis, utgång, återinträde och terminal P=100,5/M=100. C/q kontrolleras efter varje stapel och kapital vid varje close/dag. Årsskiftesfacit ger 2023-01-03 04:00 UTC. O9 kräver capminskning trots obrutet band; protokollet och oraklet ändras inte för uppdragets felaktiga hold-formulering.
- D1-01/D1-02/D1-05 omprövas med sex ursprungliga adapterfel, bevarad earliest_fill, anroparens respektive internt ändrad 2025-rad, ändrad intern markcell, cap `10**5000` och motstridiga dubblettrader.
- Alla 31 ordinarie fångster omprövas individuellt mot sparad matris. Delat förlopp återanvänder faktiskt mom7:s RunLog/slutstate; identitetsmutanten är separat. Kalender-/observationsmutationen är ekvivalent inom Markets obligatoriska fullständiga raster. Körtider ingår inte i jämförelsen.

## Revisionsaudit och integritet

[review.py](../research/audits/momentum-d1-7345f06/review.py) läser källorna med `git show` från fullständig 7345f06 och laddar dem i separat modulrymd. Testkörningar och injektioner sker i temporära källkopior med syntetiska data. [verification.json](../research/audits/momentum-d1-7345f06/verification.json) låser SHA-256, exakt diff-fillista, skyddskontroll, oberoende referenser, mutationer och egna injektioner. `--check` räknar om underlaget; gamla audits och deras historiska slutsatser ändras inte.

Diff e148199..7345f06 omfattar exakt fem filer: mutationsskript, mutations-JSON, Claudes D1-rapport, momentumstatus och genererad momentumvy. **Signal, control, ledger, funding, risk, marginal, event, bound, stats, tester, protokoll, register, gamla resultat, gamla audits och gamla granskningar är byte-oförändrade.** Exakt fillista och separat skyddad git-diff kontrolleras i auditen. Denna granskningsleverans ändrar bara den nya auditen med underlag, denna granskning och momentumstatus/vy.

## Körda kontroller

Interpreter för motor och audits: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest från `engine/` med `-m pytest -p no:cacheprovider -o addopts= -q`.

- Momentum, `tests/test_momentum*.py`: **605 passerade**, exit 0.
- Hela motorsviten: **1 158 passerade**, exit 0; en joblib-varning om fysisk CPU-detektering.
- `python3 scripts/momentum-a1-oracles.py --check`: **PASS**, exit 0.
- `python3 scripts/momentum-d1-mutations.py --check`: **PASS**, exit 0; **31 FÅNGAD, 0 MISSAD, 1 EKVIVALENT, 0 EJ_TILLÄMPLIG**, grön **65-provsbaslinje**. Sju självtestade miljöfel ger MILJÖFEL; kvarlämnad resurs inför fallback ger MISSAD och verklig mutation FÅNGAD.
- Ny revisionsaudit genererad och därefter separat körd med `--check`: **PASS**, exit 0. Samtliga oberoende referenser, 31 fångster och egna injektioner ovan reproducerade. Även självtestets hela utfall jämförs med den sparade matrisen.
- Samtliga **29 äldre** `research/audits/momentum-*/review.py --check`: **PASS**, exit 0, som historisk reproduktion. Med den nya auditen passerar **30 av 30** momentum-audits; gamla slutsatser ändras inte.
- Alla **fyra** checklistgeneratorer med `--check`: **PASS** före och efter statusändringen. Momentumvyn regenererad med `python3 scripts/render-momentum-checklist.py` och kontrollerad med samma kommando plus `--check`.
- `git diff --check e148199 7345f06` och granskningsleveransens `git diff --check`: rena. `git merge-base e148199 7345f06` är exakt e148199. HEAD och gren är oförändrade. Alla uppgiftsstatusar och alla andra uppgifter är oförändrade; endast MOM-D01:s underlag/not och övergripande granskningsmetadata uppdateras i JSON.

## Status och nästa steg

MOM-D01 förblir `in_progress`, utan nya done-markeringar. buy_and_hold, legacy, no_vol, blandningar och komponent-bound återstår. D1-Q01/Q02 avgörs inte här. Övriga D-punkter och A/B/C:s tidigare avgränsade godkännanden ändras inte. **Nästa avgränsade D-del kan tilldelas.** Inget nytt uppdrag skrivs.

Enligt Edwins beslut 2026-11-14 heter momentumhypotesen **H-0026** på main, tidigare H-0017 på grenen; squeezen heter **H-0025**, tidigare H-0016. Hänvisning: `research/id-omnumrering.md` på origin/main i `3cd3c4c`. Protokollen uppges vara byte-identiska och N=17 behålls. Ingen nätverkskontroll av main har gjorts här. Grenens register, protokoll och gamla id ändras inte.

Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live utförd eller godkänd. H-0013 förblir REJECT. Inget committat eller pushat. Checklistan är en regenererad lokal ögonblicksbild.
