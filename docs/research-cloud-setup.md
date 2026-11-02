# Research Engine: molnanslutning

## Verifierat 2026-11-02

- SSH fungerar till dropleten som root med befintlig lokal DigitalOcean-nyckel.
- ED25519-värdnyckeln jämfördes med fingeravtryck från användarens Web Console.
- Servern har cirka 114 GB ledig disk och 3,4 GB tillgängligt minne.
- `/etc/tradergo/research.env` är root-ägd, rättighet 600, i katalog med rättighet 700.
- Supabase-servernyckeln är sparad på servern och används utan loggning.
- Användaren körde första-installationsfilen i Supabase SQL Editor med lyckat resultat.
- Alla åtta tabeller, inklusive research_members, gav därefter HTTP 200 från servern.
- Anrop utan API-nyckel gav HTTP 401. Detta verifierar API-grinden, inte RLS för
  en anonym session med publishable-nyckel eller en inloggad session.
- Användaren skapade sitt konto i Supabase Auth. Medlemsraden lades därefter till
  och verifierades via servern (HTTP 201 vid registrering). Ingen inbjudan skickades.
  RLS med en faktisk inloggad användarsession är fortfarande inte verifierad.

## Nästa steg: schema

`0001_research.sql` är en oförändrad kopia av schemat från lokal main fde66ae.
`0002_research_members.sql` begränsar läsning till manuellt godkända medlemmar
och spärrar klientskrivning tills validerad jobbkö och worker finns.
Det följer Supabases princip att kombinera tabellrättigheter och RLS:
https://supabase.com/docs/guides/database/postgres/row-level-security

Bygg första-installationsfilen med:

```bash
python3 scripts/build-research-bootstrap.py
```

Kör hela `supabase/research-first-install.sql` i projektets SQL Editor. Filen
körs i en transaktion och avbryter om någon forskningstabell redan finns, för att
undvika att ändra ett okänt schema. Vid fel: skicka feltexten, kör inte enstaka
delar på måfå. Filen använder inga hemligheter.

Detta är en manuell bootstrap, inte ett registrerat Supabase CLI-migrationsflöde.
Innan CLI-migrationer införs måste migrationshistoriken stämmas av med faktiskt
installerat schema. Kör inte 0001/0002 igen mot en bootstrappad databas.

Efter installation behöver medlemsåtkomst och RLS verifieras med medlems-,
icke-medlems- och anonym session. `research_members` är avsiktligt tom tills
administratören väljer vilka Auth-användare som ska ha åtkomst.

## Anslutningsadapter

`engine/traderlab/research_engine/supabase.py` läser en skyddad miljöfil och
erbjuder schemakontroll och paginerad läsning av stängda staplar. Den är fristående
från strategi-/backtestmotorn och innehåller ingen skrivning eller jobbexekvering.
Datasetlåsning, kontrollsummor, UTC-validering och datakvalitet återstår före forskning.

Fem isolerade tester kördes med:

```bash
PYTHONPATH=engine python3 -m unittest discover -s engine/tests -p test_supabase_connection.py -v
```

Adaptern har installerats separat på servern under
`/opt/tradergo-connection/20261102-v1`. Anslutningen kan kontrolleras där med:

```bash
PYTHONPATH=/opt/tradergo-connection/20261102-v1 python3 -m traderlab.research_engine check --env-file /etc/tradergo/research.env
```

Ingen bakgrundstjänst startas. Den skyddade miljöfilen läses som root för denna
engångskontroll; framtida worker ska ha ett separat tjänstekonto.

## Kvarstår

- SQL-installation och privilegierad REST-läsning fungerar. RLS och faktisk
  tabellstruktur/constraints behöver fortfarande verifieras separat.
- Kömigration 0003 är installerad och workern är aktiverad. API-flöde, medlems-RLS
  och resultatvisning i Research Labs webbgränssnitt är verifierade. Desktopappen är
  lokalt byggd; native GUI-automation gav timeout och är inte ett verifierat desktop-inloggningstest.
- Koden baseras på huvudkopians `fde66ae`. Ett tidigare mergeförsök i den gamla
  arbetsgrenen avbröts utan kvarstående konflikter. Releaseversionen ska verifieras mot respektive workflow-körning.
- Endast teknisk utforskning har körts; ingen strategi har godkänts för papper/live.

Servernyckeln får aldrig kopieras till frontend, Git eller chatt. Läs den endast
på servern. Nyckeln ger privilegierad åtkomst och ersätter inte en separat
databas-/Management API-anslutning för migrationskörning.

## Leverans 2026-11-02: jobbkö och Research Lab

Ny kod har byggts mot huvudkopians commit `fde66ae` i en isolerad stagingkatalog,
så att gamla arbetsgrenens orelaterade appkonflikter inte behöver föras in.

### Installationsordning

