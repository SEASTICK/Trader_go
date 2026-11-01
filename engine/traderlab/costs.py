"""Kostnader per affär. Alltid med i ett test (CLAUDE.md)."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class CostModel:
    """Alla värden i baspunkter (1 bp = 0,01 %).

    fee_bps: avgift per sida. spread_bps: hela spreaden (halva betalas per sida).
    slippage_bps: glidning per sida.
    """
    fee_bps: float = 10.0
    spread_bps: float = 2.0
    slippage_bps: float = 5.0

    @property
    def per_side(self) -> float:
        """Kostnad som andel av handlat belopp, per sida."""
        return (self.fee_bps + self.spread_bps / 2 + self.slippage_bps) / 10_000

    def stressed(self, factor: float = 2.5) -> "CostModel":
        """Stresstest av kostnader (granska-backtest: ungefär 2,5 gånger normalt)."""
        return replace(self, fee_bps=self.fee_bps * factor, spread_bps=self.spread_bps * factor,
                       slippage_bps=self.slippage_bps * factor)


ZERO = CostModel(0.0, 0.0, 0.0)
