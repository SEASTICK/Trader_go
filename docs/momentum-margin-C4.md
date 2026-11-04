# H-0017 leverans C4 – marginal och absorberande likvidation mom-margin/1.0.0

Datum 2026-11-04. Rättad efter [Codex granskning av 0773f76](momentum-C4-granskning-0773f76.md): trösklarnas
nämnare kontrolleras före division (C4-01) och sats och kontotyp valideras före konvertering och fältåtkomst (C4-02).
Efter [omgranskningen av c312dfa](momentum-C4-granskning-c312dfa.md): ett reellt tal som inte kan bli en ändlig float,
till exempel heltalet 10**400, ger MarginError i stället för OverflowError (C4-03). Efter
[omgranskningen av d7d2434](momentum-C4-granskning-d7d2434.md): felmeddelanden formateras säkert även för heltal som
inte kan skrivas som text, som 10**5000 (C4-04), och ledgerns gemensamma `_num` avvisar reella tal som inte kan bli
ändliga flyttal med LedgerError (C4-05). Vakten från C4-03 ligger därför i ledgern.
Underlag: [research/h0017-protokoll.md](../research/h0017-protokoll.md) §4, §6, §8.1–§8.4, §9, D21
och [uppdraget](claude-uppdrag-momentum-C4.md). Implementation för Codex granskning, inte godkänd. Endast syntetiska
konton och prispunkter; ingen marknadshistorik har lästs och ingen H-0017-körning har startats. Protokoll, register,
signalmodulen (B), fundingmodulen (C2) och riskmodulen (C3) är oförändrade. Ledgern (C1) kompletteras.

## API

Modul: [engine/traderlab/momentum_margin.py](../engine/traderlab/momentum_margin.py), `VERSION = "mom-margin/1.0.0"`,
`MMRS = (0,05; 0,005)` som separata scenarier.

| Del | Beskrivning |
|---|---|
| `MarginState(account_key, scenario, mmr, liquidated=False, record=None)` | likvidationstillstånd per konto och scenario; satsen valideras numeriskt först (reellt, ändligt, inte bool eller komplext) och måste sedan vara en av de två registrerade |
| `check(acct, state, phase, m, price_source, bar_open)` | direktvillkoret E(m) = C + q × m ≤ mmr × abs(q) × m utan epsilon; returnerar `MarginCheck` med exakt konto, fas, stapel, sats, källa, m, q, E (ej klippt), MM, träff och diagnostisk tröskel |
| `check_bar(acct, state, bar_open, mark_open, mark_high, mark_low, mark_close)` | validerar mark-OHLC och prövar den ogynnsamma extremen: mark_low för long, mark_high för short |
| `liquidate(acct, state, check)` | atomisk nollställning efter en träff på exakt samma konto; returnerar nollkonto, likviderat tillstånd och `LiquidationRecord` |
| `threshold(acct, mmr)` | diagnostisk gräns: long −C/(q(1 − mmr)), short C/(abs(q)(1 + mmr)); None för platt konto. Nämnaren kontrolleras för overflow före divisionen, så en oändlig mellanprodukt ger fel i stället för ett påhittat nollpris. Används aldrig för beslutet |
| `MarginError` | underklass till `LedgerError`. Alla publika ingångar (`threshold`, `check`, `check_bar`, `liquidate`) avvisar ett konto som inte är ledger-Account innan något fält läses |

Faser: `gap` (källa mark_open) och `intrabar_adverse` (källa mark_low för long, mark_high för short). En träff inom
stapeln anges med stapelns öppningstid, aldrig med en påhittad händelsetid. Inga handelsbeslut tas från high/low.

## Bokföringsidentiteter

Account har fått fältet `liquidation_adjustment` (standard 0, samma ändlighetskontroll som övriga fält, även via
`dataclasses.replace`). Avstämningen blir

C = deposit + realized − costs − funding_net + liquidation_adjustment − q × avg_price.

