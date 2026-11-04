# Codex granskning av H-0017 D1-rättning, revision 4

Datum: 2026-11-04. Exakt revision **c0da8510f8e932b56bac9e56d4033bc46906009e**, diffbas **adad84cbf386982517d985552c5d334251afc5fd**. Gren `codex/momentum-d1-review`; HEAD, bas och ren arbetskopia verifierade före arbetet. Endast syntetiska minnesdata, ingen marknadshistorik eller nätverk.

**Beslut: EJ GODKÄND.** D1-06 och D1-07 stängs. D1-03:s återstående mutationsdel är verifierad. D1-04:s konkreta FileNotFoundError-fall är rättat, men garantin mot fångster från setupfel är fortfarande otillräcklig, preciserat som D1-08 nedan. MOM-D01 förblir `in_progress`; D1 ensam slutför inte uppgiften. A/B/C:s tidigare avgränsade godkännanden består.

Underlag: AGENTS.md, CLAUDE.md, metodgranskning, kontraktsutkast, fryst H-0017-protokoll, D1-uppdrag, tidigare D1-granskning/audit och den exakta revisionens källor, test, mutationsmatris och rapport.

## Fynd

### D1-08 [P2] – setupfel med andra undantagstyper räknas fortfarande som fångad mutation

`scripts/momentum-d1-mutations.py:194–200,241–246` bevarar JUnits `error`/`failure`, men använder inte denna skillnad för att kräva en körd testkropp. En svartlista över undantagsnamn avgör i stället om felet är miljöfel. `RuntimeError` och `AssertionError` från testuppsättningen blir därför FÅNGAD.

Den nya auditen kör en grön oförändrad baslinje och gör därefter bara en semantiskt neutral kommentarändring i källkopian. En separat autouse-fixtur kastar `RuntimeError("synthetic missing test resource")`. Pytest ger exit 1, `1 error`, JUnit `typ=error`, `orsak=RuntimeError`, och skriptet ger **FÅNGAD**. Samma prov med `AssertionError` ger också **FÅNGAD**. Ingen testkropp har körts och inget beteendefel har införts. FileNotFoundError i samma fixtur ger nu korrekt **MILJÖFEL**.

Klassningen måste skilja fel i uppsättning/nedstädning från verifierade beteendefel; att enbart lägga fler namn i svartlistan löser inte den reproducerade luckan. Bevara fas/orsak och säkerställ att ett setupfel utan beteendemutation inte kan bli FÅNGAD. Detta är den kvarstående delen av D1-04, inte ett påstående att revisionens 31 ordinarie fångster är miljöfel. Riktad körning ändrar inte problemet: den kan avslutas med FÅNGAD innan någon testkropp prövat mutanten.

## Stängda fynd och verifierade delar

- **D1-06 stängt:** körtider har tagits bort ur sammanfattningarna. Skriptets egen `--check` och den nya auditens separata omkörning reproducerar sparad matris utan tidsberoende jämförelse.
- **D1-07 stängt, D1-03 stängt inom D1:s verifieringskrav:** den nya mutanten kör mom7 en gång och låter alla tre komponenterna återanvända samma RunLog och slutstate via `dataclasses.replace(first, component=k)`. Detta delar faktiskt förloppets riskpeak, lås och funding-id; det är inte tre nystartade konton med fel namn. `test_components_differ_from_each_other_and_are_isolated` fångar de identiska kapitalförloppen. Identitetsmutanten finns kvar separat. Detta verifierar just denna state-/förloppsdelningsmutation, inte varje tänkbar delningsbugg.
- **D1-04 delvis stängt:** den tidigare konkreta FileNotFoundError-fixturen ger MILJÖFEL, både i självtestet och egen injektion genom `run_one`. Den bredare setupgarantin kvarstår som D1-08.
- **Riktat urval/fallback:** egen körning med ett verkligt passerande, orelaterat riktat prov går vidare till hela D1-sviten och fångar main-s-mutanten där. Ett tomt urval (pytest exit 5) gör samma sak. En neutral kommentarändring får MISSAD först efter samtliga 65 D1-prov. Ingen dold miss har påvisats i fallbacken. Falska fångster från setupfel återstår enligt D1-08.
- **D1-01/D1-02 fortsatt stängda:** samtliga sex gamla adaptermotexempel avvisas med ControlError; anroparens 2025-tillägg isoleras, internt 2025-tillägg avvisas före signals och ändrad intern markcell avvisas.
- **D1-05 fortsatt stängt:** `10**5000` i cap och motstridiga dubblettrader avvisas med utskrivbart ControlError.
- **Oberoende Decimal-facit:** 3 288 signaljämförelser vid precision 70, alla åtta komponentkombinationer, 1 096 cap<1-dagar samt lika-prisfall. Tre fulla konstanta exekveringsprisförlopp med eget kapitalfacit. Separat varierande ledger räknar från 100 000 genom inträde, ökning, minskning med basis, utgång, återinträde och terminal P=100,5/M=100; C/q jämförs efter alla 6 576 staplar samt kapital vid alla 6 577 closepunkter och 1 096 dagsslut. Motorresultat matar inte facit. Årsskiftesfacit anger första permanenta trigger 2023-01-03 04:00 UTC; årsresetmutanten fångas av det avsedda provet.

