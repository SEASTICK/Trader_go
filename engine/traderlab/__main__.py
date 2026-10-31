"""Kommandorad: python -m traderlab <kommando>

  fetch  --market spot --symbol BTCUSDT --interval 4h --start 2021-01 --end 2024-12
  check  --market spot --symbol BTCUSDT --interval 4h
  krav   17
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import URLError

from . import quality, stats
from .data import binance

REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="traderlab", description="Trader_go forskningsmotor (bara historik och papper)")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="Hämta historik från Binance publika datafiler")
    c = sub.add_parser("check", help="Kör kvalitetskontroller på hämtad data")
    for s in (f, c):
        s.add_argument("--market", default="spot", choices=sorted(binance.MARKETS))
        s.add_argument("--symbol", required=True)
        s.add_argument("--interval", required=True)
        s.add_argument("--data-dir", type=Path, default=REPO / "data")
    f.add_argument("--start", required=True, help="ÅÅÅÅ-MM")
    f.add_argument("--end", required=True, help="ÅÅÅÅ-MM")
    f.add_argument("--funding", action="store_true", help="Hämta finansieringsränta i stället (bara um)")
    k = sub.add_parser("krav", help="Krav på t-värde efter N försök")
    k.add_argument("n", type=int)

    a = p.parse_args(argv)
    if a.cmd == "krav":
        print(f"{stats.t_krav(a.n):.2f}")
        return 0
    if a.cmd == "fetch":
        kind = "funding" if a.funding else "klines"
        try:
            r = binance.fetch(a.market, a.symbol, a.interval, a.start, a.end, a.data_dir, kind=kind)
        except URLError as exc:
            print(f"Kunde inte nå data.binance.vision ({exc.reason}). Kontrollera nätverket eller att "
                  "domänen är tillåten i miljön. Inget sparades för den månad som misslyckades.", file=sys.stderr)
            return 2
        print(f"Hämtade {len(r.downloaded)}, fanns redan {len(r.skipped_existing)}, saknas hos Binance: "
              f"{', '.join(r.missing) or 'inga'}")
        return 0
    bars = binance.load(a.market, a.symbol, a.interval, a.data_dir)
    rep = quality.check(bars, a.interval)
    print(rep.to_markdown(f"{a.market} {a.symbol} {a.interval}"))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
