# Fas 2: driftsättning av H-0013-kön (F2-605), plan för granskning

Detta är underlaget före driftsättning. **Inget är gjort på servern eller i Supabase.** Migrationen 0005 är inte
applicerad, inget paket är uppladdat och workern kör fortfarande den tidigare releasen. Varje steg nedan kräver
att granskningen är godkänd och att Edwin uttryckligen säger ja. Ingen riktig H-0013-körning startas i samband
med driftsättningen; den kräver ett separat ja efteråt.

## Vad som ingår

| Del | Fil | Vad den gör |
|---|---|---|
| Paket | `scripts/build-research-release.sh` | Bygger `tradergo-research-<commit12>.tar.gz` ur en commit med `git archive`: motor, tjänstefiler, migrationer, register, protokoll, frysta auditfiler och Fas 1-underlag. Paketet innehåller `REVISION.env` (`TRADERGO_REVISION=<commit>`) och `release.json` (SHA-256 per fil, migrationer, krävd migration). Samma commit ger samma SHA-256, så granskaren kan bygga om och jämföra. |
| Verifiering | `scripts/verify-research-release.py` | Kontrollerar ett uppackat paket mot `release.json`: inga saknade, extra eller ändrade filer, och `REVISION.env` och katalognamnet ska stämma med commiten. Körs av `install.sh` innan något installeras. |
| Tjänst | `services/research-worker/tradergo-research-worker.service` | Läser `EnvironmentFile=/opt/tradergo/current/REVISION.env`. Saknas filen startar tjänsten inte. I övrigt oförändrad: en tjänst, `TimeoutStopSec=45`, `MemoryMax=2G`, `CPUQuota=150%`, skrivrätt bara i `/var/lib/tradergo`. |
| Worker | `worker.py` | Loggar `revision=<commit>` vid start. Låset på datakatalogen ligger i `acquire_single_worker_lock`, så en andra worker avbryts direkt. Den kontrollerade stoppvägen från PR #73 (20 s, sedan SIGKILL) ryms inom 45 s. |
| En worker | `services/research-worker/check-single-worker.sh` | Bara läsning. Kontrollerar att den nya tjänsten är aktiv och att den äldre `tradergo-worker.service` varken är aktiv eller aktiverad. Exakt en workerprocess, och det är tjänstens MainPID. Låset är taget. Paketet i `current` verifierar, och processens `TRADERGO_REVISION` och journalen visar paketets commit. |
| Samtidighet | `scripts/test-h0013-concurrency.mjs`, `scripts/run-h0013-concurrency-local.sh` | Migrationerna 0001–0005 i en tillfällig lokal PostgreSQL 17 med åtta riktiga anslutningar. Vägrar allt utom localhost. |
| Återgång | `supabase/rollback/0005_h0013_queue_down.sql`, `scripts/test-h0013-rollback.mjs` | Tar bort H-0013-funktionerna och återställer `research_finish` exakt som i 0004. Vägrar om någon H-0013-körning finns, och raderar ingen data. |

## Ordning (efter godkänd granskning och uttryckligt ja)

Koden går först och migrationen sist. Den nya koden fungerar med databasen före 0005, eftersom inga H-0013-jobb
kan köas förrän 0005 finns. Den gamla koden med 0005 skulle däremot skicka ett H-0013-jobb till Fas
1-reproduktionen, där det misslyckas. Därför appliceras 0005 först när den nya workern kör och är kontrollerad.

1. **Förutsättningar.** PR för F2-605 är mergad och granskad. Supabase-backupen och DigitalOceans backup är
   bekräftade för dagen, och en egen export tas med `traderlab.research_engine.backup` (se
   `docs/research-backup-restore.md`). Inga körningar är `running`.
2. **Bygg paketet lokalt** från den mergade commiten på `main`:
   `scripts/build-research-release.sh <commit>`. Notera SHA-256. Granskaren bygger samma commit och får samma
   värde.
3. **Ladda upp och verifiera** till `/opt/tradergo/releases/`. Kontrollera SHA-256, packa upp och kör
   `python3 scripts/verify-research-release.py /opt/tradergo/releases/tradergo-research-<commit12>`.
4. **Stoppa workern kontrollerat:** `systemctl stop tradergo-research-worker`. Vänta tills den är `inactive` och
   kontrollera i Supabase att slotten är tom (`research_worker_slot.run_id is null`). Pågår en körning väntar man
   ut den. Avbryts den, sparas försöket enligt PR #73.
5. **Installera** med `services/research-worker/install.sh /opt/tradergo/releases/tradergo-research-<commit12>`.
   Skriptet verifierar paketet, byter `current` och installerar tjänstefilen. Det startar ingenting.
   Den föregående releasen ligger kvar orörd.
6. **Starta** med `systemctl start tradergo-research-worker` och kör
   `services/research-worker/check-single-worker.sh`. Workern synkar registret vid start, så H-0013 hamnar i
   `hypotheses` från det committade registret.
