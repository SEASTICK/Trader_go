"""Workerns huvudloop: synka marknadsdata, spegla registret och kör köade backtester.

Startas av systemd (deploy/tradergo-worker.service): python -m traderlab.server.main
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from . import jobs, registry_sync, sync
from .supa import Supabase

SYNC_EVERY = int(os.environ.get("TRADERGO_SYNC_SECONDS", "300"))
POLL_EVERY = int(os.environ.get("TRADERGO_POLL_SECONDS", "15"))
REPO = Path(os.environ.get("TRADERGO_REPO", Path(__file__).resolve().parents[3]))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    log = logging.getLogger("tradergo")
    db = Supabase()
    log.info("worker startar (bara papper och publik data), repo %s", REPO)
    try:
        log.info("register: %s", registry_sync.sync(db, REPO))
    except Exception:
        log.exception("spegling av registret misslyckades")
    last_sync = 0.0
    while True:
        if time.time() - last_sync >= SYNC_EVERY:
            log.info("synk: %s", sync.sync_all(db))
            last_sync = time.time()
        try:
            while jobs.process_one(db):
                pass
        except Exception:
            log.exception("jobbkön fallerade")
        time.sleep(POLL_EVERY)


if __name__ == "__main__":
    main()
