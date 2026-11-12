"""Bygger käll- och täckningstabellerna för research/basis-uppfoljning-data.md ur rapportfilerna i research/coverage/.

Inget handskrivs: varje siffra kommer ur filerna `basis-sources-*.json` och `basis-cm-liquidity-*.json`, som i sin tur
skapas av `traderlab.data.basis_sources`. Körs: `python -m traderlab.data.basis_report` (från engine/).
"""
from __future__ import annotations

import json
from pathlib import Path

from .basis_sources import CM_UNDERLYINGS


def _load(folder: Path, pattern: str) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob(pattern))]


def sources_table(reports: list[dict]) -> str:
    """En rad per källprov: nåbar, och vad som svarade."""
    rows = ["| Källa | Nåbar | Vad som svarade |", "|---|---|---|"]
    for rep in reports:
        for name, v in rep["sources"].items():
            if not v.get("reachable"):
                rows.append(f"| {name} | nej | {v.get('error', '')[:110]} |")
                continue
            body = {k: x for k, x in v.items() if k != "reachable"}
            if name == "binance":
                what = (f"USDⓈ-M: {len(body['um_dated_futures']['underlyings'])} underliggande, "
                        f"COIN-M: {len(body['cm_dated_futures']['underlyings'])} underliggande (detaljer nedan)")
            elif name == "deribit":
                what = "; ".join(f"{c}: {d['expired_dated_contracts']} utgånget kontrakt via API" for c, d in body["currencies"].items())
            elif name == "bybit":
                what = f"{body['symbols_listed']} symboler listade, {body['dated_count']} med datum i namnet (affärsfiler)"
            elif name == "okx":
                what = f"{body['live_dated_contracts_btc_usd']} aktiva BTC-USD-terminer, {body['expired_contract_candles']} dagsstaplar för utgånget kontrakt"
            elif name == "bitmex_files":
                what = ", ".join(f"{d}: {'finns' if x['available'] else 'nej (' + x.get('error', '')[:30] + ')'}" for d, x in body["public_trade_files"].items())
            elif name == "bitstamp":
                first = body.get("btcusd_first_daily_bar_from_2011-09-13") or body.get("btcusd_first_daily_bar_from_start_2011")
                what = f"BTC/USD dagsstaplar från {first}" if first else "tomt svar (första provet hade fel startdatum)"
            elif name == "binance_docs":
                what = "; ".join(f"{k}: " + (f"läsbar ({x['characters']} tecken)" if x.get("readable") else f"ej läsbar ({x.get('error', '')[:30]})") for k, x in body.items())
            elif name == "binance_api":
                what = "; ".join(f"{s}: " + (f"{x['bars']} staplar" if "bars" in x else x["error"][:40]) for s, x in body["gap_fill_probe"].items())
            else:
                what = json.dumps(body, ensure_ascii=False)[:110]
            rows.append(f"| {name} | ja | {what} |")
    return "\n".join(rows)


def dated_table(binance: dict) -> str:
    rows = ["| Marknad | Underliggande | Kontrakt | Första förfall | Sista förfall | Kontrakt med saknade månader | Spot-referens (USDT) från |",
            "|---|---|---|---|---|---|---|"]
    spot = binance["spot_reference"]
    for m, label in (("um_dated_futures", "USDⓈ-M"), ("cm_dated_futures", "COIN-M")):
        for und, v in binance[m]["underlyings"].items():
            first = spot.get(und, {}).get("first_month") or "–"
            rows.append(f"| {label} | {und} | {v['contracts']} | {v['first_expiry']} | {v['last_expiry']} | "
                        f"{len(v['contracts_with_missing_months'])} | {first} |")
    return "\n".join(rows)


def liquidity_table(liq: dict) -> str:
    rows = ["| Underliggande | Kontrakt med data före 2025 | Dagsstaplar | Saknade dagar | Dagar med närmaste kontrakt | Median USD/dag | P10 USD/dag | Andel nollvolym |",
            "|---|---|---|---|---|---|---|---|"]
    for und in CM_UNDERLYINGS:
        v = liq[und]
        rows.append(f"| {und} | {v['contracts_with_data']} | {v['bars']} | {v['missing_days']} | {v['front_contract_days']} | "
                    f"{v['front_median_daily_usd_volume']:,.0f} | {v['front_p10_daily_usd_volume']:,.0f} | {v['front_share_zero_volume_days']:.1%} |".replace(",", " "))
    return "\n".join(rows)


def example_table() -> str:
    """Spot + invers COIN-M-short hållen till förfall, i mynt och USD (traderlab.basis_example)."""
    from ..basis_example import hold_to_expiry
    rows = ["| Fall | Kurs vid förfall | Mynt vid förfall | USD-värde | Avkastning på spot-kostnaden | Marginalkvot |", "|---|---|---|---|---|---|"]
    for label, x in (("10 mynt, 102 kontrakt (exakt säkring)", 10), ("7 mynt, 71 kontrakt (heltalsavrundning)", 7)):
        r = hold_to_expiry(x, 100, 102, 10, [150, 100, 50])
        for o in r["outcomes"]:
            rows.append(f"| {label} | {o.price_at_expiry:.0f} | {o.coins:.3f} | {o.usd_value:.2f} | {o.return_on_cost:.2%} | {o.margin_ratio_at_expiry:.3f} |".replace(".", ","))
    return "\n".join(rows)


def main() -> None:
    folder = Path(__file__).resolve().parents[3] / "research" / "coverage"
    reports = _load(folder, "basis-sources-*.json")
    binance = next(r["sources"]["binance"] for r in reports if "binance" in r["sources"])
    liq = json.loads(next(iter(sorted(folder.glob("basis-cm-liquidity-*.json")))).read_text(encoding="utf-8"))
    print("## Källprov\n\n" + sources_table(reports))
    print("\n## Daterade terminer hos Binance\n\n" + dated_table(binance))
    print("\n## Handelsbarhet, COIN-M (närmaste kontrakt med mer än 14 dagar kvar, volym i USD)\n\n" + liquidity_table(liq))
    print("\n## Numeriskt exempel: spot + invers short\n\n" + example_table())


if __name__ == "__main__":
    main()
