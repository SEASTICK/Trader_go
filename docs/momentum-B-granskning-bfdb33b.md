# Codex granskning av H-0017 leverans B – bfdb33b

Datum: 2026-11-03. Granskad revision: `bfdb33b8c083ec65af2da8eecabc30de1f1a1b3f`, diffbas `e66d730`.

**Beräkningarna och de granskade tidsreglerna stämmer, men B behöver en avgränsad API-rättning före slutgodkännande och leverans C.** Ett P2-fynd. Ingen ändring av fryst metod eller ny registrering behövs.

## [P2] Returnera ett stabilt signalschema även när indata är tomma

Plats: `engine/traderlab/momentum_signal.py:115–120`.

`validate_bars()` accepterar en tom DataFrame med close-kolumn och UTC-index, och `daily_closes()` har en uttrycklig tomdatahantering som ger 0×2. `signals()` skapar däremot utdata från en tom lista utan de vanliga kolumnerna och försöker sedan välja hela `COLUMNS`. Resultatet är ett oavsiktligt KeyError om saknade kolumner. Det bryter det dokumenterade signalschemat för ett legitimt tomt prefix och förhindrar att anroparen når den uttryckliga hanteringen av inget känt beslut.

Minimal reproduktion från katalogen engine med projektets venv:

```python
import pandas as pd
from traderlab import momentum_signal as ms
bars = pd.DataFrame({'close': pd.Series(dtype=float)},
                    index=pd.DatetimeIndex([], tz='UTC'))
ms.validate_bars(bars)       # accepterar
ms.daily_closes(bars)        # tom DataFrame, 0 rader och 2 kolumner
ms.signals(bars)             # KeyError: close/s7/.../available/reason finns inte
```

Ett tomt prefix kan uppstå före första mottagna stapeln eller efter en tom periodfiltrering. Signallagret ska ge ett kontrollerat resultat; körlagret får därefter avvisa saknade data enligt protokollet. Ett internt kolumnfel är inte den hanteringen.

**Krävd rättning:** behåll den nu accepterade tomma UTC-indatan och returnera en tom signalram med exakt `COLUMNS`, UTC-index, UTC-tidskolumner samt konsekventa numeriska/booleska typer. Inga påhittade dagsrader, nollvikter eller tidigare signaler får läggas till. `latest_decision()` på denna tomma ram ska ge sitt dokumenterade KeyError om att inget beslut är känt, inte ett saknat-kolumnfel.

**Regressioner:** tom indataram, ett tomt prefix av en giltig serie, schema/tidszon/datatyp och anrop till `latest_decision` på det tomma resultatet. Kontrollera också att en icke-tom men ofullständig dag fortfarande ger `incomplete_day` med available=false och otillgänglig målvikt. Uppdatera API-dokumentationen; ändra inte protokollets numeriska regler. De befintliga 32 testerna innehåller inget tomt signalanrop och fångar därför inte felet.

## Delar som verifierats på exakt bfdb33b

- **MOM-B01:** 7/14/28 kalenderdagar, strikt positiv prisförändring, lika vikt och long/platt stämmer med §5.
- **MOM-B02:** 61 stängningar ger 60 enkla dagsavkastningar; ddof=1, sqrt(365), cap och målvikt stämmer med oberoende `statistics.stdev`-beräkning.
- **MOM-B04:** dagsclose från 20-stapeln, decision_time/earliest_fill först nästa 00:00, första tillgängliga dag, ofullständiga dagar, kalenderluckor och återhämtning är granskade.
- Version, unavailable-orsaker och NaN för beräknade signalfält finns. **MOM-B03** behöver ovanstående tomdatahantering innan helheten är verifierad.
- Prefix-/framtidsproven passerar, men **MOM-B05** omfattar också slutgodkännande av signalrevisionen och hålls därför öppen tills rättningen är omgranskad.

Egen syntetisk avstämning kontrollerar 91 dagsbeslut från en deterministiskt varierande prisserie, sex prefixgränser, ändrade framtida priser och 61-dagars återhämtning efter en saknad stapel. Tre egna avsiktliga fel fångas: beslut vid 20:00 i stället för nästa 00:00, ddof=0 och ofullständig dag godkänd. Mutanterna kördes enbart i minnet, utan att ändra Claudes fil.

Reproduktion: `engine/.venv/bin/python research/audits/momentum-b-bfdb33b/review.py --check`. Den läser signalmodulens **låsta Git-version bfdb33b** och använder enbart syntetiska tal. Den sparade verification.json innehåller källhash, verifierade fall och felet. Att skriptet fortfarande reproducerar bfdb33b efter en senare rättning är historiskt underlag, inte en underkänd ny revision.

## Tester och integritet

- Signaltesterna: **32 godkända**, med `.venv/bin/python -m pytest tests/test_momentum_signal.py -q -p no:cacheprovider` från engine.
- Hela motorsviten: **585 godkända**, exit 0. En joblib-varning om detektering av fysiska CPU-kärnor förekom i det befintliga ML-testet; logiska kärnor användes, inget test föll.
- A1-orakel, fyra tidigare Codex-audits och alla fyra checklistgeneratorer: PASS i projektets venv. `git diff --check e66d730 bfdb33b` är rent.
- Fryst H-0017-protokoll, register, gamla moduler, app och migrationer är oförändrade i leverans B. Fjärrgrenen `claude/momentum-b` verifierad på bfdb33b; arbetskopian var ren före granskningen.
- Claudes rapport om 14 mutationsprov är hans underlag; Codex har själv utfört de tre riktade felproven ovan och påstår inte att alla 14 körts om oberoende.

MOM-B01/B02/B04 markeras klara med verifiering på bfdb33b. MOM-B03/B05 förblir in_progress. A-status bevaras; checklistan blir **8/40**. Inga C-punkter är påbörjade genom denna granskning.

## Nästa leverans från Claude

Utgå från denna granskningskedja och rätta enbart P2-fyndet i signalmodul, tester och API-dokumentation. Redovisa ny commit/diffbas, riktade tester och påverkan på tidigare verifiering. Bevara granskningsdokumentet och frysta filer. Lämna B03/B05 in_progress tills Codex omgranskat exakt rättad revision. Återöppna tidigare verifierade punkter bara om ändringen faktiskt ändrar deras underlag. Leverans C väntar på B:s slutgodkännande.

Ingen marknadshistorik eller skyddad data har lästs i granskningen och ingen H-0017-körning har startats. Körlagrets historikskydd/OGILTIG_DATA, ledger, band, fyllningar, funding, marginal, risk och all drift återstår för senare leveranser. H-0013 REJECT och H-0016:s separata protokoll är orörda. Ingen lönsamhet eller paper/live är godkänd.
