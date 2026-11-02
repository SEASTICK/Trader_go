# Servern: en gemensam forskningskö

Den driftsatta lösningen beskrivs i [research-cloud-setup.md](research-cloud-setup.md).
Tjänsten heter `tradergo-research-worker.service`; koden ligger under
`/opt/tradergo/current/engine/traderlab/research_engine/`.

Använd inte den äldre `deploy/setup.sh`, `tradergo-worker.service` eller
`server.jobs`. De är avstängda efter integrationsgranskningen eftersom de inte
följde databasens globala reservation, lease, heartbeat och fencing. Starta inte
en extra worker och ersätt inte den aktiva venv-mappen med rsync.

- Serverhemlighet: `/etc/tradergo/research.env`, root, 0600. Workern läser en
  systemd-credential; ingen nyckel ska skrivas i frontend eller Git.
- Kö: validerade Supabase RPC:er, en global aktiv forskningskörning åt gången.
- Registrerade körningar: teknisk reproduktion av frysta fönster, inte nya beslut.
- Marknadsinsamling: separat `tradergo-market-sync.service`/`.timer`, inga köjobb.
  Operativ framåtinsamling från 2026-11-02; tidigare forskning och slutprov hålls isär.
- De äldre GitHub-flödena för automatisk serverdeploy och migration är avstängda.
  Migreringar granskas och tillämpas en gång; ändra aldrig utgivna SQL-filer.

Kontroller och motivering: [research-integration-review.md](research-integration-review.md).
Backup/återställning: [research-backup-restore.md](research-backup-restore.md).
Inga börsnycklar, riktiga ordrar eller driftlarm ingår.
