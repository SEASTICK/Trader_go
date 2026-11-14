# Codex granskning av H-0017 D1-rättning, revision 6

Datum: 2026-11-14. Exakt revision **fcbbb02dbf0938ffd182a0eb06c068cdec39fb47**, diffbas **f1de702dabe20c9ea54a83140e72213a9681fc59**. Gren `codex/momentum-d1-review`; HEAD, diffbas och ren arbetskopia verifierade före ändring. Endast syntetiska data, ingen marknadshistorik eller nätverk.

**Beslut: EJ GODKÄND.** D1-09:s processlokala ordningsfel är rättat, men D1-04:s bredare klassningsgaranti kvarstår som **D1-10 P2**: tvillingen ärver provens filändringar från den redan körda mutanten. En neutral källändring kan fortfarande klassas FÅNGAD. MOM-D01 förblir `in_progress`; D1 ensam slutför inte kontrollmatrisen. A/B/C:s tidigare avgränsade godkännanden består.

Underlag: AGENTS.md, CLAUDE.md, D1-uppdraget, samtliga tidigare D1-granskningar och föregående revisionsaudit, metodgranskning, kontraktsutkast, fryst protokoll, Claudes rapport, status och revisionslåsta källor. Claudes rapport behandlas som påståenden att kontrollera.

## Fynd

### D1-10 [P2] – tvillingen kopieras efter provet och ärver dess ändrade resurstillstånd

`scripts/momentum-d1-mutations.py:210–222,236–238,303–308`. `_twin_passes` kopierar `dst` först efter mutantens pytestkörning. Den återställer källfilen, men behåller övriga filer som den körningen har skapat eller ändrat. Samma provurval och ordning räcker därför inte för samma initiala provförutsättningar.

Egen deterministisk injektion i temporär arbetsyta, efter grön 65-provsbaslinje: källmutationen är enbart en neutral kommentar. En autouse-fixtur kontrollerar en lokal resursmarkör. Om markören saknas skapar fixturen den och kastar `RuntimeError("synthetic first-use resource failure")`. Ingen testkropp hinner pröva mutantens beteende. Mutantkörningen ger exit 1, `1 error`; skriptet ger ändå **FÅNGAD**, fas `setup/nedstädning`, tvilling `passerar`. Tvillingen har ärvt markören och får därför andra initiala förutsättningar.

Två färska arbetsytor med helt oförändrad källa ger vardera exit 1 och samma RuntimeError vid setup. Felet orsakas alltså inte av mutationen. Auditen prövar även motsvarande resursfel i anropsfasen och vid nedstädning; båda ger falsk FÅNGAD med neutral ändring och fallerar i två färska omuterade kontrollkörningar per fas. Totalt tre falska fångster och sex negativa kontrollkörningar. Inga implementationer, testfiler eller resurser i arbetskopian ändras för injektionerna.

Rättningen behöver utgå från samma orörda resurs-/filögonblicksbild före den jämförda körningen för båda grenarna, återställa endast den avsiktliga mutationen i kontrollgrenen och behålla urval/ordning. Lägg till regressionsprov där setup skapar eller ändrar en resurs innan det fallerar. En kopia av mutantens arbetsyta efter körningen verifierar inte det utlovade orsakssambandet. Detta preciserar kvarstående D1-04; ingen ny ekonomisk bugg har påvisats och de 31 ordinarie fångsterna påstås inte ha detta fel.

## Stängda fynd och verifierade delar

- **D1-09 stängt för det reproducerade ordningsfelet:** två prov med processlokal fixturräknare och RuntimeError vid andra setup ger nu MILJÖFEL med neutral ändring. Samma omuterade sekvens fallerar också. Tvillingen använder samma `-k`/TESTS och ordning samt kräver exit 0 för hela körningen. Claudes nya självtest och egen tidigare reproduktion verifieras separat.
- **D1-08:s konkreta motexempel fortsatt stängda:** ovillkorliga FileNotFoundError, RuntimeError och AssertionError vid setup ger MILJÖFEL genom egen `run_one`-injektion. Den generella garantin är fortfarande öppen enligt D1-10.
- **D1-01/D1-02/D1-05 fortsatt stängda inom tidigare gränser:** sex ursprungliga adapterfel avvisas; earliest_fill bevaras. Anroparens 2025-tillägg isoleras, internt tillägg avvisas före signals, ändrad intern markcell avvisas. Cap `10**5000` och motstridiga dubbletter ger ControlError.
- **D1-03/D1-06/D1-07 fortsatt stängda inom tidigare gränser:** alla 31 ordinarie fångster omkörs individuellt mot sparad matris. Delat förlopp återanvänder faktiskt mom7:s RunLog/slutstate; identitetsmutanten är separat. Jämförelsen innehåller inga körtider.
- **Fallback:** verkligt passerande och tomt riktat urval går vidare till hela D1-sviten och fångar main-s-mutanten. Neutral kommentar överlever samtliga 65 prov och blir MISSAD i den oförstörda miljön.
- **Oberoende referenser:** 3 288 Decimal-signaljämförelser med precision 70, alla åtta kombinationer, 1 096 cap<1-dagar och lika-prisfall. Tre fulla publika komponentförlopp jämförs mot eget kapitalfacit, vardera 6 576 staplar, 6 577 closepunkter och 1 096 dagsslut. Separat varierande Decimal-ledger räknar inträde, ökning, minskning med basis, utgång, återinträde och terminal P=100,5/M=100; C/q kontrolleras efter varje stapel och kapital vid varje close/dag. Årsskiftesfacit ger 2023-01-03 04:00 UTC. O9 kräver capminskning trots obrutet band.

