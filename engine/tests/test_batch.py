import json
import subprocess

import pytest

from traderlab import batch
from traderlab.synthetic import make_ar_bars

REGISTRY = """| id | datum | hypotes |
|---|---|---|
| H-0001 | 2026-11-01 | ML på BTC 4h |
| H-0002 | 2026-11-01 | Trend på ETH 4h |
"""

PLAN = {
    "E-01": {"hypothesis": "H-0001", "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
             "strategy": {"name": "ml", "params": {"min_train": 600, "step": 200}}},
    "E-02": {"hypothesis": "H-0009", "market": "spot", "symbol": "BTCUSDT", "interval": "4h",
             "strategy": {"name": "ma_cross"}},
    "E-03": {"hypothesis": "H-0002", "market": "spot", "symbol": "ETHUSDT", "interval": "4h",
             "strategy": {"name": "ma_cross"}},
    "E-04": {"hypothesis": "H-0002", "market": "spot", "symbol": "GAPUSDT", "interval": "4h",
             "strategy": {"name": "ma_cross"}},
}


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    (tmp_path / "app/data").mkdir(parents=True)
    (tmp_path / "research/registry.md").write_text(REGISTRY)
    (tmp_path / "research/experiments.json").write_text(json.dumps(PLAN))
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "reg")
    return tmp_path


def loader(market, symbol, interval, data_dir):
    if symbol == "BTCUSDT":
        return make_ar_bars(1500, seed=1)
    if symbol == "GAPUSDT":
        b = make_ar_bars(800, seed=2)
        return b.drop(index=b.index[100:120])  # 2,5 % saknas: fel
    raise FileNotFoundError(symbol)


def test_batch_runs_only_registered_tiles_with_clean_data(repo):
    rep = batch.run_all(repo, loader=loader)
    assert rep.ran == ["E-01"]
    assert "inte registrerad" in rep.skipped["E-02"]
    assert "ingen data" in rep.skipped["E-03"]
    assert "datakvalitet" in rep.skipped["E-04"] and "1 %" in rep.skipped["E-04"]


def test_period_slicing_keeps_a_clean_holdout(repo):
    import json as _json
    plan = _json.loads((repo / "research/experiments.json").read_text())
    plan["E-01"]["period"] = {"end": "2020-06-01"}
    (repo / "research/experiments.json").write_text(_json.dumps(plan))
    git(repo, "add", "-A"); git(repo, "commit", "-qm", "period")
    batch.run_all(repo, loader=loader, only=["E-01"])
    out = batch.export_to_app(repo)
    assert out["E-01"]["period"][1] < "2020-06-01"


def test_export_writes_real_results_for_the_app(repo):
    batch.run_all(repo, loader=loader, only=["E-01"])
    out = batch.export_to_app(repo)
    assert list(out) == ["E-01"]
    e = out["E-01"]
    assert e["source"] == "HISTORIK" and e["hypothesis"] == "H-0001"
    assert len(e["curve"]["t"]) == len(e["curve"]["strategy"]) == len(e["curve"]["buy_and_hold"]) <= 301
    assert e["curve"]["strategy"][0] == pytest.approx(100, abs=1)
    assert 0 <= e["deflated_sharpe"] <= 1
    assert e["result_file"].startswith("research/results/H-0001-")
    on_disk = json.loads((repo / "app/data/results.json").read_text())
    assert on_disk["E-01"]["trades"] == e["trades"]
