---
name: release
description: Använd när en ny version av Trader_go-appen ska släppas, när någon frågar hur test och stable fungerar, när en release-körning har misslyckats, eller när Actions-minuter och kostnader kommer på tal.
---

# Släppa Trader_go

Fullständig beskrivning finns i `docs/release.md`. Den här skillen är reglerna och de vanliga felen.

## Regler

1. **Claude startar aldrig en release-körning.** Människan kör *Run workflow* själv.
2. **Stable släpps bara efter ett uttryckligt ja**, och godkänns sedan i ett ärende (`approve` / `deny`).
3. **Inget publiceras vid push eller merge.** Bara *Publish Trader_go release* (`.github/workflows/desktop-release.yml`) släpper något.
4. Hemligheter (`RELEASES_DEPLOY_KEY`, `TAURI_SIGNING_PRIVATE_KEY`, `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`) skrivs aldrig i chatt eller filer.

## Kanaler

| | test | stable |
|---|---|---|
| App som får uppdateringen | Trader_go Updater Test (eget program-id) | Trader_go |
| Uppdateringssida | `seastick.github.io/trader-go-releases/test/latest.json` | `.../latest.json` |
| Release i repot | förhandsversion `test-vX.Y.Z` | vanlig release `vX.Y.Z` |
| Godkännande | nej | ärende, bara `SEASTICK` och `edwinfighter42-star` |

Stable byggs om från samma commit. Det är inte samma fil som testbygget.

## När behövs test?

- **Ja:** ändringar i uppdateringen, installationen, Rust-delen (`app/src-tauri/`), Tauri-paketen eller release-flödet. Ett fel där kan göra att appen inte går att uppdatera.
- **Kan hoppas över:** vanliga UI-ändringar. Ett fel rättas med nästa stable så länge uppdateraren är orörd.

## Spara tid och minuter

- Windows-minuter räknas dubbelt. Ett bygge med varm cache tar cirka 5 minuter, utan cache cirka 14.
- Samla ändringar: merga PR:er, kör sedan **en** release. Inte en per ändring.
- PR-kontroller: `app-check.yml` (Linux, cirka 1 minut) för `app/`. `windows-build.yml` bara vid ändringar i `app/src-tauri/`, paketfilerna eller flödena.
- Pusha inte i onödan till öppna PR:er som startar Windows-kontroller.

## Versionsnummer

Tomt fält ger föregående version + 1 (patch), räknat över både `vX.Y.Z` och `test-vX.Y.Z`. Skriv ett eget nummer bara för att byta mellan- eller huvudversion. Kör aldrig samma nummer två gånger på samma kanal.

## Vanliga fel

| Symptom | Orsak | Gör |
|---|---|---|
| Jobb föll efter 1 s, inga loggar, `runner_id: 0` | GitHub-konto: kvot slut eller betalning | Kolla Billing på GitHub. Inget kodfel. |
| `Repository secret ... is missing` | Hemlighet saknas | Människan lägger in den |
| `ar redan slappt` | Versionen finns redan på kanalen | Lämna fältet tomt eller välj högre |
| Appen hittar ingen uppdatering | Ingen nyare version i kanalens `latest.json`, eller fel kanal | Kontrollera under Status → "Senaste kontrollen" |
| Releasen saknar ny kod | PR:en är inte mergad till `main` | Merga först, kör sedan |

## Efter en körning

Kontrollera med GitHub-verktygen: körningens jobb, att releasen finns och att taggen pekar på byggd commit. Säg vad som är verifierat och vad som bara är publicerat men inte provat i appen.
