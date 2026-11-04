# Claude: H-0017 C4 – marginal och absorberande likvidation

C3 godkänns på **8c19618d431ad59c22fbbcf43171ab5f38b7b13f** enligt docs/momentum-C3-granskning-8c19618.md. Utgå från granskningskedjan som innehåller detta uppdrag, inte äldre main. Kontrollera HEAD, diffbas, dirty-läge och fjärrstatus; använd egen gren utan reset/force-push eller att skriva över annan sessions arbete.

Läs AGENTS.md, CLAUDE.md, research/h0017-protokoll.md (§4, §6, §8.1–8.4, §9, D21), orakel O11/O18 och tidigare A/B/C-granskningar. Det frysta protokollet styr. Det här är en avgränsad kodleverans med syntetiska priser, inga historikkörningar eller driftåtgärder.

## Enda leveransen

Bygg en separat, versionsmärkt marginal-/likvidationsmodul för redan givna konton/prispunkter. Huvudmodellen behöver long/platt; legacy-kontrollerna kräver också short. Ingen ny storleks-, strategi- eller stoppregel införs.

| Regel | Låst värde | Kontroll |
|---|---|---|
| Underhållssats | 0,05 respektive 0,005, separata scenarier | MM = mmr × abs(q) × m |
| Träff | E(m) <= MM, utan extra epsilon | E = C + q × m |
| Ogynnsam mark-extrem | low för long, high för short | välj efter positionens tecken, inte efter bästa utfall |
| Ekonomisk effekt | total kontoförlust, E=C=q=0 | absorberande tillstånd, ingen ny affär/funding/tillskott |
| Avgift | ingen separat likvidationsavgift | skapa ingen artificiell fill eller dubbel kostnad |

Satserna är förregistrerade forsknings-/stressantaganden, inte verifierade historiska Binance-villkor. Ingen får ändra dem i leveransen för att förbättra utfall; materiella kontraktsfrågor redovisas till Codex före kodning.

1. **Prövning:** använd direkt villkoret E(m) <= mmr×abs(q)×m för given positiv ändlig markpunkt. Returnera spårbar E före nollställning, MM, sats, q, pris/källa och fas. Logga negativt E efter ett gap som det är; ingen tyst klippning före kontrollen. Trösklar för diagnostik följer §9: long −C/(q(1−mmr)), short C/(abs(q)(1+mmr)). Dela inte med q=0 och ersätt inte okänd tröskel med ett uppfunnet pris.
2. **Prispunkter:** skilj gap/mark_open från ogynnsam intrastapelpunkts mark_low/mark_high. En intrastapelträff har känd stapel men okänd exakt händelsetid; redovisa inte extremens tid som observerad. Validera positiva ändliga priser och givna OHLC-relationer där en hel stapel tas emot. Skapa inga handelsbeslut från high/low.
3. **Absorberande övergång:** en träff ger dokumenterat likvidationstillstånd och platt nollkonto, med ursprungligt konto och all historisk redovisning spårbar. Gör prövning/övergång atomiskt på samma konto; ett gammalt prövningsresultat får inte blint nollställa ett ändrat konto. Definiera kontrollerat återanrop på redan likviderat tillstånd så att inga belopp eller poster bokförs två gånger. Ett oförklarat platt noll-/negativt konto är fortfarande ogiltigt, inte ett nytt legitimt likvidationsbevis.
4. **Ledgerkomplettering:** bevara insättning, handelsrealiserat, kostnader och funding_net. Blanda inte modellens likvidation med en verklig handelsfill eller funding. Komplettera Account med en separat, ändlig, signerad `liquidation_adjustment`, default 0, additiv i avstämningen:

   C = deposit + realized − costs − funding_net + liquidation_adjustment − q×avg_price.

   Vid likvidation blir C=q=avg_price=0. Behåll övriga gamla fält; förändringen i justeringsfältet är −C_old−q_old×avg_price_old. Då är identiteten fortsatt sann utan ny insättning, påhittad handelsrealisation eller avgift. Logga separat mark-to-market-resultatet q_old×(m−avg_price_old) och kapitalreseten −E_before; deras summa ska stämma med justeringsförändringen inom dokumenterad numerisk tolerans. Ett negativt E_before kan ge en positiv resetkomponent när det frysta modellvalet sätter kontot till noll; dölj inte detta och kalla det inte marknadsvinst. Denna komplettering är redovisning av redan fryst totalförlust, ingen ändring av marginalmodellen.
