#!/bin/bash
# Kör som root med sökvägen till en uppackad, verifierad release.
# Installerar tjänsten men startar den först efter separat schemakontroll.
set -euo pipefail
release=${1:?Ange en absolut releasekatalog}
test "${release#/opt/tradergo/releases/}" != "$release"
test -f "$release/engine/traderlab/research_engine/worker.py"
# Varje fil mot paketets release.json och REVISION.env mot dess commit, innan något installeras.
python3 "$release/scripts/verify-research-release.py" "$release"
test -f /etc/tradergo/research.env
id tradergo >/dev/null 2>&1 || useradd --system --home-dir /var/lib/tradergo --shell /usr/sbin/nologin tradergo
install -d -m 700 -o tradergo -g tradergo /var/lib/tradergo
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-venv
test -x /opt/tradergo/venv/bin/python || python3 -m venv /opt/tradergo/venv
/opt/tradergo/venv/bin/pip install --disable-pip-version-check -r "$release/engine/requirements.txt"
ln -sfn "$release" /opt/tradergo/current
install -m 644 "$release/services/research-worker/tradergo-research-worker.service" /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/tradergo-research-worker.service
echo 'Installerat; tjänsten har inte startats. Följ docs/fas2-driftsattning.md för start och migration.'
