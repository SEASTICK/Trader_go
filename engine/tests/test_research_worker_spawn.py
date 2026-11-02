"""Workerns stopp med riktiga spawn-processer och riktiga signaler (granskning av PR #73, P1). Inget nätverk."""
import json
import time

import pytest

from traderlab.research_engine import h0013, worker

import _spawn_targets as targets  # ligger bredvid testerna; barnprocessen importerar samma modul

H0013_JOB = {"id": "run-h", "lease_token": "tok", "attempts": 1, **h0013.EXPECTED,
             "period_start": "2020-01-01T00:00:00+00:00", "period_end": "2025-01-01T00:00:00+00:00"}
FAS1_JOB = {"id": "run-f", "lease_token": "tok", "kind": "registered", "hypothesis_id": "H-0009"}
EXPLORATION_JOB = {"id": "run-e", "lease_token": "tok", "kind": "exploration"}


class Store:
    """Kön sedd från workern. `when_ready` styr vad heartbeat svarar när barnet är igång."""
    def __init__(self, data_dir, when_ready="running"):
        self.data_dir, self.when_ready, self.calls, self.at_finish = data_dir, when_ready, [], None

    def ready(self):
        return (self.data_dir / "ready").exists()

    def rpc(self, name, params):
        self.calls.append((name, params))
        if name == "research_heartbeat":
            return self.when_ready if self.ready() else "running"
        if name == "research_finish":
            # Det här är ögonblicket då slotten släpps: barnet måste redan ha avslutat och sparat.
            self.at_finish = {
                "aborted_files": sorted(p.name for p in (self.data_dir / "h0013-attempts").glob("*-aborted.json")),
                "stopped_markers": sorted(str(p) for p in self.data_dir.glob("research-*/result.stopped")),
                "error": params.get("p_error"), "result": "p_result" in params}
            return True

    def finishes(self):
        return [p for n, p in self.calls if n == "research_finish"]


def wait_ready_then_stop(store, timeout=60):
    start = time.monotonic()
    def stopping():
        if time.monotonic() - start > timeout:
            raise AssertionError("barnet blev aldrig redo")
        return store.ready()
    return stopping


def saved_attempt(data_dir):
    files = sorted((data_dir / "h0013-attempts").glob("H-0013-*-aborted.json"))
    assert len(files) == 1, files
    return json.loads(files[0].read_text())


def assert_partial_saved(body):
    assert body["status"] == "aborted" and "decision" not in body
    assert body["steps"]["walk_forward"] == "done" and body["steps"]["h0013"] == "done"
    assert body["steps"]["stressed"] == "incomplete"
    assert body["h0013"] == {"sharpe": 0.25, "trades": 3} and "WorkerStop" in body["error"]


def test_normal_worker_stop_lets_h0013_save_partial_results(tmp_path):
    store = Store(tmp_path)
    worker.execute(store, H0013_JOB, tmp_path, wait_ready_then_stop(store), timeout=7200, beat=0.2,
                   target=targets.h0013_child)
    assert_partial_saved(saved_attempt(tmp_path))
    assert store.at_finish["aborted_files"], "the attempt was saved before the slot was released"
    assert store.at_finish["stopped_markers"] and "dödades" not in store.at_finish["error"]
    assert not store.at_finish["result"]


def test_user_cancel_lets_h0013_save_partial_results(tmp_path):
    store = Store(tmp_path, when_ready="cancelled")
    worker.execute(store, H0013_JOB, tmp_path, lambda: False, timeout=7200, beat=0.2, target=targets.h0013_child)
    assert_partial_saved(saved_attempt(tmp_path))
    assert store.at_finish["aborted_files"] and store.at_finish["error"] == "Avbruten"
    assert not store.at_finish["result"]


def test_lost_lease_stops_and_saves_but_never_publishes(tmp_path):
    store = Store(tmp_path, when_ready="lost")
    worker.execute(store, H0013_JOB, tmp_path, lambda: False, timeout=7200, beat=0.2, target=targets.h0013_child)
    assert_partial_saved(saved_attempt(tmp_path))
    assert store.finishes() == [], "a lost lease publishes nothing, not even an error"


def test_timeout_lets_h0013_save_partial_results(tmp_path):
    store = Store(tmp_path)
    started = time.monotonic()
    # Tidsgränsen räcker för att barnet ska starta och bli redo, men inte för att bli klart.
    worker.execute(store, H0013_JOB, tmp_path, lambda: False, timeout=12, beat=0.2, target=targets.h0013_child)
    assert time.monotonic() - started >= 12
    assert store.ready(), "the child was running when the deadline came"
    assert_partial_saved(saved_attempt(tmp_path))
    assert "tidsgräns" in store.at_finish["error"] and store.at_finish["aborted_files"]


@pytest.mark.parametrize("job", [FAS1_JOB, EXPLORATION_JOB], ids=["fas1", "exploration"])
def test_fas1_and_exploration_stop_cleanly_before_the_slot_is_released(tmp_path, job):
    store = Store(tmp_path, when_ready="cancelled")
    worker.execute(store, job, tmp_path, lambda: False, timeout=7200, beat=0.2, target=targets.runner_child)
    assert store.at_finish["stopped_markers"], "the child had stopped when finish was called"
    assert store.at_finish["error"] == "Avbruten" and not store.at_finish["result"]


def test_unresponsive_child_is_killed_and_not_claimed_as_saved(tmp_path):
    store = Store(tmp_path)
    started = time.monotonic()
    worker.execute(store, H0013_JOB, tmp_path, wait_ready_then_stop(store), timeout=7200, beat=0.2, grace=1,
                   target=targets.deaf_child)
    assert time.monotonic() - started < 60
    assert "dödades, delresultat kan saknas" in store.at_finish["error"]
    assert not (tmp_path / "h0013-attempts").exists()


def test_stop_returns_only_when_the_process_is_gone():
    import multiprocessing as mp
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        p = mp.get_context("spawn").Process(target=targets.deaf_child, args=({}, d, str(Path(d) / "o.json")))
        p.start()
        while not Path(d, "ready").exists():
            time.sleep(0.05)
        assert worker.stop(p, grace=0.5) is True
        assert not p.is_alive() and p.exitcode == -9
