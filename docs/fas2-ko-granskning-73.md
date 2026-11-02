# H-0013-kö och worker – granskning av PR #73

Granskad PR-head: `a852aa34fb6139ffa2cd9867af017e48a112d8cb`, kod `cd9701d`, metodtolkningar `8fa1135`, gren `fas2-ko`. PR: https://github.com/SEASTICK/Trader_go/pull/73.

Granskningen använder isolerad PR-kopia, syntetiska arkiv, lokala processer och PGlite. Ingen molnanslutning, migration i Supabase, driftsättning, riktig forskningskörning eller slutprovsläsning har gjorts.

## Ursprungliga fynd före rättning

### P1 – vanligt workeravbrott dödar processen innan försöket sparas

`engine/traderlab/research_engine/worker.py:38–44` använder `process.terminate()` och därefter vid behov `kill`. `execute` använder denna väg vid normalt workerstopp/tidsgräns på rad 65–68 och vid avbrott/förlorad lease på rad 75–80. Beräkningsprocessen installerar ingen SIGTERM-hanterare. Därför körs inte `h0013.run_job`-funktionens `except BaseException` på rad 146–149 vid dessa stopp, och försöksfilen med delresultat saknas. Det är inte bara den uttryckligt uppskjutna hårda serverkraschen; även användarens vanliga avbrytning och timeout använder denna väg.

Oberoende prov med en riktig `spawn`-process: workerns `child` körde H-0013-ingången med stubbat syntetiskt datalager och en utvärdering som hade lagt ett färdigt huvudresultat i progress. Efter en redo-markör anropades den riktiga `worker.stop(process)`. Processen avslutades med **exitcode -15 (SIGTERM)** och **0 försöksfiler** i `h0013-attempts`. Inga riktiga data eller tjänster användes.

Rätta genom ett kontrollerat stopp som låter H-0013 spara aborted-post och färdiga delresultat före processavslut. Behåll en begränsad väntetid och hård fallback för en process som inte svarar; en sådan fallback får inte utges för att ha sparat progress. Publicera inget resultat efter avbrott eller förlorad lease och behåll fencing. Testa normala stopp, användaravbrott och timeout med riktiga spawn-processer, så att en FakeProcess inte döljer signalbeteendet. Regressionstesta även att Fas 1 och utforskning fortfarande stoppas korrekt och att global slot inte släpps före stoppad process.

### P2 – SQL:s strikta resultatkontrakt accepterar godtyckliga kriterier och motsägande beslut

`supabase/migrations/0005_h0013_queue.sql:66–76` kontrollerar endast att `criteria` är ett objekt med fem nycklar. Namn och booleska värden verifieras inte, och `decision` stäms inte av mot kriterierna. `holdout_loaded` kontrolleras med `->>`, så strängen `"false"` accepteras som om den vore booleskt false.

Oberoende prov i PGlite, under aktuell lease och service_role, accepterades av `research_finish` och returnerade **true**:

1. `criteria = {"a":"x","b":null,"c":123,"d":{},"e":[]}` med `decision = "MORE_RESEARCH"`.
2. De fem rätt namngivna kriterierna, med flera false, men ändå `decision = "MORE_RESEARCH"`.
3. `holdout_loaded = "false"` (JSON-sträng).

Varje prov rullades tillbaka, och den oförändrade ordinarie kötestsviten passerade därefter. Huvudworkern producerar rätt resultat i befintliga tester; felet gäller databasgränsens utlovade validering, som ska fånga en felaktig producent före lagring.

Validera exakt de fem registrerade nycklarna, att alla värden är JSON-booleans och att `MORE_RESEARCH` gäller exakt när alla fem är true, annars `REJECT`. Kräv booleskt `holdout_loaded = false`. Avvisning ska lämna körning, resultat och slot oförändrade så att aktuell lease fortfarande kan publicera ett korrekt resultat. Utöka regressionerna med fel namn, saknade/extra nycklar, null/sträng/tal/objekt/array som värden och båda sorternas motsägande beslut. Eftersom 0005 ännu inte är applicerad kan rättningen göras i den nya migrationen; ändra inte 0001–0004.

## Verifierat

- Exakt PR-head kördes i isolerad arkivkopia: **513 Python-testfall passerar**, inklusive **35 H-0013-testfall**. CI Engine check är grön på samma head. Lokal joblib-varning om identifiering av fysiska CPU-kärnor påverkar inte utfallet.
- **Båda lokala PGlite-sviterna passerar:** nya `test-h0013-queue.mjs` (0001–0005) och befintliga `test-research-queue.mjs` (0001–0004). Den nya sviten kontrollerar också Fas 1 och utforskning efter 0005. Fyndproven ovan visar vad de ordinarie testerna ännu missar.
- PR #72 är mergad som `d25f444`; utvärderingskoden och testerna är oförändrade mot godkänd `a5e8fc3`.
- Köning kräver medlemskap och synkad H-0013-registrering, ger ett fast jobb utan användarval av forskningsparametrar och är idempotent för rätt medlem/hypotes. Samma advisory lock används som i befintliga köfunktioner. Aktiv H-0013 och tidigare klart resultat blockerar ny begäran.
- Workern använder samma claim/heartbeat/finish, globala slot, lease och token. H-0013 routas separat i samma beräkningsprocessmodell och får två timmars tidsgräns; övriga jobb behåller 30 minuter. Gamla token och andra publiceringar avvisas i lokala SQL-tester. Ingen andra worker har tillkommit.
- Jobbkontraktets marknad, parametrar, period, kapital och kostnader kontrolleras före dataläsning. Avvikelser och extra strategiparametrar avvisas.
- Arkivurvalet jämförs med manifestets exakta namn före arkivinläsning; därefter verifieras arkivens SHA256 och CHECKSUM samt inlästa staplars/fundings hash. Syntetiska 120-arkivstester täcker saknad/ändrad fil, omskrivet arkiv och CHECKSUM, värdehash och filer utanför perioden. Arkiv från 2019/2025 öppnas inte i testerna.
- Vanliga fångade beräkningsfel sparar delresultat som aborted utan beslut. Fullständiga försök sparas lokalt och får spårbar revision, dataset-id och värdehash. Fynd P1 gäller specifikt att verkliga workerstopp inte når denna fångst.
- SQL-kön skriver inte Git-registrets beslut. Inga frysta protokoll, strategier, resultat eller H-0014/H-0015 har ändrats.