1. Kör **endast** `supabase/migrations/0003_research_queue.sql` i SQL Editor.
   0001/0002 är redan installerade genom första-installationsfilen och ska inte köras igen.
2. Kör serverns `services/research-worker/activate.sh` efter lyckad migration.
3. Kontrollera `systemctl status tradergo-research-worker` och journalen.
4. Starta en ny appbyggnad, öppna Research Lab och logga in med Supabase Auth.
5. Köa ett litet historiskt experiment och verifiera resultat, avbrott och behörighet.

Serverkoden finns under `/opt/tradergo/releases/20261102-research-v1` med
symlänken `/opt/tradergo/current`. Pythonmiljön finns i `/opt/tradergo/venv`.
Workern körs som systemanvändaren `tradergo`, inte root. Systemd levererar
servernyckeln med `LoadCredential`; källfilen behåller rättigheten 600.
Rådata, manifest och arbetsfiler finns i `/var/lib/tradergo` (rättighet 700).
Ingen inkommande workerport öppnas.

### Kontrakt och avgränsning

- En global databas-slot med 90 sekunders lease. Heartbeat var tionde sekund.
- Varje reservation får ny token. Resultat publiceras transaktionellt endast med
  aktuell token. Avbrutna jobb håller slotten tills processen stoppats eller leasen löpt ut.
- Övergivna jobb kan tas om högst tre gånger; alla försök räknas på körningsraden.
- Användaren kan ha högst fem köade/pågående jobb. Global kögräns 100.
- RPC kräver medlemskap. Ingen direkt klientskrivning till tabeller tillåts.
- En separat child-process beräknar utan servernyckel. Förlorad lease eller
  anslutning stoppar processen. Tidsgräns 30 minuter.
- Worker och UI stöder endast **UTFORSKNING**, BTCUSDT, spot eller USDⓈ-M, 1H/4H/1D.
  Spot är long/platt; terminer kan vara long/short med 1x och faktisk funding.
- Perioden måste vara minst 30 dygn inom 2020-01-01 till 2025-01-01, exklusivt slut.
  Befintligt fryst slutprov läses inte. Registrerade optimeringskörningar exponeras
  inte via denna kö; befintlig fas1-pipeline och beslut ändras inte.
- Fasta kostnader 10/2/5 bps och kapital 100000. Parametrar valideras mot strategiversion.
- 600 staplars uppvärmningsfönster (tidigast 2019-09-01). Positionen startar platt
  vid begärd period; första signalen fylls tidigast nästa öppning.
- Binance-månadsarkiv bevaras med CHECKSUM. Fullständiga periodgränser, ändliga värden,
  OHLCV, ordning, tidsjustering och internluckor kontrolleras. Funding kräver en
  faktisk avräkning inom 60 sekunder efter varje 8h-gräns; originaltiden bevaras
  och maximal fördröjning redovisas. Inga luckor fylls och inga utstickare tas bort.
- Andra börskällan och mark-price-data är inte verifierade. Resultaten är utforskning
  och kan inte automatiskt ge READY_FOR_PAPER.
- Resultatet sparar konfiguration, kodhash, runtimeversioner, dataset-hash,
  källfilernas SHA-256, kvalitetsrapport, affärer, nyckeltal, kurvor och baslinje.
  Kanoniska OHLCV-/fundingtabeller är en cache; körningens manifest är versionskällan.
- Sessionstoken och refresh-token hålls endast i minnet i Research Lab. Lösenordet
  sparas inte. Frontend innehåller en offentlig publishable-nyckel, ingen servernyckel.
- Tauri CSP tillåter HTTPS endast till det specifika Supabase-projektet utöver lokala anrop.

### Drift och återställning

```bash
systemctl status tradergo-research-worker
journalctl -u tradergo-research-worker --since today
systemctl stop tradergo-research-worker
systemctl start tradergo-research-worker
```

Systemd begränsar minne till 2 GB, CPU till 150 % och startar om vid processfel.
En kontrollerad tjänstestopp markerar aktiv körning som failed; ett hårt avbrott
återtas via lease efter 90 sekunder. Inga färdiga resultat skrivs över vid återstart.
Vid rollback: stoppa tjänsten, peka `current` till tidigare kompatibel release och
starta igen. Rulla inte tillbaka SQL genom att radera tabeller. Säkerhetskopiera
Supabase-databasen före vidare schemabyte och bevara `/var/lib/tradergo` samt relevanta
kodreleaser för reproducerbarhet. Automatisk backup och extern larmkanal är ännu inte konfigurerade.

### Verifiering

- 134 Python-tester lokalt; 47 frontendtester; TypeScript/Vite-bygge godkänt.
- SQL-migrationerna körda i isolerad PostgreSQL/PGlite med Supabase-liknande roller.
  Medlem/icke-medlem/anonym, begränsade grants, idempotent köning, avbrott,
  lease-återtagning, tre-försöksgräns och fencing av gammal token testade.
  PGlite använder en anslutning: riktig fleranslutningskonkurrens återstår i Supabase.
