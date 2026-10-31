"""Backtest-motor.

Regler (CLAUDE.md):
- Beslut på **stängd** stapel: målpositionen för stapel t räknas med data till och med stängningen av t.
- Fyllning vid **nästa stapels öppning** (t+1). Ingen affär sker på samma pris som gav signalen.
- Avgift, spread och slippage på **varje sida**.
- Terminer: finansieringsränta betalas av den som håller positionen vid avräkningen. Likvidation
  kontrolleras mot stapelns högsta och lägsta pris (isolerad marginal).

Position anges som andel av kapitalet i [-1, 1]. Positivt = long, negativt = short.
Med hävstång L blir exponeringen L gånger positionen.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .bars import validate_schema
from .costs import CostModel


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    side: str               # "Long" eller "Short"
    size: float             # andel av kapitalet, 0..1
    equity_at_entry: float
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    gross_pnl: float = 0.0  # prisrörelse
    costs: float = 0.0      # avgift + spread + slippage, in och ut
    funding: float = 0.0    # betald (+) eller mottagen (-) finansieringsränta
    liquidated: bool = False
    bars_held: int = 0

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.costs - self.funding

    @property
    def net_return(self) -> float:
        """Nettoresultat som andel av kapitalet vid inträdet."""
        return self.net_pnl / self.equity_at_entry if self.equity_at_entry else 0.0

    @property
    def is_open(self) -> bool:
        return self.exit_time is None


@dataclass
class BacktestResult:
    equity: pd.Series                 # kapital efter varje stapel (start 1,0)
    position: pd.Series               # hållen position under varje stapel
    trades: list[Trade] = field(default_factory=list)
    total_costs: float = 0.0
    total_funding: float = 0.0
    liquidations: int = 0

    @property
    def bar_returns(self) -> pd.Series:
        prev = self.equity.shift(1).fillna(1.0)
        return self.equity / prev - 1

    @property
    def closed_trades(self) -> list[Trade]:
        return [t for t in self.trades if not t.is_open]


def _funding_by_bar(index: pd.DatetimeIndex, funding: pd.Series | None) -> np.ndarray:
    """Summerar avräkningar av finansieringsränta per stapel [open_i, open_{i+1})."""
    out = np.zeros(len(index))
    if funding is None or funding.empty:
        return out
    pos = index.searchsorted(funding.index, side="right") - 1
    for p, rate in zip(pos, funding.to_numpy(dtype=float)):
        if 0 <= p < len(index):
            out[p] += rate
    return out


def run(bars: pd.DataFrame, target: pd.Series, costs: CostModel, leverage: float = 1.0,
        maintenance_margin: float = 0.005, funding: pd.Series | None = None) -> BacktestResult:
    """Kör ett backtest.

    target: målposition per stapel, beräknad vid stängning. NaN räknas som 0. Värden klipps till [-1, 1].
    funding: finansieringsränta per avräkning (andel, till exempel 0.0001), indexerad med avräkningstid i UTC.
    """
    validate_schema(bars)
    if leverage < 1:
        raise ValueError("Hävstång måste vara minst 1.")
    target = target.reindex(bars.index).astype(float).fillna(0.0).clip(-1.0, 1.0)

    o = bars["open"].to_numpy(dtype=float)
    h = bars["high"].to_numpy(dtype=float)
    l = bars["low"].to_numpy(dtype=float)
    tgt = target.to_numpy()
    fund = _funding_by_bar(bars.index, funding)
    rate = costs.per_side
    n = len(bars)

    equity = 1.0
    eq_out = np.full(n, np.nan)
    pos_out = np.zeros(n)
    trades: list[Trade] = []
    cur: Trade | None = None
    qty = 0.0               # antal enheter (negativt = short)
    pos = 0.0
    seg_pnl = 0.0           # nettoresultat i kronor sedan inträdet (för likvidation)
    liq_lock: float | None = None
    total_costs = total_funding = 0.0
    liquidations = 0

    for i in range(n - 1):
        desired = tgt[i - 1] if i >= 1 else 0.0
        if liq_lock is not None:
            if desired == liq_lock:
                desired = 0.0
            else:
                liq_lock = None

        if desired != pos:
            if cur is not None:  # stäng vid öppningen av stapel i
                c = abs(qty) * o[i] * rate
                equity -= c
                cur.costs += c
                total_costs += c
                cur.exit_time, cur.exit_price = bars.index[i], o[i]
                cur = None
                qty = 0.0
            pos = desired
            if pos != 0.0:  # öppna vid samma öppning
                notional = abs(pos) * leverage * equity
                c = notional * rate
                equity -= c
                total_costs += c
                qty = np.sign(pos) * notional / o[i]
                cur = Trade(entry_time=bars.index[i], entry_price=o[i], side="Long" if pos > 0 else "Short",
                            size=abs(pos), equity_at_entry=equity + c, costs=c)
                trades.append(cur)
                seg_pnl = -c

        if cur is not None:
            cur.bars_held += 1
            liq_price = (cur.entry_price * (1 - 1 / leverage + maintenance_margin) if qty > 0
                         else cur.entry_price * (1 + 1 / leverage - maintenance_margin))
            hit = (qty > 0 and l[i] <= liq_price) or (qty < 0 and h[i] >= liq_price)
            if hit:
                # Isolerad marginal: hela marginalen för positionen går förlorad.
                loss_total = -cur.size * cur.equity_at_entry
                bar_pnl = loss_total - seg_pnl
                equity += bar_pnl
                cur.gross_pnl += bar_pnl
                cur.liquidated = True
                cur.exit_time, cur.exit_price = bars.index[i], liq_price
                liquidations += 1
                liq_lock = pos
                cur, qty, pos, seg_pnl = None, 0.0, 0.0, 0.0
            else:
                pnl = qty * (o[i + 1] - o[i])
                f = qty * o[i] * fund[i]   # long betalar positiv ränta, short tar emot
                equity += pnl - f
                cur.gross_pnl += pnl
                cur.funding += f
                total_funding += f
                seg_pnl += pnl - f

        eq_out[i] = equity
        pos_out[i] = pos

    idx = bars.index[: n - 1]
    return BacktestResult(equity=pd.Series(eq_out[: n - 1], index=idx, name="equity"),
                          position=pd.Series(pos_out[: n - 1], index=idx, name="position"),
                          trades=trades, total_costs=total_costs, total_funding=total_funding,
                          liquidations=liquidations)


class LookaheadError(AssertionError):
    pass


def check_no_lookahead(strategy, bars: pd.DataFrame, cutoffs: int = 6, seed: int = 0) -> None:
    """Kontrollerar att en strategi bara använder data fram till varje stapel.

    Strategin körs på hela historiken och på avklippta versioner. Signalerna fram till varje
    klippunkt måste vara identiska. Annars tittar strategin framåt.
    """
    full = strategy(bars).reindex(bars.index)
    rng = np.random.default_rng(seed)
    n = len(bars)
    points = sorted(set(rng.integers(max(2, n // 10), n - 1, cutoffs).tolist()))
    for k in points:
        part = strategy(bars.iloc[:k]).reindex(bars.index[:k])
        a, b = full.iloc[:k].to_numpy(dtype=float), part.to_numpy(dtype=float)
        same = np.isclose(a, b, equal_nan=True)
        if not same.all():
            first = int(np.argmin(same))
            raise LookaheadError(f"Signalen vid {bars.index[first]} ändras när framtida data tas bort. "
                                 "Strategin tittar framåt.")
