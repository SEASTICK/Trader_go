"""Kör H-0027–H-0029 enligt research/intradag-protokoll.md. En körning per hypotes, resultatet sparas och skrivs aldrig över.

    python -m traderlab.intradag_run H-0027
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from . import quality
from .costs import CostModel
from .data import binance
from .experiment import run_experiment
from .intradag import STRATEGIES

COSTS = CostModel(fee_bps=5, spread_bps=0.1, slippage_bps=1)   # 6,05 bp per sida, låst i protokollet
START = pd.Timestamp("2020-01-01", tz="UTC")
END = pd.Timestamp("2025-01-01", tz="UTC")   # exklusivt; slutprovet 2025- öppnas aldrig


def run(hid: str, repo: Path) -> Path:
    interval, fn = STRATEGIES[hid]
    data = repo / "data"
    bars = binance.load("um", "BTCUSDT", interval, data, start=START, end=END)
    funding = binance.load_funding("BTCUSDT", data, start=START, end=END)
    report = quality.check(bars, interval)
    print(report.to_markdown())
    if not report.ok:
        raise SystemExit(f"{hid}: datakontrollen hittade fel, ingen körning: {report.problems}")
    return run_experiment(hid, repo, bars, fn, COSTS, market="um BTCUSDT (perpetual)", interval=interval,
                          funding=funding, track="B",
                          note=f"research/intradag-protokoll.md; kostnader 6,05 bp/sida; krav t ≥ 2,93 (N=29). "
                               f"Datakontroll: {report.rows} staplar, {report.missing_bars} saknade, varningar: {'; '.join(report.warnings) or 'inga'}")


if __name__ == "__main__":
    repo = Path(__file__).resolve().parents[2]
    for hid in sys.argv[1:] or list(STRATEGIES):
        print(hid, run(hid, repo))
