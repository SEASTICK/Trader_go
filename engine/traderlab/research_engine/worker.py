"""En parent med heartbeat och en avbrytbar beräkningsprocess utan servernyckel."""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import multiprocessing as mp
import signal
import socket
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from .supabase import ConnectionFailure, SupabaseStore

LOG = logging.getLogger("research-worker")


def child(job, data_dir, output):
    try:
        if job.get("kind") == "registered" and job.get("hypothesis_id") == "H-0013":
            from .h0013 import run_job
        elif job.get("kind") == "registered":
            from .registered import run_job
        else:
            from .runner import run_job
        run_job(job, Path(data_dir), Path(output))
    except ValueError as exc:
        # ValueError i denna beräkningsprocess kan inte innehålla servernyckeln.
        Path(output).with_suffix(".error").write_text(str(exc)[:1000])
        raise SystemExit(1)
    except Exception as exc:
        Path(output).with_suffix(".error").write_text("Beräkningen misslyckades: " + type(exc).__name__)
        raise SystemExit(1)


def stop(process):
    if process.is_alive():
        process.terminate()
        process.join(5)
    if process.is_alive():
        process.kill()
        process.join(5)


def timeout_for(job) -> int:
    """H-0013 får två timmar (200 permutationer och 81 spelböcker); allt annat 30 minuter."""
    if job.get("kind") == "registered" and job.get("hypothesis_id") == "H-0013":
        from .h0013 import TIMEOUT
        return TIMEOUT
    return 1800


def execute(store, job, data_dir, stopping, timeout=1800):
    identity = {"p_id": job["id"], "p_token": job["lease_token"]}
    with TemporaryDirectory(prefix="research-", dir=data_dir) as folder:
        output = Path(folder) / "result.json"
        process = mp.get_context("spawn").Process(target=child, args=(job, str(data_dir), str(output)))
        process.start()
        deadline = time.monotonic() + timeout
        last_beat = 0.0
        try:
            while process.is_alive():
                if stopping() or time.monotonic() >= deadline:
                    stop(process)
                    store.rpc("research_finish", {**identity, "p_error": "Worker stoppad eller tidsgräns nådd"})
                    return
                if time.monotonic() - last_beat >= 10:
                    progress_file = output.with_suffix(".progress")
                    try:
                        progress = float(progress_file.read_text()) if progress_file.exists() else 0.05
                    except ValueError:
                        progress = 0.05
                    state = store.rpc("research_heartbeat", {**identity, "p_progress": progress})
                    if state != "running":
                        stop(process)
                        if state != "lost":
                            store.rpc("research_finish", {**identity, "p_error": "Avbruten"})
                        return
                    last_beat = time.monotonic()
                process.join(0.5)
            if process.exitcode != 0:
                error = output.with_suffix(".error")
                store.rpc("research_finish", {**identity, "p_error": error.read_text() if error.exists() else "Processen avslutades oväntat"})
                return
            for suffix, table in ((".candles", "candles"), (".funding", "funding_rates")):
                path = output.with_suffix(suffix)
                if not path.exists():
                    continue
                rows = json.loads(path.read_text())
                for offset in range(0, len(rows), 500):
                    if stopping():
                        store.rpc("research_finish", {**identity, "p_error": "Worker stoppad"})
                        return
                    state = store.rpc("research_heartbeat", {**identity, "p_progress": 0.95})
                    if state != "running":
                        if state != "lost":
                            store.rpc("research_finish", {**identity, "p_error": "Avbruten"})
                        return
                    store.insert_market_rows(table, rows[offset:offset + 500])
            accepted = store.rpc("research_finish", {**identity, "p_result": json.loads(output.read_text())})
            LOG.info("run=%s result_accepted=%s", job["id"], accepted)
        finally:
            stop(process)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args.data_dir.mkdir(parents=True, exist_ok=True)
    lock = (args.data_dir / "worker.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    halted = False

    def halt(*_):
        nonlocal halted
        halted = True

    signal.signal(signal.SIGTERM, halt)
    signal.signal(signal.SIGINT, halt)
    store = SupabaseStore.from_env_file(args.env_file)
    from .catalog import sync_catalog
    try:
        LOG.info("catalog=%s", sync_catalog(store,Path(__file__).resolve().parents[3]))
    except ConnectionFailure as exc:
        LOG.warning("Catalog sync unavailable: %s",exc)
    while not halted:
        try:
            job = store.rpc("research_claim", {"p_worker": socket.gethostname()})
            if job:
                LOG.info("run=%s started", job["id"])
                execute(store, job, args.data_dir, lambda: halted, timeout=timeout_for(job))
        except ConnectionFailure as exc:
            # Ingen ny körning medan pågående process har förlorat anslutningen.
            LOG.warning("%s", exc)
        if args.once:
            break
        for _ in range(10):
            if halted:
                break
            time.sleep(1)


if __name__ == "__main__":
    main()
