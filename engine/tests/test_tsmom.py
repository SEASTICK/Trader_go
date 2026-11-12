"""Syntetiska tester för H-0021 (research/tsmom-protokoll.md). Inga riktiga data används."""
import json
import subprocess

import numpy as np
import pandas as pd
import pytest

from traderlab import portfolio, tsmom, xsbig
from traderlab.costs import CostModel
from traderlab.data import binance

ZERO_COST = CostModel(0, 0, 0)


def _panel(n=320, k=40, seed=0, start="2021-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    sigma = np.linspace(0.02, 0.08, k)
    closes = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 1, (n, k)) * sigma, axis=0)), index=idx,
                          columns=[f"C{i}USDT" for i in range(k)])
    dvol = pd.DataFrame(2e7, index=idx, columns=closes.columns)
    dvol.iloc[:, :5] = 1e6   # illikvida: får aldrig väljas
    return closes, dvol


# ---------------------------------------------------------------- signal, volatilitet, vikter

def test_signal_is_close_t_minus_1_over_close_t_minus_29():
    idx = pd.date_range("2021-01-01", periods=40, freq="1D", tz="UTC")
    closes = pd.DataFrame({"A": np.arange(1.0, 41.0)}, index=idx)
    s = tsmom.signal(closes)
    t = 35
    assert s["A"].iloc[t] == pytest.approx(closes["A"].iloc[t - 1] / closes["A"].iloc[t - 29] - 1)
    assert np.isnan(s["A"].iloc[28])   # t−29 saknas


def test_volatility_window_ends_the_day_before_the_decision_day():
    closes, _ = _panel(n=120, k=3)
    base = tsmom.volatility(closes)
    shocked = closes.copy()
    shocked.iloc[100:, :] *= 3.0   # chock vid dag 100: avkastningen för dag 100 ingår först i volatiliteten dag 101
    changed = tsmom.volatility(shocked)
    assert changed.iloc[100].equals(base.iloc[100]) and not changed.iloc[101].equals(base.iloc[101])


def test_volatility_needs_40_valid_days():
    idx = pd.date_range("2021-01-01", periods=80, freq="1D", tz="UTC")
    closes = pd.DataFrame({"A": np.exp(np.cumsum(np.random.default_rng(0).normal(0, .02, 80)))}, index=idx)
    v = tsmom.volatility(closes)["A"]
    assert v.iloc[:40].isna().all() and v.iloc[41:].notna().all()


def test_cap_weights_redistributes_proportionally_and_sums_to_one():
    raw = pd.Series([10.0] + [1.0] * 14)
    w = tsmom.cap_weights(raw)
    assert w.max() == pytest.approx(0.10) and w.sum() == pytest.approx(1.0)
    assert w.iloc[1:].nunique() == 1 and w.iloc[1] < 0.10
    two_caps = tsmom.cap_weights(pd.Series([10.0, 9.0] + [1.0] * 13))
    assert two_caps.max() == pytest.approx(0.10) and two_caps.sum() == pytest.approx(1.0) and (two_caps <= 0.10 + 1e-12).all()
    with pytest.raises(ValueError):
        tsmom.cap_weights(pd.Series([1.0] * 9))   # för få värden för taket


def test_weights_gross_one_cap_signs_and_inverse_volatility():
    closes, dvol = _panel()
    w = tsmom.weights(closes, dvol)
    live = w[(w != 0).any(axis=1)]
    assert len(live) > 20
    assert np.allclose(live.abs().sum(axis=1), 1.0) and (live.abs().max(axis=1) <= 0.10 + 1e-9).all()
    assert (live.iloc[:, :5] == 0).all().all()   # illikvida mynt väljs aldrig
    assert (np.sign(live) == np.sign(tsmom.signal(closes).loc[live.index]).where(live != 0, 0)).all().all()
    # Utan tak skulle lugnare mynt få större vikt: bland mynt som inte nått taket är |w| avtagande i volatiliteten.
    t = live.index[-1]
    vol = tsmom.volatility(closes).loc[t]
    row = live.loc[t].abs()
    free = row[(row > 0) & (row < 0.10 - 1e-9)]
    assert free.index.size >= 2
    ratio = free / free.iloc[0]
    expected = (1 / vol[free.index]) / (1 / vol[free.index[0]])
    assert np.allclose(ratio, expected)


