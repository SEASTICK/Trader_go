# Släppa en ny version av Trader_go

Modellen kommer från Vinstly Desktop. Trader_go byggs för Windows (x64) och macOS (universal: Apple Silicon och Intel), och båda finns i samma `latest.json`.

**Inget publiceras vid push.** Allt startas för hand i GitHub: **Actions → Publish Trader_go release → Run workflow**.
Arbetsflödet måste ligga på `main` för att kunna startas.

## Kanaler

| Kanal | Vad det gör |
|---|---|
| `test` | Bygger och publicerar under `/test` på den publika uppdateringssidan. Skapar en förhandsversion `test-vX.Y.Z` under Releases (inte "Latest") och ingen `v`-tagg. Hoppar över godkännandet. Testappen heter **Trader_go Updater Test** och har eget program-id, så den följer bara testkanalen. |
| `stable` | Bygger, **pausar för godkännande**, publicerar i roten på uppdateringssidan och skapar en vanlig release med taggen `vX.Y.Z`. Alla som har appen får uppdateringen. |

## Så släpper du

1. **Förbered versionen.** Låt `app/package.json`, `app/src-tauri/tauri.conf.json` och `app/src-tauri/Cargo.toml` ha samma version. Lämna fältet *version* tomt i Run workflow så blir det föregående version +1 (patch). Både stable- och test-releaser räknas, så numren går bara uppåt. Skriv ett eget nummer bara när du vill ändra mellan- eller huvudversion (till exempel `0.2.0`). Skriv `app/RELEASE_NOTES.md` om du vill ha egna anteckningar, annars används de senaste commit-meddelandena.
2. **Kör `test` först.** Run workflow med `channel = test`. Vänta tills `version`, `build-windows`, `build-macos` och `publish` är gröna, och `approve` är **hoppad över** (grå).
3. **Kontrollera testet.**
   - `https://seastick.github.io/trader-go-releases/test/latest.json` finns och innehåller `windows-x86_64`, `windows-x86_64-nsis`, `darwin-aarch64` och `darwin-x86_64`.
   - Förhandsversionen `test-vX.Y.Z` finns under Releases. Ladda ner `.exe`, installera, starta.
   - Kör `test` igen med en högre version. Starta den installerade testappen, välj **Sök efter uppdateringar** i användarmenyn och bekräfta att den installerar, startar om och visar den nya versionen.
4. **Släpp `stable`** (först när steg 3 fungerat). Run workflow med `channel = stable`.
5. **Godkänn.** Efter bygget skapas ett ärende **"Godkänn uppdatering vX.Y.Z till användarna"**, tilldelat den som startade körningen (eller båda godkännarna om en annan startade den). Svara med en kommentar:
   - `approve` publicerar.
   - `deny` avbryter. Körningen blir röd och inget publiceras.
   Bara `SEASTICK` och `edwinfighter42-star` räknas. Första beslutet gäller. Jobbet väntar högst 300 minuter och stänger ärendet om körningen avbryts.
6. **Kontrollera.** `https://seastick.github.io/trader-go-releases/latest.json` visar nya versionen och releasen `vX.Y.Z` finns.

Taggar som startar arbetsflödet ska bara vara `v*`. Versionsberäkningen läser bara taggar på formen `vX.Y.Z`.

## TraderGO Universe

Universe släpps i samma körning som Trader_go, med samma version, kanal och godkännande. Rutan
**universe** i Run workflow (förvald) styr det; bockas den av släpps bara Trader_go och den
publicerade Universe-versionen lämnas orörd.

- Byggs för Windows (x64, NSIS) och macOS (universal, ad hoc-signerad) i jobbet `build-universe`.
- Publiceras under `universe/` på uppdateringssidan (`test/universe/` för test), med egen
  `universe/latest.json`. Rotens filer och Trader_go:s `latest.json` rörs inte av Universe.
- Testbygget heter **TraderGO Universe Test** (`com.seastick.tradergo.universe.updatertest`).
- Samma uppdateringsnyckel som Trader_go; ingen ny hemlighet behövs.
- Kontrollera efter `test`: `https://seastick.github.io/trader-go-releases/test/universe/latest.json`
  innehåller `windows-x86_64` och `darwin-aarch64`.
