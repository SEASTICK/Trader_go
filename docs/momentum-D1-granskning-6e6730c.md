# Codex granskning av H-0017 leverans D1

Datum: 2026-11-04. Exakt granskad revision: **6e6730cc950b880aa0aa247ec29892bb767a2f4d**, diffbas **fc02e1d2bd4384d5dffcdbdd7b6d4b7129c07493**. Gren `codex/momentum-d1-review`. HEAD, full diffbas och ren arbetskopia kontrollerades före ändring. Endast syntetiska minnesdata; inga nätverksanrop.

**Beslut: EJ GODKÄND.** D1-01–D1-03 är öppna. MOM-D01 förblir `in_progress`; D1 skulle inte ensamt slutföra kontrollmatrisen. Tidigare avgränsade A/B/C-godkännanden ändras inte.

Underlag: AGENTS.md, CLAUDE.md, frysta protokollets §4–§8, §11, D07–D21 och oraklen inklusive O2/O9/O12, D1-uppdraget, Claudes D1-rapport, revisionsstatus, implementation och tester. Claudes rapporterade verifiering har behandlats som påståenden att kontrollera.

## Fynd

### D1-01 [P2] – signaladaptern tappar tidsproveniens och accepterar inkonsekventa källrader

`engine/traderlab/momentum_control.py:52–93`. Uppdragets punkt 1 kräver att `earliest_fill` bevaras. Fältet finns varken i ComponentSignal eller i sparade beslut; en ändrad earliest_fill ignoreras helt. Adaptern kontrollerar kolumnlista, version och endast den valda delsignalens binära värde. Den verifierar inte källdag/tidszon/raster, decision_time, main-medelvärde, övriga delsignaler, vol/cap-samband eller strikt boolesk available.

Den revisionslåsta auditen ändrar ett fält åt gången i en riktig signals-rad: `s=.123`, `available='False'`, earliest_fill en dag för sent, decision_time på källdagen, `s14=.25` i mom7-adaptern samt `vol=NaN`. Alla sex accepteras; strängen `'False'` blir tillgänglig genom `bool(...)`. earliest_fill försvinner. ComponentSignal kan dessutom konstrueras direkt utan validering, inklusive godtycklig adapterversion. En senare SignalInput-validering kan inte återskapa eller verifiera borttagen källproveniens.

Den vanliga run_component-vägen använder intern signals() och reproducerar korrekta rader i de giltiga proven. Fyndet gäller det levererade publika adapterkontraktet och spårbarheten, inte ett påstående om att normal signalberäkning alltid ger fel. Rättningen behöver bevara tidsfältet och avvisa inkonsekvent/otillåten indata med utskrivbara domänfel; obligatoriska negativa adapterprov saknas.

### D1-02 [P1] – Market skyddar inte underlaget vid körning; 2025 kan nå signalberäkningen

`engine/traderlab/momentum_control.py:96–153, 173–176`. `frozen=True` fryser referenserna, men kontrakts- och marktabellerna är samma muterbara DataFrames som anroparen äger. run_component kontrollerar bara isinstance och återvaliderar inte underlaget innan signals().

Reproduktion: skapa giltigt Market; lägg därefter till en syntetisk kontraktsrad för 2025-01-01 i den ursprungliga tabellen; anropa run_component. Auditen instrumenterar den revisionsladdade signalingången och visar att tabellen med 2025-01-01 skickas dit. Provet avbryter där med en lokal sentinel innan signalberäkningens kropp: det verifierar gränsöverträdelsen utan att beräkna på 2025-raden. Konstruktörens 2025-kontroll körs inte igen. Detsamma gör att tidigare kontrollerad kalender, bool-/prisvalidering och gemensamt jämförelseunderlag kan ändras mellan kontoanrop.

Det bryter uppdragets krav på 2025-avvisning före beräkning och oföränderligt jämförelseunderlag. Köringången behöver säkerställa att det faktiska underlaget är validerat och inte kan ändras bakom valideringen; enbart en fryst dataklass räcker inte. Ingen verklig historik har använts för reproduktionen.

### D1-03 [P2] – obligatoriska komponentprov och redovisning av felprov är ofullständiga

Hela `engine/tests/test_momentum_control.py` är granskad. Dess 26 tester ger inte uppdragets obligatoriska täckning:

- Inga komponentintegrerade O5/O5b/O16-tabeller för A/B vid inträde, minskning och utgång med T, T±30s och T±1ms, första öppning, midnatt och terminal, med ordnade faser och separat E_trade/E_post-facit.
- Inga integrerade O6/O14/O15-prov, permanent stopp över flera dygn eller exakt 0,02/−2 %/−15 % med angränsande representerbara floatvärden. O9:s dagsstopp täcker bara ett snitt.
- Inga komponentfall för gap-/intrastapellikvidation i båda mmr, negativa prövningsvärden, blandade fundingtecken, unresolved/absorbed, liquidation_adjustment och absorberande noll över midnatt till terminal.
- Inget handräknat komponentförlopp med ökningar/minskningar och terminal där P≠M. Fullhorisontstestet kontrollerar längder och normalmålvikt, men inte detta oberoende beloppsfacit.
- Inte alla åtta scenarioetiketter; L1/L2 jämförs bara i B/0,005 och bara på dagskapital, inte hela ekonomiska spåret. Isoleringsprovet jämför separatanrop med samlingsanrop, men ändrar inte ett annat kontos signal/risk och prövar inte egna risklås.
- Flera obligatoriska negativa prov saknas: adapterradernas dag/tidszon/version/available/koherens, 10**5000, overflow från ändliga argument, dubbletter och fullständig fel-/mutationskontroll. De konkreta adapter- och Market-hålen ovan passerar testerna.