5. **Komposition, inte eventloop:** syntetiskt kontrollera ordningen från §8.1: given gapvärdering, A-funding om tillämpligt, marginalprövning före eventuell fill. För adverse kontroll inne i stapeln kräver §8.3 C efter betald och före mottagen funding från mellanhändelser; demonstrera på givna event och konton. C2 väljer inte marginal-/positionsordning. Ingen full L1/L2-/ATR-stoporkestrering byggs här; kommande eventlager väljer vilket q som kunde ha funnits och säkrar att inga senare fills/funding anropas efter likvidation.
6. **Gräns till C3:** nollkontot och flaggan ska fungera i C3:s dokumenterade likvidationsväg, inklusive terminal utan avsikt eller kostnad. Ändra inte C3 för att tillåta återupplivning. Levande konton ska bete sig oförändrat.

## Oberoende syntetiska prov

- O11: exakt sizing/mark-gap/funding från oraklet och båda underhållssatserna. Legacy-short har ungefär 190,48 respektive 199,00 som kontrollvärden; använd exakta formler/orakelfacit, inte bara avrundade tal. Long med betald funding kan också likvideras; anta inte att 1× gör det omöjligt.
- Direkt marginvillkor under/på/över den beräknade floatgränsen för long och short, båda satserna, olika konto- och prisnivåer. Tröskelformeln är diagnostik; testet avgörs av direktvillkoret med faktisk floataritmetik, utan extra epsilon. Decimal/handräkning ska vara fristående från produktionskoden.
- Gap med negativt E före reset, intrastapel-low för long och high för short, ingen träff, q=0 med positivt kapital. Felaktig sats, pris, fas/tidsmetadata, NaN/inf/feltyp och overflow ger kontrollerat fel utan halv uppdatering.
- Account-validering inklusive replace för nytt fält. Default 0 ska ge identiskt utfall på alla tidigare C1/C2/C3-fall. Ingen ändring av gamla beloppsfacit för att dölja differenser.
- Total nollställning med tidigare partialaffär, kostnader och funding; avstämning före/efter med separat justering. Ursprungliga bokföringsfält behålls, justeringen bokförs en gång. Prov med olika skalor samt negativa/positiva resetkomponenter.
- Absorberande tillstånd över flera observationer, midnatt och terminal. Inga nya avsikter, fills eller kostnader i kompositionen. För O18: visa att en likviderad del står på noll medan en separat överlevande del kan fortsätta; skapa inga nya avkastnings-/statistikregler här. Den fullständiga dagliga avkastningsserien integreras senare.
- Givna A/B-kompositioner och betalning/kredit inom stapel, med båda satserna, utan att återanvända ett redan behandlat fundingevent. En senare kredit får inte återuppliva ett konto som redan likviderats.
- Avsiktliga fel i villkorets riktning/inkludering, fel extrem för short, fel sats, fill före gapprövning i kompositionstestet, tyst klippt negativt E, dubbel nollställning, förlorad avstämningsjustering eller borttagna kostnads-/fundingposter. Återställ före commit; skilj fångade, missade och ekvivalenta mutationer.

## Ingår inte och status

Ingen historikläsning/dataaudit/nedladdning, H-0017-jobb, full eventloop, intrastapel-drawdown-bound, signaländring, parameteroptimering, utvärderare, kö/worker, app, SQL/server, release eller paper/live. Ändra inte fryst protokoll/register/resultat eller gamla auditfiler. Intrastapel-bound enligt §10.2 är en separat kommande leverans och får inte smygas in som ett handelsstopp.

MOM-C05 får nytt delunderlag, inte fullt godkännande. **Återöppna MOM-C01 till in_progress** eftersom ledgern kompletteras; redovisa även påverkan på andra godkända moduler/verifieringar. Bevara MOM-C02-godkännandet om riskmodulen och dess giltiga funktion är oförändrade, med ny kompatibilitetsevidens; återöppna om förändringen faktiskt ogiltigförklarar verifieringen. C03/C04 förblir öppna för integration/bound. Bocka inte av nya punkter själv.

Kör hela motorsviten, relevanta momentumtester, A1-orakel, samtliga tidigare revisionslåsta audits samt alla fyra checklistgeneratorer med --check i projektets venv. Lämna gren, full HEAD, diffbas, ändrade filer, API/version, exakta bokföringsidentiteter, oberoende facit, faktiskt testutfall, felprov, påverkan på tidigare godkännanden och begränsningar. Nästa del väntar på Codex granskning av exakt revision.