## Revisionsaudit och integritet

[review.py](../research/audits/momentum-d1-c0da851/review.py) läser källorna med `git show` från full c0da851 och laddar dem i separat modulrymd. Körningar och felinjektion sker i temporära källkopior med syntetiska data. [verification.json](../research/audits/momentum-d1-c0da851/verification.json) låser källhashar, exakt diff-fillista, skyddskontroll, gamla motexempel, Decimal-facit, 31 individuellt omkörda fångster (samtliga JUnit `failure`, inget setup-`error`), fallbackprov, neutral överlevare och tre egna setupfel. `--check` räknar om underlaget utan flyktiga körtider. PASS betyder reproducerad granskning, inte implementationsgodkännande. Inga äldre audits ändras.

Diff adad84c..c0da851 omfattar exakt sex filer: mutationsskript, mutations-JSON, D1-rapport, momentumstatus, genererad vy och ett extra assert i O9-testet före läsning av avsiktens typ. Assertet gör det saknade dagsstoppet till ett uttryckligt testfel. **Signal, control, ledger, funding, risk, marginal, event, bound, stats, frysta protokoll, register, gamla resultat och gamla audits är byte-oförändrade.** Även äldre granskningsdokument är orörda. Exakt tillåten fillista och skyddad git-diff verifieras i auditen.

## Körda kontroller

Interpreter för motorn och audits: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest kördes från `engine/`, med `-m pytest -p no:cacheprovider -q`; antal verifierades även med separat insamling och `-o addopts=`. Övriga skript/checklistor kördes med python3.

- Momentum: **605 passerade**, exit 0. Insamling: 605.
- Hela motorn: **1 158 passerade**, exit 0. Insamling: 1 158. En joblib-varning om fysisk CPU-detektering, inga testfel.
- `python3 scripts/momentum-a1-oracles.py --check`: PASS.
- Samtliga **25 äldre** `research/audits/momentum-*/review.py --check`: PASS som historisk reproduktion. Inga gamla slutsatser skrivs om.
- `python3 scripts/momentum-d1-mutations.py --check`: **PASS**, exit 0: **31 FÅNGAD, 0 MISSAD, 1 EKVIVALENT, 0 EJ_TILLÄMPLIG**. Baslinje **65 passed**. Självtest: MILJÖFEL (FileNotFoundError).
- Ny revisionsaudit genererad och därefter körd med `--check`: **PASS**, exit 0. Alla 31 fångster reproducerade individuellt; två verkliga fallbackprov och en neutral överlevare verifierade. Tre egna setupfel omkörda. Totalt **26 av 26 momentum-audits** passerar. Det gröna auditutfallet reproducerar även D1-08 och innebär därför inget implementationsgodkännande.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändringen. Momentumvyn regenererad med `python3 scripts/render-momentum-checklist.py` och kontrollerad med `--check`. Alla fyra passerar även efter statusändringen.
- `git diff --check adad84c c0da851` och granskningsleveransens `git diff --check`: rena.

## Status och nästa steg

MOM-D01 förblir `in_progress`; inga nya done-markeringar. D1-06/D1-07 och D1-03:s återstående mutationsdel stängs. D1-04:s konkreta miljöfel är åtgärdat, men setupklassningen behöver rättas enligt D1-08 före godkännande. Tidigare underlag bevaras med daterad korrigering till denna granskning. Övriga uppgifter och A/B/C:s avgränsade godkännanden ändras inte.

Rättning och ny granskning av exakt revision krävs. Detta är inget nytt uppdrag. buy_and_hold, legacy, no_vol, blandningar och komponent-bound återstår; D1-Q01/Q02 avgörs inte här. Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live har utförts eller godkänts. H-0013 förblir REJECT och H-0016 oförändrat. Inget har committats eller pushats. Checklistan är en regenererad lokal ögonblicksbild.