Den oförändrade motorns omfattande äldre tester fortsätter att ge värdefullt modulunderlag, men ersätter inte de uttryckligen beställda proven genom den nya kompositionen. Rapportens ”14 av 14” felprov har ingen reproducerbar mutationsmatris i leveransen med varje föreskrivet fel klassat fångat/missat/bevisat ekvivalent. Det räknas inte som egen verifiering. Den nya auditen kompletterar några facit och reproducerar två kodfynd; den fyller inte automatiskt alla luckor i Claudes leverans.

## O9-avvikelsen

**Claudes tolkning är korrekt.** Protokollets D06 och §7 kräver minskning vid w_current > cap oavsett band. Oraklets `mom7_band=false` betyder bara att 2 pp-bandet inte bryts. Vid vikt cirka 0,90825688 och cap 0,9 är capbrott sant; en capavsikt till 0,9 är riktig, inte hold. Main har separat bandbrott mot 0,3. Uppdragets formulering ”hold” var felaktig. Den ändrar varken protokollet eller oraklet och ska inte införas i implementationen. Nedgångsfallet 97,7 och fullkapitalets homogenitet mot tredjedelsfallet passerar i Claudes test. Ingen new_mix godkänns här.

## Verifierade delar och audit

[review.py](../research/audits/momentum-d1-6e6730c/review.py) läser produktionskällor, test, protokoll, register, uppdrag, orakel, rapport och revisionsstatus med `git show` från fullständig 6e6730c. Ingen arbetskopieimport av produktionsmoduler används. [verification.json](../research/audits/momentum-d1-6e6730c/verification.json) innehåller SHA-256, exakt diff-fillista, Decimal-resultat och reproducerade öppna fynd. `--check` räknar om och jämför hela underlaget; PASS betyder reproducerad granskning, inte godkänd kod.

- **3 288 signaljämförelser**, alla åtta komponentkombinationer, 1 096 källdagar med cap<1. Decimal med precision 70 räknar själv kalenderlagsavkastning, 60 avkastningar, ddof=1-vol, cap och komponentmål. Separat lika-prisfall ger noll i alla tre horisonter.
- **Tre fulla publika förlopp**, ett per komponent: vardera 6 576 staplar, 6 577 closepunkter och 1 096 kalenderdagar, utan restore eller privata fixturer. Syntetisk positiv trend med varierande avkastning ger cap=1; separat konstant exekverings-/markpris ger ett genomräknat inträde och terminalutträde. Varje close- och dagkapital jämförs med Decimal, inklusive 100 000 före kostnad. O2:s inträdes-q är 998,40255591054313099 och terminalkapitalet 99 680,5111821086262 efter två kostnader. Dessa enkla referensförlopp påstås inte täcka risk-/fundingmatrisen ovan.
- Koden väljer namngiven s7/s14/s28, skiljer s_main från s_used och märker käll-/adapterversion. Normal run_component använder publik EngineState.start/process_bar/RunLog och håller ihop hela horisonten utan delkontoskalning. RunLog behåller event-, close- och dagspunkter och de godkända motorversionerna.
- Konton skapas med egna state-objekt och komponent/L1–L2-nycklar. Eventmotorns scenarioidentitet bär A/B och mmr; legacy-ordningen ingår i account_key. Ingen gynnsam scenarioväljare eller deduplicering finns. L1/L2:s hela grid är dock inte verifierat av D1-testerna.
- Vid direkt konstruktion av ofullständigt Market och vid otillgänglig intern signal avvisas underlaget utan platt fallback. Inga fil-/nät-/jobbingångar, statistikmått, ekonomiskt beslut eller komponent-bound har lagts till.

## Diff och kontroller

Diffen fc02e1d..6e6730c innehåller exakt kontrollmodulen, dess testfil, Claudes rapport, momentumstatus och genererad momentumvy. Godkända signal/ledger/funding/risk/margin/event/bound samt tidigare tester är oförändrade. Exakt fillista och separat skyddskontroll visar att fryst protokoll, register, gamla resultat och gamla audits är orörda. Tidigare godkännanden består inom sina dokumenterade gränser; D1:s nya kontrakt godkänns inte av detta.

Interpreter för pytest och audits: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest från engine/ med `-m pytest -p no:cacheprovider`.

- Momentumsviten `tests/test_momentum*.py`: **566 passerade**, exit 0, 33,94 s; därav 26 kontrolltester.
- Hela motorsviten: **1 119 passerade**, exit 0, 129,13 s; en joblib-varning om fysisk CPU-detektering, inga testfel.
- A1-oraklet med `--check`: PASS.
- Samtliga **23** `research/audits/momentum-*/review.py --check`: PASS, inklusive 22 oförändrade äldre audits och den nya D1-auditen. Äldre PASS reproducerar respektive historiskt beslut och är inte nya godkännanden.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändring. Momentumvyn regenererad och kontrollerad igen efter uppdateringen: PASS.
- `git diff --check fc02e1d HEAD` och granskningsleveransens `git diff --check`: rena.

## Status och nästa steg

MOM-D01 är fortsatt `in_progress`, med D1-01–D1-03 öppna och revisionslåst underlag. Övriga D-punkter är todo; A/B/C-status ändras inte. D1-Q01 (komponenternas bound) och D1-Q02 (senare no_vol-cap) är fortfarande utanför denna implementation och inte avgjorda här. Lokal checklistvy regenereras från JSON och är en ögonblicksbild.

Rättning och kompletterande syntetisk verifiering av de öppna fynden krävs före ny oberoende granskning av exakt revision. Detta dokument är inget nytt uppdrag. Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live är godkänd eller utförd. H-0013 förblir REJECT och H-0016 är oförändrat. Inget har committats eller pushats.
