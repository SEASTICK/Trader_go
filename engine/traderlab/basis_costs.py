"""Kostnads- och likvidationsunderlag för COIN-M kassa-och-termin (H-0022), som körbar specifikation med syntetiska tester.

Inga marknadspriser används här och ingen avkastning har räknats på historik. Modulen gör två saker:
1. `implied_contract_size`: härleder kontraktsstorleken i USD ur kline-kolumnerna (kontrakt och mynt) för en serie, utan priser
   som urvalskriterium. COIN-M-klines har volym i *kontrakt* (kolumn 5) och i *mynt* (kolumn 7); kontraktsstorlek ≈ mynt · pris / kontrakt.
2. Kostnadsbudget och mynt-bokföring för en hållen-till-förfall-cykel (`hold_cycle`) som räknar hela kapitalet och coin-marginalen:
   spotbenet köps för kapitalet, mynten ligger som marginal, det inversa kontraktet säljs, och allt (avgifter, PnL, restmynt) bokförs i mynt.
"""
from __future__ import annotations

import csv
import io
import math
import statistics
import zipfile
from dataclasses import dataclass
from pathlib import Path

# ------------------------------------------------------------------ daterade avgifter (vanlig användare, ingen BNB-rabatt)
# Källa: Binance-meddelanden (se research/universe/h0022-kostnad-antaganden.md). Maker används inte: konservativt tas alltid taker.
COINM_FEES = (
    # (gäller från, maker, taker, källa)
    ("2020-07-17", 0.00015, 0.00040, "meddelande 2020-07-10 (ny avgiftsstruktur från 2020-07-17, siffror ej i texten) och Before-kolumnen i meddelandet 2021-04-22"),
    ("2021-04-27", 0.00010, 0.00050, "Notice on Binance Futures Coin-Margined Futures Fee Adjustments, 2021-04-22"),
    ("2023-09-26", 0.00020, 0.00050, "Binance Futures Updates Trading Fees for COIN-M Futures Contracts, 2023-09-18"),
)
SPOT_FEE = 0.001            # 0,100 % maker och taker, allmän nivå (2017-08-24, 2018-07-19); 25 % BNB-rabatt används inte
LOCKED_FUT_TAKER = 0.0005   # högsta daterade taker (0,050 %) för hela perioden: konservativt över 0,040 % före 2021-04-27
LOCKED_SLIPPAGE = 0.0005    # 5 bp per ben: ett märkt ANTAGANDE (orderbokshistorik saknas), inte en mätning
STRESS = 2.5


def fut_taker_on(day: str) -> float:
    """Daterad takeravgift för COIN-M (regular) en given dag; före första kända datum: första kända nivån."""
    rate = COINM_FEES[0][2]
    for since, _maker, taker, _src in COINM_FEES:
        if day >= since:
            rate = taker
    return rate


def round_trip_cost(*, spot_fee: float = SPOT_FEE, fut_taker: float = LOCKED_FUT_TAKER, slippage: float = LOCKED_SLIPPAGE,
                    stress: float = 1.0, exit: str = "pre_expiry") -> dict:
    """Total kostnad (andel av positionens värde) för en cykel: spot-köp, termin-sälj, terminsutträde och spot-sälj.

    `exit="pre_expiry"` (förslaget): terminen stängs 7 dagar före förfall med takeravgift **och** glidning. `exit="settlement"`:
    hållen till förfall, då avräkningen kostar bara takeravgift (ingen glidning, men avräkningsfönstret är oklart)."""
    if exit not in ("pre_expiry", "settlement"):
        raise ValueError(exit)
    legs = {"spot_buy": spot_fee + slippage, "future_sell": fut_taker + slippage,
            "future_exit": fut_taker + (slippage if exit == "pre_expiry" else 0.0), "spot_sell": spot_fee + slippage}
    total = sum(legs.values()) * stress
    return {"legs": {k: v * stress for k, v in legs.items()}, "total": total, "total_bp": total * 1e4}


# ------------------------------------------------------------------ kontraktsstorlek ur data
def implied_contract_size(zip_paths: list[Path]) -> dict:
    """Härleder kontraktsstorleken i USD per dagsstapel: mynt-volym · (high+low+close)/3 / kontrakt-volym. Bara staplar med volym > 0."""
    sizes: list[float] = []
    for path in zip_paths:
        with zipfile.ZipFile(path) as zf:
            raw = zf.read(zf.namelist()[0]).decode("utf-8")
        for row in csv.reader(io.StringIO(raw)):
            if not row or not row[0].strip().lstrip("-").isdigit():
                continue
            contracts, coins = float(row[5]), float(row[7])
            if contracts > 0 and coins > 0:
                typical = (float(row[2]) + float(row[3]) + float(row[4])) / 3
                sizes.append(coins * typical / contracts)
    if not sizes:
        return {"bars": 0}
    return {"bars": len(sizes), "median": statistics.median(sizes), "p05": sorted(sizes)[int(0.05 * (len(sizes) - 1))],
            "p95": sorted(sizes)[int(0.95 * (len(sizes) - 1))], "min": min(sizes), "max": max(sizes)}


