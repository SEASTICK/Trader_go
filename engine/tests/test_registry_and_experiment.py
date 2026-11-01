import json
import subprocess

import pytest

from traderlab import registry
from traderlab.costs import CostModel
from traderlab.experiment import run_experiment
from traderlab.strategies import examples
from traderlab.synthetic import make_bars

TABLE = """# Register

| id | datum | hypotes |
|---|---|---|
| H-0001 | 2026-11-01 | Trend i BTC 4h |
| H-0001 | 2026-11-02 | resultat: REJECT |
| H-0002 | 2026-11-03 | Mean-reversion ETH 1h |
"""


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    return tmp_path


def test_count_attempts_uses_distinct_ids():
    assert registry.ids_in(TABLE) == ["H-0001", "H-0001", "H-0002"]
    assert registry.count_attempts(TABLE) == 2


def test_requires_registry_file(repo):
    with pytest.raises(registry.NotRegisteredError, match="finns inte"):
        registry.require_registered("H-0001", repo)


def test_uncommitted_registration_is_refused(repo):
    (repo / "research/registry.md").write_text(TABLE)
    with pytest.raises(registry.NotRegisteredError, match="inte committad"):
        registry.require_registered("H-0001", repo)


def test_committed_registration_passes_and_dirty_is_refused(repo):
    (repo / "research/registry.md").write_text(TABLE)
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "reg")
    reg = registry.require_registered("H-0002", repo)
    assert reg.attempts == 2 and len(reg.registry_commit) == 40
    with pytest.raises(registry.NotRegisteredError, match="finns inte i den committade"):
        registry.require_registered("H-0009", repo)
    (repo / "research/registry.md").write_text(TABLE + "| H-0003 | x | y |\n")
    with pytest.raises(registry.NotRegisteredError, match="ocommittade"):
        registry.require_registered("H-0002", repo)


def test_run_experiment_refuses_unregistered_and_lookahead(repo):
    (repo / "research/registry.md").write_text(TABLE)
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "reg")
    bars = make_bars(400, seed=1)
    with pytest.raises(registry.NotRegisteredError):
        run_experiment("H-0007", repo, bars, examples.ma_cross, CostModel(), market="syn", interval="4h")
    from traderlab.backtest import LookaheadError
    with pytest.raises(LookaheadError):
        run_experiment("H-0001", repo, bars, examples.peeking, CostModel(), market="syn", interval="4h")


def test_run_experiment_writes_result_with_stress_and_control(repo):
    (repo / "research/registry.md").write_text(TABLE)
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "reg")
    bars = make_bars(1500, seed=2, vol=0.01)
    path = run_experiment("H-0001", repo, bars, examples.ma_cross, CostModel(), market="syntetisk", interval="4h",
                          note="test på påhittad data")
    out = json.loads(path.read_text())
    assert out["hypothesis_id"] == "H-0001" and out["summary"]["attempts"] == 2
    assert out["summary_stressed_costs"]["costs"] > out["summary"]["costs"]
    assert out["summary"]["t_required"] == 2.0  # 2 försök: max(2,0; 1,96)
    assert "random_label_t" in out and out["simulated"] is False
    bh = out["baseline_buy_and_hold"]
    assert set(bh) == {"total_return", "max_drawdown", "sharpe", "t_daily_nw"}


def test_short_history_gives_valid_json_without_nan(repo):
    (repo / "research/registry.md").write_text(TABLE)
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "reg")
    bars = make_bars(120, seed=3)  # cirka 20 dagar: för lite för bootstrap
    path = run_experiment("H-0002", repo, bars, examples.ma_cross, CostModel(), market="syn", interval="4h")
    text = path.read_text()
    assert "NaN" not in text
    assert json.loads(text)["summary"]["sharpe_ci"] == [None, None]
