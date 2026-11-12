"""Litet numeriskt exempel: spot + invers COIN-M-short hållen till förfall, i mynt och i USD.

Syftet är att visa vad säkringen faktiskt gör, så att rapporten inte påstår mer än matematiken ger. Ingen historisk data,
inga avgifter (de är inte verifierade) och ingen optimering. Förenklingar: terminspriset konvergerar till spot vid
förfall (F1 = S1), kontrakt är heltal, och avräkningspriset är lika med spot.

Invers kontrakt: ett kontrakt är `contract_usd` USD. Resultatet betalas i mynt.
  short, i mynt:  n · contract_usd · (1/F1 − 1/F0)      (kursfall ger fler mynt, kursuppgång ger färre)
Att äga X mynt och sälja n kontrakt (n · contract_usd = X · F0) låser alltså **USD-värdet** X · F0, inte antalet mynt.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Outcome:
    price_at_expiry: float
    coins: float
    usd_value: float
    return_on_cost: float
    margin_ratio_at_expiry: float   # equity i mynt / positionens värde i mynt (1,0 = exakt 1× täckt)


def hold_to_expiry(x_coins: float, spot0: float, fut0: float, contract_usd: float, expiry_prices: list[float],
                   contracts: int | None = None) -> dict:
    """Kassa-och-termin: köp `x_coins` spot (som också är marginalen), sälj `contracts` kontrakt till `fut0`.
    Utan `contracts` används det antal heltalskontrakt som ligger närmast `x_coins · fut0` i USD."""
    n = contracts if contracts is not None else round(x_coins * fut0 / contract_usd)
    notional = n * contract_usd
    cost = x_coins * spot0
    out = []
    for p in expiry_prices:
        coins = x_coins + notional * (1 / p - 1 / fut0)
        usd = coins * p
        position_coins = notional / p
        out.append(Outcome(p, coins, usd, usd / cost - 1, coins / position_coins if position_coins else float("inf")))
    return {"contracts": n, "notional_usd": notional, "cost_usd": cost, "target_usd": x_coins * fut0, "outcomes": out}