7. **Applicera 0005** i Supabase SQL Editor, en gång och bara den filen. Verifiera utan att köa något:
   - `select proname from pg_proc where proname in ('research_enqueue_h0013','research_h0013_result_ok');`
     ger två rader.
   - `has_function_privilege('anon','public.research_enqueue_h0013(uuid)','execute')` är `false`,
     `has_function_privilege('authenticated','public.research_enqueue_h0013(uuid)','execute')` är `true`, och
     `has_function_privilege('authenticated','public.research_h0013_result_ok(jsonb)','execute')` är `false`.
8. **Kontrollera igen** med `check-single-worker.sh` och journalen (`journalctl -u tradergo-research-worker`).
   Ingen H-0013-körning köas i samband med detta.

## Återgång

Ordningen är omvänd mot driftsättningen: H-0013-kön stängs i databasen innan den gamla koden får reservera
jobb. Den gamla workern har ingen H-0013-ingång och skulle annars skicka ett H-0013-jobb till Fas
1-reproduktionen.

1. **Stoppa workern kontrollerat:** `systemctl stop tradergo-research-worker`. Vänta tills den är `inactive`. Ett
   pågående jobb avbryts, och dess försök sparas enligt PR #73.
2. **Stäng kön i databasen** (om 0005 är applicerad): kör `supabase/rollback/0005_h0013_queue_down.sql` i SQL
   Editor. Skriptet tar samma rådgivande lås som all köning:
   - Har en köning redan låset, väntar återgången tills köningen är klar. Den nya körningen syns då, och
     återgången vägrar utan att ändra något.
   - Startar en köning medan återgången har låset, väntar den. När låset släpps är `research_enqueue_h0013` borta,
     och köningen avbryts (`H-0013-kön är stängd`) innan något sparas.
   - Finns H-0013-körningar, även historiska, vägrar återgången. Inga resultat eller försök raderas för att den
     ska gå igenom. Då stannar databasen på 0005, och den nya koden ska vara kvar (gå till steg 3 bara om
     återgången lyckades).
3. **Byt tillbaka koden** först när 0005 är borttagen, eller när 0005 aldrig applicerades: peka `current` på den
   föregående releasen (`ln -sfn /opt/tradergo/releases/<föregående> /opt/tradergo/current`), installera den
   releasens tjänstefil, kör `systemctl daemon-reload` och starta.
4. **Kontrollera** med `check-single-worker.sh` från den releasen (finns den inte där: `systemctl is-active`,
   `pgrep -f traderlab.research_engine.worker` och journalen).

Kan återgången inte köras eftersom H-0013-körningar finns, är den gamla koden inte ett säkert läge. Rätta då
felet i den nya releasen och driftsätt den igen, i stället för att backa koden.

**Data:** inget i återgången tar bort data. Försöksfilerna i `/var/lib/tradergo/h0013-attempts` ligger kvar.
Efter en lyckad återgång kan 0005 appliceras igen.

## Verifierat lokalt (ingen server, inget moln)

- `scripts/run-h0013-concurrency-local.sh`: åtta riktiga anslutningar mot PostgreSQL 17 (embedded-postgres i en
  tom temp-katalog). Exakt en köning vinner, samma `request_key` ger samma körning och exakt en worker reserverar.
  Under giltig lease reserveras inget. Exakt en av samtidiga publiceringar lyckas. Gammal token publicerar aldrig
  medan en ny worker tar om jobbet (försök 2), och en avbruten körning behåller slotten. Utan det rådgivande låset
  i köningen (med en kort `pg_sleep` som vidgar fönstret) fångar testet kapplöpningen.
- `scripts/run-h0013-concurrency-local.sh test-h0013-rollback-concurrency.mjs`: återgång och köning samtidigt
  med riktiga anslutningar. När köningen startar först väntar återgången och vägrar sedan utan ändring. När
  återgången startar först avbryts den väntande köningen, och inget H-0013-jobb blir kvar. Kontrollen visar att
  samma kapplöpning utan låset lämnar 1 jobb och 0 funktioner. Tas köningens kontroll efter låset bort, blir ett
  jobb kvar.
- `scripts/test-h0013-rollback.mjs` (PGlite): vägrar med H-0013-körningar, återställer `prosrc`, inställningar och
  rättigheter för `research_finish` exakt som en databas med bara 0001–0004, behåller data, och 0005 kan
  appliceras igen.
- `engine/tests/test_research_release.py`: paketet är reproducerbart och verifierar. Ändrade, extra och saknade
  filer samt fel revision avvisas. Inga hemligheter ingår. Tjänsten läser `REVISION.env`, och `install.sh`
  verifierar före installation. Kontrollskriptet ändrar ingenting. En andra worker kan inte ta låset (riktiga
  processer), och workern loggar sin revision. Revisionskontrollen godkänner en tidig träff i 1 MiB journal och
  avvisar både saknad revision och misslyckad `journalctl`. Den tidigare pipen gav exit 141 (SIGPIPE) i samma prov.

## Kvar efter detta underlag

- Riktig driftsättning och migration enligt ordningen ovan, med ja från Edwin.
- Faktiska systemd-rättigheter och katalogrättigheter på dropleten kontrolleras där, i steg 5–8.
- Samtidighet mot Supabase själv (pooler, RLS med riktiga JWT) är inte provad. Det lokala testet använder samma
  SQL men en egen PostgreSQL.
- Larm och övervakning ingår inte.
