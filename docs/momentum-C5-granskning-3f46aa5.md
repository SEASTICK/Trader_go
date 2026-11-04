# Codex granskning av H-0017 leverans C5, rättning

Datum: 2026-11-04. Exakt revision: **`3f46aa572d5315527ef45e48ac218e9d80e551c8`**. Diffbas: **`8e447cbc4b68174a1b7c4ff821b0e1feb869fcf0`**. HEAD, diffbas och grenen `codex/momentum-c5-review` kontrollerades; arbetskopian var ren före granskningen. Endast syntetiska data.

**C5 är EJ GODKÄND. C5-01 och C5-03 stängs inom C5; C5-02 [P1] kvarstår via den publika återställningen. Nytt fynd C5-04 [P2] gäller återställningens felkontrakt.** Nästa C-del kan inte tilldelas genom detta beslut. Inget nytt uppdrag skrivs.

## C5-02 [P1], kvarstående: restore går förbi bindningen av konto och risklås

Plats: `engine/traderlab/momentum_event.py:254–271`, tillsammans med kontrollerna vid 221–240.

De fyra tidigare `dataclasses.replace`-motexemplen avvisas nu kontrollerat: dubblerat startkapital, position före start, oförklarat nollkonto och främmande riskstate. Exakt startläge och avstämning kontrolleras också bakom konstruktionsgrinden. Detta är en förbättring, men grinden omfattar inte motsvarande publika komposition genom `EngineState.restore`.

Återställningen tar fortfarande emot Account och RiskState som oberoende delar utan bunden proveniens. Att anroparen enligt dokumentationen intygar att delarna hör ihop ersätter uppdragets valideringskrav. Förbudet mot att börja en RunLog från restore hindrar inte `process_bar` från att handla med detta tillstånd.

**Oberoende reproduktion av tidigare riskbyte:** `locked` med permanent stopp och ett annat kontos/scenarios olåsta riskstate har samma cursor 2023-05-02 00:00. `replace` avvisas, men `restore(locked.scenario, locked.account, other.risk_state, locked.funding_state, locked.margin_state, ...)` godtas. Nästa signal köper **q=499,6003197442046**; med det riktiga låset förblir q=0. Inga privata hjälpfunktioner, ändrade objekt eller ändrad implementationskod behövs.

**Starkare reproduktion från vanliga motorsteg:** två konton körs från det låsta startläget genom sex staplar till nästa midnatt. Det ena går in med vikt 0,5, får close 300 och därefter 220, utlöser permanent stopp och stänger. Dess kontanter är då **159 696,24300559552**, q=0. Det andra kontot är platt utan permanent stopp. Publik restore av det första kontot med det andras riskstate godtas. Den riktiga fortsättningen köper inget; den blandade köper **q=362,6558821251988**. Här har det borttagna stoppet faktiskt uppstått genom `process_bar`, inte fabricerats i en fixtur.

Dessutom godtas ett återställt konto med deposit=initial=**200 000**, trots §4:s låsta 100 000; nästa platta steg returnerar 200 000. Likheten deposit=initial binder två tal till varandra, inte till strategins kapitalbas. Ett avstämt konto med `funding_net=1` och tom `FundingState.processed` godtas också, trots att dess påstådda fundinghistorik saknas. Detta är kvarstående delar av C5-02:s tidigare krav på återställningsinvarianter, inte nya fyndnummer.

**Krävd rättning:** återställning som får fortsätta i motorn måste bevara konto-/scenariobunden risk- och bokföringsproveniens och det låsta startkapitalet. En uttrycklig syntetisk fixturväg får inte samtidigt fungera som en okontrollerad väg runt det granskade risklåset. Giltiga återställningar mitt i horisonten och nära terminal måste fortsatt fungera. Ingen ändring av C3-formler eller det frysta protokollet krävs av detta fynd.

## C5-04 [P2]: restore jämför tid före UTC-valideringen

Plats: `engine/traderlab/momentum_event.py:267`.

Med i övrigt giltiga delar och `next_bar=pd.Timestamp('2023-05-02')` utan tidszon kastar den publika återställningen **`TypeError: Cannot compare tz-naive and tz-aware timestamps`**. Jämförelsen `START < next_bar` görs före `_bar_time`. Den når därför varken modulens kontrollerade EventError eller dess utskrivbara valideringsfel enligt API-kontraktet. NaT avvisas däremot kontrollerat. Inga indata ändras.

**Krävd rättning:** validera UTC-tid och upplösning före intervalljämförelsen, med kontrollerat modulfel även för naiv tid. Lägg regression på den publika återställningsvägen.

## Stängda fynd och verifierade delar

**C5-01 stängt enligt Edwins val, utan omprövning.** Beslutsdokumentet återger alternativ 1 korrekt: ingen mellanhändelse i träffstapeln bokförs som betald/mottagen; varje händelse redovisas separat som olöst med exakt tid och belopp, och nollställningen tar resten. Dokumentet anger uttryckligen ett dokumenterat tillägg för luckan. Det frysta protokollet är byte-oförändrat; detta godkännande påstår inte att konventionen redan följde entydigt av dess ursprungliga text.

