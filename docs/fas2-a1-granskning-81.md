# Fas 2 – A1 och Mac-förberedelser, PR #81

Granskad head `66d59bb396cd6a0e3dbb6456f416c699a4906cb7`, 2026-11-03. PR: https://github.com/SEASTICK/Trader_go/pull/81. Byggcommit `6c16638823688c3577884ba2557a444d70e7df08`. Separat main-kopia användes för granskning och dokumentation eftersom den gemensamma arbetskopian stod på Claudes aktiva PR-gren. Den grenen ändrades inte.

## A1 verifierad

- Mergecommiten och CI-head `be9d958` har exakt samma träd, `7228743fd5d88a09b0d6ad3e198fc8c2394bd2d3`. App, Rust och Windows är gröna på PR-head; App och Rust på main är gröna.
- App-/motorkod och Rust-rättning är oförändrade mot godkänd `4e85f4e`. Tidigare oberoende kontrollkedja täcker 553 Python-/118 frontendtester och bygge samt Rust fmt, clippy, 44 enhetstester + 4 integrationstester, 1 ignorerat nätverkstest och 20 egna upprepningar. Oförändrade tester kördes inte om enbart för dokumentändringen.
- Universe omkörd oberoende: säkerhetsskript PASS för 15 källfiler, frontendbygge PASS, Rust **27 PASS och 2 ignorerade prestandatester**. Npm-testet hittar inga Vitest-testfiler och accepterar detta med `--passWithNoTests`; det är inte passerande frontend-enhetstester.
- Tre PGlite-kö-/återgångstester samt båda samtidighetstesterna mot tillfällig lokal PostgreSQL 17 omkörda: PASS. Inget moln användes.
- Eget workerpaket byggt två gånger från `6c16638`: byteidentiskt, SHA-256 **3f477aecb886ae630d878fe4f5320f93aa1d23430f50559c64de717b227f112d**. Egen uppackning och paketverifiering godkänner 186 filer.

**F2-801 godkänns. Status: 36 av 40 verifierade.** Det gäller automatiska kontroller, inte installerad Mac-app eller riktig forskning.

## Mac-paket verifierat utan start

Zip-filens SHA-256 är oberoende verifierad: **df0436dc6517bd0f7779914e7e3c28a8d9f6e050febd6245e1c2b10f19463cfc**. Egen separat uppackning och `codesign --verify --deep --strict` godkänner appen. Signaturmetadata, plist och Mach-O bekräftar ad hoc, inget Team ID, arm64, `com.seastick.tradergo`, version 0.1.0. Detta är inte notariseringsbevis eller start-/inloggningstest. Stable ändrades inte.

## P2 – backupmanifestet innehåller en felaktig självpost

A2-underlaget i `docs/fas2-sluttest-plan.md` anger manifestkontroll för `~/TraderGO-backups/a2-20261103T102650Z/`. Oberoende kontroll av alla poster fallerar för **`./MANIFEST.sha256` självt**. Posten anger hash `3cd1e7fd4631acd43c2a09b209a23565bd911b68cf9b5f6e5294cc2e700b16f8`, medan filens faktiska hash är `9d5c0f533cf000ae29ebbc7a3e01e7814d4fe19fecb96d9ebca8906a431b08f4`.

Alla **23 övriga filer matchar** sina kontrollsummor. Samtliga **nio SQLite-filer**, inklusive WebKit-databaserna, ger `pragma integrity_check=ok` i separata read-only/immutable-anslutningar. Inga tabellrader lästes ut. Ingen korruption har påvisats i backupinnehållet. Felet är att manifestet tar med sig självt; en full kontroll enligt återställningsplanen skulle alltid rapportera fel.

Uteslut manifestfilen vid generering, verifiera samtliga 23 innehållsfiler och redovisa manifestets egen hash separat om den behövs. Ange 23 innehållsfiler plus manifest, 24 filer totalt. Ändra inte backupinnehållet för att få kontrollen att passera. Använd samma regel vid en ny backup före A2. Ingen backupfil eller manifest ändrades av granskningen.

## Bedömning

A1 och Mac-paketets tekniska kontroller är godkända. **PR #81 behöver kompletteras för manifestfyndet innan A2 startas.** F2-803 förblir `todo`. Efter rättningen: bevara Codex checklistestatus och förbered A2 med Stable avslutad och aktuell verifierad backup. Separat appkopia med samma identifierare delar lokala data.

Ingen app startades eller installerades, ingen server ändrades, ingen release publicerades och ingen forskningskörning startades. Slutprovsarkiven öppnades inte. Ingen strategi är godkänd för papper/live.


## Omgranskning av manifesträttningen – 2026-11-03

Granskad head `6ff6b5e0249099419ad4fad99f39e255e2c4b68c`. **P2 rättad.** Egen ny kontroll av den befintliga backupen bekräftar 23 manifestposter utan självpost, samtliga med korrekt SHA-256, och 24 filer totalt inklusive manifestet. Manifestets egen hash är `f86865d51192e8867e94ca4dfdb4572edbafa2eb15b64f08024259c28a46fec4`, samma som dokumentationen. De 23 innehållsfilerna matchar fortfarande sina tidigare verifierade kontrollsummor.

Egen read-only/immutable-integritetskontroll omfattar nu **alla tio SQLite-filer** och ger `ok` för samtliga. Det tidigare antalet nio i denna granskning berodde på att Codex filfilter bara tog `.db` och `.sqlite`, och därför missade WebKits `localstorage.sqlite3`. Det var en begränsning i den tidigare kontrollen, inte en nytillkommen eller ändrad backupfil. Historiken ovan behålls, men korrekt total är tio SQLite-filer.

Planen redovisar rättningen och generering av nya manifest utan självpost. **PR #81 är godkänd för merge som A1-/A2-förberedelse på `6ff6b5e`.** Inga öppna fynd återstår från denna granskning. Vid en eventuell återställning bör även destinationens återställda filer verifieras mot backupen; en kontroll i backupmappen ensam bevisar backupens integritet, inte att återkopieringen lyckats.

F2-801 förblir verifierad, F2-803 förblir `todo` eftersom A2 inte är utfört. Status **36/40**. Nästa steg är A2 enligt planen med aktuell backup och Stable avslutad. Ingen riktig köning, publicering eller slutprovsåtkomst omfattas. Ingen app startades eller installerades och inga backupfiler ändrades av omgranskningen.
