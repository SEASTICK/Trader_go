# Trader_go-appen

Vite + React + TypeScript. Samma gränssnitt körs som webbsida (Cloudflare Pages) och som
datorprogram för macOS och Windows (Tauri v2). Appen handlar inte och ansluter inte till någon
börs. Datorprogrammet fungerar offline; nätet används bara för att leta efter uppdateringar.

```bash
cd app
npm ci
npm run dev           # webbsidan lokalt
npm run tauri dev     # datorprogrammet lokalt (kräver Rust)
cd src-tauri && cargo test
```

## Struktur

| Sökväg | Vad |
|---|---|
| `src/`, `data/` | Gränssnittet och datan det visar |
| `src/desktop.tsx` | Flikarna *Uppdateringar* och *Papper*, syns bara i datorprogrammet |
| `src/projectmap.tsx`, `src-tauri/src/project_map/` | Projektkartan, se [PROJEKTKARTA.md](PROJEKTKARTA.md) |
| `src-tauri/src/main.rs` | Start och kommandon |
| `src-tauri/src/db.rs` | SQLite, migreringar, säkerhetskopior |
| `src-tauri/src/updater.rs` | Leta, ladda ner, installera uppdateringar |
| `src-tauri/src/activity.rs` | Pågående papperssessioner och backtester (installation väntar på dem) |
| `src-tauri/src/safety.rs` | Spärr som håller appen på papper |
| `../.github/workflows/release.yml` | Testa, bygga, signera, publicera (push till `main`) |
| `../.github/workflows/ci.yml` | Tester på macOS och Windows, plus en Windows-installationsfil att ladda ner (varje PR) |

## Cloudflare Pages (görs av människa, inget hemligt i Git)

- Root directory: `app`
- Build command: `npm run build`
- Build output directory: `dist`
- Skydda sidan med Cloudflare Access (e-post) så bara ni två kommer in.

På webben syns inte flikarna Uppdateringar och Papper.

## Så fungerar uppdateringar

1. En push till `main` kör `release.yml`. Testerna måste gå igenom först.
2. Versionen blir `0.1.<körningsnummer>`, alltså unik och alltid högre. Körningarna köas.
3. macOS (universal) och Windows byggs till en **utkast**-release. Varje uppdateringspaket
   signeras med uppdateringsnyckeln.
4. Först när båda byggena lyckats och `latest.json` har en signerad post per plattform
   publiceras utkastet. Misslyckade körningar förblir utkast och syns aldrig för installerade appar.
5. Appen letar vid start och via **Leta efter uppdateringar**, laddar ner i bakgrunden (kan
   stängas av), kontrollerar signaturen mot den publika nyckeln i appen och visar **Starta om
   och uppdatera**. Pågår en papperssession eller ett backtest väntar installationen.

Appen uppdateras aldrig med `git pull` eller genom att köra kod från repot.

### Varför ett separat release-repo

`SEASTICK/Trader_go` är privat. En installerad app kan inte ladda ner från ett privat repo utan
en token, och en token i appen går att plocka ut. Releasefilerna läggs därför i ett litet
**publikt** repo, `SEASTICK/TraderGO-releases`, som bara innehåller installationsfiler,
uppdateringspaket och `latest.json`. Källkoden förblir privat.

## Data mellan uppdateringar

- Datan ligger i appens datamapp: `~/Library/Application Support/com.seastick.tradergo/` på
  macOS, `%APPDATA%\com.seastick.tradergo\` på Windows. Installationen byter appen, inte mappen.
- **Ändra aldrig `identifier` i `tauri.conf.json`.** Datamappen heter som den.
- Schemaändringar läggs sist i `MIGRATIONS` i `db.rs`. Ändra aldrig en utgiven post.
- Varje migrering körs i en transaktion. Misslyckas den ändras ingenting.
- Före migrering sparas en kopia i `backups/` bredvid databasen. De 5 senaste behålls.
- En äldre app vägrar öppna en databas från en nyare version och ändrar ingenting.
- En misslyckad nedladdning eller signaturkontroll lämnar den installerade appen orörd.

## Engångsinställning (för repoägarna)

Inget av detta är gjort än. Tills steg 1 är klart stoppar `release.yml` vid nyckelkontrollen och
publicerar ingenting.

### 1. Uppdateringsnyckel (krävs)

På egen dator, utanför repot:

```bash
cd app && npx tauri signer generate -w ~/.tauri/tradergo-updater.key
```

- Lägg den **publika** nyckeln (innehållet i `~/.tauri/tradergo-updater.key.pub`) i
  `src-tauri/tauri.conf.json` → `plugins.updater.pubkey` och committa. Den är publik med flit.
- Lägg den privata nyckeln och lösenordet som secrets (nästa steg). Spara en kopia i en
  lösenordshanterare. **Försvinner nyckeln kan installerade appar aldrig uppdateras igen.**

### 2. Secrets (Settings → Secrets and variables → Actions)

| Secret | Krävs | Värde |
|---|---|---|
| `TAURI_SIGNING_PRIVATE_KEY` | ja | Innehållet i `~/.tauri/tradergo-updater.key` |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | ja | Lösenordet |
| `RELEASES_TOKEN` | ja | Fine-grained token: **bara** `TraderGO-releases`, *Contents: read and write* |
| `APPLE_CERTIFICATE` | macOS-signering | Base64 av *Developer ID Application*-`.p12` |
| `APPLE_CERTIFICATE_PASSWORD` | macOS-signering | Lösenordet till `.p12` |
| `APPLE_SIGNING_IDENTITY` | macOS-signering | t.ex. `Developer ID Application: Namn (TEAMID)` |
| `APPLE_ID` | notarisering | Apple-ID |
| `APPLE_PASSWORD` | notarisering | App-specifikt lösenord |
| `APPLE_TEAM_ID` | notarisering | Team-ID (10 tecken) |

Valfri variabel `RELEASES_REPO_NAME` om release-repot heter något annat.

### 3. Release-repo

Skapa ett publikt `SEASTICK/TraderGO-releases` med en README på `main`. Heter det något annat,
ändra `endpoints` i `tauri.conf.json`.

### 4. Plattformssignering

- **macOS:** kräver Apple Developer Program (betalt). Utan det fungerar bygget, men macOS
  stoppar första starten tills man tillåter den under Systeminställningar → Integritet och
  säkerhet. Uppdateringar kontrolleras med signatur ändå.
- **Windows:** installationsfilen är inte kodsignerad, så Windows kan visa "okänd utgivare".
  Välj "Mer info" och "Kör ändå". Signering kan läggas till via `bundle.windows.signCommand`.

## Regler som gäller

- Ingen livehandel, ingen orderkod, inga mäklar- eller börsnycklar i appen. Från papper till
  riktiga pengar går via skillen `pengar-grind` och ett uttryckligt beslut.
- Testerna i `safety.rs` fäller bygget om ett nätverks-, shell- eller HTTP-tillägg eller ett
  tradingbibliotek läggs till, eller om en affär kan sparas med annat läge än `paper`.
- Behöver en framtida funktion en hemlighet (t.ex. en API-nyckel för marknadsdata), lägg den i
  operativsystemets nyckelring (`keyring`), aldrig i SQLite, inställningar eller repot.
