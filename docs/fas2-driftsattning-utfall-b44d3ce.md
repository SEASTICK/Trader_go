# Fas 2: uppgradering av H-0013-workern till b44d3ce, utfall 2026-11-03

Genomförd enligt `docs/fas2-driftsattning-b44d3ce.md`, efter Edwins uttryckliga ja och Codex granskning
`8e7ea5e`. Bara workerkoden byttes. **Ingen SQL-migration kördes, ingen H-0013-körning startades, slutprovet lästes
inte och ingen Stable publicerades.** Återgång behövdes inte.

## Identitet

| | |
|---|---|
| Ny commit | `b44d3cecaac6e05077c8ce2c74acf73a8455d0d8` (merge av PR #78, jämförelsekurvor) |
| Paket | `tradergo-research-b44d3cecaac6.tar.gz`, 186 filer |
| SHA-256 | `015c190c5e9819c0d53795468dc00d551f23edbf78bc094fce34d8d6a46823f0` (lokalt och på servern) |
| Föregående | `tradergo-research-dee88eb65196` (`dee88eb…`), kvar orörd för återgång |
| Server | 201.79.3.175. SSH mot den betrodda värdnyckeln i `/private/tmp/tradergo-host-key` med `StrictHostKeyChecking=yes` |

## Före ändringen (09:42–09:43 UTC)

- **Nuläge:** `current` pekade på `tradergo-research-dee88eb65196`. `check-single-worker.sh` godkände (PID 24061,
  0 omstarter sedan 2026-11-02 20:17:44 UTC). Den äldre `tradergo-worker` var inaktiv och maskad.
- **Kö:** inga körningar `queued` eller `running` och 0 H-0013-körningar. Ingen oväntad H-0013-körning fanns.
- **Egen export:**
  - Första försöket avbröts av exportens eget skydd ("Research data changed during export"), eftersom
    marknadsinsamlingen skrev nya staplar mitt i läsningen. Inget sparades.
  - Exporten togs därefter direkt efter insamlingskörningen 09:42:49: `/root/tradergo-backups/pre-b44d3ce/research-20261103T094318363643Z.json.gz`.
    Filen har rättighet 0600 i en katalog med 0700, och läsningen efter skrivning är verifierad.
  - Tabell-SHA-256: `203aba6f826fa5db054b9bf3074f6cf37623bbec770c09760a6585b7cfd1f8b6`. Den omfattar 12 006 candles,
    5 486 fundingrader, 15 hypoteser, 12 körningar, 7 resultat och 274 affärer.
  - Exporten omfattar forskningstabellerna, inte Auth eller hela databasen.
- **Leverantörernas backup:**
  - DigitalOcean har veckobackup. Det faktiska datumet för senaste lyckade backup kan inte läsas från servern:
    dropletens metadata innehåller ingen backupinformation, och ingen DigitalOcean-åtkomst finns i sessionen.
  - Senaste kända uppgift är Edwins dashboard 2026-11-03: "Last backup was 1 day ago", alltså omkring 2026-11-02.
    **Det exakta datumet är inte verifierat här.**
  - Supabase visade enligt Edwin en backup 2026-11-03 06:47:12 UTC.

## Ändring

1. **Uppladdning:** SHA-256 stämmer på servern, och `verify-research-release.py` godkände 186 filer med
   `TRADERGO_REVISION=b44d3ce…`. Tjänstefilen och `engine/requirements.txt` är identiska med den installerade
   releasen.
2. **Kontrollerat stopp 09:43:50 UTC:** tjänsten blev `inactive`, ingen workerprocess fanns kvar och ingen körning var
   köad eller pågick.
3. **Installation:** `install.sh` verifierade paketet och bytte `current` till `tradergo-research-b44d3cecaac6`.
   Samma tjänstefil installerades igen och kontrollerades med `systemd-analyze verify`. Den delade venv-miljön
   ändrades inte, eftersom beroendena är identiska.
4. **Start 09:43:56 UTC:** journalen visar `revision=b44d3cecaac6e05077c8ce2c74acf73a8455d0d8` och
   `catalog={'hypotheses': 15, 'strategies': 4}`.

## Kontroller efter ändringen

- **Exakt en worker:** `check-single-worker.sh` gav `OK: en worker (PID 30868), lås taget, paket
  tradergo-research-b44d3cecaac6, revision b44d3cecaac6…`. 0 omstarter och inga varningar i journalen.
- **Driftsatt kod:** `fas2_eval.comparison_curves` finns, `curve_selection(3000)` ger 1 500 punkter och workerns
  resultatpaket innehåller jämförelsekurvorna.
- **Databaskontraktet** (oförändrat 0005, som service_role):
  - `research_h0013_result_ok` ger `true` för en konsekvent `REJECT`;
  - `false` för `MORE_RESEARCH` med falska kriterier;
  - `true` för `MORE_RESEARCH` med fem sanna kriterier;
  - `false` för `holdout_loaded` som sträng.
- **Anon nekas** med HTTP 401 / `42501` för köning, kontrollfunktionen och `research_finish`.
- **Kö och register:** 0 H-0013-körningar, inget köat eller pågående, och H-0013 står utan beslut i `hypotheses`.
- **Marknadsinsamlingen:** första körningen på den nya releasen var klar 09:48:02 UTC med `Result=success`. Den
  skrev en ny pågående stapel för var och en av spot och um i 1h, 4h och 1d, och ingen ny funding vid den tidpunkten.
  `check-single-worker.sh` godkände igen efteråt (samma PID 30868, 0 omstarter).

## Återgång (behövdes inte)

1. Stoppa workern med `systemctl stop tradergo-research-worker`.
2. Peka tillbaka: `ln -sfn /opt/tradergo/releases/tradergo-research-dee88eb65196 /opt/tradergo/current`.
3. Kör `systemctl daemon-reload`, starta och kör `check-single-worker.sh`. Den ska visa `dee88eb`.

0005 och databasen lämnas orörda.
