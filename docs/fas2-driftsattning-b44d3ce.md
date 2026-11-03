# Fas 2: uppgradering av H-0013-workern till b44d3ce (plan för beslut)

Detta är en plan. **Inget är uppladdat eller driftsatt.** Servern kör fortfarande `dee88eb`, som driftsattes och
verifierades 2026-11-02/03 (`docs/fas2-driftsattning-utfall-20261102.md`). Uppgraderingen kräver Edwins
uttryckliga ja. Ingen H-0013-körning startas i samband med den, och slutprovet läses inte.

## Paket

| | |
|---|---|
| Commit | `b44d3cecaac6e05077c8ce2c74acf73a8455d0d8` (merge av PR #78, jämförelsekurvor) |
| Paket | `tradergo-research-b44d3cecaac6.tar.gz`, 653 661 byte, 186 filer |
| SHA-256 | `015c190c5e9819c0d53795468dc00d551f23edbf78bc094fce34d8d6a46823f0` |
| REVISION.env | `TRADERGO_REVISION=b44d3cecaac6e05077c8ce2c74acf73a8455d0d8` |
| Lokalt | `dist/research-release/` (git-ignorerad), byggd två gånger med identiskt resultat, `.sha256` stämmer, `verify-research-release.py` godkänner |

## Vad som ändras mot den driftsatta dee88eb

- **Ändrat:** bara `engine/traderlab/fas2_eval.py` och `engine/traderlab/research_engine/h0013.py`. H-0013-resultatet får
  `curves.comparisons`, jämförelsekurvor med källor (`docs/fas2-jamforelsekurvor-tolkningar.md`).
- **Kriterier, nyckeltal och beslut ändras inte.** Codex före/efter-prov på `db9a4ec` gav samma resultat bortsett
  från det nya fältet. Rättningarna efter det rör bara kurvfunktionens skydd och urval.
- **Oförändrat:** migrationerna (0005 är identisk, SHA-256 `a5e093b0…1a72`, och redan applicerad),
  `engine/requirements.txt`, tjänstefilerna i `services/research-worker/`, `research_engine/sync.py` och
  `scripts/verify-research-release.py`.
- **Ingen migration och ingen databasändring behövs,** och den delade venv-miljön ändras inte.

## Ordning (efter uttryckligt ja)

1. **Förutsättningar.**
   - Inga körningar är `running`, och ingen H-0013-körning är köad eller pågår. Finns en sådan, vänta tills den
     är klar. Byts koden mitt i en körning avbryts försöket och räknas.
   - Ta en egen export med `traderlab.research_engine.backup` till `/root/tradergo-backups/pre-b44d3ce/`.
   - Bekräfta dagens backupdatum i DigitalOcean och Supabase.
2. **Kontrollera nuläget** utan att ändra något: `check-single-worker.sh` ska godkänna `dee88eb`, och `current`
   ska peka på `tradergo-research-dee88eb65196`.
3. **Ladda upp och verifiera** till `/opt/tradergo/releases/`. SHA-256 ska vara `015c190c…23f0`. Packa upp och kör
   `verify-research-release.py`.
4. **Stoppa workern kontrollerat** med `systemctl stop tradergo-research-worker`. Den ska bli `inactive`, och inga
   körningar får vara `running`.
5. **Installera** med `install.sh /opt/tradergo/releases/tradergo-research-b44d3cecaac6`. Skriptet verifierar
   paketet och byter `current`. Tjänstefilen är identisk med den installerade. Föregående release ligger kvar.
6. **Starta och kontrollera.** Journalen ska visa `revision=b44d3cecaac6…`, och `check-single-worker.sh` ska
   godkänna (en worker, låset taget, paketet verifierat, rätt revision).
7. **Kontrollera databasen utan att skriva:**
   - 0 H-0013-körningar;
   - inga körningar `running`;
   - `research_h0013_result_ok` ger samma svar som vid slutkontrollen av `dee88eb`;
   - anon nekas fortfarande.
8. **Kontrollera marknadsinsamlingen:** nästa `tradergo-market-sync` ska gå felfritt på den nya releasen.

## Återgång

Uppgraderingen ändrar bara kod, så återgången ändrar bara kod. Databasen och 0005 lämnas orörda.

1. Stoppa workern med `systemctl stop tradergo-research-worker`.
2. Peka tillbaka: `ln -sfn /opt/tradergo/releases/tradergo-research-dee88eb65196 /opt/tradergo/current`.
   Tjänstefilen är densamma i båda releaserna. Kör ändå `systemctl daemon-reload`.
3. Starta och kör `check-single-worker.sh`. Den ska visa `revision=dee88eb…`.

`dee88eb` har H-0013-ingången och samma kontrakt som 0005, så den kan ta över även om en H-0013-körning skulle
vara köad. Ett resultat från `dee88eb` saknar jämförelsekurvorna och visas i Research Lab med dem som saknade.
Att gå längre tillbaka, till `008f612`, kräver den äldre planen med återgång av 0005
(`docs/fas2-driftsattning.md`).
