"""Läsande omräkning av H-0013:s sparade resultat; kör aldrig forskningsmotorn."""
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "research/results/H-0013-20261103T143504962276Z-completed.json"
assert hashlib.sha256(PATH.read_bytes()).hexdigest() == "f752202e7c6413265d0dc404f546720d835d569af2251704134a41b44d561ee1"
d = json.loads(PATH.read_text())
r, main = d["result"], d["stats"]
comp = r["comparisons"]
times = pd.DatetimeIndex(d["curves"]["t"])
equity = np.asarray(d["curves"]["equity"])
returns = np.r_[equity[0] - 1, equity[1:] / equity[:-1] - 1]
daily = (pd.Series(1 + returns, index=times).groupby(times.floor("D")).prod() - 1).to_numpy()
n, mean, sd = len(daily), float(daily.mean()), float(daily.std(ddof=1))
sharpe = mean / sd * math.sqrt(365) if sd else 0.0
lags = math.floor(4 * (n / 100) ** (2 / 9))
centered = daily - mean
variance = sum(float(x * x) for x in centered) / n
for lag in range(1, lags + 1):
    covariance = sum(float(centered[i] * centered[i - lag]) for i in range(lag, n)) / n
    variance += 2 * (1 - lag / (lags + 1)) * covariance
t = mean / math.sqrt(variance / n) if variance > 0 else 0.0
recalculated = {
    "total_return": float(equity[-1] - 1), "sharpe": sharpe, "t_daily_nw": t,
    "max_drawdown": float(min(equity / np.maximum.accumulate(equity) - 1)),
}
for key, value in recalculated.items():
    assert math.isclose(value, main[key], abs_tol=1e-10), key
criteria = {
    "t_at_least_required": t >= 2.67,
    "stressed_costs_positive": r["stressed"]["total_return"] > 0,
    "sharpe_above_buy_and_hold": sharpe > comp["buy_and_hold"]["sharpe"],
    "sharpe_above_best_candidate": sharpe > max(comp[name]["sharpe"] for name in ("ema_adx_trend", "bb_rsi_reversion")),
    "sharpe_above_equal_weight_mix": sharpe > comp["equal_weight_mix"]["sharpe"],
}
assert criteria == d["criteria"] == r["criteria"]
assert d["decision"] == ("MORE_RESEARCH" if all(criteria.values()) else "REJECT")
assert d["holdout_loaded"] is False and d["data"]["last"] < "2025"
assert times.is_monotonic_increasing and times.is_unique
assert times[0] == pd.Timestamp("2022-01-01", tz="UTC")
assert times[-1] < pd.Timestamp("2025-01-01", tz="UTC")
assert len(r["walk_forward"]["windows"]) == 6
assert all(value == "done" for value in r["steps"].values())
assert len(r["permutation"]["runs"]) == r["permutation"]["n"] == 200
k = sum(run["sharpe"] >= main["sharpe"] for run in r["permutation"]["runs"])
assert k == r["permutation"]["at_least_as_high"]
assert k / 200 == r["permutation"]["p_value"]
assert len(r["playbooks"]["playbooks"]) == r["playbooks"]["n"] == 81
assert len(d["trades"]) == main["trades"] == r["walk_forward"]["trades"] == 5
# Affärsprocent har kapitalet vid respektive inträde som nämnare: summera dem inte.
trade_return = float(np.prod([1 + trade["net_return"] for trade in d["trades"]]) - 1)
assert math.isclose(trade_return, main["total_return"], abs_tol=1e-10)
for key in ("costs", "funding"):
    windows = r["walk_forward"]["windows"]
    assert math.isclose(sum(window[key] for window in windows), main[key], abs_tol=1e-10)
    assert all(math.isclose(window[key], window["local_" + key] * window["capital_start"], abs_tol=1e-10) for window in windows)
curves = d["curves"]["comparisons"]
assert curves["points"] == len(curves["t"]) == 1500
assert curves["bars"] == len(times) == 6570
for name, curve in curves["series"].items():
    assert len(curve) == 1500 and np.isfinite(curve).all()
    expected = 1 + (main["total_return"] if name == "h0013" else comp[name]["total_return"])
    assert math.isclose(curve[-1], expected, abs_tol=1e-8)
assert np.allclose(curves["series"]["h0013"], pd.Series(equity, index=times).loc[pd.DatetimeIndex(curves["t"])].to_numpy(), atol=1e-8)
print(json.dumps({
    "recalculated": recalculated, "daily_observations": n, "criteria": criteria,
    "decision": d["decision"], "trade_compounded_return": trade_return,
    "permutation_k": k, "permutation_p": k / 200, "complete_steps": len(r["steps"]),
    "curves_points": len(times), "comparisons_points": curves["points"],
    "canonical_payload_sha256": hashlib.sha256(json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
}, indent=2))
