# Codex granskning av H-0017 D1-rättning, revision 7

Datum: 2026-11-14. Exakt revision **3becd973cee37e7609e4c54da0b9698e57f85ecc**, diffbas **add449593234970e23ea01ecc260e5ec595acd65**. Gren `codex/momentum-d1-review`; HEAD, full diffbas och ren arbetskopia verifierade före ändring. Endast syntetiska data, ingen marknadshistorik eller nätverk.

**Beslut: EJ GODKÄND.** D1-10:s tre konkreta resursmotexempel är rättade. D1-04:s bredare klassningsgaranti kvarstår som **D1-11 P2**: fallback återanvänder mutantens ändrade arbetsyta men kör kontrollgrenen från orört läge. MOM-D01 förblir `in_progress`; D1 ensam slutför inte kontrollmatrisen. A/B/C:s tidigare avgränsade godkännanden består.

Underlag: AGENTS.md, CLAUDE.md, D1-uppdraget, tidigare D1-granskningar och revisionsaudits, metodgranskning, kontraktsutkast, fryst protokoll, Claudes rapport, momentumstatus och revisionslåsta källor. Rapportens påståenden har prövats självständigt.

## Fynd

### D1-11 [P2] – fallback jämför olika körhistorik och kan ge falsk FÅNGAD

`scripts/momentum-d1-mutations.py:308–314`, tillsammans med kontrollkörningen på rad 228–240. Kontrollgrenen skapas nu före proven, men om det riktade urvalet passerar körs hela sviten i **samma redan använda mutantarbetsyta**. Kontrollgrenen kör bara hela sviten från sin ursprungliga ögonblicksbild. Det riktade anropets resursändringar saknas där.

Egen deterministisk injektion genom revisionslåst `run_one`, efter grön ordinarie baslinje: källändringen är enbart en neutral kommentar. En tillfällig testfil innehåller `test_resource`, som skapar en lokal markör första gången och passerar; om markören redan finns kastar provet `RuntimeError("synthetic resource reused by fallback")`. Ett andra prov passerar alltid. Riktat `-k test_resource` passerar och skapar markören. Fallback till hela sviten återanvänder den och fallerar i första provet. Kontrollgrenen kör hela sviten utan markör och passerar båda proven.

Skriptets faktiska utfall är **FÅNGAD**, `pytest: 1 failed`, `orsak: RuntimeError`, `fas: anrop`, `körda_prov: hela D1-sviten`, `tvilling_utan_mutation: passerar`. Ingen beteendemutation finns. Två färska omuterade kontrollarbetsytor körs också med samma tvåstegsföljd: riktat prov passerar, därefter fallerar hela sviten med samma RuntimeError. Felet orsakas alltså av återanvändningen, inte av källändringen.

Rättningen behöver jämföra samma initiala resurstillstånd **och hela den relevanta körföljden** när fallback används. Exempelvis kan fullsvitens båda grenar startas från varsin orörd kopia, eller kontrollgrenen få samma föregående riktade körning med kontrollerat utfall. Lägg till ett regressionsprov där det passerande riktade urvalet ändrar en resurs som fullsviten senare läser. Detta preciserar D1-04; ingen ny ekonomisk bugg har påvisats och de 31 ordinarie fångsterna påstås inte vara falska.

## Stängda fynd och verifierade delar

- **D1-10 stängt för de tre reproducerade fallen:** första användning skapar en markör och fallerar i setup, anrop respektive nedstädning. Alla tre ger nu MILJÖFEL genom egna injektioner. Två färska omuterade negativa kontroller per fas fallerar också, totalt sex. Kontrollkopian tas före första körningen och ärver inte markören. Den bredare garantin är fortsatt öppen enligt D1-11.
- **D1-08:s ursprungliga motexempel fortsatt stängda:** ovillkorliga FileNotFoundError, RuntimeError och AssertionError i setup ger MILJÖFEL via egen `run_one`-injektion. **D1-09:s processlokala ordningsfel** ger också MILJÖFEL; samma omuterade tvåprovssekvens fallerar som väntat.
- **D1-01/D1-02/D1-05 fortsatt stängda inom tidigare gränser:** sex felaktiga adapterfält avvisas, earliest_fill bevaras, anroparens 2025-tillägg isoleras och internt tillägg avvisas före signals. Ändrad intern markcell, cap `10**5000` och motstridiga dubbletter avvisas med ControlError.
- **D1-03/D1-06/D1-07 fortsatt stängda inom tidigare gränser:** alla 31 ordinarie fångster omkörs individuellt mot sparad matris. Delat förlopp återanvänder faktiskt mom7:s RunLog/slutstate. Körtider ingår inte i jämförelsen.
- **Vanlig fallback och neutral överlevare:** passerande respektive tomt riktat urval går vidare till hela sviten och fångar main-s-mutanten. Neutral kommentar i oförstörd miljö blir MISSAD efter alla 65 D1-prov. Dessa fall undanröjer inte D1-11.
- **Oberoende referenser:** 3 288 Decimal-signaljämförelser vid precision 70, alla åtta kombinationer, 1 096 cap<1-dagar och lika-prisfall. Tre publika komponentförlopp med eget kapitalfacit, vardera 6 576 staplar, 6 577 closepunkter och 1 096 dagsslut. Separat varierande Decimal-ledger räknar inträde, ökning, minskning med basis, utgång, återinträde och terminal P=100,5/M=100; C/q kontrolleras efter varje stapel och kapital vid varje close/dag. Årsskiftesfacit ger 2023-01-03 04:00 UTC. O9 kräver capminskning trots obrutet band.