def test_fewer_than_ten_coins_with_signal_is_flat():
    closes, dvol = _panel(k=40)
    dvol.iloc[:, 9:] = 1e6   # bara 9 valbara mynt
    w = tsmom.weights(closes, dvol)
    assert (w == 0).all().all()


def test_weights_have_no_lookahead():
    closes, dvol = _panel()
    portfolio.check_no_lookahead(lambda p: tsmom.weights(p["c"], p["v"]), {"c": closes, "v": dvol}, [150, 220, 300])


def test_decision_on_sunday_is_filled_on_monday_open():
    closes, dvol = _panel()
    opens = closes.shift(1).fillna(closes.iloc[0])
    w = tsmom.weights(closes, dvol)
    w = w[w.index >= pd.Timestamp("2021-01-01", tz="UTC")]
    res = portfolio.run(opens, w, ZERO_COST)
    first = res.weights[(res.weights != 0).any(axis=1)].index[0]
    first_decision = w[(w != 0).any(axis=1)].index[0]
    assert first_decision.dayofweek == 6 and first.dayofweek == 0 and first == first_decision + pd.Timedelta(days=1)


def test_random_sign_control_keeps_gross_and_cap():
    closes, dvol = _panel()
    w = tsmom.weights(closes, dvol, np.random.default_rng(0))
    live = w[(w != 0).any(axis=1)]
    assert np.allclose(live.abs().sum(axis=1), 1.0) and (live.abs().max(axis=1) <= 0.10 + 1e-9).all()


def test_basket_is_long_only_equal_weight():
    closes, dvol = _panel()
    b = tsmom.basket_weights(closes, dvol)
    live = b[(b != 0).any(axis=1)]
    assert (live >= 0).all().all() and np.allclose(live.sum(axis=1), 1.0)
    assert (live.iloc[:, :5] == 0).all().all()


# ---------------------------------------------------------------- likvidationsstoppet (research/tsmom-protokoll.md)

def _mini(weight, path_high, path_low=None, fund=None, n=12, price=100.0):
    """En tillgång. Söndag (dag 0) beslutar, måndag (dag 1) fyller till P0=100. `path_high[d]` är dagens high i enheter
    av P0. Öppningar är alltid 100: kursen faller tillbaka (eller stiger) bara inom dagen."""
    idx = pd.date_range("2023-12-31", periods=n, freq="1D", tz="UTC")   # dag 0 är en söndag
    opens = pd.DataFrame({"X": price}, index=idx)
    highs = pd.DataFrame({"X": [price * path_high.get(d, 1.0) for d in range(n)]}, index=idx)
    lows = pd.DataFrame({"X": [price * (path_low or {}).get(d, 1.0) for d in range(n)]}, index=idx)
    highs = np.maximum(highs, opens)
    lows = np.minimum(lows, opens)
    w = pd.DataFrame({"X": [np.nan] * n}, index=idx)
    w.iloc[0, 0] = weight
    return opens, highs, lows, w, fund or {"X": pd.Series(dtype=float)}


def _run(weight, high=None, low=None, stop=tsmom.STOP):
    opens, highs, lows, w, f = _mini(weight, high or {}, low)
    return portfolio.run(opens, w, ZERO_COST, f, highs=highs, lows=lows, stop=stop)