Vid likvidation: C = q = avg_price = 0; deposit, realized, costs och funding_net behålls oförändrade;
liquidation_adjustment ändras med −C_old − q_old × avg_price_old. Spåret delar ändringen i mark-to-market
q_old × (m − avg_price_old) och kapitalreset −E_before; deras summa stäms av mot ändringen med relativ tolerans 1e−9.
Ett negativt E_before efter ett gap ger en positiv resetkomponent; det är modellens nollgolv, ingen marknadsvinst.
Ingen likvidationsavgift och ingen artificiell fill.

## Tillstånd och återanrop

- `liquidate` kräver att prövningen gjordes på exakt det konto som skickas (dataklasslikhet) och med tillståndets
  sats; ett gammalt resultat nollställer aldrig ett ändrat konto.
- Efter likvidation avvisas både ny prövning och ny nollställning för samma (konto, scenario) med MarginError; inga
  belopp eller poster bokförs två gånger.
- Ett platt konto med E ≤ 0 utan likvidation är ett oförklarat nollkonto och avvisas, inte ett likvidationsbevis.
- Nollkontot uppfyller C3:s dokumenterade likvidationsväg (C = q = 0, `liquidated=True`), också vid terminal utan
  avsikt eller kostnad. En senare fundingkredit på nollkontot ger beloppet 0 eftersom q = 0.

## Gräns mot kommande eventloop

Eventloopen väljer vilket q som kunde ha funnits (även L1/L2), ordnar §8.1 (gappunkt, scenario A-funding,
marginalprövning, fyllning) och säkerställer att inga fills eller funding anropas efter likvidation. För prövningen
inom stapeln ska den skicka kontot efter betald och före mottagen funding från stapelns mellanhändelser (§8.3).
Intrastapel-drawdown-bound (§10.2) är en separat leverans och inget handelsstopp.

## Verifiering

- [engine/tests/test_momentum_margin.py](../engine/tests/test_momentum_margin.py): 73 tester, alla godkända. Nio
  regressioner för C4-04/C4-05: att 10**5000 inte kan skrivas som text i denna tolk; ±10**5000 och 10**400 som sats vid
  konstruktion, replace och `threshold` med läsbart felmeddelande och oförändrade indata; övriga marginalmeddelanden med
  10**5000 som pris, källa, fas, stapeltid och nyckel; ledgerns `Account`, `replace`, `Account.open`, `equity`,
  `Fraction`, `solve_units` och `fill_normal` med ±10**400 och 10**5000 som ger LedgerError med oförändrat konto; vanliga
  värden och numpy oförändrade. 7 av testerna fäller d7d2434. Fyra
  regressioner för C4-03: ±10**400 som sats vid konstruktion, replace och `threshold` med oförändrade indata, 10**400 som
  pris i `check` och `check_bar`, och vanliga satser oförändrade. 3 av dem fäller c312dfa. Tidigare: De 14 nya
  regressionerna för granskningen: nämnaröverflow i short-tröskeln vid båda satserna (Codex exakta värden) med
  kontrollerat fel i både `threshold` och `check` och oförändrat konto; vanliga gränser, legitim nolltröskel och None;
  komplex, text, None, bytes och lista som sats vid konstruktion, replace och `threshold`; numpy-satser; fyra feltyper
  som konto i alla publika ingångar och feltyp som tillstånd. 8 av dem fäller den granskade revisionen 0773f76. Facit från
  [orakelfilen](momentum-a1-orakel.json) och fristående Decimal-räkning:
  - O11: legacy-short w = −1 med trösklar 190,476… (5 %) och 199,004… (0,5 %) mot exakt formel, träff strax över och
    ingen strax under; long w = 1 likvideras efter 500 i betald funding (tröskel 0,527).
  - Direktvillkoret vid exakt float-gräns för long och short, båda satserna och två skalor. Beslutet följer faktisk
    float-aritmetik; exakt reell aritmetik kan skilja sig någon ulp vid själva gränsen men stämmer 1e−9 därifrån, och
    float-gränsen ligger inom 1e−14 relativt från den exakta. Exakt likhet E = MM = 5 000 (q = ±1000, m = 100) är träff.
  - Gap med negativt E före reset (−5 000, positiv reset 5 000), intrastapel-low för long och high för short, ingen
    träff, platt konto med positivt kapital, oförklarat platt noll-/negativt konto, fel extrem och fas, nio ogiltiga
    indata, sex ogiltiga satser, ogiltig OHLC och overflow.
  - Validering av liquidation_adjustment, likvidation efter partialaffärer, kostnader och funding med bevarad historik
    och avstämning före och efter, skalinvarians med negativ reset, gammal prövning, fel sats, ingen träff och dubbel
    nollställning.
  - Komposition enligt §8.1 med båda satserna: A-funding före prövning, ingen fill eller avgift vid träff. Prövning
    inom stapeln efter betald och före mottagen funding, där omvänd ordning skulle dölja träffen, och ingen
    återupplivning av en senare kredit. C3:s likvidationsväg med terminal. O18: likviderat delkonto står på noll
    medan ett separat överlevande konto handlar vidare. Tidigare modulers utfall med standardvärdet 0.
