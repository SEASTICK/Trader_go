# Servern: forskningsworker på DigitalOcean och data i Supabase

Workern hämtar publik marknadsdata, speglar registret och kör backtester som köas. Den har inga börsnycklar
och ingen orderkod, och ett test i `engine/tests/test_server.py` stoppar sådan kod.

| Del | Var |
|---|---|
| Kod | `engine/traderlab/server/` (`sync.py`, `jobs.py`, `registry_sync.py`, `main.py`) |
| Tjänst | `deploy/tradergo-worker.service`, körs som användaren `tradergo` med låst filsystem |
| Installation | `deploy/setup.sh`: Python-venv, brandvägg (bara SSH), automatiska säkerhetsuppdateringar |
| Deploy | `.github/workflows/server-deploy.yml` vid ändring i `engine/`, `deploy/` eller registret på main |
| Databas | `supabase/migrations/*.sql`, körs av `.github/workflows/supabase-migrate.yml` |

## Hemligheter (bara i GitHub, aldrig i Git)

| Namn | Används av |
|---|---|
| `SERVER_HOST`, `SERVER_SSH_KEY` | Deploy |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Workern (skrivs till `/etc/tradergo/worker.env`, läsbar bara för root) |
| `SUPABASE_DB_URL` | Migreringar |
| `SUPABASE_ANON_KEY` (variabel, inte hemlig) | Appen, för inloggning och läsning |

## Vad workern gör

- **Var 5:e minut:** hämtar nya staplar för BTCUSDT spot 1h, 4h och 1d, terminer 4h, och finansieringsränta.
  Första gången hämtas hela historiken (spot från 2017, terminer från 2020). Pågående stapel märks `closed = false`.
- **Var 15:e sekund:** tar köade körningar i `runs`, kör dem och sparar statistik, kurvor och affärer.
- **Vid start:** speglar `research/registry.md` och strategierna till tabellerna `hypotheses` och `strategies`.

## Felsökning på servern

```bash
journalctl -u tradergo-worker -f
```

```bash
systemctl restart tradergo-worker
```
