# Samarbete: Edwin och Philip på samma main

`SEASTICK/Trader_go` är den gemensamma källan, och båda arbetar direkt på `main`. Det finns inget
grenskydd på `main` (kontrollerat 2026-11-01). Inför ni ett skydd som kräver pull request gäller det,
och då används PR-flödet i stället.

## Arbetsflöde

Synkronisera → ändra → testa → commit → synkronisera → push.

```bash
git switch main && git pull --ff-only     # 1. Hämta det den andra har pushat
# 2. Ändra. Skriv i tabellen nedan om ändringen är större eller rör delad kod.
# 3. Testa det du ändrat (se Kontroller)
git add <bara filerna för uppgiften>      # 4. Commit: inga orelaterade filer, aldrig .env eller nycklar
git commit -m "Vad och varför"
git pull --rebase                         # 5. Hämta igen och lägg dina commits ovanpå
# kör kontrollerna igen om pull gav nya ändringar i samma delar
git push                                  # 6. Push. Nekas den: gör om 5 och 6. Aldrig --force.
```

- Committa eller lägg undan pågående ändringar innan `git pull`. Git skriver inte över dem, men vägrar.
- Krockar det i samma fil: lös konflikten så att bådas avsikt finns kvar, testa och pusha. Är det
  oklart vad som ska gälla, fråga den andra.
- Git hindrar inte att ni ändrar samma funktion samtidigt. Därför finns tabellen nedan.

## Kontroller före push

En push till `main` kör **ingen** CI: kontrollerna i `.github/workflows/` körs bara på pull requests.
Kör därför det som berörs lokalt:

| Ändrat | Kör |
|---|---|
| `app/` (gränssnitt) | `npm --prefix app test && npm --prefix app run build` |
| `app/src-tauri/` | samma som ovan, plus `cd app/src-tauri && cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test` |
| `apps/trader-go-universe/` | `npm --prefix apps/trader-go-universe test && npm --prefix apps/trader-go-universe run build && cargo test --manifest-path apps/trader-go-universe/src-tauri/Cargo.toml` |
| `engine/` | `cd engine && .venv/bin/python -m pytest` |

Windows provas bara av CI eller på en Windows-dator. Behövs det före en release: kör `windows-build.yml`
och `universe-windows.yml` för hand (Actions → Run workflow).

## Push är inte en appuppdatering

En push ändrar källkoden, inte de installerade apparna. En push till `main` startar inte heller
någon release: `desktop-release.yml` körs bara av en `v*`-tagg eller för hand. De installerade apparna
uppdateras först när en release har byggts, godkänts och publicerats (se [release.md](release.md)):

1. Run workflow med `channel = test`, och prova.
2. Run workflow med `channel = stable`, och svara `approve` i ärendet.
3. Båda apparna hämtar och verifierar uppdateringen och frågar "Starta om nu".

Pusha inga `v*`-taggar utan att ni båda vill släppa: en sådan tagg startar en stable-release.

## Samma app

Det finns en TraderGO (`com.seastick.tradergo`) och en TraderGO Universe
(`com.seastick.tradergo.universe`), byggda från `app/` och `apps/trader-go-universe/`.

- **Version och byggcommit** syns i TraderGO:s toppfält, under "Om Trader_go" och på Status, och i
  Universe-huvudet. Samma värden hos er båda betyder samma program.
- **"+ändrad"** efter commiten betyder ett lokalt bygge med ocommittade ändringar.
- **Gemensam app är inte gemensam data.** Marknadsdatan, paper-affärerna och inställningarna ligger i
  varje dators egen datamapp. Ni har samma program, men inte samma insamling eller papperssession.

## Pågående arbete

Skriv in större ändringar här, eller ändringar i delad kod (uppdateraren, datalagret, Universe), innan
du börjar. Ta bort raden när det är pushat.

| Vem | Vad | Filer/delar | Sedan |
|---|---|---|---|
| – | – | – | – |