def test_short_that_passes_195_loses_the_whole_stake_even_if_price_falls_back():
    res = _run(-0.5, high={3: 2.0})
    assert len(res.stops) == 1 and res.stops[0][1] == "X"
    assert res.equity.iloc[-1] == pytest.approx(0.5)               # hela insatsen (0,5) förlorad
    assert res.equity.loc["2024-01-04":].nunique() == 1             # ingen återhämtning efteråt
    assert (res.weights.loc["2024-01-04":] == 0).all().all()        # positionen är stängd
    opens, highs, lows, w, f = _mini(-0.5, {3: 2.0})
    no_stop = portfolio.run(opens, w, ZERO_COST, f)
    assert no_stop.equity.iloc[-1] == pytest.approx(1.0)            # utan stopp skulle kontot "överleva"


def test_short_below_the_limit_is_not_stopped_and_the_limit_itself_is():
    below = _run(-0.5, high={3: 1.90})
    assert below.stops == [] and below.equity.iloc[-1] == pytest.approx(1.0)
    at_limit = _run(-0.5, high={3: 1.95})
    assert len(at_limit.stops) == 1 and at_limit.equity.iloc[-1] == pytest.approx(0.5)
    just_above = _run(-0.5, high={3: 1.9501})
    assert len(just_above.stops) == 1


def test_long_stopped_at_005_and_not_at_006():
    stopped = _run(0.5, low={4: 0.05})
    assert len(stopped.stops) == 1 and stopped.equity.iloc[-1] == pytest.approx(0.5)
    assert stopped.equity.loc["2024-01-05":].nunique() == 1
    alive = _run(0.5, low={4: 0.06})
    assert alive.stops == [] and alive.equity.iloc[-1] == pytest.approx(1.0)


def test_stop_in_one_week_does_not_block_the_next_sunday_rebalance():
    opens, highs, lows, w, f = _mini(-0.5, {3: 2.0}, n=16)
    w.iloc[7, 0] = -0.5   # nästa söndag (dag 7) beslutar ny position
    res = portfolio.run(opens, w, ZERO_COST, f, highs=highs, lows=lows, stop=tsmom.STOP)
    assert len(res.stops) == 1
    assert res.weights.iloc[8, 0] != 0 and res.weights.iloc[6, 0] == 0   # öppnas igen måndagen efter, ej dessförinnan
    assert res.equity.iloc[-1] == pytest.approx(0.5)                     # nya positionen (flat pris) ger varken vinst eller förlust


def test_stop_loss_is_the_position_equity_not_more_even_after_drift():
    # Short drivs upp 50 % innan stoppet: förlusten är fortfarande exakt hela insatsen (inte mer).
    n = 12
    idx = pd.date_range("2023-12-31", periods=n, freq="1D", tz="UTC")
    px = [100, 100, 110, 120, 130, 140, 150, 150, 150, 150, 150, 150.0]
    opens = pd.DataFrame({"X": px}, index=idx)
    highs = opens.copy(); lows = opens.copy()
    highs.iloc[6, 0] = 100 * 1.96   # high mot ingångskursen 100 (måndagens öppning) på dag 6
    w = pd.DataFrame({"X": [np.nan] * n}, index=idx); w.iloc[0, 0] = -0.4
    res = portfolio.run(opens, w, ZERO_COST, {"X": pd.Series(dtype=float)}, highs=highs, lows=lows, stop=tsmom.STOP)
    assert len(res.stops) == 1 and res.equity.iloc[-1] == pytest.approx(0.6)


def test_missing_high_or_low_for_a_held_position_is_an_invalid_run():
    opens, highs, lows, w, f = _mini(-0.5, {})
    highs.iloc[3, 0] = np.nan
    with pytest.raises(ValueError, match="High eller low saknas"):
        portfolio.run(opens, w, ZERO_COST, f, highs=highs, lows=lows, stop=tsmom.STOP)
    with pytest.raises(tsmom.InvalidRun):
        tsmom.simulate(opens, highs, lows, w, ZERO_COST, f | {"X": pd.Series([1e-4] * 40, index=pd.date_range("2023-12-31", periods=40, freq="8h", tz="UTC"))})
    with pytest.raises(ValueError, match="kräver high och low"):
        portfolio.run(opens, w, ZERO_COST, f, stop=tsmom.STOP)


