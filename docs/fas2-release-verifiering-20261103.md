# Fas 2 – verifierad release och slutgodkännande, 2026-11-03

Endast dokumentation. Ingen kod, ingen forskningskörning, ingen serverändring. H-0013:s protokoll, resultat och REJECT är oförändrade. Slutprovet är oläst. Inget aktiverat för papper eller live.

Alla körningar startades av Edwin själv enligt [release-skillen](../.claude/skills/release/SKILL.md). Claude startade ingen körning och skrev inget i godkännandeärendet.

## Källkod

Alla tre byggena kommer från main `72107eda7995a86ad990547faa10c3237c8d57a9`. App- och Rust-källkoden är oförändrad mot den granskade kopian 9471e51 (se [överlämningen](fas2-release-overlamning-20261103.md)).

## Testkanal 0.1.21

- Körning [41658461455](https://github.com/SEASTICK/Trader_go/actions/runs/41658461455), kanal test: version, build-macos, build-windows, build-universe ×2 och publish gröna; approve hoppad över. Dubbelstarten 41658588341 avbröts.
- Förhandsversion `test-v0.1.21`; taggen pekar på 72107ed. `test/latest.json` 0.1.21 med sex plattformsnycklar. Stable var kvar på 0.1.20.
- SHA-256: dmg `029cf8a1254f94e2467d7717d06233d00ecfb902406957e053dd748f778fdf92` (samma på Pages och i releasen), app.tar.gz `3c9e9cc833cdca6c102fd59c13e6c29d7720a7fd1baaa01a1eb75b42e13d8a18`, exe `3ffc0b43ca3cfa058ed54db3d40958e3a66cb8bae3a9ef14a97b04888a3f0568`.
- Minisign-signaturer för app.tar.gz och exe giltiga mot `plugins.updater.pubkey` (nyckel-id EC18EB6CCB90882F), identiska med manifestet; betrodd kommentar "TraderGO Updater Test", version 0.1.21.
- Appen: `com.seastick.tradergo.updatertest` 0.1.21, universal, ad hoc-signerad, `codesign --verify --deep --strict` OK. Installerad i `~/Applications/TraderGO Updater Test.app` med egen appdata.

### Testappen i bruk

- Status: v0.1.21, kanal Test (`test/latest.json`).
- Fas 1: H-0009–H-0012 REJECT med nyckeltal, krav, kapitalkurva, drawdown och walk-forward. Marknad ansluten med diagram. Papper tomt (egen data).
- H-0013 efter att Edwin själv loggat in: körning ca59d441 Klar 100 %, försök 1 av 3, ingen köknapp ("H-0013 har redan ett resultat"). Resultatet HISTORIK · REJECT, alla fem kriterier inte uppfyllda, statistisk styrka −1,8 mot 2,67, med 2,5× kostnader −13,01 %. Sharpe −0,77, 95 % −1,36 till −0,24, permutationer 0,88, Deflated Sharpe 0. Jämförelsetabell och jämförelsekurvor (1500 punkter av 6570 staplar), kapitalutveckling, drawdown, marknadslägen, kandidatval per testfönster och fem affärer.
- Spårbarhet: revision b44d3cecaac6…, dataset 6a84c4f4…, inläst data 4d5cfd5f…, manifest 9401fa42…, h0013-evaluation/1.0.0, körning ca59d441, försök 1. Allt lika med [H-0013-granskningen](fas2-h0013-granskning-20261103.md).

## Uppdateringsprov 0.1.21 → 0.1.22

- Körning [41681950148](https://github.com/SEASTICK/Trader_go/actions/runs/41681950148): "Publishing Trader_go 0.1.22 on the test channel", utan Universe. Alla jobb gröna; approve hoppad över.
- `test-v0.1.22` förhandsversion på 72107ed; `test/latest.json` 0.1.22. SHA-256 dmg `059be35ac1208fe446d7fc8d56becaed44b25d3e7cd87e1a44b6be2a71587ca3` (lika i releasen), app.tar.gz `ce69e98b3d2e61a5acfea1a8af93f91ee15e1a1f5be1c6d14679d0a4f78eaba3`, exe `bcbdfa2df526d7b430d7fa00e12de43a8b1c2c8c4a4e393f9ef936dabd84ebc1`. Signaturer giltiga och lika med manifestet, version 0.1.22.
- I installerad 0.1.21: "Sök efter uppdateringar" → "Ny version finns v0.1.22, hämtad och verifierad" → "Starta om nu". Appen startade om och visar v0.1.22, "Du har den senaste versionen". Info.plist 0.1.22, codesign OK.

## Stable 0.1.23

- Edwin gav uttryckligt ja till Stable 0.1.23 från 72107ed, startade körning [41683850552](https://github.com/SEASTICK/Trader_go/actions/runs/41683850552) ("Publishing Trader_go 0.1.23 on the stable channel") och skrev `approve` i [ärende #83](https://github.com/SEASTICK/Trader_go/issues/83) (edwinfighter42-star, 2026-11-03T17:34:07Z).
- Alla jobb gröna: version, build-macos, build-windows, build-universe (macOS, Windows), approve, publish.
- Release `v0.1.23`, inte förhandsversion, tagg på 72107ed. `latest.json` 0.1.23, pub_date 2026-11-03T17:34:38Z, sex plattformsnycklar. `universe/latest.json` 0.1.23.
- SHA-256: dmg `38894873e5e63b8a21ad948d1bf4c1cd357f98c82ce5ab00b2512b93a3ae6ab1` (lika i releasen), app.tar.gz `64f153218200d7686929fb8a27401b84c415d079bdcc0d3b863dda5b38f4b80d`, exe `08cbb783c2a563e2584e54c62a668172d894bbd040b38df2a4acf128e3a6c2f4`. Signaturer giltiga, nyckel-id EC18EB6CCB90882F, lika med manifestet, version 0.1.23.

### Installerad Stable

- Granskningskopian avslutades först (samma app-id). `/Applications/TraderGO.app` 0.1.20 startades och erbjöd själv "Ny version finns v0.1.23, hämtad och verifierad". Efter "Starta om nu": Status v0.1.23 (72107ed+ändrad), kanal Stable (`latest.json`), "Du har den senaste versionen".
- Info.plist 0.1.23, `com.seastick.tradergo`, universal x86_64/arm64, codesign strict OK.
- Översikt: 15 hypoteser, 15 REJECT. H-0013 efter Edwins inloggning: samma körning, resultat, kurvor, fem affärer och spårbarhet som i testappen.

## Fas 2-slutgodkännande (F2-805)

- Forskningsbeslut: H-0013 **REJECT** enligt förregistrerade kriterier. Inget slutprov öppnas för H-0013. Inga strategier är READY_FOR_PAPER. Ingen paper- eller liveaktivering.
- Leverans: Adaptive Strategy Engine, kö, worker och Research Lab är släppta i Stable 0.1.23 och verifierade på installerad app.
- Edwin gav uttryckligt slutgodkännande 2026-11-03 efter Codex granskning, med dokumenterade begränsningar. F2-805 är klar.

## Begränsningar

- Windows: inget manuellt prov (ingen testdator, tidigare beslut). Bygge och signaturer är kontrollerade.
- Driftlarm uppskjutna på Edwins begäran.
- Gatekeeper ej prövat: filerna hämtades med curl utan karantän, och uppdateringar via appen sätter ingen karantän.
- Releasebyggen visar `+ändrad` efter commiten, eftersom workflowen skriver version och kanalidentitet i package.json, tauri.conf.json och Cargo.toml före bygget. Stable 0.1.20 hade samma märkning. Missvisande men ingen kodskillnad.
- Prisdiagrammet förblir mörkt i ljust tema (fanns före Fas 2).
- Universe 0.1.23 publicerades i Stable-körningen trots rekommendation att stänga av det. Universe-koden är oförändrad.
- Den driftsatta hypoteskatalogen speglar fortfarande registret i b44d3ce (null för H-0013), se överlämningen.

## Codex oberoende slutgranskning, 2026-11-03

Claude har dokumenterat releaseflödet ovan i c73d061. Codex har därefter kontrollerat GitHubs körningar, taggar, publicerat manifest och den installerade Stable-appen. Historiska GUI-steg för testuppdateringen och minisign-verifieringen är Claudes/Edwins redovisning; de kryptografiska minisign-proven upprepades inte i denna granskning.

- GitHub visar lyckad Stable-körning 41683850552, inklusive Universe på båda plattformarna och godkännandet från Edwin i #83. Stable- och testtaggarna pekar på 72107eda7995a86ad990547faa10c3237c8d57a9. Testkörningarna lyckades och dubbelstarten är avbruten.
- Den installerade `/Applications/TraderGO.app` var redan 0.1.23 när Codex började. Ingen ominstallation gjordes. Granskningskopian kördes inte. Bundle-id är `com.seastick.tradergo` och `codesign --verify --deep --strict` passerar.
- Publicerad Mac-uppdatering har SHA-256 `64f153218200d7686929fb8a27401b84c415d079bdcc0d3b863dda5b38f4b80d`. Dess binär är byteidentisk med den installerade, SHA-256 `fd47ae0ede824a1fda7b33698cb94ea1e6c5c935a2d597ec519a719170e5c5e7`.
- Efter Edwins inloggning visar verkliga Stable H-0013 ca59d441-3ab3-489b-b762-c368a6220834: klar, 100 %, försök 1 av 3, HISTORIK och REJECT. Alla fem krav faller, t är −1,8 mot 2,67, netto −10,86 % och kostnadsstress −13,01 %. Fem affärer, sex testfönster, kapital/drawdown, regimtabell och full spårbarhet stämmer med resultatgranskningen. Ingen ny köknapp erbjuds eftersom resultat redan finns.
- Läsande serverkontroll 2026-11-03T17:41:29Z: exakt en worker b44d3ce/PID 30868, lås taget, tom aktiv kö och exakt ett H-0013-resultat. Ingen ny körning, migration eller serverändring utfördes.


**Codex tekniska granskning är godkänd inom begränsningarna ovan. F2-804 är klar. Edwin har därefter slutgodkänt leveransen med dessa begränsningar; F2-805 är klar.** Ett sådant godkännande innebär att forskningsverktyget är levererat; H-0013 förblir REJECT, slutprovet öppnas inte och inget godkänns för papper eller live.

## Edwins slutgodkännande, 2026-11-03

På Codex fråga om godkännande av Fas 2 med de dokumenterade begränsningarna, bland annat uteblivet manuellt Windows-test och uppskjutna driftlarm, svarade Edwin: **”ja jag godkänner”**. Codex tekniska granskning var redan godkänd.

**Fas 2 är klar: 40 av 40 uppgifter.** Stable 0.1.23 är publicerad och verifierad i installerad Mac-app. Godkännandet gäller forskningsverktygets leverans inom redovisade begränsningar. H-0013 förblir REJECT; inget slutprov öppnas och ingen strategi aktiveras för papper eller live. Fas 3 har inte startats. Inga nya körningar, releaser, kodändringar eller serverändringar gjordes för detta godkännande.
