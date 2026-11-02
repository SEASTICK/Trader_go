from types import SimpleNamespace

import pytest

from traderlab.research_engine import worker
from traderlab.research_engine.supabase import ConnectionFailure


class Process:
    def __init__(self):
        self.alive = True
        self.stopped = False

    def start(self):
        pass

    def is_alive(self):
        return self.alive

    def terminate(self):
        self.alive = False
        self.stopped = True

    def join(self, timeout):
        pass


@pytest.mark.parametrize("state", ["cancelled", "lost", "network"])
def test_lost_or_cancelled_lease_stops_child_before_any_publish(tmp_path, monkeypatch, state):
    process = Process()
    monkeypatch.setattr(worker.mp, "get_context", lambda _: SimpleNamespace(Process=lambda **_: process))
    calls = []

    class Store:
        def rpc(self, name, params):
            calls.append(name)
            if name == "research_heartbeat":
                if state == "network":
                    raise ConnectionFailure("network")
                return state
            assert name == "research_finish"
            assert process.stopped
            assert "p_result" not in params

    job = {"id": "test-job", "lease_token": "test-token"}
    if state == "network":
        with pytest.raises(ConnectionFailure):
            worker.execute(Store(), job, tmp_path, lambda: False)
    else:
        worker.execute(Store(), job, tmp_path, lambda: False)
    assert process.stopped
    assert calls == (["research_heartbeat", "research_finish"] if state == "cancelled" else ["research_heartbeat"])


def test_timeout_stops_process_and_marks_error(tmp_path, monkeypatch):
    process = Process()
    monkeypatch.setattr(worker.mp, "get_context", lambda _: SimpleNamespace(Process=lambda **_: process))
    calls = []

    class Store:
        def rpc(self, name, params):
            assert process.stopped
            calls.append((name, params))

    worker.execute(Store(), {"id": "test-job", "lease_token": "token"}, tmp_path, lambda: False, timeout=-1)
    assert len(calls) == 1
    assert calls[0][0] == "research_finish"
    assert "p_error" in calls[0][1]