- Research Lab-inloggningsvyn visuellt granskad i lokal webbförhandsvisning.
- Riktig 4H-historik 2022-01-01 till 2022-03-01 kördes två gånger på servern:
  identiska resultat, 954 staplar inklusive uppvärmning, 0 luckor, 0 feljusteringar,
  sex kontrollsummerade källfiler. Båda körningarna tog totalt 7,15 s, toppminne 80,1 MiB.
- Detta är inte ännu ett godkänt end-to-end-test genom live-kön och den installerade desktopappen.
- Serverns Linux-miljö: 134 Python-tester passerar. Rust: fmt och clippy godkända,
  48 tester passerar och ett befintligt nätverkstest är ignorerat.
- Anonym REST-åtkomst med den riktiga publishable-nyckeln nekades med HTTP 401
  för runs, run_results, candles och research_members.
- Riktig spot 1H (2022-01-01 till 2022-03-01) och 1D (2022-01-01 till 2023-01-01)
  passerade med noll luckor/feljusteringar i de perioderna. Detta identifierar inte
  orsaken till eventuella tidigare rapporterade feljusteringar i appens insamlare.
- Riktig USDⓈ-M 4H (2022-01-01 till 2022-03-01) passerade med 177 funding-händelser,
  högst 28 ms fördröjning från avräkningsgränsen och bevarade originaltidsstämplar.
- Femårsperioden 2020-01-01 till 2025-01-01 är **inte godkänd**: spotarkivet saknar
  4H-stapeln 2020-02-19 12:00 UTC. Terminsförsöket stoppades vid saknat månadsarkiv
  i det begärda uppvärmningsfönstret. Inga kompletteringsstaplar skapades.
- Full datatäckning, andra datakällan och faktiskt desktop-GUI-test återstår för
  Fas 1-slutgodkännande. Fleranslutningskonkurrens, användarsessions-RLS, aktiv
  worker och lokalt desktopbygge verifierades i följande driftstest.


## Driftstest efter migration 0003

- Migrationen kördes av användaren i Supabase SQL Editor. Workern är enabled och
  active/running på DigitalOcean som tradergo, med 0 omstarter efter korrigering.
- Driftstarten hittade ett credential-fel: Systemd exponerar privata credentials
  read-only med 0440 i tjänstens mount. Valideringen accepterar nu detta endast
  under den angivna privata `/run/credentials/`-katalogen. Originalfilens skydd
  behålls. Ett regressionstest täcker både tillåten och otillåten grupp-läsbar fil.
- Riktig medlemssession, icke-medlem och anonym åtkomst verifierades mot Supabase.
  Medlem kan inte anropa worker-RPC eller skriva direkt till runs.
- Två samma-konfiguration-jobb gick från kö till workern och sparade identiska
  resultat. Samma request_key skapade inget dubbelt jobb.
- Avbrutet köjobb förblev cancelled. Ogiltiga parametrar gav failed med feltext.
  Försök att använda perioden efter 2025 nekades före köning. Alla testjobb bevaras.
- Två samtidiga HTTP/databasanslutningar försökte reservera samma jobb: exakt en
  lyckades. Efter utgången lease och omstart återtogs jobbet och slutfördes med
  attempts=2. Gammal token kunde inte skriva över resultatet. Detta är ett
  tjänste-/lease-test, inte en omstart av hela dropleten.
- Research Labs verkliga inloggning, körningslista, statistik, diagram och affärer
  granskades i webbförhandsvisning mot live-Supabase, utan simulerade resultat.
- Två tillfälliga Auth-testkonton användes för icke-medlem och UI-kontroll och
  togs bort efter testerna. Inga mejl skickades och användarens lösenord ändrades inte.
- Senaste tjänstekontroll: ActiveState=active, SubState=running, NRestarts=0,
  MemoryCurrent cirka 20 MiB, MemoryPeak cirka 64 MiB för den systemd-starten.
- Lokal Mac-testapp byggd ad-hoc, ingen notifiering/publicering/release:
  `app/src-tauri/target/release/bundle/macos/TraderGO.app`. Den ersätter inte
  automatiskt `/Applications/TraderGO.app` och är inte notariserad.
- Native appkontroll kunde inte verifieras eftersom UI-verktyget gav timeout
  vid val av den nya appen. Faktisk desktop-inloggning återstår att prova manuellt.
- Rå verifieringsrapport: `docs/research-cloud-verification.json`.
- Källändringarna samlas i Research Lab-leveransen för test- och Stable-kanalen.

Detta godkänner den första molnkopplingen för historisk utforskning, inte hela
Fas 1, strategiers lönsamhet, papperstest eller livehandel. Automatisk backup och
extern larmkanal återstår, liksom tidigare dokumenterade historikbegränsningar.
