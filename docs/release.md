# Släppa en ny version av Trader_go

Modellen kommer från Vinstly Desktop. Bara Windows än så länge.

**Inget publiceras vid push.** Allt startas för hand i GitHub: **Actions → Publish Trader_go release → Run workflow**.
Arbetsflödet måste ligga på `main` för att kunna startas.

## Kanaler

| Kanal | Vad det gör |
|---|---|
| `test` | Bygger och publicerar under `/test` på den publika uppdateringssidan. Skapar en förhandsversion `test-vX.Y.Z` under Releases (inte "Latest") och ingen `v`-tagg. Hoppar över godkännandet. Testappen heter **Trader_go Updater Test** och har eget program-id, så den följer bara testkanalen. |
| `stable` | Bygger, **pausar för godkännande**, publicerar i roten på uppdateringssidan och skapar en vanlig release med taggen `vX.Y.Z`. Alla som har appen får uppdateringen. |

## Så släpper du

1. **Förbered versionen.** Låt `app/package.json`, `app/src-tauri/tauri.conf.json` och `app/src-tauri/Cargo.toml` ha samma version. Lämna fältet *version* tomt i Run workflow så blir det föregående version +1 (patch). Både stable- och test-releaser räknas, så numren går bara uppåt. Skriv ett eget nummer bara när du vill ändra mellan- eller huvudversion (till exempel `0.2.0`). Skriv `app/RELEASE_NOTES.md` om du vill ha egna anteckningar, annars används de senaste commit-meddelandena.
2. **Kör `test` först.** Run workflow med `channel = test`. Vänta tills `version`, `build-windows` och `publish` är gröna, och `approve` är **hoppad över** (grå).
3. **Kontrollera testet.**
   - `https://seastick.github.io/trader-go-releases/test/latest.json` finns och innehåller `windows-x86_64` och `windows-x86_64-nsis`.
   - Förhandsversionen `test-vX.Y.Z` finns under Releases. Ladda ner `.exe`, installera, starta.
   - Kör `test` igen med en högre version. Starta den installerade testappen, välj **Sök efter uppdateringar** i användarmenyn och bekräfta att den installerar, startar om och visar den nya versionen.
4. **Släpp `stable`** (först när steg 3 fungerat). Run workflow med `channel = stable`.
5. **Godkänn.** Efter bygget skapas ett ärende **"Godkänn uppdatering vX.Y.Z till användarna"**, tilldelat den som startade körningen (eller båda godkännarna om en annan startade den). Svara med en kommentar:
   - `approve` publicerar.
   - `deny` avbryter. Körningen blir röd och inget publiceras.
   Bara `SEASTICK` och `edwinfighter42-star` räknas. Första beslutet gäller. Jobbet väntar högst 300 minuter och stänger ärendet om körningen avbryts.
6. **Kontrollera.** `https://seastick.github.io/trader-go-releases/latest.json` visar nya versionen och releasen `vX.Y.Z` finns.

Taggar som startar arbetsflödet ska bara vara `v*`. Versionsberäkningen läser bara taggar på formen `vX.Y.Z`.

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
- Mac är inte med. Att lägga till det kräver en matris som i Vinstlys `desktop-release.yml` och, för signering på riktigt, ett Apple Developer-konto.
- Testa godkännandeskriptet lokalt: `bash .github/scripts/test_wait_for_approval.sh`.
