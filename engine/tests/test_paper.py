import json
import subprocess

import pytest

from traderlab import backtest
from traderlab.costs import CostModel
from traderlab.paper import engine as paper
from traderlab.registry import NotRegisteredError, latest_decisions
from traderlab.strategies import examples
from traderlab.synthetic import make_bars

HEADER = "| id | datum | hypotes | beslut |\n|---|---|---|---|\n"
SPEC = {"market": "spot", "symbol": "BTCUSDT", "interval": "4h",
        "strategy": {"name": "ma_cross", "params": {"fast": 10, "slow": 30}},
        "costs": {"fee_bps": 10, "spread_bps": 2, "slippage_bps": 5}}


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def make_repo(tmp_path, rows):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    (tmp_path / "research/registry.md").write_text(HEADER + rows)
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "reg")
    return tmp_path


def test_latest_decision_per_id():
    text = HEADER + "| H-0001 | a | x | MORE_RESEARCH |\n| H-0001 | b | x | READY_FOR_PAPER |\n| H-0002 | c | y | REJECT |\n"
    assert latest_decisions(text) == {"H-0001": "READY_FOR_PAPER", "H-0002": "REJECT"}


def test_freeze_requires_ready_for_paper(tmp_path):
    repo = make_repo(tmp_path, "| H-0001 | a | x | MORE_RESEARCH |\n| H-0002 | a | x |  |\n")
    for hid in ("H-0001", "H-0002", "H-0009"):
        with pytest.raises(NotRegisteredError):
            paper.freeze(repo, "P-0001", hid, SPEC, planned_trades=60, stop_rule="förlust över 20 %")


@pytest.fixture
def ready(tmp_path):
    repo = make_repo(tmp_path, "| H-0001 | a | x | READY_FOR_PAPER |\n")
    paper.freeze(repo, "P-0001", "H-0001", SPEC, planned_trades=60, stop_rule="förlust över 20 %")
    return repo


def test_paper_equals_backtest_exactly(ready):
    bars = make_bars(400, seed=1, vol=0.015)
    paper.step(ready, "P-0001", bars)
    bt = backtest.run(bars, examples.ma_cross(bars, 10, 30), CostModel(**SPEC["costs"]))
    logged = [e for e in paper._events(ready, "P-0001") if e["type"] == "bar"]
    assert len(logged) == len(bars) - 1 == len(bt.equity)  # sista stapeln väntar på nästa öppning
    for e in logged:
        assert e["equity"] == pytest.approx(bt.equity.loc[e["time"]], rel=1e-12)


def test_incremental_steps_equal_one_big_step_and_log_only_grows(ready, tmp_path_factory):
    bars = make_bars(300, seed=2, vol=0.015)
    for n in range(200, 301, 25):
        before = (paper.folder(ready, "P-0001") / "log.jsonl").read_text()
        paper.step(ready, "P-0001", bars.iloc[:n])
        after = (paper.folder(ready, "P-0001") / "log.jsonl").read_text()
        assert after.startswith(before)  # append-only
    inc = [e for e in paper._events(ready, "P-0001") if e["type"] == "bar"]

    other = make_repo(tmp_path_factory.mktemp("b"), "| H-0001 | a | x | READY_FOR_PAPER |\n")
    paper.freeze(other, "P-0001", "H-0001", SPEC, planned_trades=60, stop_rule="x")
    paper.step(other, "P-0001", bars)
    big = [e for e in paper._events(other, "P-0001") if e["type"] == "bar"]
    assert [(e["time"], round(e["equity"], 12)) for e in inc] == [(e["time"], round(e["equity"], 12)) for e in big]


def test_step_is_idempotent(ready):
    bars = make_bars(250, seed=3)
    first = paper.step(ready, "P-0001", bars)
    assert first > 0 and paper.step(ready, "P-0001", bars) == 0


def test_changed_strategy_is_refused(ready):
    p = paper.folder(ready, "P-0001") / "strategy.json"
    frozen = json.loads(p.read_text())
    frozen["spec"]["strategy"]["params"]["fast"] = 12
    p.write_text(json.dumps(frozen))
    with pytest.raises(paper.TamperedError):
        paper.step(ready, "P-0001", make_bars(100, seed=4))


def test_cannot_refreeze_same_id(ready):
    with pytest.raises(FileExistsError):
        paper.freeze(ready, "P-0001", "H-0001", SPEC, planned_trades=60, stop_rule="x")


def test_status(ready):
    paper.step(ready, "P-0001", make_bars(300, seed=5, vol=0.015))
    st = paper.status(ready, "P-0001")
    assert st["bars"] == 299 and st["trades"] > 0 and st["planned_trades"] == 60


def test_closed_only_drops_the_running_bar():
    import pandas as pd
    bars = make_bars(10, interval="4h", start="2024-01-01")
    now = bars.index[-1] + pd.Timedelta(hours=2)  # sista stapeln pågår
    assert len(paper.closed_only(bars, "4h", now)) == 9
    assert len(paper.closed_only(bars, "4h", bars.index[-1] + pd.Timedelta(hours=4))) == 10
