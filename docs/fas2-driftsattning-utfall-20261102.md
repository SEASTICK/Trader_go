# Fas 2: driftsättning av H-0013-kön, utfall 2026-11-02/03

Genomfört enligt `docs/fas2-driftsattning.md` steg 1–8, efter Edwins uttryckliga ja. Ingen H-0013-körning har
startats. Slutprovet har inte lästs.

## Identitet

| | |
|---|---|
| Commit | `dee88eb65196b17879b2fc22c0b7521ad37501c3` (merge av PR #74) |
| Paket | `tradergo-research-dee88eb65196.tar.gz`, 186 filer |
| SHA-256 | `62c7d8e482ef6a1755d670f74a7631c221469e61259a09b285f32627936c8575` (lokalt och på servern) |
| Migration | `supabase/migrations/0005_h0013_queue.sql`, SHA-256 `a5e093b051d6eee206025cc1810be7abba2a1322c684b9f9682d09c6f99e1a72` |
| Server | DigitalOcean-droplet 201.79.3.175 (FRA1). SSH som root med kontroll mot den betrodda värdnyckeln i `/private/tmp/tradergo-host-key`, ED25519 `SHA256:LaecJ+HSUDhJAc5UH4wM3b9xwMTTBOO8KAwQAOTcZ0k`, med `StrictHostKeyChecking=yes` |
| Supabase | Projekt `klspebwvipfzvqbdexxh` |

## Steg

1. **Förutsättningar (2026-11-02 20:15 UTC).**
   - En aktiv `tradergo-research-worker` (PID 20089, 0 omstarter). Den äldre `tradergo-worker` är inaktiv och
     maskad.
   - `current` pekade på `20261102-research-008f612`.
   - Inga körningar `running` och 0 H-0013-körningar.
   - `engine/requirements.txt` och `research_engine/sync.py` är identiska med paketet, så den delade venv-miljön
     ändrades inte.
   - **Egen export:** `/root/tradergo-backups/pre-dee88eb/research-20261102T201620836519Z.json.gz` (0600),
     tabell-SHA-256 `dcfb6fa4f669055d61c1372edb49a2e9bb17b53c5295e29e603fec68cbdf8074`, verifierad efter
     skrivning. Den omfattar 11 972 candles, 5 484 fundingrader, 12 körningar, 7 resultat och 274 affärer.
     Exporten omfattar inte Auth eller hela databasen.
   - **Leverantörernas backupdatum** (DigitalOcean, Supabase) har inte kontrollerats från servern; det kräver
     deras dashboards.
2. **Paket.** Det reproducerbara bygget lokalt gav samma SHA-256 två gånger.
3. **Uppladdning och verifiering.** Paketet laddades upp till `/opt/tradergo/releases/`. SHA-256 stämmer på
   servern, och `verify-research-release.py` godkände: 186 filer, `TRADERGO_REVISION=dee88eb…`.
4. **Kontrollerat stopp 20:17:08–09 UTC.** Tjänsten stoppades rent (`Deactivated successfully`) och är `inactive`.
   Ingen workerprocess finns kvar och ingen körning är `running`.
5. **Installation.**
   - `install.sh` verifierade paketet och bytte `current` till `tradergo-research-dee88eb65196`.
   - Tjänstefilen med `EnvironmentFile=/opt/tradergo/current/REVISION.env` installerades och
     `systemd-analyze verify` godkände den.
   - Den tidigare tjänstefilen är sparad som `/root/tradergo-backups/tradergo-research-worker.service.before-dee88eb`.
   - Föregående release ligger kvar orörd.
6. **Start 20:17:44 UTC.**
   - Journalen visar `revision=dee88eb65196b17879b2fc22c0b7521ad37501c3` och `catalog={'hypotheses': 15, 'strategies': 4}`.
   - `check-single-worker.sh`: `OK: en worker (PID 24061), lås taget, paket tradergo-research-dee88eb65196,
     revision dee88eb…`.
   - H-0013 finns i `hypotheses` med registercommit `008f612` och utan beslut.
7. **Migration 0005.** Edwin körde filen i SQL Editor.
   - Första försöket applicerades inte. Kontrollfrågan gav `42883 function "public.research_enqueue_h0013(uuid)"
     does not exist`, och servern fick `PGRST202` för båda funktionerna.
   - Hela filen kördes därefter som en körning: `Success. No rows returned`.
8. **Slutkontroll 2026-11-03.**
   - **PostgREST ser funktionerna.** Som service_role ger `research_h0013_result_ok`:
     - `true` för ett konsekvent `REJECT`;
     - `false` för `MORE_RESEARCH` med falska kriterier;
     - `true` för `MORE_RESEARCH` med alla fem kriterier sanna;
     - `false` för `holdout_loaded` som sträng.
   - **Anon nekas** med HTTP 401 / `42501` för `research_enqueue_h0013`, `research_h0013_result_ok` och
     `research_finish`.
   - **Kö och körningar:** 0 H-0013-körningar och inga körningar `running`.
   - **Workern:** `check-single-worker.sh` godkänner igen (samma PID 24061, 0 omstarter sedan 20:17:44 UTC). Inga
     varningar i journalen sedan starten.
   - **Marknadsinsamlingen** har körts på den nya releasen utan fel (`Result=success`, senast 08:17:32 UTC).

## Inte verifierat

- **Inloggade medlemmars rättighet** att köa (`authenticated`) är inte provad från servern; det kräver en riktig
  användarsession. Kontrollfrågan för rättigheterna i SQL Editor visar den.
- **Leverantörernas backupdatum** för dagen.
- **Samtidighet mot själva Supabase** med riktiga JWT. Lokalt provat mot PostgreSQL 17.
- **Larm** ingår inte.

## Återgång

Enligt `docs/fas2-driftsattning.md`:

1. Stoppa workern.
2. Kör `supabase/rollback/0005_h0013_queue_down.sql`. Den vägrar om H-0013-körningar finns.
3. Peka `current` tillbaka på `20261102-research-008f612` och installera den releasens tjänstefil.

Föregående release, tjänstefil och export finns kvar.
