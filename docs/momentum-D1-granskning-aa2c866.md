# Codex granskning av H-0017 D1-rättning, revision 3

Datum: 2026-11-04. Exakt revision **aa2c8669680b017d9d9a98e46d1f9a0cb1a4fb9d**, diffbas **ab79f2a5f8c63456075f2e1c5d22a28f3c4e1f19**. Gren `codex/momentum-d1-review`; HEAD, bas och ren arbetskopia verifierade före arbetet. Endast syntetiska minnesdata, ingen marknadshistorik eller nätverk.

**Beslut: EJ GODKÄND.** Adapterrättningen D1-05 och det saknade oberoende beloppsförloppet är verifierade. D1-03 kvarstår avgränsat till den föreskrivna mutationen av delat risk-/fundingstate. D1-04 är delvis rättat men miljöfel i testuppsättning kan fortfarande räknas som fångst. Nytt D1-06 gäller en icke reproducerbar `--check`; D1-07 preciserar den kvarstående state-mutationen. MOM-D01 förblir `in_progress`; D1 ensam slutför inte uppgiften. A/B/C:s tidigare avgränsade godkännanden består.

Underlag: AGENTS.md, CLAUDE.md, metodgranskning, kontraktsutkast, fryst H-0017-protokoll, D1-uppdrag, tidigare D1-granskning/audit samt den exakta revisionens källor, test, mutationsmatris och rapport.

## Fynd

### D1-06 [P2] – --check jämför körningarnas exakta tidsåtgång

`scripts/momentum-d1-mutations.py:125,136,149–151,164–175` sparar hela pytestsammanfattningen, inklusive exempelvis `65 passed in 55.85s`, och jämför sedan hela JSON-texten bytevis. Även varje mutants körtid ingår. Identiska antal, utfall och fallerande test ger därför FAIL när tiden varierar. Dessa flyktiga mätvärden behöver skiljas från det reproducerbara verifieringsunderlaget. Den egna körningens faktiska utfall redovisas nedan.

### D1-07 [P2] – mutanten för delat state muterar bara kontoidentitet

`scripts/momentum-d1-mutations.py:90–91` ersätter `EngineState.start(scenario)` med ett nytt `EngineState.start(Scenario("mom7/" + legacy_order, ...))` vid varje anrop. Varje konto får fortfarande ett nytt eget konto-, risk-, funding- och marginalstate. Mutanten prövar en felaktig etikett för mom14/mom28, inte överföring eller delning av peak, day_start, lock_day, permanent eller behandlade funding-id. Den fångas av `test_full_horizon_per_component`, men detta ersätter inte uppdragets uttryckliga stateisolationsmutation. Identitetsprovet är nyttigt som identitetsprov; inget faktiskt stateisoleringsfel i produktionskoden har påvisats här. D1-03 kan inte stängas fullt ut med detta underlag.

### D1-04 [P2], kvarstående del – miljöfel efter insamling kan fortfarande bli FÅNGAD

Det saknade oraklet kopieras nu korrekt, oförändrad baslinje körs och insamlingsfel skiljs från körda prov. Revision 2:s 26 ogiltiga fångster återupprättas inte av detta. Den återstående klassningen på rad 126 och 150 accepterar både `FAILED` och `ERROR` utan orsakskontroll.

Den nya revisionsauditen kör först en grön baslinje och injicerar därefter ett separat autouse-fixturfel i den temporära testmiljön: `FileNotFoundError("synthetic missing test resource")`. Ingen testkropp hinner pröva mutantens beteende. Skriptet returnerar ändå **FÅNGAD**, med `1 error`. Detta är ett konkret miljöfel vid setup, inte ett insamlingsfel eller en verifierad beteendefångst. Bevara orsaksunderlag och skilj sådana fel från verklig mutationseffekt. Detta betyder inte att alla revision 3:s ordinarie fångster är miljöfel.

## Stängda fynd och verifierade delar

- **D1-01:** de sex ursprungliga motexemplen avvisas åter med ControlError: s=.123, available='False', sen earliest_fill, decision_time på källdagen, s14=.25 och NaN-vol.
- **D1-02:** anroparens 2025-tillägg ändrar inte Market; internt 2025-tillägg avvisas före signals. Ändrad intern markcell avvisas. Ingen utvidgad garanti om samtidighet eller kryptografisk byteidentitet görs.
- **D1-05 stängt:** cap `10**5000` avvisas med utskrivbart ControlError före aritmetik; två individuellt koherenta men motstridiga dubblettrader avvisas. Index kräver UTC, unikhet och ordning. Produktionens ändring är lokal till adaptern.
- **D1-03:s beloppsdel stängd:** det nya testets köp-/säljreferenser börjar från 100 000 och räknar C/q genom inträde, ökning, minskning med basis, utgång, återinträde och terminal P=100,5/M=100. Inga motorresultat används som indata till facitet. Testet kontrollerar alla dagsslut och closepunkter efter återinträdet; det påstår i källkommentaren mer om tidiga closepunkter än det faktiskt kontrollerar. Den nya auditen kompletterar med egen Decimal-ledger och jämför C/q efter varje stapel samt **samtliga 6 577 closepunkter och 1 096 dagsslut**.
- **Årsskifte verifierat:** eget Decimal-facit ger första permanenta trigger **2023-01-03 04:00 UTC**, efter uppbyggd decemberpeak och 11 prisfall à 1,5 %. Produktionsresultat används inte i facitet. Årsresetmutanten behåller peak≥initial och ändrar faktiskt risksemantiken; det riktade omprovet fångas av just årsskiftestestet. Detta är en meningsfull mutation.
- **3 288 Decimal-signaljämförelser**, precision 70, alla åtta kombinationer och 1 096 dagar med cap<1; dessutom lika-prisfall och tre fulla konstanta exekveringsprisförlopp med oberoende kapitalfacit.
- Kalender-/observationsmutationen är ekvivalent på Markets obligatoriska fullständiga raster. Det är inte en generell ekvivalens på ofullständiga signaldata.

