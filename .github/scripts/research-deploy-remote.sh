#!/bin/bash
# Körs på servern (som root, via ssh från research-deploy.yml). Följer docs/fas2-driftsattning.md steg 3–6:
# verifiera paketet, vänta tills inget jobb kör, stoppa kontrollerat, installera med install.sh, starta och
# kontrollera med check-single-worker.sh. Rör inte Supabase-schemat: migrationer görs fortfarande för hand.
# Argument: paketnamn (tradergo-research-<commit12>) och förväntad SHA-256 för tar.gz.
set -euo pipefail
name=${1:?paketnamn}; sha=${2:?sha256}
rel=/opt/tradergo/releases; dir=$rel/$name; tgz=/tmp/$name.tar.gz
unit=tradergo-research-worker.service
store_py() { PYTHONPATH=/opt/tradergo/current/engine /opt/tradergo/venv/bin/python - "$@"; }

echo "== 1. Verifiera paketet"
echo "$sha  $tgz" | sha256sum -c -
if [ -d "$dir" ]; then echo "$dir finns redan, verifierar det i stället för att packa upp igen."
else tar -xzf "$tgz" -C "$rel"; fi
python3 "$dir/scripts/verify-research-release.py" "$dir"
current=$(readlink -f /opt/tradergo/current || true)
echo "Nuvarande release: $current"

echo "== 2. Inga körningar får vara igång"
store_py <<'PY'
from pathlib import Path
from traderlab.research_engine.supabase import SupabaseStore
s = SupabaseStore.from_env_file(Path('/etc/tradergo/research.env'))
running = s._get('runs', {'select': 'id', 'status': 'eq.running', 'limit': 5})
if running:
    raise SystemExit(f"Avbryter: {len(running)} körning(ar) pågår. Vänta tills de är klara och kör igen.")
print("Inga pågående körningar.")
PY

echo "== 3. Stoppa workern kontrollerat"
systemctl stop "$unit"
for _ in $(seq 1 60); do [ "$(systemctl is-active "$unit" || true)" != active ] && break; sleep 1; done
[ "$(systemctl is-active "$unit" || true)" != active ] || { echo "Workern stoppade inte inom 60 s." >&2; exit 1; }
store_py <<'PY'
from pathlib import Path
from traderlab.research_engine.supabase import SupabaseStore
s = SupabaseStore.from_env_file(Path('/etc/tradergo/research.env'))
slot = s._get('research_worker_slot', {'select': 'run_id', 'limit': 1})
if slot and slot[0].get('run_id'):
    raise SystemExit(f"Slotten är inte tom (run_id={slot[0]['run_id']}). Stoppat, men installerar inte.")
print("Slotten är tom.")
PY

echo "== 4. Installera (install.sh verifierar igen och byter current, startar inget)"
bash "$dir/services/research-worker/install.sh" "$dir"

echo "== 5. Starta och kontrollera"
systemctl start "$unit"
sleep 8
bash "$dir/services/research-worker/check-single-worker.sh"
echo "Klart: $(readlink -f /opt/tradergo/current) kör. Föregående release ($current) ligger kvar för återgång."
