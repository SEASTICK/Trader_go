#!/bin/bash
# Kontrollerar att exakt en forskningsworker kör, från rätt paket. Bara läsning: startar, stoppar och ändrar inget.
# Kör som root på servern. Avslutar med fel om något avviker. Se docs/fas2-driftsattning.md.
set -euo pipefail
unit=tradergo-research-worker.service
fail() { echo "FEL: $*" >&2; exit 1; }

# 1. Den nya tjänsten är aktiv, den äldre är varken aktiv eller aktiverad.
[ "$(systemctl is-active "$unit")" = active ] || fail "$unit är inte aktiv"
for legacy in tradergo-worker.service; do
  state=$(systemctl is-active "$legacy" 2>/dev/null || true)
  enabled=$(systemctl is-enabled "$legacy" 2>/dev/null || true)
  [ "$state" != active ] || fail "äldre $legacy är aktiv"
  [ "$enabled" != enabled ] || fail "äldre $legacy är aktiverad"
done

# 2. Exakt en workerprocess (förälder) på maskinen, och det är tjänstens huvudprocess.
main_pid=$(systemctl show -p MainPID --value "$unit")
parents=$(pgrep -f -- '-m traderlab.research_engine.worker' || true)
[ "$(printf '%s\n' "$parents" | grep -c .)" = 1 ] || fail "antal workerprocesser är inte 1: $(echo $parents)"
[ "$parents" = "$main_pid" ] || fail "workerprocessen $parents är inte tjänstens MainPID $main_pid"

# 3. Workerns lås är taget: en andra worker kan inte starta mot samma datakatalog.
if flock -n /var/lib/tradergo/worker.lock true; then fail "worker.lock är inte låst"; fi

# 4. Den körda koden är paketet som current pekar på, med samma revision som REVISION.env.
current=$(readlink -f /opt/tradergo/current)
python3 "$current/scripts/verify-research-release.py" "$current" >/dev/null || fail "paketet i $current är inte verifierat"
expected=$(sed -n 's/^TRADERGO_REVISION=//p' "$current/REVISION.env")
running=$(tr '\0' '\n' < "/proc/$main_pid/environ" | sed -n 's/^TRADERGO_REVISION=//p')
[ -n "$expected" ] && [ "$running" = "$expected" ] || fail "workerns TRADERGO_REVISION ($running) är inte paketets ($expected)"
journalctl -u "$unit" --since "-1 day" --no-pager | grep -q "revision=$expected" || fail "journalen visar inte revision=$expected"

echo "OK: en worker (PID $main_pid), lås taget, paket $(basename "$current"), revision $expected"
