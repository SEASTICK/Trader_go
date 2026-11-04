# Codex granskning av H-0017 leverans C5

Datum: 2026-11-04. Exakt revision: **`b131ff47a03f9d49f6e9df0ebd172a4bea0b6fcf`**. Diffbas: **`cd25ac80f087079b9632a845cc81b63ae9c649b4`**. HEAD och diffbas kontrollerades först på `codex/momentum-c5-review`; arbetskopian var ren. Granskningen följer Edwins beslut att fortsätta leverans C med syntetiska data och samma oberoende granskningsflöde.

**C5 är EJ GODKÄND. Tre fynd: C5-01 [P1], C5-02 [P1] och C5-03 [P2].** Normala öppningsförlopp och den sekventiellt matade horisonten passerar, men fundingledgern vid intrastapelträff, återställda tillstånd och den publika loggkompositionen uppfyller inte hela uppdraget. Nästa C-del kan inte tilldelas genom detta beslut. Inget nytt uppdrag skrivs här.

## C5-01 [P1] Adverse-underlaget ersätter den kronologiska fundingledgern vid träff

Plats: `engine/traderlab/momentum_event.py:329–351`, särskilt `paid`-urvalet och kravet `acct == ichk.account`.

Marginalprövningen ska använda C efter betald och före mottagen mellanfunding. Det är ett separat prövningsunderlag. Vid träff använder implementationen däremot bara de positiva betalningarna även som faktisk ledger och räknar alla krediter som absorberade, oavsett deras exakta tid. Det gör adverse-ordningen till en faktisk omordning/strykning av fundinghistoriken. §8.3/D18 kräver kronologisk bokföring; uppdragets punkt 5 skiljer uttryckligen underlaget från den faktiska ledgern och kräver att materiella ordningsfrågor redovisas före implementation.

**Egen reproduktion:** stapel 2023-04-10 08:00 UTC, C=−60 000, q=1 000, genomsnittspris=100, insättning=40 000; föregående close=70, peak=day_start=10 100, initial=10 100. Mark O/H/L/C=64/66/63,5/65; mmr=0,05. Kredit −0,02 kl 08:30 och betalning +0,02 kl 10:00, båda med M_ref=64, ger beloppen −1 280 och +1 280. Adverse-underlaget är korrekt: C=−61 280, E_low=2 220 ≤ MM=3 175. Men resultatet bokför bara betalningen kl 10:00; krediten kl 08:30 saknar ledgerpost och räknas som absorberad. `funding_net=1 280`, `liquidation_adjustment=−38 720`. Händelsen som faktiskt loggas sist får inte användas som bevis för att den tidigare krediten låg efter en träff vars tid uttryckligen är okänd.

Med mmr=0,005 träffas inte marginalen: båda händelserna bokförs kronologiskt och funding_net=0. Med betalningen först reproduceras den tidigare C4-kompositionens tillåtna debit→adverse→senare kredit. C4:s fyra äldre fall verifierade denna senare kredit, inte att en tidigare kredit får flyttas eller strykas. Den generella regeln i C5 är därför inte täckt av C4-godkännandet. Slutkapital 0 och en algebraisk avstämning räcker inte för att verifiera historiska ledgerfält.

**Krävd rättning:** håll marginalens konservativa underlag separat från faktisk kronologisk fundingbokföring och likvidationsjustering. En kredit får inte rädda adverse-prövningen eller återuppliva kontot; det ger inte rätt att presentera teckenordningen som observerad kronologi. Redovisa hur den okända träfftidens relation till exakta fundingtider hanteras inom det frysta kontraktet innan ett materiellt ordningsval kodas. Inga protokolländringar eller påhittade extremtider för att få godkänt.

**Regressioner:** kredit före betalning och omvänt; flera betalningar/krediter och nollränta; båda mmr, med/utan samtidig funding, träff/ingen träff. Verifiera ordnade event-id/tider, separata underlagsbelopp, historisk funding, nollställningsdelta och avstämning, inte enbart slutkapital. Testet `test_intrabar_margin_uses_paid_before_received_and_books_once` låser idag samma strykning även när krediten är först och fångar därför inte bristen.

## C5-02 [P1] EngineState binder inte hela tillståndet till konto/scenario eller startinvarianter

Plats: `engine/traderlab/momentum_event.py:159–189` och första steget i `process_bar`.

Endast funding- och marginalstate har en kontrollerad konto-/scenarioidentitet. Account och RiskState kan bytas utan motsvarande bindning eller konsistenskontroll. Att `next_boundary` stämmer räcker inte för att bevisa att risklåsen tillhör kontot. Dessutom kontrolleras inte ostartat kontos kapital/position mot det låsta startläget.

**Egna reproduktioner, samtliga accepterade via `dataclasses.replace`:**

