"""H-0030: de 50 låsta varianterna i research/intradag-grid-protokoll.md, och körningen av dem.

    python -m traderlab.intradag_grid

Tre kontrollvarianter ska återge H-0027–H-0029 exakt. Resultatet sparas i en fil som aldrig skrivs över.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from . import backtest, intradag, quality
from .costs import ZERO
from .data import binance
from .experiment import _baseline, random_label_control
from .intradag_run import COSTS, END, START
from .registry import require_registered
from .report import summarize

NY = intradag.NY
DELTA = {"5m": pd.Timedelta(minutes=5), "15m": pd.Timedelta(minutes=15), "1h": pd.Timedelta(hours=1)}
LAST_OPEN = {"5m": pd.Timestamp("2024-12-31 23:55", tz="UTC"), "15m": intradag.LAST_OPEN_15M,
             "1h": intradag.LAST_OPEN_1H}
T_REQUIRED = 3.23
N_ATTEMPTS = 79


def reversal(bars: pd.DataFrame, *, interval: str, k: float, hold_hours: int) -> pd.Series:
    """Familj R. Mot första stapeln per UTC-dygn med |r| > k·σ (30 dygns fönster), i hold_hours eller till 00:00."""
    d_bar = DELTA[interval]
    w = int(pd.Timedelta(days=30) / d_bar)
    last_open = LAST_OPEN[interval]
    idx = bars.index
    target = np.zeros(len(bars))
    if len(bars) < w + 2:
        return pd.Series(target, index=idx)
    close = bars["close"].astype(float)
    contiguous = pd.Series(idx, index=idx).diff() == d_bar
    r = (close / close.shift(1) - 1).where(contiguous)
    sigma = r.shift(1).where(contiguous).rolling(w, min_periods=w).std(ddof=1)
    extreme = (r.abs() > k * sigma) & sigma.notna() & r.notna()
    day = idx.floor("D")
    first = extreme & (extreme.astype(int).groupby(day).cumsum() == 1)
    for i in np.flatnonzero(first.to_numpy()):
        t0 = idx[i]
        entry = t0 + d_bar
        exit_at = min(entry + pd.Timedelta(hours=hold_hours), t0.floor("D") + pd.Timedelta(hours=24))
        if exit_at <= entry or exit_at >= last_open:
            continue
        target[(idx >= t0) & (idx < exit_at - d_bar)] = -float(np.sign(r.iloc[i]))
    return pd.Series(target, index=idx)


def opening_range(bars: pd.DataFrame, *, interval: str, range_minutes: int, exit_hour: int) -> pd.Series:
    """Familj O. Utbrott ur USA-öppningens intervall, signal senast 12:00, ut vid exit_hour New York-tid."""
    d_bar = DELTA[interval]
    step = int(d_bar / pd.Timedelta(minutes=1))
    start = 600 if interval == "1h" else 570          # 1h: intervallet börjar 10:00 (protokollet)
    end = start + range_minutes
    exit_min = exit_hour * 60
    last_open = LAST_OPEN[interval]
    target = np.zeros(len(bars))
    if bars.empty:
        return pd.Series(target, index=bars.index)
    local = bars.index.tz_convert(NY)
    minutes = np.asarray(local.hour * 60 + local.minute)
    day = local.normalize()
    high = bars["high"].to_numpy(dtype=float)
    low = bars["low"].to_numpy(dtype=float)
    close = bars["close"].to_numpy(dtype=float)
    for d in day.unique():
        if d.weekday() >= 5:
            continue
        in_day = np.flatnonzero(day == d)
        m = minutes[in_day]
        rng = in_day[(m >= start) & (m < end)]
        if len(rng) != range_minutes // step:
            continue
        exit_utc = (d.tz_localize(None) + pd.Timedelta(minutes=exit_min)).tz_localize(NY).tz_convert("UTC")
        if exit_utc >= last_open:
            continue
        hi, lo = high[rng].max(), low[rng].min()
        for i in in_day[(m >= end) & (m + step <= 720)]:
            s = 1.0 if close[i] > hi else -1.0 if close[i] < lo else 0.0
            if s == 0.0:
                continue
            target[in_day[(m >= minutes[i]) & (m < exit_min - step)]] = s
            break
    return pd.Series(target, index=bars.index)


def early_late(bars: pd.DataFrame, *, window_hours: int, entry_hour: int) -> pd.Series:
    """Familj M. Tecknet på 00:00 till window_hours UTC ger positionen från entry_hour till 00:00 UTC."""
    last_open = LAST_OPEN["1h"]
    idx = bars.index
    target = np.zeros(len(bars))
    if bars.empty:
        return pd.Series(target, index=idx)
    hour = np.asarray(idx.hour)
    day = idx.floor("D")
    opens = bars["open"].to_numpy(dtype=float)
    closes = bars["close"].to_numpy(dtype=float)
    for d in day.unique():
        in_day = np.flatnonzero(day == d)
        h = hour[in_day]
        if sorted(h[h < window_hours].tolist()) != list(range(window_hours)):
            continue
        if d + pd.Timedelta(hours=24) >= last_open:
            continue
        s = float(np.sign(closes[in_day[h == window_hours - 1][0]] / opens[in_day[h == 0][0]] - 1))
        if s == 0.0:
            continue
        target[in_day[(h >= entry_hour - 1) & (h < 23)]] = s
    return pd.Series(target, index=idx)


@dataclass(frozen=True)
class Variant:
    id: str
    family: str
    interval: str
    params: dict
    fn: Callable[[pd.DataFrame], pd.Series]
    control_of: str | None = None


def variants() -> list[Variant]:
    out: list[Variant] = []
    n = 0
    for itv in ("5m", "15m", "1h"):
        for k in (2.5, 3.0, 4.0):
            for hold in (1, 3, 6):
                n += 1
                ctrl = "H-0027" if (itv, k, hold) == ("1h", 3.0, 3) else None
                out.append(Variant(f"H-0030-R{n:02d}", "R", itv, {"k": k, "hold_hours": hold},
                                   partial(reversal, interval=itv, k=k, hold_hours=hold), ctrl))
    n = 0
    for itv, ranges in (("5m", (30, 60, 120)), ("15m", (30, 60, 120)), ("1h", (60,))):
        for rm in ranges:
            for ex in (13, 16):
                n += 1
                ctrl = "H-0028" if (itv, rm, ex) == ("15m", 60, 16) else None
                out.append(Variant(f"H-0030-O{n:02d}", "O", itv, {"range_minutes": rm, "exit_hour": ex},
                                   partial(opening_range, interval=itv, range_minutes=rm, exit_hour=ex), ctrl))
    n = 0
    for wh in (3, 6, 12):
        for eh in (12, 18, 21):
            n += 1
            ctrl = "H-0029" if (wh, eh) == (6, 18) else None
            out.append(Variant(f"H-0030-M{n:02d}", "M", "1h", {"window_hours": wh, "entry_hour": eh},
                               partial(early_late, window_hours=wh, entry_hour=eh), ctrl))
    return out


def _evaluate(v: Variant, bars: pd.DataFrame, funding: pd.Series, base: dict, rand_t: float) -> dict:
    backtest.check_no_lookahead(v.fn, bars)
    target = v.fn(bars)
    normal = backtest.run(bars, target, COSTS, funding=funding)
    stressed = backtest.run(bars, target, COSTS.stressed(), funding=funding)
    s = summarize(normal, N_ATTEMPTS).to_dict()
    ss = summarize(stressed, N_ATTEMPTS).to_dict()
    crit = {
        "t": s["t_daily_nw"] >= T_REQUIRED,
        "stressed_positive": ss["total_return"] > 0,
        "drawdown_40pct_smaller": s["max_drawdown"] >= 0.6 * base["max_drawdown"],
        "controls": s["liquidations"] == 0 and abs(rand_t) < 2,
    }
    return {"id": v.id, "family": v.family, "interval": v.interval, "params": v.params, "control_of": v.control_of,
            "summary": s, "summary_stressed_costs": ss, "criteria": crit, "passes_all": all(crit.values()),
            "trades_total": len(normal.trades), "target_nonzero_bars": int((target != 0).sum()),
            "_target": target}


def main(repo: Path) -> Path:
    reg = require_registered("H-0030", repo)
    data = repo / "data"
    funding = binance.load_funding("BTCUSDT", data, start=START, end=END)
    cache: dict[str, tuple] = {}
    rows = []
    for v in variants():
        if v.interval not in cache:
            bars = binance.load("um", "BTCUSDT", v.interval, data, start=START, end=END)
            rep = quality.check(bars, v.interval)
            if not rep.ok:
                raise SystemExit(f"Datafel i {v.interval}: {rep.problems}")
            base = _baseline(bars, COSTS, N_ATTEMPTS)
            cache[v.interval] = (bars, base, random_label_control(bars), rep)
        bars, base, rand_t, _ = cache[v.interval]
        row = _evaluate(v, bars, funding, base, rand_t)
        print(v.id, v.interval, v.params, row["summary"]["trades"], round(row["summary"]["total_return"], 3),
              round(row["summary"]["t_daily_nw"], 2), flush=True)
        rows.append(row)
    # Kontroller: varianterna ska återge H-0027–H-0029 i mål, affärer och siffror.
    controls = {}
    for row in rows:
        if not row["control_of"]:
            continue
        hid = row["control_of"]
        itv, fn = intradag.STRATEGIES[hid]
        orig = fn(cache[itv][0])
        res = backtest.run(cache[itv][0], orig, COSTS, funding=funding)
        so = summarize(res, N_ATTEMPTS).to_dict()
        same = (orig.equals(row["_target"]) and so["trades"] == row["summary"]["trades"]
                and np.isclose(so["total_return"], row["summary"]["total_return"])
                and np.isclose(so["t_daily_nw"], row["summary"]["t_daily_nw"]))
        controls[hid] = {"variant": row["id"], "identical": bool(same)}
        if not same:
            raise SystemExit(f"Kontrollen för {hid} ({row['id']}) återger inte originalet. Analysen stoppas.")
    for row in rows:
        row.pop("_target")
    qualifying = sorted([r for r in rows if r["passes_all"]],
                        key=lambda r: (-r["summary"]["t_daily_nw"], -r["summary"]["trades"]))
    out = {
        "hypothesis_id": "H-0030", "registry_commit": reg.registry_commit,
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "market": "um BTCUSDT (perpetual)", "period": [str(START), str(END)],
        "costs_bps_per_side": COSTS.per_side * 10_000, "t_required": T_REQUIRED, "n_attempts": N_ATTEMPTS,
        "baseline_buy_and_hold": {k: v[1] for k, v in cache.items()},
        "random_label_t": {k: v[2] for k, v in cache.items()},
        "data_quality": {k: {"rows": v[3].rows, "missing_bars": v[3].missing_bars, "warnings": v[3].warnings}
                         for k, v in cache.items()},
        "controls": controls, "variants": rows,
        "selected": qualifying[0]["id"] if qualifying else None,
        "note": "research/intradag-grid-protokoll.md. Ingen variant kan godkännas direkt.",
    }
    folder = repo / "research/results"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = folder / f"H-0030-{stamp}.json"
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(main(Path(__file__).resolve().parents[2]))
