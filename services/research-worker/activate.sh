#!/bin/bash
# Kräver att 0003 har applicerats. Kontrollera migrationsstatus utan att reservera ett jobb.
set -euo pipefail
PYTHONPATH=/opt/tradergo/current/engine /opt/tradergo/venv/bin/python - <<'PY'
from pathlib import Path
from traderlab.research_engine.supabase import SupabaseStore
store = SupabaseStore.from_env_file(Path('/etc/tradergo/research.env'))
store.check_schema()
# Att läsa kolumnen visar att kömigrationen finns. RPC-grants verifieras i sluttestet.
store._get('runs', {'select': 'id,attempts,request_key', 'limit': 0})
print('Schema och kökolumner tillgängliga.')
PY
touch /etc/tradergo/queue-ready
chmod 600 /etc/tradergo/queue-ready
systemctl enable --now tradergo-research-worker.service
systemctl is-active tradergo-research-worker.service
