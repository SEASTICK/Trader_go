"""Tvärsnitt med stort universum (research/xs-stort-protokoll.md): H-0018 momentum och H-0019 funding-carry.

Återanvänder portföljmotorn (portfolio.py) och signalerna i xs.py, med tre skillnader enligt protokollet:
universum ur Binances arkiv, ett likviditetsfilter och tiondelar i stället för fem per sida.
"""
from __future__ import annotations

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import portfolio, stats, xs
from .costs import CostModel
from .data import binance
from .experiment import RESULTS, benchmark_stats
from .registry import require_registered

LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix=data/futures/um/monthly/klines/"
INDEX_CONTRACTS = {"BTCDOMUSDT", "DEFIUSDT", "BLUEBIRDUSDT", "FOOTBALLUSDT"}
START, HOLDOUT = "2021-01-01", "2025-01-01"
COSTS = CostModel(fee_bps=10, spread_bps=10, slippage_bps=10)   # 25 bp per sida
MIN_DOLLAR_VOLUME = 10_000_000
MIN_HISTORY = 60


def list_symbols(data_dir: Path) -> list[str]:
    """Alla USDⓈ-M-kontrakt i arkivet (sparas i data/raw/binance/um-symbols.json)."""
    path = data_dir / "raw" / "binance" / "um-symbols.json"
    if path.exists():
        return json.loads(path.read_text())
    syms, marker = [], ""
    while True:
        url = LIST + (f"&marker={marker}" if marker else "")
        xml = urllib.request.urlopen(url, timeout=60).read().decode()
        page = re.findall(r"<Prefix>data/futures/um/monthly/klines/([^/<]+)/</Prefix>", xml)
        syms += page
        if "<IsTruncated>true</IsTruncated>" in xml and page:
            marker = f"data/futures/um/monthly/klines/{page[-1]}/"
        else:
            break
    out = sorted(set(syms))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def _has_month(sym: str, month: str = "2021-01") -> bool:
    url = binance.kline_url("um", sym, "1d", month)
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def universe(data_dir: Path) -> list[str]:
    """Protokollets regel: USDT-kontrakt med en månadsfil för 2021-01, utom indexkontrakt."""
    path = data_dir / "raw" / "binance" / "xs-big-universe.json"
    if path.exists():
        return json.loads(path.read_text())
    cands = [s for s in list_symbols(data_dir) if s.endswith("USDT") and s not in INDEX_CONTRACTS]
    with ThreadPoolExecutor(8) as ex:
        ok = [s for s, has in zip(cands, ex.map(_has_month, cands)) if has]
    path.write_text(json.dumps(sorted(ok)))
    return sorted(ok)


def fetch(data_dir: Path, symbols: list[str]) -> None:
    """Dagsstaplar och finansieringsränta 2020-11 till 2024-12 (uppvärmning före start). Slutprovet hämtas inte."""
    import threading
    lock = threading.Lock()
    orig = binance._append_manifest

    def locked(*a, **k):   # MANIFEST.md skrivs från flera trådar: en i taget
        with lock:
            return orig(*a, **k)
    binance._append_manifest = locked

    def one(s):
        binance.fetch("um", s, "1d", "2020-11", "2024-12", data_dir)
        binance.fetch("um", s, "1d", "2020-11", "2024-12", data_dir, kind="fundingRate")
    try:
        with ThreadPoolExecutor(6) as ex:
            list(ex.map(one, symbols))
    finally:
        binance._append_manifest = orig


def eligible(closes: pd.DataFrame, dollar_volume: pd.DataFrame) -> pd.DataFrame:
    hist = closes.notna().cumsum()
    liquid = dollar_volume.rolling(30, min_periods=20).median() >= MIN_DOLLAR_VOLUME
    return closes.notna() & (hist >= MIN_HISTORY) & liquid


def decile_long_short(score: pd.DataFrame, elig: pd.DataFrame, long_high: bool) -> pd.DataFrame:
    w = pd.DataFrame(0.0, index=score.index, columns=score.columns)
    for t in score.index:
        s = score.loc[t][elig.loc[t]].dropna()
        if len(s) < 10:
            continue
        k = max(5, int(len(s) * 0.1))
        order = s.sort_values(ascending=not long_high, kind="mergesort")
        w.loc[t, order.index[:k]] = 0.5 / k
        w.loc[t, order.index[-k:]] = -0.5 / k
    return w


def weights(kind: str, closes: pd.DataFrame, dvol: pd.DataFrame, funding: dict[str, pd.Series]) -> pd.DataFrame:
    days = xs.rebalance_days(closes.index)
    elig = eligible(closes, dvol).loc[days]
    if kind == "momentum":
        score = (closes.shift(1) / closes.shift(29) - 1).loc[days]
        return decile_long_short(score, elig, long_high=True)
    score = xs.funding_score(closes.index, {s: funding[s] for s in closes.columns if s in funding}).reindex(columns=closes.columns)
    return decile_long_short(score.loc[days], elig, long_high=False)


