#!/usr/bin/env bash
set -euo pipefail
# The old installer created another service and could replace the active venv.
printf '%s\n' 'Använd services/research-worker/tradergo-research-worker.service och docs/research-cloud-setup.md.' >&2
printf '%s\n' 'Den äldre installeraren är avstängd; ingen ändring utförd.' >&2
exit 1
