import json
import subprocess

import pandas as pd
import pytest

from traderlab import backtest, batch
from traderlab.strategies.funding import funding_contrarian, last_known_funding
from traderlab.synthetic import make_bars


def test_only_settled_funding_is_used():
    bars = make_bars(12, interval="4h", start="2024-01-01")
    # Avräkning 08:00 blir känd vid stängningen av stapeln som öppnar 04:00 (stänger 08:00), inte tidigare.
    f = pd.Series([0.001], index=[pd.Timestamp("2024-01-01 08:00", tz="UTC")])
    k = last_known_funding(bars, f)
    assert pd.isna(k.iloc[0])                   # 00:00–04:00: inget känt än
    assert k.iloc[1] == 0.001                    # 04:00–08:00 stänger 08:00: känd
    assert (k.iloc[2:] == 0.001).all()


def test_contrarian_signs_and_threshold():
    bars = make_bars(6, interval="4h", start="2024-01-01")
    times = bars.index + pd.Timedelta(hours=4)  # en avräkning vid varje stapels stängning
    f = pd.Series([0.0001, 0.0006, -0.0007, 0.0004, 0.0, 0.0005], index=times)
    pos = funding_contrarian(bars, f, threshold=0.0005)
    assert list(pos) == [0.0, -1.0, 1.0, 0.0, 0.0, -1.0]


def test_funding_strategy_has_no_lookahead():
    bars = make_bars(800, interval="4h", seed=1)
    idx = pd.date_range(bars.index[0], bars.index[-1] + pd.Timedelta(hours=4), freq="8h", tz="UTC")
    f = pd.Series(((pd.Series(range(len(idx))) % 7) - 3).to_numpy() * 0.0003, index=idx)
    backtest.check_no_lookahead(lambda b: funding_contrarian(b, f), bars)


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


def test_batch_passes_funding_to_strategy_and_backtest(tmp_path):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir(); (tmp_path / "app/data").mkdir(parents=True)
    (tmp_path / "research/registry.md").write_text("| id | x |\n|---|---|\n| H-0001 | f |\n")
    (tmp_path / "research/experiments.json").write_text(json.dumps({"E-07": {
        "hypothesis": "H-0001", "market": "um", "symbol": "BTCUSDT", "interval": "4h", "funding": True,
        "strategy": {"name": "funding_contrarian", "params": {"threshold": 0.0005}}}}))
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "x")
    bars = make_bars(600, interval="4h", seed=2)
    idx = pd.date_range(bars.index[0], periods=400, freq="8h", tz="UTC")
    f = pd.Series(0.001, index=idx)  # alltid hög: strategin är short hela tiden och tar emot ränta
    rep = batch.run_all(tmp_path, loader=lambda *a: bars, funding_loader=lambda *a: f)
    assert rep.ran == ["E-07"], rep.skipped
    out = json.loads(next((tmp_path / "research/results").glob("H-0001-*.json")).read_text())
    assert out["summary"]["funding"] < 0       # negativ = mottagen ränta (short tar emot)
