"""Mål för riktiga spawn-processer i test_research_worker_spawn.py. Körs i barnprocessen, så stubbar sätts här.

Inget nätverk, ingen servernyckel och ingen riktig data: datalagret och utvärderingen ersätts med syntetiska
stubbar som fyller i delresultat och sedan väntar tills föräldern stoppar processen.
"""
from __future__ import annotations

import signal
import time
from pathlib import Path

import pandas as pd

from traderlab import fas2_eval
from traderlab.research_engine import h0013, registered, runner, worker
from traderlab.synthetic import make_bars


def _ready(data_dir) -> None:
    Path(data_dir, "ready").write_text("ready")


def _wait_forever():
    for _ in range(1200):
        time.sleep(0.05)
    raise AssertionError("processen stoppades aldrig")


def h0013_child(job, data_dir, output):
    bars = make_bars(60, interval="4h", seed=1)
    funding = pd.Series(0.0001, index=pd.date_range(bars.index[0], bars.index[-1], freq="8h"))

    def evaluate(b, f, attempts_now=None, progress=None, **kw):
        progress["config"] = {"n_permutations": fas2_eval.N_PERMUTATIONS, "playbooks": fas2_eval.N_PLAYBOOKS}
        progress["steps"] = {s: "pending" for s in fas2_eval.STEPS}
        progress["walk_forward"] = {"windows": [{"playbook_id": "spelbok#test"}]}
        progress["steps"]["walk_forward"] = "done"
        progress["h0013"] = {"sharpe": 0.25, "trades": 3}
        progress["steps"]["h0013"] = "done"
        progress["steps"]["stressed"] = "incomplete"
        _ready(data_dir)
        _wait_forever()

    h0013.load_frozen = lambda d, m=None: (bars, funding)
    fas2_eval.evaluate = evaluate
    worker.child(job, data_dir, output)


def runner_child(job, data_dir, output):
    """Fas 1-reproduktion eller utforskning som räknar tills den stoppas."""
    def run_job(j, d, o):
        _ready(data_dir)
        _wait_forever()
    registered.run_job = run_job
    runner.run_job = run_job
    worker.child(job, data_dir, output)


def deaf_child(job, data_dir, output):
    """En process som inte svarar på SIGTERM: föräldern måste döda den."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    _ready(data_dir)
    _wait_forever()
