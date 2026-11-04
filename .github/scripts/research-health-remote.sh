#!/bin/bash
# Körs på servern av research-health.yml. Bara läsning. Avslutar med fel om något avviker.
set -uo pipefail
err=0
bad() { echo "- FEL: $*"; err=1; }
ok() { echo "- OK: $*"; }
unit=tradergo-research-worker.service
echo "### Serverhälsa $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Release: \`$(basename "$(readlink -f /opt/tradergo/current)")\`"

[ "$(systemctl is-active "$unit")" = active ] && ok "forskningsworkern kör" || bad "forskningsworkern kör inte"
n=$(pgrep -fc -- '-m traderlab.research_engine.worker' || true)
[ "$n" = 1 ] && ok "exakt en workerprocess" || bad "antal workerprocesser är $n"
legacy=$(systemctl is-active tradergo-worker.service 2>/dev/null || true)
[ "$legacy" != active ] && ok "äldre worker är avstängd" || bad "äldre tradergo-worker.service är aktiv"

[ "$(systemctl is-active tradergo-market-sync.timer)" = active ] && ok "marknadssynken är schemalagd" || bad "timern för marknadssynken är inte aktiv"
result=$(systemctl show -p Result --value tradergo-market-sync.service)
[ "$result" = success ] && ok "senaste marknadssynk lyckades" || bad "senaste marknadssynk: $result"
last=$(systemctl show -p ExecMainExitTimestampMonotonic --value tradergo-market-sync.service)
now=$(awk '{print int($1*1000000)}' /proc/uptime)
if [ -n "$last" ] && [ "$last" != 0 ]; then
  age=$(( (now - last) / 60000000 ))
  [ "$age" -le 30 ] && ok "senaste marknadssynk för $age min sedan" || bad "senaste marknadssynk för $age min sedan (över 30)"
else bad "marknadssynken har inte körts sedan start"; fi

use=$(df --output=pcent /var/lib/tradergo | tail -1 | tr -dc 0-9)
[ "$use" -lt 85 ] && ok "disk $use % använd" || bad "disk $use % använd"
restarts=$(systemctl show -p NRestarts --value "$unit")
[ "${restarts:-0}" -lt 5 ] && ok "$restarts omstarter av workern" || bad "$restarts omstarter av workern"
exit $err
