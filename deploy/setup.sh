#!/usr/bin/env bash
# Körs på servern av .github/workflows/server-deploy.yml efter att koden kopierats till /opt/tradergo.
# Idempotent: kan köras hur många gånger som helst.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
if ! command -v python3 >/dev/null || ! python3 -c "import venv" 2>/dev/null || ! dpkg -s unattended-upgrades >/dev/null 2>&1; then
  apt-get update -q
  apt-get install -y -q python3 python3-venv python3-pip rsync unattended-upgrades ufw
fi

# Grundskydd: bara SSH in, automatiska säkerhetsuppdateringar.
ufw allow OpenSSH >/dev/null
ufw --force enable >/dev/null
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true

id tradergo >/dev/null 2>&1 || useradd --system --home /opt/tradergo --shell /usr/sbin/nologin tradergo

python3 -m venv /opt/tradergo/venv
/opt/tradergo/venv/bin/pip install -q --upgrade pip
/opt/tradergo/venv/bin/pip install -q -r /opt/tradergo/engine/requirements.txt
chown -R tradergo:tradergo /opt/tradergo

test -f /etc/tradergo/worker.env || { echo "Saknar /etc/tradergo/worker.env" >&2; exit 1; }
chmod 600 /etc/tradergo/worker.env

install -m 644 /opt/tradergo/deploy/tradergo-worker.service /etc/systemd/system/tradergo-worker.service
systemctl daemon-reload
systemctl enable tradergo-worker >/dev/null
systemctl restart tradergo-worker
sleep 5
systemctl --no-pager --lines=20 status tradergo-worker