- Alla momentumtester (signal, ledger, funding, risk, marginal): 380 godkända.
- Riktade felprov efter rättningarna: de 16 ursprungliga, 3 för C4-01/C4-02 (nämnare utan kontroll, sats utan
  typkontroll, kontotyp okontrollerad) och 3 för C4-04/C4-05 (ledgern fångar inte overflow, ledgern visar repr
  osäkert, satsmeddelande med repr). Alla 22 fångas. Mutanten för C4-03 i marginalmodulen är ersatt eftersom vakten
  flyttat till ledgern. C1:s och C2:s felprov ger samma utfall mot den rättade ledgern.
- Riktade felprov i första leveransen: 16 avsiktliga fel i marginalmodulen, ledgern och kompositionstestet. Alla fångades: villkor åt fel
  håll, strikt `<`, epsilon, fel extrem för short och för long, fel sats, tyst klippt negativt E, dubbel nollställning,
  gammal prövning accepterad, tappad justering, raderade kostnad/funding, justering saknas i avstämningen, justering
  ovaliderad, okänd sats accepterad, oförklarat nollkonto accepterat och fill före gapprövning i kompositionen. Strikt
  `<` missades först eftersom inget test hade exakt likhet; ett sådant fall lades till. C1:s, C2:s och C3:s tidigare
  felprov kördes om mot den kompletterade ledgern med samma utfall som vid deras godkännanden. Filerna återställdes och
  jämfördes byte för byte.

## Påverkan på tidigare godkännanden

Ledgern ändras (nytt fält och ny avstämningsterm), så MOM-C01 återöppnas. Med standardvärdet 0 är alla tidigare
belopp och identiteter oförändrade: 82 ledger-, 88 funding-, 101 risk- och 36 signaltester passerar utan ändring.
Funding- och riskmodulerna är byte-identiska mot sina godkända revisioner; MOM-C02 behålls med kompatibilitetsunderlag.

## Observation till granskaren

Ledgerns `_num` är rättad (C4-05), och eftersom funding (C2) och risk (C3) använder den för sina numeriska fält ger
till exempel en ränta på 10**400 nu FundingError. Samma `repr`-mönster som i C4-04 finns dock kvar i felmeddelanden i
de godkända modulerna `momentum_funding.py` (nio ställen, bland annat event_id, källa och fas) och `momentum_risk.py`
(fyra ställen: tider, available och version), där ett heltal som 10**5000 i ett sådant fält skulle ge ValueError i
stället för FundingError/RiskError. Jag har inte ändrat dem, eftersom de ligger utanför C4:s ändringsyta och en
ändring skulle återöppna godkända punkter. Rättningen är mekanisk (samma `_show` som ledgern) om granskaren vill att
den görs.

## Utanför C4

Ingen historikläsning, H-0017-körning, full eventloop, intrastapel-drawdown-bound, signaländring, utvärderare, kö,
app, server, release eller paper/live. Satserna 5 % och 0,5 % är förregistrerade forsknings-/stressantaganden, inte
verifierade Binance-villkor. Endast syntetiskt prövat.
