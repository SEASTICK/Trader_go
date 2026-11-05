import json
import subprocess

import numpy as np
import pandas as pd
import pytest

from traderlab import xsrun
from traderlab.data import binance
from traderlab.registry import NotRegisteredError


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    (tmp_path / "research/registry.md").write_text("| id | datum | hypotes |\n|---|---|---|\n| H-0001 | 2026-11-02 | x |\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "reg")
    rng = np.random.default_rng(1)
    idx = pd.date_range("2020-01-01", "2026-06-30", freq="1D", tz="UTC")
    syms = [f"S{i}USDT" for i in range(14)]
    data = {}
    for i, s in enumerate(syms):
        c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, len(idx))))
        o = np.r_[c[0], c[:-1]]
        data[s] = pd.DataFrame({"open": o, "high": np.maximum(o, c) * 1.01, "low": np.minimum(o, c) * 0.99, "close": c,
                                "volume": 1.0}, index=idx)
    data["BTCUSDT"] = data["S0USDT"]
    monkeypatch.setattr(xsrun, "universe", lambda d: syms)
    monkeypatch.setattr(binance, "load", lambda m, s, i, d, **kw: data[s])
    monkeypatch.setattr(binance, "load_funding", lambda s, d, **kw: pd.Series(1e-4, index=pd.date_range("2020-01-01", "2026-06-30", freq="8h", tz="UTC")))
    return tmp_path


def test_refuses_unregistered(repo):
    with pytest.raises(NotRegisteredError):
        xsrun.run("H-0002", "momentum", repo)


@pytest.mark.parametrize("kind", ["momentum", "carry"])
def test_runs_without_holdout_and_writes_result(repo, kind):
    r = json.loads(xsrun.run("H-0001", kind, repo).read_text())
    assert r["period"][1] < "2025-01-01" and r["curve"]["t"][-1] < "2025-01-01"
    assert r["rebalances"] > 200 and set(r["criteria"]) == {"t_at_least_required", "stressed_costs_positive", "beta_within_0_2"}
    assert abs(r["random_label_t"]) < 3
    assert len(r["universe"]) == 14