## Revisionsaudit och integritet

[review.py](../research/audits/momentum-d1-3becd97/review.py) läser källorna med `git show` från fullständig 3becd97 och laddar dem i separat modulrymd. Körningar och injektioner sker i temporära arbetsytor. [verification.json](../research/audits/momentum-d1-3becd97/verification.json) låser SHA-256, exakt diff-fillista, skyddskontroll, oberoende referenser, mutationer och egna motexempel. `--check` reproducerar även det öppna fyndet; PASS innebär inte godkännande. Äldre audits ändras inte.

Diff add4495..3becd97 omfattar exakt fem filer: mutationsskript, mutations-JSON, D1-rapport, momentumstatus och genererad momentumvy. **Signal, control, ledger, funding, risk, marginal, event, bound, stats, tester, protokoll, register, gamla resultat, gamla audits och gamla granskningar är byte-oförändrade.** Auditen kontrollerar exakt fillista och separat skyddad git-diff. Denna granskningsleverans ändrar endast nytt auditunderlag, detta dokument och momentumstatus/vy.

## Körda kontroller

Interpreter för motor och audits: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest från `engine/` med `-m pytest -p no:cacheprovider -o addopts= -q`.

- Momentum, `tests/test_momentum*.py`: **605 passerade**, exit 0.
- Hela motorsviten: **1 158 passerade**, exit 0; en joblib-varning om fysisk CPU-detektering.
- `python3 scripts/momentum-a1-oracles.py --check`: **PASS**, exit 0.
- `python3 scripts/momentum-d1-mutations.py --check`: **PASS**, exit 0; **31 FÅNGAD, 0 MISSAD, 1 EKVIVALENT, 0 EJ_TILLÄMPLIG**, grön **65-provsbaslinje**. Självtestets sju miljöfel ger MILJÖFEL, verklig mutation FÅNGAD.
- Ny revisionsaudit genererad med exit 0: **3 288** Decimal-signaljämförelser, tre fulla referensförlopp, separat varierande ledger, alla **31** sparade fångster, tidigare motexempel, fallback och neutral överlevare omprövade. D1-10 ger tre MILJÖFEL med sex omuterade negativa kontroller; D1-11 ger falsk FÅNGAD med två omuterade tvåstegskontroller som fallerar på samma sätt.
- Ny audit separat körd med `--check`: **PASS**, exit 0. PASS reproducerar även D1-11 och innebär inte godkännande.
- Samtliga **28 äldre** `research/audits/momentum-*/review.py --check`: **PASS**, exit 0, som historisk reproduktion. Med den nya auditen passerar **29 av 29** momentum-audits. Gamla slutsatser skrivs inte om.
- Alla **fyra** checklistgeneratorer med `--check`: **PASS** före statusändring; momentumvyn regenererad från JSON och kontrollerad igen. Alla fyra passerar även efter statusändringen.
- `git diff --check add4495 3becd97` och granskningsleveransens `git diff --check`: rena. Uppgiftsstatusar och alla andra uppgifter är oförändrade; bara MOM-D01:s underlag/not och övergripande granskningsmetadata uppdateras.

## Status och nästa steg

MOM-D01 förblir `in_progress`, utan nya done-markeringar. D1-10:s konkreta motexempel stängs; D1-04:s bredare garanti kvarstår som D1-11. buy_and_hold, legacy, no_vol, blandningar och komponent-bound återstår. D1-Q01/Q02 avgörs inte här. Övriga D-punkter och tidigare avgränsade A/B/C-godkännanden ändras inte. Rättning och ny granskning av exakt revision krävs före godkännande. Inget nytt uppdrag skrivs.

Enligt Edwins beslut 2026-11-14 heter momentumhypotesen **H-0026** på main, tidigare H-0017 på grenen; squeezen heter **H-0025**, tidigare H-0016. Hänvisning: `research/id-omnumrering.md` på origin/main i `3cd3c4c`. Protokollen uppges vara byte-identiska och N=17 behålls. Ingen nätverkskontroll av main görs här. Grenens register, protokoll och gamla id ändras inte.

Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live utförd eller godkänd. H-0013 förblir REJECT. Inget committat eller pushat. Checklistan är en regenererad lokal ögonblicksbild.
