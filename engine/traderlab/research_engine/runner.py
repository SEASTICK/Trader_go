"""Avgränsad utforskning, befintlig motor. Rör inte register eller fryst slutprov."""
from __future__ import annotations

import hashlib
import json
import math
import platform
from importlib.metadata import version
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from .. import backtest, metrics, quality
from ..bars import interval_delta
from ..costs import CostModel
from ..data import binance
from ..strategies.rules import SPECS


def validate(job: dict):
    if job.get("kind") != "exploration" or job.get("hypothesis_id") is not None:
        raise ValueError("Workern stöder endast separat utforskning")
    if job.get("symbol") != "BTCUSDT" or job.get("market") not in ("spot", "um"):
        raise ValueError("Ogiltig marknad")
    if job.get("interval") not in ("1h", "4h", "1d"):
        raise ValueError("Ogiltig tidsram")
    spec = SPECS.get(job.get("strategy"))
    if spec is None or job.get("version") != spec.version:
        raise ValueError("Okänd strategiversion")
    supplied = job.get("params", {})
    if not isinstance(supplied, dict) or set(supplied) - set(spec.defaults):
        raise ValueError("Okända parametrar")
    params = {**spec.defaults, **supplied}
    for name, value in params.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Parametrar måste vara ändliga tal")
        default = spec.defaults[name]
        if isinstance(default, int) and (not isinstance(value, int) or not 2 <= value <= 500):
            raise ValueError("Indikatorperioder måste vara heltal mellan 2 och 500")
        if name in spec.space:
            space = spec.space[name]
            if not space.low <= value <= space.high:
                raise ValueError("Parameter utanför registrerad sökrymd")
        elif isinstance(default, float) and not 0 < value <= 100:
            raise ValueError("Ogiltig indikatorparameter")
    if not spec.valid(params):
        raise ValueError("Ogiltig parameterkombination")
    start, end = (pd.Timestamp(job[k]) for k in ("period_start", "period_end"))
    if start.tz is None or end.tz is None:
        raise ValueError("UTC-tidszon krävs")
    start, end = start.tz_convert("UTC"), end.tz_convert("UTC")
    if (start < pd.Timestamp("2020-01-01", tz="UTC") or end > pd.Timestamp("2025-01-01", tz="UTC")
            or end - start < pd.Timedelta(days=30) or start != start.floor("D") or end != end.floor("D")):
        raise ValueError("Otillåten period; slutprovet är låst")
    costs = job.get("costs")
    expected = {"fee_bps": 10, "spread_bps": 2, "slippage_bps": 5}
    if costs != expected or job.get("capital") != 100000:
        raise ValueError("Kostnadsmodell/kapital måste matcha serverkontraktet")
    return spec, params, start, end


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def evaluate(job, bars, funding=None):
    spec, params, start, end = validate(job)
    if not np.isfinite(bars.to_numpy()).all():
        raise ValueError("Marknadsdata innehåller icke-ändliga tal")
    report = quality.check(bars, job["interval"])
    if not report.ok or report.missing_bars:
        raise ValueError("Datakvalitetsfel: " + "; ".join(report.problems + report.warnings)
                         + "; luckor: " + str(report.largest_gaps[:3]))
    selected = bars[(bars.index >= start) & (bars.index < end)]
    expected = pd.date_range(start, end, freq=interval_delta(job["interval"]), inclusive="left")
    if not selected.index.equals(expected):
        raise ValueError("Data täcker inte hela begärda perioden")
    funding_validation = None
    if job["market"] == "um":
        if funding is None or funding.empty or not np.isfinite(funding.to_numpy()).all():
            raise ValueError("Finansieringsränta krävs")
        funding = funding[(funding.index >= start) & (funding.index < end)]
        expected_funding = pd.date_range(start, end, freq="8h", inclusive="left")
        # Binance publicerar faktiska avräkningstider några millisekunder efter
        # klockslaget. Kontrollera en händelse per 8h-fönster utan att ändra tiden.
        buckets = funding.index.floor("8h")
        delay = funding.index - buckets
        if not buckets.equals(expected_funding) or (delay > pd.Timedelta(seconds=60)).any():
            raise ValueError("Finansieringsräntan täcker inte periodens 8h-avräkningar")
        funding_validation = {"events": len(funding), "max_delay_ms": float(delay.max().total_seconds() * 1000),
                              "timestamp_policy": "original timestamps; one event within 60s of each 8h boundary"}
    elif funding is not None:
        raise ValueError("Spot får inte använda finansieringsränta")
    params["allow_short"] = job["market"] == "um"
    backtest.check_no_lookahead(lambda b: spec.signals(b, params).target, bars)
    signals = spec.signals(bars, params)
    # Indikatorer värms upp före perioden. Positionen startar platt; första
    # beslutet i perioden fylls tidigast nästa öppning.
    cost_model = CostModel(**job["costs"])
    res = backtest.run(selected, signals.target.reindex(selected.index), cost_model,
                       funding=funding, stop_distance=signals.stop_distance,
                       take_profit_distance=signals.take_profit_distance)
    baseline = backtest.run(selected, pd.Series(1.0, index=selected.index), cost_model, funding=funding)
    return clean({"mode": "exploration", "simulated": False,
                  "stats": metrics.full_stats(res, selected, job["capital"]),
                  "curves": metrics.curves(res), "baseline": metrics.curves(baseline),
                  "baseline_stats": metrics.full_stats(baseline, selected, job["capital"]),
                  "quality": asdict(report), "effective_params": params,
                  "funding_validation": funding_validation,
                  "warnings": ["UTFORSKNING: inget registrerat strategibeslut",
                               "Andra börskällan är inte verifierad; inga utstickare har tagits bort",
                               "BTCUSDT är ett i förväg valt instrument; ingen slutsats om andra marknader",
                               "Perioden är historiskt använd; den utgör inget orört slutprov"] +
                              (["Terminer använder kontrakts-OHLC, inte separat mark price; likvidationsmodell vid 1x"]
                               if job["market"] == "um" else []),
                  "trades": [{"entry_time": t.entry_time.isoformat(), "entry_price": t.entry_price,
                              "exit_time": t.exit_time.isoformat() if t.exit_time is not None else None,
                              "exit_price": t.exit_price, "side": t.side,
                              "net_return": t.net_return, "exit_reason": t.exit_reason} for t in res.trades]})