## Kvar till drift

PGlite använder en anslutning. Verklig konkurrens från flera anslutningar måste fortfarande verifieras i en isolerad PostgreSQL-/Supabase-kontroll före driftgodkännande. Ingen sådan konkurrens är bevisad av denna granskning. Driftsättningspaketet måste identifieras med `TRADERGO_REVISION`; katalogrättigheter, tidsgränser och återgång ska kontrolleras i F2-605. Hård serverkrasch kan ge lease-återförsök utan sparade delresultat enligt den redovisade begränsningen; detta ska hållas åtskilt från normala avbrott som ska spara.

## Checklista och beslut

F2-602 och F2-603 är kodmässigt verifierade lokalt. F2-601 lämnas `in_progress` för resultatkontraktet, F2-604 för det verkliga avbrottsbeteendet. F2-605 är inte gjord. Gemensam status: **27/40 verifierade**. Lokal kodverifiering betyder inte att molnintegrationen är i drift.

**PR #73 är inte godkänd för merge ännu.** Nästa kontroll är strikt resultatvalidering och ett normalt workeravbrott som faktiskt sparar försöket. Migration 0005 och workerdrift ska fortsatt vänta. Inget strategiresultat har bedömts och inget är godkänt för papper/live.


## Omgranskning av rättningarna – 2026-11-02

Granskad PR-head: `445178d4d0738ac030f13bc720661164aaa394cb`, kod `2160c6e`, merge av granskningsunderlaget `34adec6`. Tidigare fynd ovan bevaras som historik och är nu rättade.

- **P1 rättad:** beräkningsprocessen installerar en SIGTERM-hanterare som kastar `WorkerStop`. H-0013:s befintliga felhantering sparar då aborted-post och delresultat före avslut. Parent väntar upp till 20 sekunder före hård fallback och rapporterar uttryckligen när delresultat kan saknas. Slot/publiceringsvägar behåller ordningen: stoppa och vänta före finish, ingen publicering vid förlorad lease.
- Det tidigare oberoende provet med riktig `spawn`-process och den riktiga `worker.stop` upprepades på rättad kod: **exitcode 3 och 1 sparad aborted-fil**, jämfört med tidigare -15 och 0 filer. Provet använder syntetiskt stubbat datalager/utvärdering och den riktiga H-0013-ingången.
- Samtliga **8 nya tester med riktiga spawn-processer och signaler passerar** i hela testsviten. De täcker normalt stopp, användaravbrott, timeout, förlorad lease, Fas 1/utforskning samt hård fallback. Avbrutet försök finns innan finish släpper slotten; tvingat stopp påstås inte ha sparat delresultat.
- **P2 rättad:** SQL kräver exakt de fem namngivna JSON-booleska kriterierna, beslutet MORE_RESEARCH exakt vid fem true och annars REJECT, samt booleskt `holdout_loaded=false`. Hjälpfunktionen är begränsad till service_role. 0001–0004 är oförändrade.
- Båda lokala PGlite-kötesterna passerar. Nya sviten avvisar **27 ogiltiga resultat**, kontrollerar oförändrad lease efter avvisning och accepterar korrekta REJECT/MORE_RESEARCH. Mina tre tidigare egna felprov avvisas nu också; körningen förblir running, slotten är oförändrad och resultatantalet är 0. Därefter kan rätt resultat publiceras med samma token.
- Exakt PR-head kördes i isolerad arkivkopia: **521 Python-testfall passerar**, inklusive de 8 riktiga processtesterna. Samma lokala joblib-varning om identifiering av fysiska CPU-kärnor förekommer. CI Engine check var fortfarande `IN_PROGRESS` vid senaste kontrollen och ska vara grön före merge.
- Arkivkontrollen, H-0013-runnern, backtest-/utvärderingskoden och tidigare frysta migrationer är oförändrade i rättningen. Tidigare verifieringar gäller fortsatt.

F2-601, F2-602 och F2-604 är nu kodmässigt verifierade och F2-603 gäller fortsatt. Gemensam status: **29/40 verifierade**. F2-605 är ännu inte gjord: migrationen är inte applicerad i Supabase, koden är inte driftsatt och verklig konkurrens mellan databasanslutningar är inte verifierad. Hård serverkrasch och driftsmiljöns faktiska systemd-/katalogrättigheter måste fortsatt hållas åtskilda från de lokala signaltesterna.

**Bedömning:** PR #73 är kodmässigt godkänd för merge på `445178d`, förutsatt grön CI och bevarad granskad kod. Inga öppna fynd kvar från denna granskning. Nästa steg är ett konkret, granskningsbart F2-605-underlag med versionsmärkt paket, TRADERGO_REVISION, migrationsordning, kontroll av samma enda worker, isolerat samtidighetstest och återgång. Ingen molnmigration, driftsättning, riktig forskningskörning, slutprovsläsning eller publicering har gjorts i omgranskningen. Inget är godkänt för papper/live.