- `replace(EngineState.start(s), account=Account.open(200000))` med platt första signal returnerar ett levande konto på 200 000, trots att riskmodulens startkapital och RunLogs startpunkt är 100 000.
- `Account(C=50000, q=500, deposit=100000, avg_price=100)` godtas redan före första öppningen. Platt första beslut lämnar den redan existerande positionen kvar.
- `Account(C=0)` godtas och första platta stapeln returnerar C=q=0 utan likvidationsflagga. Det bryter D21; avvisning först vid nästa close reparerar inte det redan returnerade ogiltiga tillståndet.
- Två återställda konton vid 2023-05-02 00:00, samma nästa gräns: `locked` i A har permanent stopp, `other` i B har inget stopp. `replace(locked, risk_state=other.risk_state)` godtas. En giltig signal med målvikt 0,5 köper därefter q=499,6003197442046 i det första kontot. Dess riktiga riskstate behåller q=0. Risklåset har alltså kunnat ersättas med ett annat kontos lås genom den publika återställningsvägen.

**Krävd rättning:** bind och validera hela eventtillståndets proveniens och konsistens vid konstruktion/replace/återanrop, inklusive Account och risklås. Ostartat tillstånd måste motsvara det låsta startkapitalet, platt position och orörd bokföring; oförklarat nollkonto avvisas. Dokumentera och kontrollera återställningsinvarianter nära terminal och mitt i horisonten. Detta är en brist i eventlagrets sammansättning, inte ett krav på att ändra godkända C1/C3-formler.

**Regressioner:** ovanstående fyra motexempel, olika konto/scenario med samma cursor, felaktiga återställda funding-/likvidationshistoriker och initial-/closevärden. Kontrollerat fel utan ändrade indata eller partiell retur; giltig explicit teståterställning och oberoende instanser ska fortsatt fungera.

## C5-03 [P2] RunLog accepterar dubbla och främmande resultat

Plats: `engine/traderlab/momentum_event.py:370–395`.

`RunLog.add` kontrollerar bara resultatets Python-typ. Loggen saknar konto/scenario, cursor och terminalvakt. Samma BarResult kan läggas till igen, ett resultat flera år framåt kan läggas till direkt efter start, och resultat från ett annat konto/scenario blandas utan fel. Den publika API-vägen kan därmed dubblera §10.1-closepunkter, §4-dagsögonblick och terminalkapital trots att `process_bar` själv skyddar sin cursor.

**Egen reproduktion:** ett giltigt resultat vid 2023-05-02 00:00 läggs två gånger till `RunLog.begin()`: loggen returnerar två identiska day_ends för 2023-05-01. Separat godtas två kopior av första resultatet och sedan första resultatet från kontot `foreign`, scenario B, i samma trace. Testet med full horisont upptäcker inget eftersom dess anropare alltid gör rätt.

**Krävd rättning:** gör loggkompositionen kontrollerad med bunden identitet, nästa förväntade resultat och en terminalövergång. Avvisa dubbla, hoppade, bakåtriktade och främmande resultat innan en ny logg returneras. Definiera en separat explicit återställningsväg om delhorisonter behövs.

**Regressioner:** dubbel första stapel, dubbel midnatt/terminal, lucka/bakåtsteg, samma tider för främmande konto/scenario och tillägg efter terminal. Verifiera att den korrekta fulla syntetiska serien fortsatt har exakt 1 096 dagar och 6 577 kapitalpunkter inklusive start/terminal.

## Egen audit och verifierade delar

Ny revisionslåst [review.py](../research/audits/momentum-c5-b131ff4/review.py), med [verification.json](../research/audits/momentum-c5-b131ff4/verification.json). Samtliga sex momentumkällor laddas med `git show` från fullständig b131ff4 till ett separat minnespaket, inklusive matchande lokala beroenden. Källhashar för kod, protokoll, register, uppdrag, orakel, eventtester och status sparas. Exakt fillista mot fullständig cd25ac8 krävs. `--check` kör om och jämför hela JSON-underlaget. PASS innebär också att de historiska C5-fynden reproduceras; det betyder inte C5-godkännande.

