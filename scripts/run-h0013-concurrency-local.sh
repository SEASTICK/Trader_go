#!/usr/bin/env bash
# Startar en tillfällig PostgreSQL i en tom katalog, kör ett samtidighetstest (standard test-h0013-concurrency.mjs,
# annars skriptet som anges) och tar bort allt. Inget moln.
#   npm install --prefix /tmp/tradergo-pg-test pg@8.13.1 embedded-postgres@17.5.0-beta.15
set -euo pipefail
prefix=${PG_TEST_PREFIX:-/tmp/tradergo-pg-test}
bin=$(ls -d "$prefix"/node_modules/@embedded-postgres/*/native/bin | head -1)
port=${PG_TEST_PORT:-54329}
work=$(mktemp -d)
trap '"$bin/pg_ctl" -D "$work/data" -m immediate stop >/dev/null 2>&1 || true; rm -rf "$work"' EXIT
"$bin/initdb" -D "$work/data" -U postgres --auth=trust --no-locale -E UTF8 >/dev/null
"$bin/pg_ctl" -D "$work/data" -o "-p $port -k $work -c listen_addresses=127.0.0.1" -l "$work/log" -w start >/dev/null
PG_ADMIN_URL="postgres://postgres@127.0.0.1:$port/postgres" PG_MODULE="$prefix/node_modules/pg/lib/index.js" \
  node "$(dirname "$0")/${1:-test-h0013-concurrency.mjs}"
