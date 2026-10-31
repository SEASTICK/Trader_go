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
| `src/desktop.tsx` | Sidan *Papper*, syns bara i datorprogrammet |
| `src-tauri/src/main.rs` | Start och kommandon |
| `src-tauri/src/db.rs` | SQLite, migreringar, säkerhetskopior |
| `src/features/updates/`, `src/lib/updater.ts` | Uppdateringar i appen, se [docs/release.md](../docs/release.md) |
| `src-tauri/src/activity.rs` | Pågående papperssessioner och backtester (installation väntar på dem) |
| `src-tauri/src/safety.rs` | Spärr som håller appen på papper |
| `../.github/workflows/desktop-release.yml` | Släpp (startas för hand), se [docs/release.md](../docs/release.md) |
| `../.github/workflows/windows-build.yml` | Windows-installationsfil att ladda ner (varje PR) |
| `../.github/workflows/ci.yml` | Rust- och frontendtester på macOS och Windows (varje PR) |

## Cloudflare Pages (görs av människa, inget hemligt i Git)

- Root directory: `app`
- Build command: `npm run build`
- Build output directory: `dist`
- Skydda sidan med Cloudflare Access (e-post) så bara ni två kommer in.

På webben syns inte sidan Papper.

## Uppdateringar

Släpp och uppdateringar beskrivs i [docs/release.md](../docs/release.md). Innan appen
installerar en uppdatering anropas `prepare_update_install`: den vägrar medan en
papperssession eller ett backtest pågår och säkerhetskopierar databasen.

## Data mellan uppdateringar

- Datan ligger i appens datamapp: `~/Library/Application Support/com.seastick.tradergo/` på
  macOS, `%APPDATA%\com.seastick.tradergo\` på Windows. Installationen byter appen, inte mappen.
- **Ändra aldrig `identifier` i `tauri.conf.json`.** Datamappen heter som den.
- Schemaändringar läggs sist i `MIGRATIONS` i `db.rs`. Ändra aldrig en utgiven post.
- Varje migrering körs i en transaktion. Misslyckas den ändras ingenting.
- Före migrering och före varje uppdatering sparas en kopia i `backups/` bredvid databasen.
  De 5 senaste behålls.
- En äldre app vägrar öppna en databas från en nyare version och ändrar ingenting.
- En misslyckad nedladdning eller signaturkontroll lämnar den installerade appen orörd.

## Regler som gäller

- Ingen livehandel, ingen orderkod, inga mäklar- eller börsnycklar i appen. Från papper till
  riktiga pengar går via skillen `pengar-grind` och ett uttryckligt beslut.
- Testerna i `safety.rs` fäller bygget om ett nätverks-, shell- eller HTTP-tillägg eller ett
  tradingbibliotek läggs till, eller om en affär kan sparas med annat läge än `paper`.
- Behöver en framtida funktion en hemlighet (t.ex. en API-nyckel för marknadsdata), lägg den i
  operativsystemets nyckelring (`keyring`), aldrig i SQLite, inställningar eller repot.
