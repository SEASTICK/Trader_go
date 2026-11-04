# Codex granskning av H-0017 leverans C6

Datum: 2026-11-04. Exakt granskad revision: **`8e27c5f0c74a7f10687695e1b8e4bd35dc078e61`**. Diffbas: **`5f5de0f8fa39f34e9353e8d90ca4c0ddff5aae4f`**. Gren: `codex/momentum-c6-review`. HEAD, gren och diffbas kontrollerades före läsning och ändringar; arbetskopian var ren. Koddiffen har även jämförts med C5:s godkända `43b2a4bd26149bb04d77e1ef94113b2b684719a5`. Endast syntetiska data.

**C6 är EJ GODKÄND: C6-02 [P2] behöver rättas. MOM-C04 förblir in_progress.** C6-01 är den redan avgjorda kontraktsfrågan och återöppnas inte. Edwins H1/I1/G1/P1 stämmer med den granskade beräkningen. Inga andra nya fynd har identifierats inom avgränsningen.

Granskningen utgår från AGENTS.md, CLAUDE.md, [C6-uppdraget](claude-uppdrag-momentum-C6.md), [frysta protokollet](../research/h0017-protokoll.md), särskilt §9, §10.1–10.2, §13.1–13.2, D21 och O7, [Edwins beslut](momentum-C6-01-edwins-beslut.md) och de fyra C6-01-granskningarna ([underlag](momentum-C6-01-granskning-underlag.md), [beslut](momentum-C6-01-granskning-beslut.md), [tillägg 2](momentum-C6-01-granskning-beslut-2.md), [tillägg 3](momentum-C6-01-granskning-beslut-3.md)). Claudes [rapport](momentum-bound-C6.md) och status har lästs som granskningsobjekt, inte använts som facit.

## Fynd

**C6-02 [P2] – faktisk close får öppningstid i boundspåret.** I `engine/traderlab/momentum_bound.py:126` skickas `T` till close-punktens `time`. Kapitalet använder däremot `mark_close` och slutkontot efter samtliga bokförda mellanevent. Vid en stapel med öppning 08:00 anger spåret alltså 08:00 för ett closekapital som blir känt 12:00. Med mellanfunding ligger den angivna tiden dessutom före de betalningar som kapitalet redan innehåller. `bar_open` bär redan källstapelns identitet; `time` får inte ge samma öppning en andra roll som close-tid.

C5:s nästa `BarResult.close_point` anger korrekt `(källstapel T, tid känd T+4h, E_close)`. Den nya boundserien ger således två olika tider för samma faktiska close. Detta bryter uppdragets spårbarhet och åtskillnaden mellan källa, faktisk fas och hypotetiska punkter enligt tillämpliga §15-delar. Det påverkar inte det aktuella numeriska minimumet, eftersom folden använder punktordningen, men det felmärker när uppgiften kan vara känd. Granskningen omfattar även tidsproveniens; korrekt slutkapital räcker inte.

Den nya revisionslåsta auditen reproducerar felet i fyra sekventiella 15-stapelsförlopp och jämför med C5:s nästa close-punkt. Exempel: sista källstapel 2022-01-03 08:00, faktisk `close.time` 08:00, väntad känd-tid 12:00. Befintliga C6-tester kontrollerar inte close-tiden och passerar därför. Close ska ange nästa gräns som faktisk close-/känd-tid med fortsatt källstapel T; terminalen ska fortsatt vara terminalens öppning och high/low fortsatt ha okänd tid. En regression behöver uttryckligen skilja dessa tider och omfatta mellanfunding. Ingen implementations- eller testfil har ändrats av Codex.

## Verifierade delar

Den fristående [auditen](../research/audits/momentum-c6-8e27c5f/review.py) laddar samtliga sju momentumkällor och `stats` med `git show` från fullständig 8e27c5f till ett separat minnespaket. Den läser även revisionslåsta kontrakts-/orakel-/statuskällor, sparar SHA-256 och kontrollerar exakt diff-fillista. [verification.json](../research/audits/momentum-c6-8e27c5f/verification.json) innehåller oberoende Decimal-referenser, precision 70, och reproducerat fynd. `--check` kör om kontrollen och jämför hela underlaget; PASS betyder reproducerbar granskning, inte C6-godkännande.

