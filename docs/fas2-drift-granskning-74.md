# H-0013 driftsättningsunderlag – granskning av PR #74

Granskad PR-head: `eb156502f0664f6bc3882cebdbd49b107dcce0aa`, kod `f2db904` och `ac6d9c4`, gren `fas2-drift`. PR: https://github.com/SEASTICK/Trader_go/pull/74.

Bara isolerad lokal kopia, tillfällig PostgreSQL/PGlite, syntetiska jobb och lokala paket har använts. Ingen uppladdning, molnmigration, workerdrift, riktig H-0013-körning eller slutprovsläsning har gjorts.

## Ursprungliga fynd före rättning

### P1 – databasåtergången kan passera kontrollen samtidigt som ett jobb köas

`supabase/rollback/0005_h0013_queue_down.sql:4–13` testar bara om H-0013-rader är synliga vid kontrolltillfället. Den samordnar inte kontrollen och funktionsändringarna med köningens advisory lock/underhållsspärr. En redan påbörjad men ännu inte committad köning är osynlig för kontrollen. Återgången kan då ta bort H-0013-funktionerna trots att det finns ett nytt köat H-0013-jobb när den är klar.

Oberoende prov med riktiga PostgreSQL-anslutningar och oförändrad SQL från återgångsfilen, uppdelad vid en deterministisk paus mellan kontroll och funktionsändring:

1. Anslutning A börjar en transaktion, kör den riktiga `research_enqueue_h0013` och får ett id, men committar inte.
2. Anslutning B kör återgångsfilens `BEGIN` och `DO`-kontroll. Den passerar eftersom A:s jobb ännu inte är synligt.
3. A committar. B fortsätter resten av den riktiga återgångsfilen och committar.
4. Resultatet är **1 köat H-0013-jobb och 0 kvarvarande research_enqueue_h0013-funktioner**. Återgången har alltså lyckats trots sin utlovade spärr mot befintliga jobb.

Samordna återgången med köning, inklusive redan påbörjade anrop, och testa båda ordningarna med riktiga anslutningar: köning först respektive återgång först. Använd en korrekt lås-/underhållsordning så att en lyckad återgång inte lämnar ett nytt H-0013-jobb efter sig; alternativt ska återgången avvisas utan schema-/dataförändring när köningen vinner. Radera inga försöksrader för att få kontrollen att passera.

Uppdatera också kodåtergången i `docs/fas2-driftsattning.md`: när 0005 redan finns räcker det inte att se en tom kö och sedan starta gammal kod medan H-0013 fortfarande kan köas. Stäng/samordna köingången eller gör den säkra databasåtergången innan den gamla workern får reservera jobb. Behåll den uttalade begränsningen att återgång vägrar när historiska H-0013-rader finns.

### P2 – revisionskontrollen kan rapportera fel trots korrekt journal

`services/research-worker/check-single-worker.sh:32` kör `journalctl ... | grep -q ...` under `set -o pipefail`. När grep hittar revisionen tidigt och stänger pipen kan journalctl få SIGPIPE om det finns mycket logg kvar. Pipen får då felstatus och skriptet påstår att revisionen inte syns.

Oberoende isolerat Bash-prov med samma pipeline, en syntetisk journalproducent som skriver den rätta revisionsraden först och därefter 1 MiB logg: matchningen finns, men kontrollen avvisas med **exit 141 (SIGPIPE)**. Ingen riktig journal eller systemd-tjänst ändrades.

Läs hela loggutmatningen i matchningssteget, till exempel med en matchare som inte avslutar tidigt, och behåll felhantering för verkliga journalctl-fel. Regressionstesta rätt revision tidigt i en stor textlogg, saknad revision och misslyckad journalhämtning. Att testa bara Bash-syntax och nyckelord fångar inte detta beteende.

## Verifierat

- Exakt PR-head kördes i en isolerad kopia med Git-objekt för samma commit så att paketeringstesterna verkligen kunde bygga den: **532 Python-testfall passerar**, inklusive **11 nya releasetestfall**. CI Engine check är grön på samma head. Lokal joblib-varning om fysiska CPU-kärnor påverkar inte utfallet.
- Ett eget paketbygge av `eb156502f0664f6bc3882cebdbd49b107dcce0aa` ger SHA256 **d8fda17ab9be853d3edab0d3d1dfd571708d4269a429178f8e1a892d1b8992e1**, identisk med rapporterat värde. Testerna bygger dessutom två gånger och verifierar reproducerbarheten.
- Paketets revisionsfil, filhashar, migrationsmetadata och verifiering av saknade/extra/ändrade filer fungerar lokalt. Ingen app-källkod eller hemlig env-fil följer med enligt kontrollerna. Detta är bygg-/integritetskontroll, inte ett godkännande att installera paketet.
- Workerns lås är semantiskt samma exklusiva fillås, nu utbrutet för test. Riktiga processer visar att andra workern blockeras och att låset släpps när första hållaren avslutas. Startloggen visar revisionsvariabeln. F2-602 återverifieras efter omstruktureringen.
- Den ordinarie samtidighetssviten passerar mot en tillfällig lokal **PostgreSQL 17 med åtta anslutningar**: en köning, idempotent nyckel, en reservation, ingen ny reservation under giltig lease, en publicering, gammal token spärrad och avbruten körning håller slotten. Det lokala servertestet behövde utökad sandboxbehörighet för delat minne; det kördes därefter utan molnanslutning.
- PGlite-testet för seriell återgång passerar: vägrar med synliga H-0013-rader, återställer funktionen/rättigheterna till 0004, behåller data och kan applicera 0005 igen. Fyndet ovan gäller konkurrens under återgången, som den sviten inte täcker.
- Båda ordinarie kötesterna körs lokalt även i denna granskning. Inga riktiga medlemskonton, JWT eller Supabase-anslutningar används.
- PR #73 är mergad som `d6f2eae`. Detta underlag ändrar inte H-0013:s utvärdering, frysta dataset eller forskningsbeslut. Stoppvägen från PR #73 gäller fortsatt.
- Migrationsordningen vid uppgradering, ny kod före 0005, kan behållas. Verifieringen av verkliga systemd-/katalogrättigheter, backup och installerad revision återstår till en godkänd driftsättning. Samtidighet mot Supabase/PostgREST är inte testad av lokal PostgreSQL.

