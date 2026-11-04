# Codex granskning av H-0017 D1-rättning

Datum: 2026-11-04. Exakt revision: **720e1f882ddc62f7e3a166e5cec09ac9e9ab754a**, diffbas **fa8980330aca325cc4d59b6f93f3fbb6e99c5ac1**. Gren `codex/momentum-d1-review`, HEAD och diffbas verifierade; arbetskopian var ren före granskningen. Endast syntetiska minnesdata, inga nätverksanrop eller marknadshistorik.

**Beslut: EJ GODKÄND.** De sex ursprungliga D1-01-motexemplen och D1-02:s 2025-motexempel är åtgärdade. D1-03 är inte stängt: felprovsmatrisens fångster är ogiltiga och det oberoende beloppsfacitet är fortfarande ofullständigt. Nya fynd D1-04 och D1-05 nedan. MOM-D01 förblir `in_progress`; D1 ensam kan inte slutföra uppgiften. Tidigare avgränsade A/B/C-godkännanden består.

Underlag: AGENTS.md, CLAUDE.md, metodgranskning, kontraktsutkast, fryst H-0017-protokoll, D1-uppdrag, föregående granskning/audit, källor, test, Claudes rapport och status. Rapporterade utfall har kontrollerats självständigt.

## Fynd

### D1-04 [P2] – felprovsskriptet klassar en trasig provmiljö som 26 fångade mutationer

`scripts/momentum-d1-mutations.py:109–119` kopierar bara `engine/`. Redan vid import läser `tests/test_momentum_control.py:24` oraklet från kopians överordnade `docs/momentum-a1-orakel.json`, som saknas. Även integrationstestet behöver den filen. Testinsamlingen faller därför före mutationsprövningen. Skriptet sparar varken felorsak eller antal körda tester och klassar varje icke-noll exitkod som FÅNGAD.

Eget `--check` ger exakt det sparade utfallet: **26 fångade, 0 missade, 1 ekvivalent, 2 ej tillämpliga**. Det är reproducerbart men sakligt missvisande. Den nya revisionsauditen kör en oförändrad källkopia i samma katalogstruktur: exit 1, `FileNotFoundError` vid testinsamling. Den anropar också revisionsladdade `run_one` för första mutationen, som felaktigt blir FÅNGAD i denna miljö. PASS betyder här bara att den felaktiga klassningen upprepas, inte att proven upptäcker felen.

Klassningen av kalenderdagar som ekvivalent är rimlig inom det fullständiga raster som Market kräver. Däremot är delat state och årsreset inte bevisat ekvivalenta eller omöjliga fel: en avsiktlig felinjektion kan införa dem, precis som övriga mutationer inför fel. ”Ny kod” är inte skäl att utesluta ett uttryckligen föreskrivet felprov. För verkligt fångstunderlag behövs en fungerande oförändrad baslinje, tillgängliga testresurser, åtskillnad mellan testfel och miljö-/insamlingsfel samt de föreskrivna felklassningarna. Ingen av de 26 fångsterna räknas som verifierad mutationsfångst i denna granskning.

### D1-05 [P2] – adaptervalideringen sker efter oskyddad aritmetik och dubbletter skrivs över

`engine/traderlab/momentum_control.py:130–139`. Adaptern räknar `used * row['cap']` innan ComponentSignal kan kontrollera numeriken. En riktig signals-rad med enbart cap ersatt av `10**5000` ger `OverflowError`, inte ett utskrivbart `ControlError`. Direktkonstruktionsprovet för samma storleksordning täcker alltså inte adaptervägen. Felaktiga operander kan på motsvarande sätt ge Python-typfel före domänvalideringen.

Adaptern kontrollerar inte heller unikt/sorterat dagsindex. Auditen ger den två individuellt koherenta rader för samma dag med motsatt s7. Båda accepteras och den sista skriver tyst över den första i `out[day]`. Det bryter det beställda negativa indatakontraktet och döljer motstridig proveniens. Detta visar inte ett fel i normal run_component med intern signals-tabell, men det publika adapterkontraktet är inte färdigvaliderat.

## Stängda och kvarstående tidigare fynd

- **D1-01, ursprungliga motexempel stängda:** s=.123, available='False', sen earliest_fill, decision_time på källdagen, s14=.25 och NaN-vol avvisas nu med ControlError. earliest_fill bevaras i ComponentSignal och sparade beslut. Direktkonstruktion validerar version, dag, tillgänglighet och radkoherens. Det nya adapterfelet redovisas separat som D1-05; det fullständiga indatakontraktet är ännu inte godkänt.
- **D1-02 stängt för den granskade synkrona körvägen:** tabellerna djupkopieras, anroparens efterföljande 2025-tillägg ändrar inte Market. Ett 2025-tillägg i den interna kontraktstabellen avvisas före signalingången; en ändrad intern markpriscell avvisas också. run_component kontrollerar före signalberäkning och run_controls även mellan konton och efteråt. Fingeravtrycket är en summa av radhashar och är ordningsoberoende, inte ett bevis på byteidentitet eller skydd mot samtidiga skrivningar. Ingen ekonomiskt förändrad, hashbevarande prisändring har påvisats här; de konkreta tidigare gränsöverträdelserna är stoppade.
- **D1-03 kvarstår, väsentligt kompletterat:** de 36 nya proven ger nyttigt underlag för fundingfaser, riskgränser, stopplås, likvidation och alla åtta scenarioetiketter. Felprovsmatrisen kan dock inte godtas (D1-04). Det finns ännu inget komplett oberoende handräknat komponentförlopp med senare ökning/minskning och separat terminalfall där P≠M. Minskningens Decimal-facit börjar från `res[T1].prev_state.account`, alltså motorns eget tidigare resultat, och terminalprovet hämtar q_old ur det granskade spåret. Formlerna är självständiga lokala kontroller, men detta verifierar inte hela kapitalförloppet oberoende. De nya riskgränsproven söker floatövergångar med samma jämförelseformler som riskkontraktet; det är relevant gränsprovning, inte ett oberoende beloppsfacit för hela förloppet.

