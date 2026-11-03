# Fas 2: sluttestplan för installerad Mac-app och inloggat flöde (arbetsområde 8)

Skriven 2026-11-03 för granskning. Inget i planen är utfört än. Den täcker F2-801 till F2-805 och skiljer på
kontroller som går att göra **utan** en riktig forskningskörning och kontroller som **kräver** den riktiga H-0013-körningen.
Slutprovet (2025-01-01 och framåt) förblir oläst i hela planen. Ingen strategi aktiveras för papper eller live
automatiskt (CLAUDE.md, regel 1 och 5).

## Utgångsläge

| | |
|---|---|
| Driftsatt worker | `b44d3cecaac6…` (jämförelsekurvor), exakt en worker, kontrollerad 2026-11-03 (`docs/fas2-driftsattning-utfall-b44d3ce.md`) |
| Databas | 0001–0005 applicerade, 0 H-0013-körningar, H-0013 utan beslut |
| Installerad Mac-app | Stable `v0.1.20`, byggd från `1f2b6b1`. Den saknar Research Lab-vyn för H-0013 (#77) och jämförelsekurvorna (#78). |
| Kod på `main` | `a32f4ab` (app, motor och worker med #77 och #78) |
| Granskningsbygge | Lokalt Mac-bygge från `a32f4ab`, se nedan. Inte installerat, inte publicerat. |

Följden är att H-0013-delarna av F2-802 och F2-803 inte kan provas i den installerade appen förrän en ny version
med #77 och #78 är installerad: antingen det lokala granskningsbygget som separat kopia, eller en testkanal-
eller Stable-release efter beslut.

## A. Utan riktig forskningskörning (kan göras nu)

### A1. Automatiska kontroller (F2-801)

| Kontroll | Kommando | Godkänt när |
|---|---|---|
| Motor | `cd engine && .venv/bin/python -m pytest` | Alla passerar (senast 553) |
| App | `npm --prefix app test && npm --prefix app run build` | Alla passerar (senast 118) och bygget lyckas |
| Appens Rust | `cd app/src-tauri && cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test` | Inga fel |
| Universe | `npm --prefix apps/trader-go-universe test && npm --prefix apps/trader-go-universe run build && cargo test --manifest-path apps/trader-go-universe/src-tauri/Cargo.toml` | Inga fel (Universe är oförändrad i Fas 2) |
| Kö i PGlite | `node scripts/test-h0013-queue.mjs`, `test-research-queue.mjs`, `test-h0013-rollback.mjs` | Alla PASS |
| Samtidighet | `scripts/run-h0013-concurrency-local.sh` och `… test-h0013-rollback-concurrency.mjs` | Alla PASS (lokal PostgreSQL 17, aldrig molnet) |
| Paket | `scripts/build-research-release.sh <commit>` två gånger och `verify-research-release.py` | Samma SHA-256, och verifieringen godkänner |
| CI | App check, Engine check och Windows-bygge på samma commit | Gröna |

**Första körningen av A1, 2026-11-03 på `a32f4ab` (lokalt, Mac):**

| Kontroll | Utfall |
|---|---|
| Motor | PASS, 553 tester |
| App | PASS, 118 tester, och bygget lyckas |
| Universe | PASS |
| Kö i PGlite (tre skript) | PASS |
| Samtidighet i lokal PostgreSQL 17 (två skript) | PASS |
| Appens Rust | **FAIL.** `cargo fmt` och `clippy` går igenom, men 43 av 44 tester (1 ignorerat nätverkstest). `market::runner::tests::reconnects_after_a_drop_catches_up_and_stops_cleanly` faller deterministiskt, 8 av 8 gånger. |

Rust-felet ligger i marknadsinsamlingens befintliga test (`app/src-tauri/src/market/runner.rs`, senast ändrad
2026-11-01) och inte i Fas 2-koden. Testets fixtur `T0` är låst till 2026-11-01 08:00 UTC (`sync.rs`), medan
insamlingen räknar luckor mot den verkliga klockan (`now_ms()`). När klockan har passerat fixturens staplar blir
utfallet 4 stängda staplar i stället för 6.

**Rättat i PR #80:**
- `Runner` läser väggklockan via en injicerad `Clock`. Den är alltid `now_ms` i appen, och `with_clock` finns bara i
  tester.
- Testet styrs av en fast testklocka, med alla ursprungliga kontroller kvar och oförändrade tidsgränser.
- 60 upprepade körningar passerar. Med väggklockan, eller med en senare klocka, faller testet igen.
- `fmt`, `clippy` och hela Rust-sviten (44 + 4 tester, 1 ignorerat nätverkstest) passerar.
- Väntar på granskning.

### A2. Installerad Mac-app med granskningsbygget (F2-803, delvis F2-802)

**Granskningsbygge 2026-11-03:**
- byggt lokalt från ren `a32f4ab` med `npm --prefix app run tauri -- build --bundles app --config '{"bundle":{"createUpdaterArtifacts":false}}'`, som `scripts/install-macos.sh` men utan installation;
- `app/src-tauri/target/release/bundle/macos/TraderGO.app`: arm64, program-id `com.seastick.tradergo`, ad hoc-signerad, `codesign --verify --deep --strict` godkänner, inte notariserad;
- version 0.1.0, eftersom release-flödet sätter versionen, och byggcommit `a32f4ab` utan `+ändrad`;
- gränssnittet innehåller fliken "Fas 2 · H-0013" och jämförelsekurvorna;
- för granskning packad som `dist/mac-review/TraderGO-a32f4ab-arm64-review.zip`, SHA-256 `0a92c8ac5be64bba938233bfd7b62e2d0c5036ba99c3595482e48ddfdf29f2a2` (git-ignorerad);
- **inte installerat, inte publicerat.**



Bygget installeras **som separat kopia**, till exempel `~/Applications/TraderGO granskning.app`, så att Stable-appen i
`/Applications` lämnas orörd. Kopian har samma program-id och samma lokala data, så papperstrading och
inställningar ska bara läsas, inte ändras. Inga order finns i appen.

1. **Start och version:** appen startar, och toppfältet och Status visar commit `a32f4ab` (version 0.1.0, eftersom
   versionen sätts av release-flödet). Utan nät visas en rad under Status och ingen dialog.
2. **Fas 1 utan inloggning:** Research Lab → Registrerade resultat visar H-0009 till H-0012 med REJECT, diagram,
   walk-forward och affärer, utan SIM-märkning. Marknad och Papper öppnas som förut.
3. **H-0013 utan inloggning:** fliken "Fas 2 · H-0013" visar de låsta inställningarna och "Logga in för att se körningar".
   Inga fält går att ändra.
4. **Inloggning:** med Edwins medlemskonto. Felaktigt lösenord ger ett tydligt fel. Rätt lösenord visar fliken med
   "Inget resultat ännu", inga H-0013-körningar och förberedelsekortet. **Knappen "Köa H-0013" trycks inte.**
5. **Utforskning:** listan visar de befintliga utforskande körningarna och inga H-0013-körningar.
6. **Anslutningsfel:** stäng av nätet med inloggad session. Ett fel visas, och appen hänger inte. Slå på nätet:
   listan återhämtar sig inom 5 sekunder utan omstart. Logga ut och in igen.
7. **Utloggning:** sessionen försvinner, och inga körningar eller resultat visas.
8. **Ljust och mörkt tema:** fliken H-0013 och Fas 1-vyn är läsbara i båda.

### A3. Kön från app till worker och resultat, utan H-0013 (F2-802, mekaniskt)

Flödet från app till kö, worker och resultat provas med **en kort utforskande körning**, till exempel
`ema_adx_trend`, um, 4h, 2022-01-01 till 2022-03-01. Den läser bara utvecklingsperioden, ger aldrig ett beslut
och har körts förut. **Den kräver ändå ett separat ja,** eftersom den använder den riktiga kön och workern.

- Köa från appen. Status går från "I kö" till "Körs" till "Klar", och förloppet stiger.
- Resultatet visas med UTFORSKNING-märkning. `run_results` har en rad.
- Avbrott: en andra körning avbryts från appen och blir "Avbruten". Workern stoppar barnprocessen och släpper slotten.
- `check-single-worker.sh` godkänner efteråt, och journalen saknar varningar.

### A4. Release-flödet utan Stable (förberedelse för F2-804)

Kräver ett **separat ja**, eftersom det publicerar en testversion till den publika testsidan.

1. Run workflow med `channel = test` från `main`. `version`, `build-windows`, `build-macos` och `publish` ska bli
   gröna, och `approve` ska hoppas över.
2. `…/test/latest.json` ska ha `darwin-aarch64`, `darwin-x86_64` och Windows.
3. Testappen "Trader_go Updater Test" installeras på Macen, och A2:s punkter 1–8 upprepas där.

## B. Kräver den riktiga H-0013-körningen (efter separat beslut)

Startas bara efter Edwins uttryckliga ja, från appen, med tvåstegsförberedelsen. Detta är den enda registrerade
körningen: ett resultat finns sedan kvar, och en ny körning kräver ett nytt beslut.

1. **Köning (F2-802):** appen visar "I kö", därefter "Körs" med förlopp och försök "1 av 3".
   Workern loggar `run=… started`, och `check-single-worker.sh` godkänner under körningen.
2. **Under körningen:** inga varningar i journalen. Om något avbryts sparas ett försök i
   `/var/lib/tradergo/h0013-attempts/` enligt PR #73, och det redovisas.
3. **Klar inom 2 timmar:**
   - `run_results` har exakt en rad, och databasens kontrakt har godkänt den: fem kriterier, ett beslut som följer
     dem, och `holdout_loaded=false`.
   - Försöksfilen `…-completed.json` finns på servern.
4. **Appen visar resultatet (F2-704, F2-705):**
   - beslutet (REJECT eller MORE_RESEARCH), kriterierna och t mot 2,67;
   - stress, osäkerhet, permutation och Deflated Sharpe;
   - lägen, kandidatval, jämförelser och jämförelsekurvor;
   - affärer och spårbarhet med revisionen `b44d3ce` och det frysta datasetet.
   - Inget ska stå som saknat. Står något som saknat ska det redovisas, inte döljas.
5. **Avstämning:** resultatets dataavtryck och de 120 arkivens manifest stämmer. Kriterierna räknas om för hand från
   de sparade nyckeltalen.
6. **Registret:** beslutet förs in som en ny rad i `research/registry.md` i en egen commit efter granskningen
   (`granska-backtest`). Det görs aldrig automatiskt av kön.

## C. Stable och godkännande

- **F2-804:** när A är godkänt, och B om den beslutats före släppet: Run workflow med `channel = stable`, `approve`
  i ärendet, och därefter kontroll av den installerade versionen och commiten i appen och av checklistan. Stable
  publiceras bara efter ett uttryckligt ja.
- **F2-805:**
  - Fas 2-godkännandet dokumenteras med resultat, kända svagheter och kvarvarande begränsningar.
  - Ett eventuellt slutprov är ett **separat beslut**, och bara aktuellt om beslutet blir MORE_RESEARCH. Det öppnar
    2025-01-01–2026-09-30 en gång.
  - REJECT stänger H-0013 utan slutprov.
  - Ingen papper- eller liveaktivering sker automatiskt.

## Underlag som sparas

Varje kontroll redovisas med commit eller revision, tid i UTC, kommando eller skärm, utfall och eventuella
avvikelser. Det förs in som evidens i `docs/fas2-status.json`. Skärmbilder från appen sparas i
granskningsunderlaget, utan lösenord och sessionstoken.
