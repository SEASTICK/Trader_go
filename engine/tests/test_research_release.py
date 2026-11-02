"""Driftsättningsunderlaget för F2-605, lokalt: paket, verifiering, tjänstefil, en worker och revision. Ingen server."""
import hashlib
import json
import logging
import multiprocessing as mp
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import pytest

from traderlab.research_engine import worker

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "scripts/build-research-release.sh"
sys.path.insert(0, str(REPO / "scripts"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("verify_release", REPO / "scripts/verify-research-release.py")
verify_release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_release)


def build(out: Path, commit="HEAD") -> tuple[Path, str]:
    lines = subprocess.run([str(BUILD), commit, str(out)], check=True, capture_output=True, text=True,
                           cwd=REPO).stdout.split()
    return Path(lines[-2]), lines[-1]


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("release")
    path, digest = build(out)
    root = tmp_path_factory.mktemp("unpacked")
    with tarfile.open(path) as tar:
        tar.extractall(root, filter="data")
    return path, digest, next(root.iterdir())


def test_package_is_reproducible_and_named_after_the_commit(package, tmp_path):
    path, digest, root = package
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    assert path.name == f"tradergo-research-{commit[:12]}.tar.gz"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    again, digest2 = build(tmp_path)
    assert digest2 == digest, "the same commit gives the same SHA-256"
    assert (path.parent / f"{path.name}.sha256").read_text().split()[0] == digest


def test_package_carries_revision_manifest_and_what_the_worker_reads(package):
    _, _, root = package
    manifest = json.loads((root / "release.json").read_text())
    assert (root / "REVISION.env").read_text() == f"TRADERGO_REVISION={manifest['commit']}\n"
    assert manifest["requires_migration"] == "supabase/migrations/0005_h0013_queue.sql"
    for needed in ("engine/traderlab/research_engine/worker.py", "engine/traderlab/research_engine/h0013.py",
                   "engine/traderlab/fas2_eval.py", "research/registry.md", "research/fas2-protokoll.md",
                   "app/data/registered-results.json", "services/research-worker/tradergo-research-worker.service",
                   "scripts/verify-research-release.py",
                   "data/audits/fas1-20261102/frozen-6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c.json"):
        assert needed in manifest["files"], needed
    # Inga hemligheter: den enda .env-filen är REVISION.env, som bara anger commiten.
    assert [f for f in manifest["files"] if f.endswith(".env") or "/.env" in f] == ["REVISION.env"]
    assert not [f for f in manifest["files"] if f.startswith("app/src")]
    assert verify_release.verify(root)["commit"] == manifest["commit"]


@pytest.mark.parametrize("damage", ["changed", "extra", "missing", "revision", "pycache_is_ignored"])
def test_verification_rejects_a_tampered_package(package, tmp_path, damage):
    import shutil
    _, _, root = package
    copy = tmp_path / root.name
    shutil.copytree(root, copy)
    if damage == "changed":
        (copy / "engine/traderlab/fas2.py").write_text("# ändrad\n")
    elif damage == "extra":
        (copy / "engine/traderlab/extra.py").write_text("x = 1\n")
    elif damage == "missing":
        (copy / "research/registry.md").unlink()
    elif damage == "revision":
        (copy / "REVISION.env").write_text("TRADERGO_REVISION=" + "0" * 40 + "\n")
    else:
        (copy / "engine/traderlab/__pycache__").mkdir(exist_ok=True)
        (copy / "engine/traderlab/__pycache__/x.pyc").write_bytes(b"cache")
        assert verify_release.verify(copy)["files"] > 0
        return
    with pytest.raises(SystemExit):
        verify_release.verify(copy)


def test_service_reads_the_revision_and_install_verifies_first():
    service = (REPO / "services/research-worker/tradergo-research-worker.service").read_text()
    assert "EnvironmentFile=/opt/tradergo/current/REVISION.env" in service
    assert "TimeoutStopSec=45" in service and "ReadWritePaths=/var/lib/tradergo" in service
    assert worker.GRACE + 5 < 45, "controlled stop and kill fit inside systemd's stop timeout"
    install = (REPO / "services/research-worker/install.sh").read_text()
    assert install.index("verify-research-release.py") < install.index("ln -sfn")
    assert "systemctl start" not in install and "enable --now" not in install


def test_single_worker_check_is_read_only_and_valid_bash():
    script = REPO / "services/research-worker/check-single-worker.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    text = script.read_text()
    for verb in ("systemctl start", "systemctl stop", "systemctl restart", "systemctl enable", "systemctl disable",
                 "daemon-reload", "kill ", "rm ", "ln -s"):
        assert verb not in text, verb
    for check in ("is-active", "MainPID", "flock -n /var/lib/tradergo/worker.lock", "verify-research-release.py",
                  "TRADERGO_REVISION", "tradergo-worker.service"):
        assert check in text, check


def _hold_lock(data_dir, ready, release):
    lock = worker.acquire_single_worker_lock(Path(data_dir))
    Path(ready).write_text("held")
    while not Path(release).exists():
        time.sleep(0.05)
    lock.close()


def _try_lock(data_dir, result):
    try:
        worker.acquire_single_worker_lock(Path(data_dir))
        Path(result).write_text("acquired")
    except BlockingIOError:
        Path(result).write_text("blocked")


def test_a_second_worker_cannot_take_the_lock(tmp_path):
    ctx = mp.get_context("spawn")
    ready, release = tmp_path / "ready", tmp_path / "release"
    holder = ctx.Process(target=_hold_lock, args=(str(tmp_path), str(ready), str(release)))
    holder.start()
    while not ready.exists():
        time.sleep(0.05)
    second = ctx.Process(target=_try_lock, args=(str(tmp_path), str(tmp_path / "second")))
    second.start(); second.join(30)
    assert (tmp_path / "second").read_text() == "blocked"
    release.write_text("go"); holder.join(30)
    third = ctx.Process(target=_try_lock, args=(str(tmp_path), str(tmp_path / "third")))
    third.start(); third.join(30)
    assert (tmp_path / "third").read_text() == "acquired", "the lock is free once the first worker is gone"


def test_worker_logs_its_revision_at_start(tmp_path, monkeypatch, caplog):
    class Store:
        def rpc(self, name, params):
            return None
    monkeypatch.setattr(worker.SupabaseStore, "from_env_file", classmethod(lambda cls, path: Store()))
    from traderlab.research_engine import catalog
    monkeypatch.setattr(catalog, "sync_catalog", lambda store, repo: {"hypotheses": 0})
    monkeypatch.setenv("TRADERGO_REVISION", "a" * 40)
    monkeypatch.setattr(sys, "argv", ["worker", "--env-file", str(tmp_path / "env"), "--data-dir", str(tmp_path), "--once"])
    monkeypatch.setattr(worker.signal, "signal", lambda *a: None)
    with caplog.at_level(logging.INFO, logger="research-worker"):
        worker.main()
    assert f"revision={'a' * 40}" in caplog.text