def run_job(job: dict, data_dir: Path, output: Path):
    spec, params, start, end = validate(job)
    step = interval_delta(job["interval"])
    # UM monthly archives used by Phase 1 are verified from January 2020.
    # Never request unavailable 2019 archives or substitute spot prices.
    archive_floor = "2020-01-01" if job["market"] == "um" else "2019-09-01"
    warmup = max(pd.Timestamp(archive_floor, tz="UTC"), start - 600 * step)
    first, last = warmup.strftime("%Y-%m"), (end - pd.Timedelta(seconds=1)).strftime("%Y-%m")
    progress = output.with_suffix(".progress")
    files = []
    frames, rates = [], []
    for kind in (["klines", "funding"] if job["market"] == "um" else ["klines"]):
        for month in binance.months(first if kind == "klines" else start.strftime("%Y-%m"), last):
            frame = job["interval"] if kind == "klines" else "fundingRate"
            folder = data_dir / "raw" / "binance" / job["market"] / job["symbol"] / frame
            url = (binance.kline_url(job["market"], job["symbol"], job["interval"], month)
                   if kind == "klines" else binance.funding_url(job["symbol"], month))
            path = folder / url.rsplit("/", 1)[1]
            check = path.with_suffix(path.suffix + ".CHECKSUM")
            folder.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                result = binance.fetch(job["market"], job["symbol"], job["interval"], month, month, data_dir, kind=kind)
                if result.missing:
                    raise ValueError(f"Historisk månadsfil saknas: {kind} {job['market']} {month}")
            if not check.exists():
                check.write_bytes(binance._default_opener(url + ".CHECKSUM"))
            raw = path.read_bytes()
            binance.verify_checksum(raw, check.read_bytes())
            files.append({"path": str(path.relative_to(data_dir)), "sha256": hashlib.sha256(raw).hexdigest(),
                          "source": url})
            parsed = binance._unzip_single(raw)
            (frames if kind == "klines" else rates).append(
                binance.parse_klines_csv(parsed) if kind == "klines" else binance.parse_funding_csv(parsed))
            progress.write_text("0.25")
    bars = pd.concat(frames)
    bars = bars[(bars.index >= warmup) & (bars.index < end)]
    funding = pd.concat(rates) if rates else None
    progress.write_text("0.5")
    result = evaluate(job, bars, funding)
    warmup_bars = int((bars.index < start).sum())
    if warmup_bars < 600:
        result["warnings"].append(
            f"Endast {warmup_bars} av 600 uppvärmningsstaplar finns före perioden; "
            "indikatorer värms färdigt inom perioden och ingen saknad data fylls i")
    dataset_hash = hashlib.sha256(bars.to_csv(float_format="%.17g").encode())
    if funding is not None:
        dataset_hash.update(funding.to_csv(float_format="%.17g").encode())
    code_hash = hashlib.sha256()
    for path in sorted(Path(__file__).parents[1].rglob("*.py")):
        code_hash.update(str(path.relative_to(Path(__file__).parents[1])).encode())
        code_hash.update(path.read_bytes())
    config = {k: job[k] for k in ("strategy", "version", "params", "market", "symbol", "interval",
                                   "period_start", "period_end", "capital", "costs")}
    metadata = {"contract_version": 1, "dataset_sha256": dataset_hash.hexdigest(),
                "engine_sha256": code_hash.hexdigest(), "configuration": config,
                "source_files": files, "warmup_start": warmup.isoformat(), "warmup_bars": warmup_bars, "seed": 0,
                "runtime": {"python": platform.python_version(),
                            **{p: version(p) for p in ("numpy", "pandas", "scipy", "ta")}}}
    metadata["fingerprint"] = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    result["metadata"] = metadata
    output.write_text(json.dumps(result, allow_nan=False))
    # Separat sidecar för lagringsadaptern; inte nedprovade diagramdata.
    rows = [{"provider": "binance", "market": job["market"], "symbol": job["symbol"],
             "interval": job["interval"], "open_time": t.isoformat(), "closed": True,
             **{k: float(v) for k, v in row.items()}} for t, row in bars.iterrows()]
    output.with_suffix(".candles").write_text(json.dumps(rows, allow_nan=False))
    if funding is not None:
        rows = [{"symbol": job["symbol"], "funding_time": t.isoformat(), "rate": float(v)}
                for t, v in funding.items() if start <= t < end]
        output.with_suffix(".funding").write_text(json.dumps(rows, allow_nan=False))
    manifest = data_dir / "manifests"
    manifest.mkdir(exist_ok=True)
    (manifest / (metadata["fingerprint"] + ".json")).write_text(json.dumps(
        {**metadata, "quality": result["quality"]}, indent=2, allow_nan=False))
    progress.write_text("0.9")