def load_panel(data_dir: Path, symbols: list[str]):
    lo, hi = pd.Timestamp("2020-11-01", tz="UTC"), pd.Timestamp(HOLDOUT, tz="UTC")
    opens, closes, dvol, funding = {}, {}, {}, {}
    for s in symbols:
        try:
            b = binance.load("um", s, "1d", data_dir)
        except FileNotFoundError:
            continue
        b = b[(b.index >= lo) & (b.index < hi)]
        if b.empty:
            continue
        opens[s], closes[s], dvol[s] = b["open"], b["close"], b["close"] * b["volume"]
        try:
            f = binance.load_funding(s, data_dir)
            funding[s] = f[f.index < hi]
        except FileNotFoundError:
            funding[s] = pd.Series(dtype=float)
    return pd.DataFrame(opens), pd.DataFrame(closes), pd.DataFrame(dvol), funding


def run(hypothesis_id: str, kind: str, repo: Path, data_dir: Path | None = None) -> Path:
    reg = require_registered(hypothesis_id, repo)
    data_dir = data_dir or repo / "data"
    syms = universe(data_dir)
    opens, closes, dvol, funding = load_panel(data_dir, syms)
    assert opens.index.max() < pd.Timestamp(HOLDOUT, tz="UTC"), "Slutprovet får inte läsas in."
    w = weights(kind, closes, dvol, funding)
    w = w[w.index >= pd.Timestamp(START, tz="UTC")]
    normal = portfolio.run(opens, w, COSTS, funding)
    stressed = portfolio.run(opens, w, COSTS.stressed(), funding)
    keep = normal.equity.index >= pd.Timestamp(START, tz="UTC")
    eq = normal.equity[keep] / normal.equity[keep].iloc[0]
    daily = stats.daily_returns(normal.bar_returns[keep])
    t_req, t_nw = stats.t_krav(reg.attempts), stats.newey_west_t(daily)
    spot = binance.load("spot", "BTCUSDT", "1d", data_dir)
    spot = spot[(spot.index >= pd.Timestamp(START, tz="UTC")) & (spot.index < pd.Timestamp(HOLDOUT, tz="UTC"))]
    bench = benchmark_stats(normal, spot, "spot BTCUSDT 1d")
    st_eq = stressed.equity[keep] / stressed.equity[keep].iloc[0]
    live = w[(w != 0).any(axis=1)]
    per_side = (w > 0).sum(axis=1)[(w != 0).any(axis=1)]
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    m = eq.resample("ME").last()
    yearly = (eq.resample("YE").last() / eq.resample("YE").last().shift(1).fillna(1.0) - 1)
    out = {
        "hypothesis_id": hypothesis_id, "registry_commit": reg.registry_commit, "phase": "xs-big", "track": "C",
        "kind": kind, "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "universe_size": len(syms), "with_data": int(opens.shape[1]),
        "eligible_median": float(eligible(closes, dvol).sum(axis=1).loc[xs.rebalance_days(closes.index)].median()),
        "per_side_median": float(per_side.median()) if len(per_side) else 0.0,
        "period": [str(eq.index[0].date()), str(eq.index[-1].date())], "rebalances": int(len(live)),
        "costs_bps_per_side": COSTS.per_side * 10_000, "attempts": reg.attempts,
        "t_daily_nw": t_nw, "t_required": t_req,
        "deflated_sharpe": stats.deflated_sharpe(daily.to_numpy(), max(reg.attempts, 1)),
        "sharpe_ci": list(stats.block_bootstrap_sharpe_ci(daily)),
        "summary": {"total_return": float(eq.iloc[-1] - 1), "cagr": float(eq.iloc[-1] ** (1 / years) - 1) if eq.iloc[-1] > 0 else -1.0,
                    "sharpe": float(stats.sharpe(daily)), "max_drawdown": float(stats.max_drawdown(eq)),
                    "turnover_per_year": float(normal.turnover[keep].sum() / years), "costs": normal.total_costs,
                    "funding": normal.total_funding,
                    "yearly": {str(k.year): round(float(v), 4) for k, v in yearly.items()},
                    "monthly_returns": {k.strftime("%Y-%m"): round(float(v), 6) for k, v in (m / m.shift(1).fillna(1.0) - 1).items()}},
        "summary_stressed_costs": {"total_return": float(st_eq.iloc[-1] - 1)},
        "benchmark": bench,
        "random_label_t": None,
        "curve": {"t": [d.isoformat() for d in eq.index[::5]], "strategy": [round(float(v) * 100, 4) for v in eq.iloc[::5]]},
        "simulated": False,
    }
    # Slumpkontroll: slumpade tiondelar samma söndagar, utan kostnader. t ska ligga nära noll.
    rng = np.random.default_rng(0)
    days = xs.rebalance_days(closes.index)
    rnd = pd.DataFrame(rng.normal(size=closes.shape), index=closes.index, columns=closes.columns).loc[days]
    wr = decile_long_short(rnd, eligible(closes, dvol).loc[days], True)
    wr = wr[wr.index >= pd.Timestamp(START, tz="UTC")]
    rr = portfolio.run(opens, wr, CostModel(0, 0, 0))
    out["random_label_t"] = float(stats.newey_west_t(stats.daily_returns(rr.bar_returns)))
    out["criteria"] = {"t_at_least_required": bool(t_nw >= t_req), "stressed_costs_positive": out["summary_stressed_costs"]["total_return"] > 0,
                       "beta_within_0_2": bench["beta"] is not None and abs(bench["beta"]) <= 0.2}
    out["meets_all_criteria"] = all(out["criteria"].values())
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{hypothesis_id}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    return path