- **107 punktsekvenser, 581 punkter:** varje fas och kapital jämförs med separat beräknat facit. Sekventiella BoundPoint-objekt kontrolleras också för varje peak, drawdown och ackumulerat minimum. Referensen härleder inträdes-q från självfinansieringsidentiteten; den tar inte boundens egna kapitalvärden som facit.
- **O7:** open/trade/post 100 000, high 106 000, low 97 500, close 100 500. Peak 106 000 ger −8 500/106 000; separat close-DD är −4 500/105 000. Lokal fixtur med tidigare peak är inte en full logg från start.
- **32 funding-/marginalfall:** A/B × båda mmr × båda teckenordningarna × två low × med/utan samtidig funding; 24 träffar och 8 utan träff. Flera betalningar, krediter och nollränta. C_post, C_high, C_low, q_open, faktisk funding_net och booked-antal stämmer med Decimal. High krediteras endast hypotetiskt, low debiteras endast hypotetiskt; faktisk close följer nettoledgern. Vid träff bokförs ingen mellanfunding.
- **H1/I1/P1 och G1:** high före low, rått negativt kapital kvar, sedan likvidationsnolla. Två separata gapfall i A/B verifierar rått −50 000 och A:s −50 550 efter funding, utan trade/post/extremer efter känd träff. Tio efterföljande absorberande staplar har endast noll. Peak och minimum behålls i folden; ingen 0/0 eller klippning införs. Reservationen om att högre peak gör negativ trough mindre negativ består.
- **Fyra verkliga sekventiella förlopp:** A/B × båda kostnaderna, 15 staplar vardera över två midnätter, start före första kostnad, ingen peakreset, bevarat tidigare minimum och oförändrat prefix. Dubblett och replace avvisas. BoundLog delegerar dessutom hela fortsättnings-/terminalkontrollen till den granskade RunLog-kedjan; inga nya restore-vägar tillkommer.
- **60 egna ickeinterferenspar:** samma ingående state och faktiska close men ändrade extremer ger identiska utgående state, riskbeslut, dags-/closepunkter och eventspår utanför marginalunderlaget. Boundpunkterna skiljer sig. Kodgranskningen visar också att ingen handelsmodul importerar eller anropar bounden; den läser färdiga resultat och återkopplar inte peak eller 20 %-magnitud till stopp/fill/marginal.
- **Två terminalfall:** A/B mot separat Decimal med basis och stängningskostnad. Ordningen är open, trade, post, terminal; ingen gammal exponering återkommer som high/low. Terminalkapitalet är 97 975,336 respektive 97 979,136. Den fulla platta syntetiska kalendern kontrolleras även av C6-testet: 6 576 staplar, 6 577 closepunkter, 1 096 dagar och 39 455 boundpunkter, noll drawdown.

**Sex egna avsiktliga mutationer fångade, noll missade:** fel tecken på high-kredit, fel tecken på low-betalning, borttappat löpande minimum, borttappad tidigare peak, klippt negativt E och borttagen terminalpunkt. Mutationerna sker endast i källsträngar laddade från revisionen. Claudes rapporterade mutationsantal räknas inte som egna kontroller. Befintliga tester har dessutom granskats för bland annat B:s E_trade/E_post, partialförsäljningens q, O6, gränsen 20 %, prefix, kedjevakter och absorberande nollor. Den nya auditen gör inget anspråk på att verifiera legacy, short, hela gridet eller boolesk slutprövning.

## BarResult och tidigare godkännanden

Ändringen i `momentum_event.py` består exakt av det nya obligatoriska fältet `bar: Bar` och `bar=bar` vid utfärdandet. Bar är fryst och validerad före behandling; BarResult har kvar samma privata konstruktionsgrind. Inga kapital-, funding-, risk-, marginal-, close- eller dagsövergångar har ändrats. Detta är en motiverad metadatautökning för att tillgängliggöra mark-OHLC, inte en ny handelsväg. Den ändrar dataklassens form, men alla interna konstruktioner är uppdaterade och direkt publik konstruktion är redan förbjuden.

**MOM-C03/C05 återbekräftas på exakt 8e27c5f inom C5:s huvudmodellgränser.** Samtliga 105 oförändrade eventtester passerar på den nya revisionen. C6-02 finns i boundens tidsmetadata och återöppnar inte deras eventsemantik. A/B och C01/C02:s komponentgodkännanden består.

## Körda kontroller och integritet

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest kördes från `engine/` med `-m pytest -p no:cacheprovider`.

- `tests/test_momentum*.py`: **539 passerade**, exit 0, 7,72 s; därav 32 boundtester och 105 eventtester.
- Hela motorsviten: **1 092 passerade**, exit 0, 102,03 s. En joblib-varning om fysisk CPU-detektering, inga testfel.
- `scripts/momentum-a1-oracles.py --check`: PASS.
- Samtliga **20 äldre** `research/audits/momentum-*/review.py --check`: PASS. Historiska audits reproducerar sina egna revisioner och eventuella gamla fynd; detta är inte i sig ett bevis för C6.
- Ny C6-audit och `--check`: PASS med C6-02 reproducerat; samtliga **21** audits är därmed kontrollerade.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändringen. Momentumvyn regenererad från den uppdaterade statuskällan och kontrollerad igen. Övriga tre statuskällor är orörda.
- `git diff --check 5f5de0f 8e27c5f` och granskningsleveransens `git diff --check`: rena.

Diffen från 5f5de0f har exakt sex filer: boundmodul, boundtester, eventmodul, Claudes rapport, momentumstatus och momentumvy. Koddiffen mot 43b2a4b har också endast de två nya kod-/testfilerna samt det additiva eventfältet. Signal, ledger, funding, risk, marginal, stats, deras gamla tester, fryst protokoll, register och gamla resultat är byte-oförändrade. Befintliga audits är byte-oförändrade mot granskningsbasen 5f5de0f. C5:s egen audit tillkom efter implementationsrevisionen 43b2a4b och är därför korrekt jämförd mot granskningsbasen; den har inte redigerats här.

## Status och nästa steg

**MOM-C04 förblir in_progress; checklistan är 14/40.** Boundens aritmetik är verifierad inom ovanstående syntetiska omfattning, men tidsproveniensen hindrar C6-godkännande. C6-02 ska rättas och exakt rättningsrevision granskas innan återstående C6-del kan stängas. Full boolesk C6-/20 %-slutprövning tillhör D; ingen sådan motor har godkänts här. Leverans D tilldelas inte genom denna granskning och inget nytt uppdrag skrivs.

Denna leverans skapar endast granskningsdokumentet och den nya auditens två filer samt uppdaterar momentumstatus och genererad momentumvy. Ingen marknadshistorik, nätverksåtkomst, registrering, merge, driftsättning, release eller paper/live. H-0013 förblir REJECT; H-0016 är oförändrat. Inget har committats eller pushats. Checklistans chatbeskrivning är en ögonblicksbild av regenererad lokal status.