## Git och checklista

Den gemensamma arbetskopian är ren och `main` och `origin/main` stod båda på `d6f2eae` vid kontrollen (0/0 commits). Det rapporterade äldre fast-forward-felet krävde därför ingen historikomskrivning eller tvingad uppdatering i denna granskning.

F2-602 är återverifierad; F2-605 är `in_progress` och inte godkänd för drift. Gemensam status: **29/40 verifierade**. Färdigt underlag ska inte räknas som utförd driftsättning.

**PR #74 är inte godkänd för merge ännu.** Nästa kontroll är en återgång som är säker vid samtidig köning och en revisionskontroll som fungerar med stor journal. Ingen molnåtgärd eller riktig forskningskörning ska göras för att rätta fynden. Inget strategiresultat är godkänt för papper/live.


## Omgranskning av rättningarna – 2026-11-02

Granskad PR-head: `e0c41ca80787b9e3308db7f33eb5910eb2370a31`, kod `d01dccd`, merge av granskningsunderlaget `7c138ad`. De tidigare fynden ovan är historik och är nu rättade.

- **P1 rättad:** återgången tar köningens advisory lock före kontrollen. Köfunktionen gör efter låset en ny kontroll av om köingången fortfarande finns. Detta täcker även en redan påbörjad funktionskörning som väntar på återgångens lås. Inga försöksrader raderas.
- Båda ordningarna verifierades mot riktig lokal PostgreSQL 17: köning först gör att återgången väntar och sedan vägrar med schema/data kvar; återgång först gör att väntande köning avvisas och inga H-0013-jobb lämnas kvar. Kontrollfallet utan återgångslås återger det gamla felet: 1 jobb och 0 funktioner. Den vanliga åttaanslutningssviten för köning/reservation/publicering passerar också.
- Återgångsplanen stoppar nu workern och stänger H-0013-ingången i databasen innan gammal kod får startas. Om historiska H-0013-rader gör att återgången vägrar behålls den nya koden och problemet rättas framåt. Det är en uttrycklig begränsning, ingen instruktion att radera historik.
- **P2 rättad:** kontrollen läser hela journalutmatningen innan matchning och skiljer på misslyckad hämtning och saknad revision. Ett eget prov med korrekt revision först och över 1 MiB efterföljande text passerar nu. Regressioner täcker tidig/sen träff, saknad revision, journalfel och att source inte kör kontroller; kontrollprovet med den gamla pipen ger fortsatt 141.
- Exakt PR-head kördes i isolerad kopia med samma Git-commit: **538 Python-testfall passerar**. De tre PGlite-sviterna (båda kötester och återgång) samt båda lokala PostgreSQL-samtidighetstesterna passerar. Samma ofarliga joblib-varning om fysiska CPU-kärnor förekommer. CI Engine check var fortfarande `IN_PROGRESS` vid senaste kontrollen; den ska vara grön före merge.
- Eget paketbygge av denna head ger **11dd7a0faabd24f8939ec2c64ea3d59b0d2a33787f0c710e3833d702e7b7378b** för `tradergo-research-e0c41ca80787.tar.gz`. Uppackat paket verifierar med 186 manifestfiler och rätt revision. Detta är granskningspaketet; ett paket från en senare mergecommit får ett nytt namn och SHA256 och ska byggas/verifieras separat.
- Worker-, H-0013- och utvärderingskoden är oförändrade i rättningen. F2-601 återverifieras för den nya kökontrollen; tidigare verifieringar av signalstopp, lås, arkiv och forskning gäller fortsatt.

Gemensam status: **29/40 verifierade**. F2-605 står kvar som `in_progress` eftersom paketet ännu inte är uppladdat, migrationen inte är applicerad och driftsmiljön inte är verifierad. Lokalt PostgreSQL-test är inte ett Supabase/PostgREST-test med riktiga JWT.

**Bedömning:** PR #74 och driftsättningsunderlaget är kodmässigt godkända för merge på `e0c41ca`, förutsatt grön CI och bevarad granskad kod. Inga öppna fynd kvar från denna granskning. Efter merge ska exakt slutlig commit och paket-SHA identifieras inför det separata driftbeslutet. Ingen uppladdning, molnmigration, driftsättning, riktig H-0013-körning, slutprovsläsning eller publicering har gjorts i omgranskningen. Inget är godkänt för papper/live.
