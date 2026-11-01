import json
import subprocess

import pandas as pd
import pytest

from traderlab import fas1
from traderlab.data import binance
from traderlab.registry import NotRegisteredError
from traderlab.synthetic import make_ar_bars


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    (tmp_path / "research/registry.md").write_text("| id | datum | hypotes |\n|---|---|---|\n| H-0001 | 2026-11-01 | x |\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "reg")
    perp = make_ar_bars(7 * 365 * 6, phi=0.05, vol=0.01, seed=4, interval="4h", start="2020-01-01")
    spot = perp.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    seen = {}

    def load(market, symbol, interval, data_dir):
        seen.setdefault("loads", []).append((market, interval))
        return perp if market == "um" else spot

    def load_funding(symbol, data_dir):
        idx = pd.date_range(perp.index[0], perp.index[-1], freq="8h")
        return pd.Series(0.0001, index=idx)

    monkeypatch.setattr(binance, "load", load)
    monkeypatch.setattr(binance, "load_funding", load_funding)
    return tmp_path


def test_refuses_unregistered(repo):
    with pytest.raises(NotRegisteredError):
        fas1.run("H-0002", "donchian_breakout", repo, n_trials=2)


def test_runs_out_of_sample_only_and_never_touches_holdout(repo):
    path = fas1.run("H-0001", "donchian_breakout", repo, n_trials=3)
    r = json.loads(path.read_text())
    assert r["curves"]["t"][0] >= "2022-01-01" and r["curves"]["t"][-1] < "2025-01-01"
    assert all(t["entry_time"] < "2025-01-01" for t in r["trades"])
    assert len(r["windows"]) == 6 and r["trials_total"] == 21
    assert set(r["criteria"]) == {"t_at_least_required", "stressed_costs_positive", "sharpe_above_buy_and_hold",
                                  "stability_at_least_half"}
    assert r["final_run_id"].startswith("donchian_breakout@1.0.0#")