## Revisionsaudit och integritet

[review.py](../research/audits/momentum-d1-fcbbb02/review.py) läser källorna med `git show` från fullständig fcbbb02 och laddar dem i separat modulrymd. Körningar och injektioner sker i temporära arbetsytor. [verification.json](../research/audits/momentum-d1-fcbbb02/verification.json) låser SHA-256, exakt diff-fillista, skyddskontroll, oberoende referenser, omkörda mutationer, fallback, gamla setupmotexempel, rättat D1-09 och öppet D1-10. `--check` reproducerar underlaget; PASS innebär inte godkännande.

Diff f1de702..fcbbb02 omfattar exakt fem filer: mutationsskript, mutations-JSON, D1-rapport, momentumstatus och genererad momentumvy. **Signal, control, ledger, funding, risk, marginal, event, bound, stats, tester, protokoll, register, gamla resultat, gamla audits och gamla granskningar är byte-oförändrade.** Exakt tillåten fillista och separat skyddad git-diff kontrolleras i auditen. Granskningsleveransen ändrar endast nytt auditunderlag, detta dokument och momentumstatus/vy.

## Körda kontroller

Interpreter för motor och audits: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest kördes från `engine/` med `-m pytest -p no:cacheprovider -o addopts= -q`.

- Momentum, `tests/test_momentum*.py`: **605 passerade**, exit 0.
- Hela motorsviten: **1 158 passerade**, exit 0; en joblib-varning om fysisk CPU-detektering.
- `python3 scripts/momentum-a1-oracles.py --check`: **PASS**, exit 0.
- `python3 scripts/momentum-d1-mutations.py --check`: **PASS**, exit 0; **31 FÅNGAD, 0 MISSAD, 1 EKVIVALENT, 0 EJ_TILLÄMPLIG**, med grön **65-provsbaslinje**. Självtestets tre ovillkorliga setupfel och det ordningsberoende setupfelet ger MILJÖFEL; verklig mutation ger FÅNGAD.
- Ny revisionsaudit genererad och därefter separat körd med `--check`: **PASS**, exit 0. Samtliga 31 sparade fångster, gamla motexempel, fallback och neutral överlevare omprövade. D1-09 ger MILJÖFEL; D1-10 ger tre falska fångster och sex färska omuterade kontrollkörningar fallerar som väntat. PASS reproducerar även det öppna fyndet och innebär inte godkännande.
- Samtliga **27 äldre** `research/audits/momentum-*/review.py --check`: **PASS**, exit 0, som historisk reproduktion. Gamla slutsatser skrivs inte om. Med den nya auditen passerar **28 av 28** momentum-audits.
- Alla **fyra** checklistgeneratorer (`render-fas2-checklist.py`, `render-fas3-checklist.py`, `render-h0016-checklist.py`, `render-momentum-checklist.py`) med `--check`: **PASS** före och efter statusändringen. Momentumvyn regenererad från statuskällan med `python3 scripts/render-momentum-checklist.py` och därefter kontrollerad med `--check`.
- `git diff --check f1de702 fcbbb02` och granskningsleveransens `git diff --check`: rena. HEAD är fortfarande exakt fcbbb02. Endast MOM-D01:s underlag/not och övergripande granskningsmetadata ändras i statuskällan; uppgiftsstatusar och alla andra uppgifter är oförändrade.

## Status och nästa steg

MOM-D01 förblir `in_progress`, utan nya done-markeringar. D1-09 stängs för sitt konkreta processlokala ordningsfel; D1-04:s bredare garanti kvarstår som D1-10. buy_and_hold, legacy, no_vol, blandningar och komponent-bound återstår. D1-Q01/Q02 avgörs inte här. Övriga D-punkter och tidigare avgränsade A/B/C-godkännanden ändras inte. Rättning och ny granskning av exakt revision krävs före godkännande; inget nytt uppdrag skrivs.

Enligt Edwins beslut 2026-11-14 heter momentumhypotesen **H-0026** på main, tidigare H-0017 på grenen; squeezen heter **H-0025**, tidigare H-0016. Hänvisning: `research/id-omnumrering.md` på origin/main i `3cd3c4c`. Protokollen uppges vara byte-identiska och N=17 behålls. Ingen nätverkskontroll av main har gjorts här. Grenens register, protokoll och gamla id ändras inte.

Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live utförd eller godkänd. H-0013 förblir REJECT. Inget committat eller pushat. Checklistan är en regenererad lokal ögonblicksbild.