## Revisionsaudit och integritet

[review.py](../research/audits/momentum-d1-aa2c866/review.py) läser källorna med `git show` från full aa2c866, laddar dem i separat modulrymd och kör riktade test/mutationer i en temporär källkopia. [verification.json](../research/audits/momentum-d1-aa2c866/verification.json) låser källhashar, diff-fillista, skyddskontroll, tidigare motexempel, Decimal-facit och egen miljöfelinjektion. `--check` räknar om underlaget och jämför utan flyktiga körtider. Auditen omprövar dessutom samtliga 30 mutanter en och en mot respektive angivet fallerande test och kontrollerar faktisk pytestutdata: exit 1, namngivet FAILED, ingen insamlingskrasch och inget saknat modul-/filunderlag. Samtliga 30 ger verkliga testfel; detta gör inte identitetsmutanten till en stateisolationsmutation och löser inte den separata setupfelklassningen. PASS betyder reproducerad granskning, inte implementationsgodkännande.

Diff ab79f2a..aa2c866 omfattar exakt sju filer: momentum_control, integrationstestet, mutationsskriptet, mutations-JSON, Claudes D1-rapport, momentumstatus och genererad vy. **Signal, ledger, funding, risk, marginal, event, bound, stats, protokoll, register, gamla resultat och gamla audits är byte-oförändrade.** Även äldre granskningsdokument är orörda. Detta verifieras genom exakt fillista och skyddad git-diff i auditen.

## Körda kontroller

Interpreter för motorn och audits: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest kördes från `engine/`, med `-m pytest -p no:cacheprovider -q`; testantal kontrollerades med separat insamling och `-o addopts=`. Skript/checklistor kördes med python3.

- Momentum: **605 passerade**, exit 0, varav **65 D1-prov** i matrisens baslinje. Insamling: 605.
- Hela motorn: **1 158 passerade**, exit 0. Insamling: 1 158. En joblib-varning om fysisk CPU-detektering, inga testfel.
- `python3 scripts/momentum-a1-oracles.py --check`: PASS.
- Samtliga **24 äldre** `research/audits/momentum-*/review.py --check`: PASS som historisk reproduktion; inga gamla slutsatser skrivs om. Ny audit med 30 individuella mutantomprov: PASS med `--check`. Totalt **25 av 25 audits** passerade.
- `python3 scripts/momentum-d1-mutations.py --check`: **FAIL, exit 1**: `FAIL: felprovsmatrisen skiljer sig från docs/momentum-D1-mutationer.json`. Baslinjen är `65 passed in 62.93s (0:01:02)` (sparat `65 passed in 55.85s`). **30 FÅNGAD, 0 MISSAD, 1 EKVIVALENT, 0 EJ_TILLÄMPLIG**. Antal, klassning, första fallerande test och samtliga övriga fält är identiska efter att enbart tidsåtgången (inklusive pytests parentes med minuter/sekunder) strukits ur sammanfattningarna. Felet i `--check` är därmed reproducerat (D1-06).
- Egen separat setupfelinjektion: ett resursfel före testkroppen blir felaktigt FÅNGAD, reproducerat i den nya auditen.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före och efter statusändringen. Momentumvyn regenererad med `python3 scripts/render-momentum-checklist.py`.
- `git diff --check ab79f2a aa2c866` och granskningsleveransens `git diff --check`: rena.

## Status och nästa steg

MOM-D01 är fortsatt `in_progress`; inga nya done-markeringar. D1-03 kvarstår för delat state, D1-04 för setup-/miljöklassning, D1-06/D1-07 är öppna. D1-05 är stängt. Statusens tidigare underlag bevaras med daterad korrigering till den nya granskningen. Övriga uppgifter och tidigare avgränsade A/B/C-godkännanden ändras inte.

Rättning och ny granskning av exakt revision krävs. Detta är inget nytt uppdrag. buy_and_hold, legacy, no_vol, blandningar och komponent-bound återstår; D1-Q01/Q02 avgörs inte här. Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live har utförts eller godkänts. H-0013 förblir REJECT och H-0016 oförändrat. Inget har committats eller pushats. Checklistan är en regenererad lokal ögonblicksbild.