- macOS-minuter kostar mer än Windows. Bocka av **universe** när bara Trader_go har ändrats.

## Engångsuppsättning (görs av människa, aldrig av Claude)

1. **Publikt repo** `SEASTICK/trader-go-releases` med en gren `gh-pages` (minst en commit) och GitHub Pages påslaget från `gh-pages`. Det innehåller bara installationsfiler och `latest.json`, inte koden.
2. **Deploy key:** skapa ett nyckelpar (`ssh-keygen -t ed25519 -f trader-go-releases-deploy -N ""`). Lägg den **publika** nyckeln som deploy key med **skrivrätt** i `trader-go-releases`.
3. **Signeringsnyckel för uppdateringar:** `npx tauri signer generate -w trader-go-updater.key`. Använd inte Vinstlys nyckel. Lägg den **publika** nyckeln i `app/src-tauri/tauri.conf.json` under `plugins.updater.pubkey`, som ersätter platshållaren.
4. **Hemligheter** i Trader_go-repot (Settings → Secrets and variables → Actions):
   - `RELEASES_DEPLOY_KEY`: innehållet i den **privata** deploy-nyckeln.
   - `TAURI_SIGNING_PRIVATE_KEY`: innehållet i `trader-go-updater.key`.
   - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: lösenordet du valde.
5. Förvara privata nycklar utanför Git. Förlorar du signeringsnyckeln kan befintliga installationer inte uppdateras och måste installeras om.

## Att veta

- Installationsfilen är **inte kodsignerad** för Windows, så SmartScreen kan visa "okänd utgivare" (Mer info → Kör ändå). Uppdateringarna verifieras ändå med Tauris egen signatur.
- Uppdateringssidan är publik, så installationsfilerna kan hämtas av vem som helst. Lägg inte känsliga strategier eller data i appen.
- **Mac:** jobbet `build-macos` bygger en universal-app och en signerad uppdateringsfil (`.app.tar.gz` + `.sig`) med samma uppdateringsnyckel. Appen är ad hoc-signerad; utan Apple Developer-konto frågar Gatekeeper första gången en nedladdad dmg öppnas (högerklicka → Öppna). Uppdateringar som appen själv hämtar påverkas inte. Med hemligheterna `APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY`, `APPLE_ID`, `APPLE_PASSWORD` och `APPLE_TEAM_ID` signeras och notariseras den i stället.
- macOS-minuter kostar mer än Windows-minuter i privata repon.
- **Så uppdaterar appen sig:** den söker vid start, var 30:e minut och när fönstret får fokus. En nyare version hämtas direkt i bakgrunden och verifieras mot den publika nyckeln; först därefter frågar appen "Starta om nu". En version som inte går att verifiera installeras aldrig. Utan nät märks bara en rad under Status.
- En Mac-app som byggts lokalt (`bash scripts/install-macos.sh`) har samma program-id och söker samma stable-flöde, så den tar emot nästa godkända stable-release som har en Mac-fil.
- Testa godkännandeskriptet lokalt: `bash .github/scripts/test_wait_for_approval.sh`.

## Tid och Actions-minuter

- Windows-körningar räknas dubbelt mot Linux i privata repon på gratisplanen, så de görs bara när det behövs.
- `universe-check.yml` (Linux) körs vid ändringar i Universe eller i uppdateringskoden den delar med Trader_go. `universe-windows.yml` bara vid ändringar i Universes Rust-del eller paketfiler.
- `app-check.yml` (Linux, cirka 1 minut) körs vid ändringar i `app/`. `windows-build.yml` körs bara vid ändringar i `app/src-tauri/`, i paketfilerna eller i release-flödena.
- Rust-biblioteken cachas (`rust-cache`). Första bygget efter ändrade beroenden eller ny Rust-version tar cirka 14 minuter, vanliga bygge cirka 5 minuter.
- Appens uppdatering laddar ner hela installationsfilen. Tauris uppdaterare har ingen delta-uppdatering.