# ------------------------------------------------------------------ mynt-bokföring för en hållen-till-förfall-cykel
@dataclass
class Cycle:
    capital_usd: float
    coins_bought: float
    contracts: int
    margin_coins: float          # myntsaldo i terminsplånboken efter öppningsavgift
    leftover_usd: float          # kapital som inte blev mynt (spotavgift ingår inte här)
    effective_leverage: float    # notional i mynt / margin i mynt vid öppning, mätt vid terminspriset
    coins_end: float             # myntsaldo efter PnL och avräkningsavgift
    usd_end: float               # slutvärde i USD efter spot-sälj med avgift och glidning
    ret: float


def hold_cycle(*, capital_usd: float, spot0: float, fut0: float, settle: float, spot_end: float, contract_usd: float,
               spot_fee: float = SPOT_FEE, fut_taker: float = LOCKED_FUT_TAKER, slippage: float = LOCKED_SLIPPAGE) -> Cycle:
    """En cykel: köp mynt för **hela** kapitalet, lägg dem som marginal, sälj heltalskontrakt till terminspriset, håll till förfall.

    Inversa kontrakt: PnL(mynt) för short = n · storlek · (1/avräkning − 1/in). Alla avgifter dras i mynt (futures) eller USD (spot).
    Kontraktsantalet avrundas **ned** (aldrig mer exponering än marginalen), så effektiv hävstång ≤ 1."""
    coins = capital_usd / (spot0 * (1 + spot_fee + slippage))
    # notional N måste rymmas av marginalen *efter* öppningsavgiften: N ≤ (coins − N/fut0·f)·fut0  ⇒  N ≤ coins·fut0/(1+f)
    contracts = math.floor(coins * fut0 / (contract_usd * (1 + fut_taker + slippage)))
    notional_usd = contracts * contract_usd
    open_fee_coins = notional_usd / fut0 * (fut_taker + slippage)
    margin = coins - open_fee_coins
    pnl_coins = notional_usd * (1 / settle - 1 / fut0)          # short: negativ när avräkningen ligger över ingångskursen
    settle_fee = notional_usd / settle * fut_taker
    coins_end = margin + pnl_coins - settle_fee
    usd_end = coins_end * spot_end * (1 - spot_fee - slippage)
    return Cycle(capital_usd, coins, contracts, margin, capital_usd - coins * spot0 * (1 + spot_fee + slippage),
                 (notional_usd / fut0) / margin if margin else math.inf, coins_end, usd_end, usd_end / capital_usd - 1)


def margin_ratio(*, margin_coins: float, contracts: int, contract_usd: float, entry: float, mark: float, mmr: float) -> float:
    """Marginalkvot (underhållsmarginal / marginalsaldo) för en kort inverst position vid markpriset `mark`.
    Likvidation när kvoten når 1. Orealiserad PnL räknas på markpris (Binance FAQ), underhållsmarginal = notional i mynt · MMR."""
    notional_usd = contracts * contract_usd
    equity = margin_coins + notional_usd * (1 / mark - 1 / entry)
    maintenance = notional_usd / mark * mmr
    return math.inf if equity <= 0 else maintenance / equity


def main() -> None:
    """Skriver research/universe/coinm-implied-contract-size.json: kontraktsstorlek härledd ur dagsdatan (före 2025) per serie."""
    import json
    repo = Path(__file__).resolve().parents[2]
    series = json.loads((repo / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
    rows = []
    for r in series:
        if not (r["in_target_seven"] and r.get("data_checked") and r.get("bars")):
            continue
        name = f"{r['underlying']}USD_{r['expiry'][2:4]}{r['expiry'][5:7]}{r['expiry'][8:]}"
        folder = repo / "data" / "raw" / "binance" / "cm" / name / "1d"
        zips = [p for p in sorted(folder.glob("*.zip")) if p.name[-11:-4] < "2025-01"]
        rows.append({"contract": name, "underlying": r["underlying"], "expiry": r["expiry"], **implied_contract_size(zips)})
    out = repo / "research" / "universe" / "coinm-implied-contract-size.json"
    out.write_text(json.dumps({"kind": "coinm-implied-contract-size", "method": "mynt-volym · (high+low+close)/3 / kontrakt-volym, dagsstaplar med volym > 0, före 2025",
                               "note": "Datahärledd kontroll, inte en Binance-källa. Ingen avkastning eller basis beräknad.", "series": rows},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    off = [r for r in rows if r.get("bars") and not (9.5 <= r["median"] <= 10.5)]
    print(json.dumps({"series": len(rows), "median_outside_9.5_10.5": [r["contract"] for r in off]}))


if __name__ == "__main__":
    main()