Den egna auditen kör **32 oberoende Decimal-fall**: A/B × båda mmr × båda teckenordningarna × med/utan samtidig funding × två low-priser. Varje fall har två betalningar, två krediter, nollränta och historisk funding 500. **16 träffar och 16 utan träff.** Underlags-C, E_low och MM verifieras separat. Vid träff bevaras historisk funding och öppningens A/B-funding; varje mellanevent får exakt en olöst kategori, exakt tid, belopp och underlagsflagga. Ingen bokförs i funding_net. Justeringen stämmer mot hela kontot efter öppningen och den oberoende avstämningen. C4:s post innehåller underlaget; dess kod ändras inte. Likvidationstiden anges som okänd inom stapeln, utan observerad ordning mot fundingtiderna. Utan träff kontrolleras varje kronologisk cashpost. Betalda/mottagna olösta belopp hålls separat från historisk funding; full §15-resultatredovisning tillhör senare leverans.

Efter träff verifieras absorberande noll genom fyra följande staplar inklusive midnatt, och genom explicit återställning nära terminal. Konto och historiska ledgerfält består, ingen funding eller handel återupplivar det. Detta verifierar nolltillstånd och kapitalpunkter, inte en ännu ej implementerad statistisk C6-utvärderare.

**C5-03 stängt inom C5:s publika normala loggkedja.** RunLog kräver startläge och matchande föregående EngineState. Åtta egna kontrollerade avvisningar omfattar dubbel första stapel, lucka, bakåtsteg, främmande konto/scenario, återställt midnattsresultat direkt efter start, återställt startförsök, ändring genom replace och tillägg efter terminal. Den fulla syntetiska serien har fortsatt **6 576 staplar, 6 577 kapitalpunkter och 1 096 dagar**, med separat kalenderfacit. Återställda delhorisonter kan inte börja en logg. C5-02 gäller fortfarande den separata vägen in i motorn.

Övrig egen verifiering: **24 Decimal-inträde/exitkompositioner** för A/B, båda mmr, båda kostnaderna och tre basispriser; två O6-reset/riskutträden; två terminalfall mot Decimal; sex exakta fundingtidsfall; gaplikvidation före tänkt fill; sju kontrollerade felprov med oförändrade indata. E_trade, E_post, kostnad, målidentitet, funding och avstämning stämmer. **Fem egna mutationer fångas, noll missade:** borttagen A-funding, B på gamla q, reset från nya öppningen, borttagen startpunkt och borttagen terminalpunkt. Claudes rapporterade mutationsantal används inte som egna antal.

## Audit, körda kontroller och integritet

Ny [review.py](../research/audits/momentum-c5-3f46aa5/review.py) och [verification.json](../research/audits/momentum-c5-3f46aa5/verification.json). Alla sex momentumkällor och lokala beroenden laddas från exakt revision med `git show` till ett separat minnespaket. Källhashar omfattar även protokoll, register, uppdrag, orakel, beslut, ordningsnotering, eventtester och status. Exakt diff-fillista krävs. `--check` kör om fallen och jämför hela underlaget. PASS inkluderar reproduktion av kvarstående fynd och innebär inte C5-godkännande. Den gamla C5-auditen ändras inte.

Interpreter: `/Users/edwinlyckoskold/Documents/GitHub/Trader_go/engine/.venv/bin/python`. Pytest kördes från `engine/` med `-m pytest -p no:cacheprovider`.

- Momentumtesterna: **503 passerade**, exit 0, 5,71 s; därav 101 eventtester.
- Hela motorsviten: **1 056 passerade**, exit 0, 102,64 s. En joblib-varning om fysisk CPU-detektering, inga testfel. Det verkliga antalet skiljer sig från Claudes rapport (1 052).
- A1-oraklet med `--check`: PASS.
- Alla **18 äldre** momentum-audits med `--check`: PASS, oförändrade historiska reproduktioner. Ny audit med `--check`: PASS.
- Alla **fyra** checklistgeneratorer med `--check`: PASS före statusändring. Momentumvyn regenereras och alla fyra kontrolleras även efter leveransen.
- `git diff --check 8e447cb HEAD`: rent. Leveransens `git diff --check`: rent.

Diffen 8e447cb..3f46aa5 innehåller exakt sex filer: eventmodulen, eventtesterna, Edwins beslutsdokument, Claudes rapport, momentumstatus och genererad momentumvy. Signal, ledger, funding, risk, marginal, deras tester, fryst protokoll, register, gamla resultat och gamla audits är därmed byte-oförändrade. Denna granskningsleverans ändrar endast den nya auditen, detta dokument och momentumstatus/vy.

## Status och nästa steg

MOM-C03/C04/C05 förblir **in_progress**, med C5 EJ GODKÄND på exakt 3f46aa5 och underlag för kvarstående C5-02 samt nya C5-04. C5-01/C5-03 är stängda inom avgränsningen. C04 saknar fortfarande §10.2-bounden. A/B och MOM-C01/C02 behåller sina oförändrade komponentgodkännanden. Checklistan förblir **12/40**.

Rättning och oberoende omgranskning av exakt ny revision behövs före nästa C-del. H-0013 förblir REJECT; H-0016 är orört. Ingen marknadshistorik, nätverk, registrering, merge, driftsättning, release eller paper/live. Inget har committats eller pushats.
