# Codex granskning av H-0017 leverans C4

Datum: 2026-11-04. Exakt revision: `0773f7647980834ddbf41365fd8f8cd3918051b7`. Diffbas: `db65a54bf96fa018c42506a2ee27886433dde71e`. HEAD och bas kontrollerade lokalt; gren `codex/momentum-c4-review`, ren arbetskopia före granskningen. Ingen nätverkskontroll eller ändring av Git-historik utförd.

**C4 är ej godkänd. Två P2-fynd kräver rättning i det numeriska API-kontraktet.** Normala marginalbeslut, separat likvidationsbokföring och den avgränsade syntetiska kompositionen stämmer. Fynden kräver ingen metodändring eller registrering. Granskningen avser mom-margin/1.0.0 och ledgerkompletteringen på exakt denna revision.

## C4-01 [P2] Kontrollera mellanberäkningen i shorttröskeln

Plats: `engine/traderlab/momentum_margin.py:68`, även returvärdet från `check` på rad 156.

`_out` kontrollerar bara den färdiga kvoten. Med ändliga indata kan nämnaren `abs(q)*(1+mmr)` bli oändlig; divisionen ger då ett ändligt men felaktigt nollpris. Det bryter uppdragets krav på spårbar tröskel och kontrollerat overflowfel utan påhittat pris. Även det vanliga `check` returnerar detta felaktiga diagnostikfält. Direktvillkorets träffbeslut påverkas inte i reproduktionen.

```python
import pandas as pd
from traderlab import momentum_ledger as L, momentum_margin as M
acct = L.Account(C=1e308, q=-1.75e308, deposit=1e308)
state = M.MarginState('main', 'A', 0.05)
M.threshold(acct, 0.05)  # 0.0; Decimal-facit 0.54421768707482993197...
r = M.check(acct, state, M.GAP, 0.5, M.MARK_OPEN,
            pd.Timestamp('2023-01-01', tz='UTC'))
# E=1.25e307, MM=4.375e306, hit=False, threshold=0.0
```

Alla kontofält och E/MM är ändliga. Felet finns även vid 0,5 %: q = −1,795e308 ger 0 i stället för 0,55433140703169389820… . Detta är ett numeriskt syntetiskt felprov, inget påstående om realistiska positionsstorlekar.

**Krävd rättning:** kontrollera nämnarens ändlighet före division och avvisa overflow kontrollerat enligt uppdraget. Låt inte en oändlig mellanprodukt bli ett legitimt nollpris. Bevara direktvillkoret och frånvaron av epsilon.

**Regressioner:** båda satserna, direkt `threshold` och `check` med ovanstående ändliga värden; kontrollerat fel och oförändrade indata. Behåll vanliga long-/shortgränser, legitim nolltröskel och q=0 → None. Befintligt overflowtest gäller q×m i E och fångar inte nämnarfelet.

## C4-02 [P2] Validera feltyper före konvertering och fältåtkomst

Plats: `engine/traderlab/momentum_margin.py:56–68` och `:159–168`.

`check` har en uttrycklig kontotypvakt, men de publika hjälpfunktionerna `threshold` och `check_bar` läser `acct.q` innan samma kontroll. `_mmr` testar medlemskap före numerisk typnormalisering: ett komplext tal med realdelen 0,05 jämförs lika med den tillåtna satsen men kraschar i `float`. Därmed läcker vanliga Python-fel i stället för det dokumenterade kontrollerade felkontraktet.

```python
M.MarginState('main', 'A', 0.05 + 0j)  # TypeError från float()
M.threshold(None, 0.05)               # AttributeError: None har inget q
M.check_bar(None, M.MarginState('main', 'A', 0.05),
            pd.Timestamp('2023-01-01', tz='UTC'), 100, 110, 90, 100)
# AttributeError: None har inget q
```

**Krävd rättning:** använd konsekvent numerisk validering för mmr före medlemskap/konvertering och validera Account vid de publika ingångarna före fältåtkomst. Feltyper ska ge MarginError/LedgerError enligt dokumenterat kontrakt utan ändrat konto eller tillstånd; tillåtna reella skalärer ska fortsätta fungera. Fånga inte godtyckliga interna undantag för att dölja fel.

**Regressioner:** konstruktion och replace av satsen med komplex/feltyp, samt fel kontotyp till `threshold` och `check_bar`; täck även de redan fungerande `check`-vakterna och giltiga Python-/numpy-tal. De befintliga testerna för ogiltig sats saknar komplexvärdet och hjälpfunktionernas kontotypvakter.

## Oberoende verifierade delar

Auditen [review.py](../research/audits/momentum-c4-0773f76/review.py) läser källorna med `git show` från exakt revision, också matchande ledger, funding, signal och risk. [verification.json](../research/audits/momentum-c4-0773f76/verification.json) sparar SHA256 per källa, exakta felutfall och kontrollantal. `--check` jämför reproducerat resultat med filen; PASS betyder också att de två historiska felen fortfarande reproduceras, inte att C4 godkänns.