- **24 oberoende Decimal-kompositioner** med 70 siffrors precision: A/B × båda mmr × båda kostnadsnivåerna × tre markpriser (99,5/100/100,5 mot P=100). Inträde, exit nästa dag, samtidiga event, basis, kostnad och funding stämmer. Referensen löser själv finansieringsidentiteten; facit kommer inte från event-/ledgerfunktionerna. E_trade och målvikt verifieras före B-funding, sedan E_post och avstämning. Ordningen vid första öppningen verifieras separat för A/B.
- **Två O6-förlopp:** old-close/reset=97 900 före gap och funding; dagsrisk stryker normalen och stänger till 97 469,17 i A respektive 97 473,92 i B. Riskmodulens StepRecord bevarar suppressionsorsaken.
- **Två terminalfall mot Decimal/O10:** gapkapital 98 000, stängningskostnad 60,864, terminal 97 975,336 i A med samtidig funding respektive 97 979,136 i B. +1 ms/+30 s möter q=0. Ingen extra fill.
- **Sex tidsfall:** A/B vid första öppningen, senare midnatt och vanlig gräns, med exakt T, T+1 ms och T+30 s; korrekt fas, q, dedupliceringsstate och exakta tider. Claudes tester täcker även T−1 ms/T−30 s och otillgänglig/feldaterad signal; dessa har körts och koden för stapel-/referensval granskats.
- **Fyra egna intrastapelfall:** två teckenordningar × båda mmr; oberoende adverse-E/MM och nollställning stämmer. Dessa reproducerar samtidigt C5-01. Gapträff i B sker före fill/B-funding; kontot blir absorberande noll och avstämningen håller.
- **Full egen syntetisk platt horisont:** 6 576 staplar, 6 577 start-/close-/terminalpunkter och 1 096 dagsslut. Varje källstapel/känd-tid och varje dag jämförs med en separat kalender; RunLogs resultat jämförs med denna referens. Första öppningen saknar fabricerat close. Sista vanliga källstapel är 2024-12-31 16, känd vid terminalgränsen; ingen 2025-gräns behandlas.
- **Sju egna kontrollerade felprov:** lucka, fel M_ref, funding före första öppningen, 10**5000, boolpris och fel konto/mmr; utskrivbara fel och oförändrat inkommande state. De tre felaktiga starttillstånden och risk-/loggblandningen redovisas däremot som reproducerade brister, aldrig som lyckade avvisningar.
- **Fem egna mutationer i minneskopior fångas:** borttagen A-funding, B på gamla q, reset från nya öppningen, borttagen startpunkt och borttagen terminalpunkt. 5 fångade, 0 missade, 0 ekvivalenta i denna serie. Claudes rapport om 16 andra mutationsprov är inte omkörd i sin helhet och används inte som eget verifieringsantal.

Den oförändrade C3-modulen äger beslut/mergeprioritet, lås och reduce-only. C5 använder föregående mark_close före nästa gap; high/low matas till marginal, inte till closebeslut. Hold gör ingen ny storleksberäkning. Normalavsikt får byta riktning efter gap; riskfill använder C1:s reduce-only. Signaldag/version valideras av C3. Dessa kodvägar och de körda syntetiska regressionerna stödjer normalförloppet men ersätter inte C5-02:s saknade statebindning.

## Körda kontroller och integritet

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Båda pytest-körningarna utfördes från `engine/` med `-m pytest -p no:cacheprovider`.

- Sex momentumtestfiler: **464 passerade**, exit 0, 3,07 s. Det omfattar de **62 nya eventtesterna** samt tidigare 402 komponenttester.
- Hela motorsviten: **1 017 passerade**, exit 0, 98,09 s. En joblib-varning om fysisk CPU-detektering; inga testfel.
- A1-oraklet `scripts/momentum-a1-oracles.py --check`: PASS.
- Samtliga **17 tidigare** `research/audits/momentum-*/review.py --check`: PASS, utan ändringar. De reproducerar sina låsta historiska revisioner, inklusive äldre fynd. Ny C5-audit med `--check`: PASS.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändring. Momentumvyn regenererad med `python3 scripts/render-momentum-checklist.py`; därefter momentum `--check` och alla övriga tre `--check`: PASS.
- `git diff --check cd25ac8 b131ff4` och granskningsleveransens `git diff --check`: rena.

Diffen cd25ac8..b131ff4 innehåller exakt fem filer: ny eventmodul, nya eventtester, Claudes C5-rapport, momentumstatus och genererad momentumchecklista. Därmed är signal, ledger, funding, risk, marginal, deras tidigare tester, protokoll, register, gamla resultat och gamla audits byte-oförändrade. Granskningsleveransen ändrar endast den nya auditen, detta dokument och momentumstatus/vy; ingen implementations- eller testfil ändras.

## Status och nästa steg

MOM-C03/C04/C05 förblir **in_progress** med uttryckligt EJ GODKÄND på b131ff4 och underlag för C5-01–C5-03. C04 saknar dessutom §10.2-bounden enligt den redan beslutade avgränsningen. A/B och MOM-C01/C02 behåller sina komponentgodkännanden: deras kod är oförändrad, och fynden gäller den nya kompositionen. Checklistan är fortsatt **12/40**. C5-rättning och oberoende omgranskning av exakt ny revision behövs före nästa C-del; detta dokument är inget nytt implementeringsuppdrag.

H-0013 förblir REJECT; H-0016:s separata protokoll/status är oförändrade. Ingen marknadshistorik, nätverk, registrering, H-0017-körning, merge, driftsättning, release eller paper/live ingår. Inget har committats eller pushats.