## Verifierade delar och revisionsaudit

[review.py](../research/audits/momentum-d1-720e1f8/review.py) läser källor med `git show` från fullständig 720e1f8 och laddar produktionsmoduler i en separat modulrymd. [verification.json](../research/audits/momentum-d1-720e1f8/verification.json) innehåller källhashar, exakt diff-fillista, skyddskontroll, Decimal-referenser, avvisade ursprungliga motexempel och de nya reproduktionerna. `--check` räknar om hela underlaget. Gamla audits är oförändrade; deras PASS återger deras historiska slutsatser.

- **3 288 oberoende Decimal-signaljämförelser**, precision 70, alla åtta delsignalskombinationer och 1 096 dagar med cap<1; kalenderlag, 60 avkastningar, ddof=1-vol, cap och komponentmål. Separat lika-prisfall ger noll för alla horisonter.
- **Tre fulla publika syntetiska förlopp**, ett per komponent, vardera 6 576 staplar, 6 577 closepunkter och 1 096 dagar. Varje close-/dagkapital jämförs med Decimal. Inträdes-q är 998,40255591054313099 och terminalkapital 99 680,5111821086262, inklusive båda kostnaderna och startkapital före kostnad. Dessa enkla konstant-exekveringsprisfall påstås inte ersätta det saknade förloppet med varierande position och basis.
- De nya integrationsprovens köp-/säljformler i Decimal är algebraiskt riktiga och oberoende av ledgerfunktionerna. Fundingbelopp jämförs mot q×M_ref×ränta och inträdets fasordning/E_trade/E_post prövas separat. Privata mittperiodsfixturer är tydligt märkta; de räknas inte som publik proveniens.
- L1/L2 jämför nu ekonomiska tracefält och dagkapital i A/B × båda mmr. Separata kontons risklås prövas i ett sekventiellt publikt EngineState-förlopp. Ingen ny blandning eller komponent-bound godkänns.
- O9:s tidigare slutsats består: capbrott kräver minskning trots att bandet inte bryts. Fryst protokoll/orakel ändras inte för uppdragets felaktiga hold-formulering.

## Diff och körda kontroller

Diffen fa89803..720e1f8 innehåller exakt åtta filer: kontrollmodulen, dess befintliga test, nytt integrationstest, felprovsskript, mutations-JSON, Claudes rapport, momentumstatus och genererad momentumvy. **Signal, ledger, funding, risk, margin, event, bound, stats, protokoll, register, gamla resultat och gamla audits är byte-oförändrade.** Den exakta ändringslistan är låst i auditen; inga andra filer i revisionen har ändrats.

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Båda testkörningarna gjordes från `engine/`, med `-m pytest -p no:cacheprovider -q`.

- Momentum: **602 passerade**, varav **62 D1-prov**, exit 0.
- Hela motorn: **1 155 passerade**, exit 0. En joblib-varning om fysisk CPU-detektering; inga testfel.
- Antalen stämdes av mot testinsamling från engine/. Ett extra insamlingskommando råkade köras från reporoten och gav 45 importfel, inga körda tester; det rättades genom insamling från engine/. Detta är skilt från de två fullföljda gröna körningarna.
- `python3 scripts/momentum-a1-oracles.py --check`: PASS.
- Samtliga **24** `research/audits/momentum-*/review.py --check`: PASS, inklusive den nya auditen och 23 oförändrade äldre audits. Den nya auditen kontrollerades igen efter sin slutliga komplettering.
- `python3 scripts/momentum-d1-mutations.py --check`: exit 0, ovanstående 26/0/1/2 reproduceras; **inte godkänt fångstunderlag**, se D1-04.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändringen. Momentumvyn regenererades och kontrollerades igen efter statusändringen.
- `git diff --check fa89803 720e1f8` och granskningsleveransens `git diff --check`: rena.

## Status och nästa steg

MOM-D01 förblir `in_progress`, med D1-03, D1-04 och D1-05 öppna. Inga nya done-markeringar. A/B/C-status och övriga D-punkter ändras inte. D1-Q01/Q02 avgörs inte här; buy_and_hold, legacy, no_vol, blandningar och komponent-bound återstår. Checklistan är en regenererad lokal ögonblicksbild.

Rättning och kompletterad syntetisk verifiering krävs före ny granskning av exakt revision. Detta dokument är inget nytt uppdrag. Ingen historikkörning, registrering, merge, driftsättning, release eller paper/live har utförts eller godkänts. H-0013 förblir REJECT; H-0016 är oförändrat. Inget har committats eller pushats.