- 600 oberoende marginaljämförelser med 70-siffrig Decimal-referens: long/short, båda satserna, varierande kapital/prisnivå och punkter på båda sidor om gränsen. 12 direkta floatgränsprov inkluderar exakt E=MM för båda tecknen och båda satserna samt grannfloats. Beslutet följer E≤MM utan epsilon.
- 300 likvidationer med varierande skalor och tidigare redovisningsfält samt två ytterligare förlopp med faktiska partialaffärer, kostnader och funding. Avstämning kontrollerad före/efter relativt kontots beloppsskala (≤1e−12); justeringsdelta och mtm+reset jämförs separat. Insättning, realiserat, kostnader och funding bevaras.
- Ledgeridentiteten är `C = deposit + realized − costs − funding_net + liquidation_adjustment − q*avg_price`. Delta är `−C_old−q_old*avg_price_old`; efteråt C=q=avg_price=0. Inga syntetiska fills eller likvidationsavgifter. Gap med E=−5 000 loggas oklippt: mtm=−15 000, reset=+5 000, delta=−10 000.
- Oföränderliga konton/tillstånd och jämförelse mot hela prövade kontot avvisar gammal prövning på ändrat konto. Fel sats, prövning efter likvidation och dubbel nollställning avvisas utan ytterligare bokföring. Giltigt platt positivt konto ger ingen träff; oförklarat nollkonto avvisas.
- Fyra öppningskompositioner: A/B × båda satserna. Gapvärdering och A-funding föregår kontrollen, fill sker bara om ingen träff; B-funding ligger efter fill. Samma syntetiska utgångskonto överlever B men likvideras i A. Ingen avgift vid utebliven fill.
- Fyra intrastapelkompositioner: long/short × båda satserna, efter betald och före mottagen funding. Low/high väljs efter q:s tecken. Återanvänt fundingevent avvisas. Efter likvidation hoppar kompositionen över senare kredit helt, utan ny fundingpost. Stapeltid redovisas utan påhittad extremtid.
- Sju C3-gränser över midnatt till terminal: nollkontot ger inga kandidater/avsikter och återupplivas inte. Ett separat överlevande delkonto fortsätter handla medan den likviderade delen bidrar med exakt noll. Full daglig avkastningsserie enligt O18 och full eventloop ingår fortsatt inte i C4.
- 200 giltiga normalfyllningar jämförda med ledgern vid diffbasen: samtliga tidigare konto-/fillfält exakt identiska och nya justeringen 0. 29 egna kontroller av ogiltiga tal, satser, metadata, fas, OHLC, oförklarat nollkonto och E-overflow ger kontrollerat fel. C4-01/C4-02 redovisas separat.
- Fyra egna mutationer enbart i minneskopior fångas: strikt `<`, omvänt villkor, fel extrem för short och tappad justering. Claudes rapporterade mutationsserie har inte körts om i sin helhet av Codex.

## Körda kontroller och integritet

Projektets interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`.

- Från `engine/`: `-m pytest -p no:cacheprovider` med de fem momentumtestfilerna: **353 passerade** (36 signal, 82 ledger, 88 funding, 101 risk, 46 marginal).
- Från `engine/`: hela motorsviten med samma flagga: **906 passerade**, exit 0; antalet verifierat genom insamling därifrån. Befintlig joblib-varning om fysiska CPU-kärnor förekom utan testfel. Ett extra insamlingsförsök från reporoten gav importfel för traderlab på grund av fel arbetskatalog; det är inte ett produktionsfynd eller resultatet från motorsvitens körning.
- A1-orakel: PASS. **Tolv tidigare** `research/audits/momentum-*/review.py --check`: PASS oförändrade. Ny C4-audit: PASS inklusive reproducerade fynd.
- Alla fyra checklistgeneratorer med `--check`: PASS före statusändring och efter leveransen. Momentumvyn regenererad från statuskällan och kontrollerad; `git diff --check` rent.
- Exakt sex leveransfiler i db65a54..0773f76: ny marginalmodul/test/rapport, kompletterad ledger samt momentumstatus/checklista. B/C2/C3-källor och deras tester, tidigare ledgertester, hela research-trädet med fryst protokoll/register/resultat/gamla audits och orakelfilen är oförändrade mot basen. Ledgertillägget är separat fält, validering och avstämningsterm; gamla beloppsfacit ändras inte.

## Status och nästa steg

**MOM-C01 återmarkeras done** efter egen omgranskning av ledgerkompletteringen och kompatibiliteten på 0773f76; fynden ligger i marginalmodulen. **MOM-C02 behåller done** med ny kompatibilitetsevidens för oförändrad C3. C03/C04/C05 förblir in_progress: full eventordning, intrastapel-bound och integration återstår, och C05 har nu C4-01/C4-02. Checklistan blir **12/40**. Ingen annan punkt blir klar genom C4:s delunderlag.

Rätta C4-01/C4-02 inom samma avgränsade C4 och låt den exakta rättade revisionen omgranskas. Inget nytt uppdrag för någon senare leverans skrivs. Nästa del väntar på Edwins beslut efter godkänd C4.

Endast syntetiskt lokalt granskningsarbete. Ingen marknadshistorik, extern tjänst, H-0017-körning, registrering, merge, driftsättning, release eller paper/live. H-0013 förblir REJECT och H-0016:s protokoll/beslut är orörda. Satserna är frysta forsknings-/stressantaganden, inte verifierade historiska Binance-villkor. Ingen commit eller push utförd.