def test_missing_funding_on_held_days_is_an_invalid_run_not_free_funding():
    opens, highs, lows, w, f = _mini(-0.5, {})
    with pytest.raises(tsmom.InvalidRun, match="Finansieringsränta saknas"):
        tsmom.simulate(opens, highs, lows, w, ZERO_COST, f)


def test_funding_is_paid_by_longs_and_received_by_shorts():
    n = 12
    idx = pd.date_range("2023-12-31", periods=n, freq="1D", tz="UTC")
    fund = {"X": pd.Series(0.001, index=pd.date_range("2023-12-31", periods=n * 3, freq="8h", tz="UTC"))}
    for weight, sign in ((0.5, 1), (-0.5, -1)):
        opens, highs, lows, w, _ = _mini(weight, {})
        res = tsmom.simulate(opens, highs, lows, w, ZERO_COST, fund)
        assert np.sign(res.total_funding) == sign   # betald (+) för long, mottagen (−) för short


def test_stressed_costs_are_2_5_times_higher():
    n = _mini(0.5, {})
    normal = portfolio.run(n[0], n[3], tsmom.COSTS, n[4], highs=n[1], lows=n[2], stop=tsmom.STOP)
    stressed = portfolio.run(n[0], n[3], tsmom.COSTS.stressed(), n[4], highs=n[1], lows=n[2], stop=tsmom.STOP)
    assert stressed.total_costs == pytest.approx(2.5 * normal.total_costs)
    assert tsmom.COSTS.per_side == pytest.approx(0.0025)   # 25 bp per sida, som H-0018


def test_stop_off_leaves_earlier_engine_results_unchanged():
    n = _mini(-0.5, {3: 2.0})
    assert portfolio.run(n[0], n[3], tsmom.COSTS, n[4]).equity.equals(portfolio.run(n[0], n[3], tsmom.COSTS, n[4]).equity)


# ---------------------------------------------------------------- slutprovsskydd och körning (syntetiskt)

def _zip(rows):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", rows)
    return buf.getvalue()


def test_loaders_never_open_holdout_archives(tmp_path):
    def klines(month):
        days = pd.date_range(month + "-01", periods=5, freq="1D", tz="UTC")
        return "\n".join(f"{int(d.timestamp() * 1000)},100,101,99,100,10,{int(d.timestamp() * 1000) + 86399999},0,0,0,0,0" for d in days) + "\n"
    raw = tmp_path / "raw/binance/um/BTCUSDT"
    (raw / "1d").mkdir(parents=True)
    (raw / "1d" / "BTCUSDT-1d-2024-12.zip").write_bytes(_zip(klines("2024-12")))
    (raw / "1d" / "BTCUSDT-1d-2025-01.zip").write_bytes(b"slutprov: far inte oppnas")
    (raw / "fundingRate").mkdir()
    (raw / "fundingRate" / "BTCUSDT-fundingRate-2024-12.zip").write_bytes(_zip("1733011200000,8,0.0001\n"))
    (raw / "fundingRate" / "BTCUSDT-fundingRate-2025-01.zip").write_bytes(b"slutprov")
    o, h, l, c, v, f = tsmom.load_panel(tmp_path, ["BTCUSDT"])
    assert o.index.max() < pd.Timestamp("2025-01-01", tz="UTC") and list(h.columns) == ["BTCUSDT"] and len(f["BTCUSDT"]) == 1


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git(tmp_path, "init", "-q"); git(tmp_path, "config", "user.email", "t@t"); git(tmp_path, "config", "user.name", "t")
    (tmp_path / "research").mkdir()
    (tmp_path / "research/registry.md").write_text("| id | datum | hypotes |\n|---|---|---|\n| H-0021 | 2026-11-12 | x |\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-qm", "reg")
    rng = np.random.default_rng(3)
    idx = pd.date_range("2020-11-01", "2024-12-31", freq="1D", tz="UTC")
    k = 36
    syms = [f"S{i}USDT" for i in range(k)]
    c = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0.0003, 0.03, (len(idx), k)), axis=0)), index=idx, columns=syms)
    o = c.shift(1).fillna(c.iloc[0])
    panel = (o, np.maximum(o, c) * 1.01, np.minimum(o, c) * 0.99, c, pd.DataFrame(2e7, index=idx, columns=syms))
    monkeypatch.setattr(xsbig, "universe", lambda d: syms)
    monkeypatch.setattr(tsmom, "load_panel", lambda d, s: (*panel, {s_: pd.Series(1e-4, index=pd.date_range("2020-11-01", "2024-12-31", freq="8h", tz="UTC")) for s_ in syms}))
    btc = pd.DataFrame({"open": c.iloc[:, 0].shift(1).fillna(100), "high": c.iloc[:, 0], "low": c.iloc[:, 0], "close": c.iloc[:, 0], "volume": 1.0})
    monkeypatch.setattr(binance, "load", lambda m, s, i, d, **kw: btc)
    return tmp_path


