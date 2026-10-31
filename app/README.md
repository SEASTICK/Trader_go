# TraderGO desktop app

A Tauri v2 desktop app for macOS and Windows. Paper trading only: the app has no broker
connection, no order API and nowhere to store exchange keys. It works offline. The internet is
used only to check for updates.

## Layout

| Path | What |
|---|---|
| `ui/` | Plain HTML/CSS/JS front end, with no build step |
| `src-tauri/src/main.rs` | App setup and commands |
| `src-tauri/src/db.rs` | SQLite store, migrations, backups |
| `src-tauri/src/updater.rs` | Update check, download, install |
| `src-tauri/src/activity.rs` | Running paper sessions and backtests (install waits for them) |
| `src-tauri/src/safety.rs` | Paper-only guard |
| `../.github/workflows/release.yml` | Test, build, sign, publish |

## Develop

Requires Rust (stable), Node 20+ and, on macOS, Xcode command-line tools.

```bash
cd app && npm ci
npm run dev                       # run the app
cd src-tauri && cargo test        # unit + signature tests
```

## How updates work

1. A push to `main` runs `release.yml`. The app's tests must pass first.
2. The version is `0.1.<run number>`, so every release is unique and higher than the last.
   Runs are queued, never run in parallel.
3. macOS (universal) and Windows builds are uploaded to a **draft** release. Each update package
   is signed with the updater key.
4. Only when both builds succeed and `latest.json` has a signed entry for every platform is the
   draft published. Failed or cancelled runs stay as drafts, and installed apps never see them.
5. The app checks `latest.json` at startup and when you click **Check for updates**. It
   downloads in the background (you can turn this off), verifies the signature against the
   public key built into the app, and shows **Restart to update**. If a paper session or
   backtest is running, installation waits.

Updates are never installed by running `git pull` or code from the repository.

### Why a separate releases repo

`SEASTICK/Trader_go` is private. An installed app cannot download from a private repo without a
token, and a token built into the app could be extracted. Release files are therefore published
to a small **public** repo, `SEASTICK/TraderGO-releases`, which holds only installers, update
packages and `latest.json`. The source stays private. The installers are public, but they
contain nothing secret.

If public installers are not acceptable, put the files behind your own update server or a
signed-URL bucket, and change `plugins.updater.endpoints` in `tauri.conf.json`.

## Your data across updates

- Data lives in the OS app-data folder: `~/Library/Application Support/com.seastick.tradergo/`
  on macOS, `%APPDATA%\com.seastick.tradergo\` on Windows. Installers replace the app, not this
  folder.
- **Never change `identifier` in `tauri.conf.json`.** The data folder is named after it.
- Schema changes are new entries appended to `MIGRATIONS` in `db.rs`. Never edit a released entry.
- Each migration runs in one transaction. If it fails, nothing changes and the app shows the
  error.
- Before migrating, a copy goes to `backups/` next to the database. The last 5 are kept.
- If an older app opens a database from a newer version, it refuses and changes nothing.
- A failed update download or signature check leaves the installed app as it was.

## One-time setup (for the repo owners)

Nothing below has been done yet.

### 1. Updater signing key (required)

On your own machine, outside the repo:

```bash
cd app && npx tauri signer generate -w ~/.tauri/tradergo-updater.key
```

- Put the **public** key (contents of `~/.tauri/tradergo-updater.key.pub`) in
  `src-tauri/tauri.conf.json` → `plugins.updater.pubkey`, and commit it. It is public by design.
- Add the private key and its password as repository secrets (next step). Keep a backup of the
  key in a password manager. **If it is lost, installed apps can never update again** and must
  be reinstalled by hand.

### 2. Repository secrets (Settings → Secrets and variables → Actions)

| Secret | Required | Value |
|---|---|---|
| `TAURI_SIGNING_PRIVATE_KEY` | yes | Contents of `~/.tauri/tradergo-updater.key` |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | yes | Its password |
| `RELEASES_TOKEN` | yes | Fine-grained token: **only** `TraderGO-releases`, permission *Contents: read and write*. Nothing else. |
| `APPLE_CERTIFICATE` | macOS signing | Base64 of the *Developer ID Application* `.p12` |
| `APPLE_CERTIFICATE_PASSWORD` | macOS signing | The `.p12` password |
| `APPLE_SIGNING_IDENTITY` | macOS signing | e.g. `Developer ID Application: Name (TEAMID)` |
| `APPLE_ID` | notarization | Apple ID email |
| `APPLE_PASSWORD` | notarization | App-specific password for that Apple ID |
| `APPLE_TEAM_ID` | notarization | 10-character team ID |

Optional variable `RELEASES_REPO_NAME` if the releases repo has another name.

### 3. Releases repo

Create a public `SEASTICK/TraderGO-releases` with a README on `main` (releases need a commit to
tag). If the name differs, update `endpoints` in `tauri.conf.json`.

### 4. Platform signing

- **macOS:** requires an Apple Developer Program membership (paid). Without it, builds still
  work, but macOS blocks the first launch until you allow it in System Settings → Privacy &
  Security. Updates are signature-checked either way.
- **Windows:** unsigned installers trigger a SmartScreen warning. To sign them, add a
  code-signing certificate or Azure Trusted Signing via `bundle.windows.signCommand`
  ([Tauri docs](https://v2.tauri.app/distribute/sign/windows/)). Not set up yet.

## Rules that stay

- No live trading, no order execution, no broker or exchange credentials in this app. Moving
  from paper to real money goes through the `pengar-grind` skill and an explicit decision.
- `safety.rs` tests fail the build if a network, shell or HTTP plugin or a trading library is
  added, or if a trade could be stored with a mode other than `paper`.
- If a future feature needs a secret (e.g. a market-data API key), store it in the OS keychain
  (`keyring` crate), never in SQLite, settings or the repo.
