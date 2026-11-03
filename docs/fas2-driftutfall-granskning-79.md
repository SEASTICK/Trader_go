# Fas 2 – granskning av uppgraderingsutfall, PR #79

Granskad PR-head `784d43980a34856e5611417e0b0115e0792c3b85`, 2026-11-03. PR: https://github.com/SEASTICK/Trader_go/pull/79. PR:en innehåller bara plan, utfall och checklistunderlag. Kodpaketet från `b44d3cecaac6e05077c8ce2c74acf73a8455d0d8` är tidigare oberoende byggt och verifierat i `docs/fas2-jamforelsekurvor-granskning-78.md`.

## Oberoende serverkontroller

Kontrollerna gjordes via SSH med StrictHostKeyChecking=yes och den redan betrodda ED25519-värdnyckeln `SHA256:LaecJ+HSUDhJAc5UH4wM3b9xwMTTBOO8KAwQAOTcZ0k`. Bara läsande kontroller; ingen tjänst ändrades eller startades av granskningen.

- `check-single-worker.sh` godkänner exakt en worker, PID **30868**, taget lås, verifierat paket `tradergo-research-b44d3cecaac6` och full revision `b44d3cecaac6e05077c8ce2c74acf73a8455d0d8`.
- Systemd visar **0 omstarter**, aktiv sedan **2026-11-03 09:43:56 UTC**. `current` pekar på samma paket.
- Marknadsinsamlingen visar **Result=success**, **ExecMainStatus=0**, senaste avslut **09:48:02 UTC** vid kontrollen.
- Föregående release `tradergo-research-dee88eb65196` finns kvar för den dokumenterade kodåtergången. Återgång utfördes inte.
- Läsning av Supabase via serverns befintliga adapter ger **0 H-0013-körningar** och **0 queued/running**. Ingen reservation, köning eller resultatpublicering anropades.
- Den privata exporten `/root/tradergo-backups/pre-b44d3ce/research-20261103T094318363643Z.json.gz` lästes och dess tabellhash räknades om på servern. SHA-256 är **203aba6f826fa5db054b9bf3074f6cf37623bbec770c09760a6585b7cfd1f8b6**, identisk med rapporten och filens metadata. Filrättighet **0600** verifierad. Inga tabellrader eller hemligheter skrevs ut eller kopierades lokalt.
- Den installerade kurvfunktionens `curve_selection(3000)` ger **1500**. Det är ett rent indexprov, ingen forskningskörning.

## Avgränsningar

Rapporten skiljer korrekt forskningsexport från full databas-/Auth-backup. DigitalOceans exakta backupdatum är inte oberoende verifierat; tidigare användaruppgift är veckobackup och omkring 2026-11-02. Supabase-backup 2026-11-03 06:47:12 UTC är tidigare redovisad av Edwin. Inget nytt dashboardbevis begärs för att beskriva den redan utförda uppgraderingen; osäkerheten kvarstår uttryckligen.

Databaskontraktets fyra prov och anon-nekanden är redovisade i utfallet. De återkördes inte i denna omgranskning: SQL, grants och tjänster är oförändrade och var tidigare kontrollerade. Ett riktigt medlemstest, JWT-samtidighet och appens fullständiga flöde har inte ersatts av dessa kontroller. Den installerade appens nya vy och Stable är inte verifierade av en serveruppgradering. Larm är fortsatt undantagna enligt Edwins tidigare beslut.

Inga nya kodtester behövs för denna dokumentations- och driftverifiering. Godkänd kod har redan 553 passerande Python-testfall, 118 frontendtestfall och lyckat bygge. Checklistans schema och generering kontrolleras i samma leverans.

## Beslut

**PR #79 är godkänd för merge som driftredovisning på `784d439`.** Uppgraderingen till `b44d3ce` är oberoende bekräftad inom avgränsningen ovan. F2-605 behålls som verifierad och får nytt underlag. Gemensam status är **35 av 40**; arbetsområde 8 återstår.

Detta är inte tillstånd att starta en riktig H-0013-körning eller läsa slutprovet. Ingen ny migration, serverändring, körning, merge eller Stable-publicering gjordes i granskningen. Nästa steg är sluttestplan och verifiering av den installerade Mac-appen samt det inloggade app–kö–worker–resultatflödet, med separat beslut före den riktiga forskningskörningen. Ingen strategi är godkänd för papper/live.
