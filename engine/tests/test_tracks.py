"""Spår B och C: beta mot BTC, säkrad carry och funding_carry."""
import pandas as pd
import pytest

from traderlab import backtest
from traderlab.costs import ZERO, CostModel
from traderlab.experiment import benchmark_stats
from traderlab.hedge import hedged_bars, two_leg_costs
from traderlab.strategies.funding import funding_carry
from traderlab.synthetic import from_closes, make_bars


def test_buy_and_hold_has_beta_one_and_flat_has_beta_zero():
    bars = make_bars(400, interval="1d", seed=3, vol=0.03)
    long = backtest.run(bars, pd.Series(1.0, index=bars.index), ZERO)
    flat = backtest.run(bars, pd.Series(0.0, index=bars.index), ZERO)
    short = backtest.run(bars, pd.Series(-1.0, index=bars.index), ZERO)
    assert benchmark_stats(long, bars, "x")["beta"] == pytest.approx(1.0, abs=0.02)
    assert benchmark_stats(long, bars, "x")["correlation"] == pytest.approx(1.0, abs=0.01)
    assert benchmark_stats(flat, bars, "x")["beta"] == pytest.approx(0.0, abs=1e-12)
    assert benchmark_stats(short, bars, "x")["beta"] < -0.9


def test_hedged_series_cancels_the_price_move():
    spot = make_bars(300, interval="4h", seed=1, vol=0.02)
    perp = spot.copy()  # termin = spot: säkringen ska vara helt platt
    x = hedged_bars(perp, spot)
    assert (x["open"] - 100).abs().max() < 1e-9
    res = backtest.run(x, pd.Series(-1.0, index=x.index), ZERO)
    assert res.equity.iloc[-1] == pytest.approx(1.0)


def test_hedged_short_receives_positive_funding_and_pays_two_legs():
    spot = make_bars(60, interval="4h", seed=2, vol=0.03)
    x = hedged_bars(spot.copy(), spot)
    funding = pd.Series(0.001, index=x.index + pd.Timedelta(hours=4))  # en avräkning per stapel
    res = backtest.run(x, pd.Series(-1.0, index=x.index), ZERO, funding=funding)
    assert res.total_funding < 0                      # negativt betyder mottaget
    assert res.equity.iloc[-1] > 1.04
    c = two_leg_costs(CostModel(10, 2, 5))
    assert c.per_side == pytest.approx(2 * CostModel(10, 2, 5).per_side)


def test_hedged_series_follows_the_basis():
    spot = from_closes([100, 100, 100, 100], interval="1d")
    perp = from_closes([100, 101, 101, 101], interval="1d")  # terminen stiger 1 % mer än spot
    x = hedged_bars(perp, spot)
    assert x["open"].iloc[2] == pytest.approx(101.0)


def test_funding_carry_is_short_only_above_threshold():
    bars = make_bars(5, interval="4h", start="2024-01-01")
    f = pd.Series([0.0002, 0.00005, -0.0003, 0.0001, 0.0], index=bars.index + pd.Timedelta(hours=4))
    assert list(funding_carry(bars, f, threshold=0.0001)) == [-1.0, 0.0, 0.0, -1.0, 0.0]


def test_funding_carry_has_no_lookahead():
    bars = make_bars(600, interval="4h", seed=4)
    idx = pd.date_range(bars.index[0], bars.index[-1] + pd.Timedelta(hours=4), freq="8h", tz="UTC")
    f = pd.Series(((pd.Series(range(len(idx))) % 5) - 1).to_numpy() * 0.0001, index=idx)
    backtest.check_no_lookahead(lambda b: funding_carry(b, f), bars)


def test_batch_runs_a_hedged_track_c_tile_and_exports_beta(tmp_path):
    import json
    import subprocess

    from traderlab import batch

    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)

    git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (tmp_path / "research").mkdir(); (tmp_path / "app/data").mkdir(parents=True)
    (tmp_path / "research/registry.md").write_text("| id | datum | hypotes |\n|---|---|---|\n| H-0001 | 2026-11-01 | carry |\n")
    plan = {"E-30": {"hypothesis": "H-0001", "track": "C", "market": "um", "symbol": "BTCUSDT", "interval": "4h",
                     "funding": True, "hedged": {"spot_symbol": "BTCUSDT"},
                     "strategy": {"name": "funding_carry", "params": {"threshold": 0.0001}}}}
    (tmp_path / "research/experiments.json").write_text(json.dumps(plan))
    git("add", "-A"); git("commit", "-qm", "reg")

    spot = make_bars(1200, interval="4h", seed=5, vol=0.02)
    perp = spot.copy()
    perp[["open", "high", "low", "close"]] *= 1.0005  # konstant bas: säkringen är platt

    def loader(market, symbol, interval, data_dir):
        return perp if market == "um" else spot

    def funding_loader(symbol, data_dir):
        idx = pd.date_range(spot.index[0], spot.index[-1], freq="8h", tz="UTC")
        return pd.Series(0.0002, index=idx)

    rep = batch.run_all(tmp_path, loader=loader, funding_loader=funding_loader)
    assert rep.ran == ["E-30"], rep.skipped
    e = batch.export_to_app(tmp_path)["E-30"]
    assert e["track"] == "C"
    assert abs(e["beta"]) < 0.01
    assert e["total_return"] > 0