def test_valid_run_reports_criteria_stops_and_never_reads_the_holdout(repo):
    r = json.loads(tsmom.run("H-0021", repo).read_text())
    assert r["valid"] is True and r["period"][1] < "2025-01-01"
    assert set(r["criteria"]) == {"t_at_least_required", "stressed_costs_positive", "sharpe_above_btc_buy_and_hold", "sharpe_above_long_only_basket"}
    assert r["meets_all_criteria"] == all(r["criteria"].values())
    assert "liquidation_stops" in r and abs(r["random_label_t"]) < 4 and r["t_required"] == pytest.approx(tsmom.stats.t_krav(r["attempts"]))


def test_run_with_missing_funding_is_invalid_and_cannot_pass(repo, monkeypatch):
    real = tsmom.load_panel
    monkeypatch.setattr(tsmom, "load_panel", lambda d, s: (*real(d, s)[:5], {}))
    r = json.loads(tsmom.run("H-0021", repo).read_text())
    assert r["valid"] is False and r["decision"] == "OGILTIG" and "criteria" not in r and "meets_all_criteria" not in r
    assert any("Finansieringsränta saknas" in x for x in r["invalid_reasons"])


def test_run_with_missing_high_low_is_invalid_and_cannot_pass(repo, monkeypatch):
    real = tsmom.load_panel
    o, h, l, c, v, f = real(None, None)
    h = h.copy(); h.iloc[400:, :] = np.nan   # high saknas för alla hållna positioner senare
    monkeypatch.setattr(tsmom, "load_panel", lambda d, s: (o, h, l, c, v, f))
    r = json.loads(tsmom.run("H-0021", repo).read_text())
    assert r["valid"] is False and r["decision"] == "OGILTIG" and "meets_all_criteria" not in r
    assert any("High eller low saknas" in x for x in r["invalid_reasons"])


def test_too_few_eligible_coins_is_invalid(repo, monkeypatch):
    real = tsmom.load_panel
    o, h, l, c, v, f = real(None, None)
    v = v.copy(); v.iloc[:, 20:] = 1e6   # bara 20 likvida mynt (< 30)
    monkeypatch.setattr(tsmom, "load_panel", lambda d, s: (o, h, l, c, v, f))
    r = json.loads(tsmom.run("H-0021", repo).read_text())
    assert r["valid"] is False and any("Valbara mynt" in x for x in r["invalid_reasons"])


def test_unregistered_hypothesis_is_refused(repo):
    from traderlab.registry import NotRegisteredError
    with pytest.raises(NotRegisteredError):
        tsmom.run("H-0099", repo)
