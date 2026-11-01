# Punkt 1: gemensam grund för Edwin och Philip

Status 2026-11-01. Uppdatera filen när ett steg är gjort, med datum och vad som visade det.
Ett steg är klart först när det har provats, inte när konfigurationen finns.

**Punkt 1 är inte klar än.** Koden och flödena är på plats och provade lokalt på Edwins Mac, men
ingen riktig release med Mac-fil har publicerats, och Windows är inte provat på en Windows-dator.

## Verifierat klart

| Vad | Evidens |
|---|---|
| `SEASTICK/Trader_go` är den gemensamma källan | `origin` pekar dit. Universe (PR #34) och valvets mappar (PR #3) ligger på `main`. |
| Lokalt arbete är skyddat | Grenen `backup/desktop-universe-2026-11-01` och en kopia av den gamla Mac-appen med data i `~/Library/Application Support/TraderGO-backups/`. Inga force pushes eller reset. |
| Privat källa, publik distribution | `Trader_go` är privat. `trader-go-releases` är publik och innehåller bara installerare, signaturer, `latest.json` och `downloads.html`. |
| Hemligheter för släpp finns | `TAURI_SIGNING_PRIVATE_KEY`, `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`, `RELEASES_DEPLOY_KEY` (bara namnen kontrollerade). |
| Windows-installerare för båda apparna går att bygga | PR #34: `Windows check` och `Universe Windows check` gröna i Windows-CI. |
| Installerad TraderGO på Edwins Mac är Philips app | `/Applications/TraderGO.app`, `com.seastick.tradergo`, byggd från commit `3da121d`. Visar Philips gränssnitt, startar utan terminal och utvecklingsserver (ingen lyssnare på 5173). Status visar kanal Stable och `…/trader-go-releases/latest.json`. |
| Uppdateringslogiken | Tester 23/23. Lokal testkedja med engångsnyckel och test-id: fel nyckel avvisas, rätt signatur hämtas och verifieras i bakgrunden, "Starta om nu" byter appen på plats till nyare version, utan nät startar appen som vanligt. |
| Universe är kopplad och bara läser | `/Applications/TraderGO Universe.app`, `com.seastick.tradergo.universe`. Hittade projektmappen automatiskt, visar 220 filer och 0 trasiga länkar. En ny fil syntes på kartan med sin länk inom sekunder och försvann när den togs bort. `git status` oförändrad efteråt. Rust-tester 27/27, säkerhetskontroll OK. |
| Inga dubbla startikoner | Bara de två apparna i `/Applications` är registrerade i Launchpad. |

## Ändrat men inte verifierat

| Vad | Varför inte verifierat |
|---|---|
| Mac-bygge i release-flödet (`build-macos`, `darwin-*` i `latest.json`), PR #35 | Jobbet körs bara i release-flödet, som inte har körts med ändringen. Simulerat lokalt med låtsasfiler. |
| Universe i release-flödet (`build-universe`, `universe/latest.json`) | Ligger på `main` men har inte körts. `universe/latest.json` finns inte än (404), så Universe kan inte uppdatera sig förrän första releasen med Universe. |
| Windows-installation och uppdatering | Installerarna byggs i CI, men ingen har installerat, startat eller uppdaterat dem på en Windows-dator. |

## Blockerat eller återstår

1. PR #35 är inte sammanslagen. Den pekar på grenen från PR #34 och behöver byta bas till `main`.
2. Nuvarande stable (0.1.6) har bara Windows. Edwins Mac säger därför "Den senaste versionen finns
   inte för den här datorn ännu" tills en release med Mac-fil publiceras.
3. Ingen Apple Developer-signering. En nedladdad dmg kräver högerklick → Öppna första gången.
   Uppdateringar som appen hämtar själv påverkas inte.
4. Ingen Windows-kodsignering, så SmartScreen varnar vid första installationen.

## Steg

**Philip**
1. Granska PR #35. Byt bas till `main` (Edit bredvid titeln) och slå ihop när kontrollerna är gröna.
2. Actions → Publish Trader_go release → Run workflow: `channel = test`, `universe` ibockad.
3. Kontrollera att `https://seastick.github.io/trader-go-releases/test/latest.json` har
   `windows-x86_64` och `darwin-aarch64`, och att `test/universe/latest.json` finns.
4. Installera testbyggena på Windows från förhandsversionen `test-vX.Y.Z`: starta båda, kontrollera
   Status, och kör testkanalen en gång till med högre version för att se att uppdateringen installeras.
5. Run workflow med `channel = stable` och svara `approve` i ärendet.
6. `git switch main && git pull`.

**Edwin**
1. Efter steg 2 ovan: installera "TraderGO Updater Test" från testets dmg och se att den uppdaterar
   sig vid nästa testkörning.
2. Efter steg 5: låt TraderGO och Universe vara öppna eller starta dem. Inom 30 minuter (direkt vid
   start eller fokus) ska de hämta och verifiera den nya versionen och fråga "Starta om nu". Bekräfta
   under Status att den nya versionen och commiten visas.
3. När PR #35 är sammanslagen: `git switch main && git pull`.

## När punkt 1 kan markeras klar

När en godkänd stable-release med både Windows- och Mac-fil har publicerats och båda har sett sina
installerade appar (TraderGO och Universe) uppdatera sig till den, och Philip har provat Windows-
installationen. Skriv in datum och version här då.
