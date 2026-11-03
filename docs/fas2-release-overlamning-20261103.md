# Fas 2 – överlämning till release, 2026-11-03

**Historisk överlämning, ersatt av [releaseverifieringen](fas2-release-verifiering-20261103.md): Stable 0.1.23 är nu publicerad och installerad; 39/40 klara, endast Edwins slutgodkännande återstår.**

**Vid överlämningen: 38/40 verifierade.** F2-802 är klar efter verklig H-0013-körning och resultatgranskning. F2-804 (publicerad/verifierad Stable) och F2-805 (samlat slutgodkännande) återstår. Ingen testrelease eller Stable har startats i denna session.

## Underlag färdigt

- Installerad granskningsapp 9471e51, A1/A2/A3 och H-0013-flödet verifierade. `git diff 9471e51 HEAD -- app/src app/src-tauri/src` var tomt före denna överlämning; app-/Rust-källkoden är oförändrad mot den installerade granskningskopian.
- H-0013-resultat/granskning arkiverade i **5ce848e**, beslutet infört som en ny registerrad i separat commit **82bd03f**. Alla fem kriterier faller: **REJECT**. Inget slutprov och ingen paper/live-aktivering.
- app/RELEASE_NOTES.md uppdaterad för nästa släpp, utan hårdkodat versionsnummer. Inga versionsfält ändrade; workflow väljer nästa lediga patchversion.
- Driftsatt worker b44d3ce fortsätter oförändrad och har redan rätt funktioner. Ingen migration behövs för appsläppet.
- Den driftsatta hypoteskatalogen använder fortfarande registret i b44d3ce och visade null för H-0013 vid efterkontroll. Git är nu REJECT. Kön skriver avsiktligt inte registerbeslut; resultatpanelen visar det granskade resultatets REJECT. Ingen ny workerrelease eller direkt databasskrivning görs för att ändra denna spegel här.

## Det Edwin behöver göra först

Projektets [.claude/skills/release/SKILL.md](../.claude/skills/release/SKILL.md) anger uttryckligen: **"Claude startar aldrig en release-körning. Människan kör Run workflow själv."** Sluttestplanens A4 kräver också ett separat beslut eftersom testkanalen är publik. Detta är en faktisk handoff enligt projektregeln, inte en teknisk avsaknad av GitHub-åtkomst.

1. Öppna [Publish Trader_go release](https://github.com/SEASTICK/Trader_go/actions/workflows/desktop-release.yml).
2. Välj **Run workflow**, gren **main**, kanal **test**, lämna **version** tomt och bocka ur **universe** eftersom Universe inte har ändrats.
3. Starta körningen och skicka dess länk. Det publicerar en testversion på den publika testsidan, med separat app-id. Stable-appen uppdateras inte av testkanalen.

Skriv inte in releasehemligheter i chatten. Välj inte stable i detta första steg. Granskningskopians erbjudande att installera gamla Stable 0.1.20 är fortfarande olämpligt för detta test.

## Kontroller därefter

- Codex följer version/build-macos/build-windows/publish, att approve hoppas över på testkanalen, tagg/commit och test/latest.json.
- Installera den separata testappen och kontrollera H-0013-resultatet och befintliga funktioner. Om Gatekeeper kräver en säkerhetsåtgärd gör Edwin den själv.
- Release-skillen kräver testkanal när Rust har ändrats. Sluttestplanen och docs/release.md beskriver även prov av uppdatering från ett testbygge till ett senare. Den andra testkörningen startas också av Edwin, först när det första bygget är verifierat.
- Först därefter: separat uttryckligt Stable-beslut, Edwin startar stable-workflow och godkänner ärendet med approve. Ingen approval-kommentar skickas automatiskt.
- Verifiera den installerade Stable-versionen och byggcommiten, H-0013-resultatet samt checklistan. Bocka först då av F2-804 och dokumentera F2-805:s slutgodkännande.

Windows manuella test saknar fortfarande testdator enligt tidigare beslut. Driftlarm är uppskjutna på Edwins begäran. Dessa begränsningar ska stå kvar i slutgodkännandet.
