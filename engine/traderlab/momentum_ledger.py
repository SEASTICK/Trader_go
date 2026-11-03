"""H-0017 ledger och mekanisk fyllning, mom-ledger/1.0.0 (research/h0017-protokoll.md §6, D17, D19).

Endast kontot, storlekslösaren, kostnadsbokföringen och fyllningen av en redan given avsikt. Inga beslut, band,
funding, marginal, dagsreset, riskstopp eller eventloop här; de kommer i senare delar av leverans C.

Konto: kontantekvivalent C och signerade enheter q. Nettokapital E = C + q * M, där M är markpris. Kontraktspris P
används bara för fyllningen. C är inte bokstavlig kassa och kan bli negativ för en long.

En affär Δq = q_new - q_old vid P bokförs en gång: C <- C - Δq * P - c * P * |Δq|. Spread och slippage ingår i c och
läggs aldrig också på priset. En vändning är ett Δq, inte en stängning plus en öppning.

Storlek (§6): q_new med q_new * M / E_trade = w, där E_trade = E + Δq(M - P) - cP|Δq| är kapitalet direkt efter
affären (fas after_trade). Funding efter affären (E_post) ingår inte här och ändrar inte E_trade.

Reduce-only (D17): en riskavsikt fyller lösarens q* bara om |q*| <= |q_old| och q* inte byter tecken. Annars behålls
q_old utan affär och kostnad, och fyllningen märks risk_reduce_only_hold. w = 0 ger alltid full stängning.

Redovisning: genomsnittligt inträdespris och realiserat resultat följer partialminskning och vändning utan fiktiva
avslut. Identitet: C = C0 + realized - costs - q * avg_price (avg_price = 0 när platt). Kapitalledgern C/q är källan.

Inga avrundningar, ingen klippning, inget epsilonkapital. Felaktig indata ger LedgerError.
"""
from __future__ import annotations

import math
import numbers
from dataclasses import dataclass, replace

VERSION = "mom-ledger/1.0.0"
COST_NORMAL = (10 + 2 / 2 + 5) / 10_000      # 0,0016 per sida
COST_STRESS = 2.5 * COST_NORMAL               # 0,0040 per sida

NORMAL = "normal"
RISK = "risk"


class LedgerError(ValueError):
    """Ogiltig indata eller ingen konsekvent lösning. Ingen tyst klippning."""


def _finite(**values) -> None:
    for name, v in values.items():
        if not isinstance(v, numbers.Real) or isinstance(v, bool) or not math.isfinite(v):
            raise LedgerError(f"{name} måste vara ett ändligt tal, fick {v!r}.")


def _prices(P: float, M: float) -> None:
    _finite(P=P, M=M)
    if P <= 0 or M <= 0:
        raise LedgerError(f"Priser måste vara > 0 (P={P}, M={M}).")


def _cost_rate(c: float) -> None:
    _finite(c=c)
    if c < 0:
        raise LedgerError(f"Kostnaden c måste vara >= 0, fick {c}.")


def _weight(w: float) -> None:
    _finite(w=w)
    if abs(w) > 1:
        raise LedgerError(f"Målvikten måste ligga i [-1, 1], fick {w}.")


@dataclass(frozen=True)
class Account:
    C: float                       # kontantekvivalent inkl. insättning, realiserat, kostnader
    q: float = 0.0                 # signerade enheter
    deposit: float = 0.0           # C0, för avstämning
    avg_price: float = 0.0         # genomsnittligt inträdespris för öppen position, 0 när platt
    realized: float = 0.0          # summerat realiserat resultat före kostnader
    costs: float = 0.0             # summerade handelskostnader

    @classmethod
    def open(cls, capital: float) -> "Account":
        _finite(capital=capital)
        if capital <= 0:
            raise LedgerError(f"Startkapital måste vara > 0, fick {capital}.")
        return cls(C=float(capital), deposit=float(capital))

    def equity(self, M: float) -> float:
        _finite(M=M)
        if M <= 0:
            raise LedgerError(f"Markpris måste vara > 0, fick {M}.")
        return self.C + self.q * M

    def weight(self, M: float) -> float:
        E = self.equity(M)
        if E <= 0:
            raise LedgerError(f"Nettokapitalet är {E}; vikt saknas.")
        return self.q * M / E

    def reconciliation_gap(self) -> float:
        """C minus C0 + realized - costs - q * avg_price. Ska vara 0 inom flyttalstolerans."""
        return self.C - (self.deposit + self.realized - self.costs - self.q * self.avg_price)


@dataclass(frozen=True)
class Fill:
    kind: str                      # NORMAL eller RISK
    w: float                       # fryst målvikt
    P: float
    M: float
    c: float
    q_old: float
    q_star: float                  # lösarens exakta enheter
    q_new: float                   # faktiskt innehav efter fyllningen
    dq: float
    cost: float
    E_before: float                # E vid M före affären
    E_trade: float                 # E vid M direkt efter affären, före eventuell funding
    weight_trade: float
    realized_delta: float
    risk_reduce_only_hold: bool
    phase: str = "after_trade"
    version: str = VERSION

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def solve_units(E: float, q_old: float, P: float, M: float, w: float, c: float = COST_NORMAL) -> float:
    """Exakt q_new enligt §6 med q_new * M = w * E_trade. Grenen väljs från den kostnadsfria lösningen."""
    _finite(E=E, q_old=q_old)
    _prices(P, M)
    _weight(w)
    _cost_rate(c)
    if E <= 0:
        raise LedgerError(f"Kapital före affär måste vara > 0, fick {E}.")
    if w == 0:
        return 0.0
    q0 = w * (E - q_old * (M - P)) / (M - w * (M - P))
    if q0 == q_old:
        return q_old
    buy = q0 > q_old
    k = M - P - c * P if buy else M - P + c * P
    den = M - w * k
    if not den > 0:
        raise LedgerError("Ingen lösning: nämnaren är inte positiv.")
    q = w * (E - q_old * k) / den
    if not math.isfinite(q) or (q > q_old) != buy or q * w < 0:
        raise LedgerError("Ingen konsekvent lösning för vald köp-/säljgren.")
    return q


def _book(acct: Account, q_new: float, P: float, c: float) -> tuple[Account, float, float]:
    """Bokför Δq vid P en gång. Returnerar nytt konto, kostnad och realiserat i denna affär."""
    q_old, dq = acct.q, q_new - acct.q
    if dq == 0:
        return acct, 0.0, 0.0
    cost = c * P * abs(dq)
    realized, avg = 0.0, acct.avg_price
    if q_old != 0 and (q_new == 0 or (q_new > 0) != (q_old > 0)):
        realized = q_old * (P - acct.avg_price)          # hela gamla positionen stängs
        avg = P if q_new != 0 else 0.0                  # vändning öppnar resten vid P
    elif q_old != 0 and abs(q_new) < abs(q_old):
        realized = (q_old - q_new) * (P - acct.avg_price)  # bara sålda enheter realiseras
    else:
        avg = (abs(q_old) * acct.avg_price + abs(dq) * P) / abs(q_new)
    new = replace(acct, C=acct.C - dq * P - cost, q=q_new, avg_price=avg,
                  realized=acct.realized + realized, costs=acct.costs + cost)
    return new, cost, realized


def _fill(acct: Account, kind: str, w: float, q_star: float, q_new: float, P: float, M: float, c: float,
          E_before: float, hold: bool) -> tuple[Account, Fill]:
    new, cost, realized = _book(acct, q_new, P, c)
    E_trade = new.equity(M)
    if not E_trade > 0:
        raise LedgerError(f"Nettokapital efter affär är {E_trade}; insolvens döljs inte.")
    return new, Fill(kind=kind, w=w, P=P, M=M, c=c, q_old=acct.q, q_star=q_star, q_new=q_new, dq=q_new - acct.q,
                     cost=cost, E_before=E_before, E_trade=E_trade, weight_trade=q_new * M / E_trade,
                     realized_delta=realized, risk_reduce_only_hold=hold)


def fill_normal(acct: Account, w: float, P: float, M: float, c: float = COST_NORMAL) -> tuple[Account, Fill]:
    """Normalavsikt: exakt målvikt w, köp eller sälj beroende på läget vid öppningen."""
    E = acct.equity(M)
    q_star = solve_units(E, acct.q, P, M, w, c)
    return _fill(acct, NORMAL, w, q_star, q_star, P, M, c, E, False)


def fill_risk(acct: Account, w: float, P: float, M: float, c: float = COST_NORMAL) -> tuple[Account, Fill]:
    """Riskavsikt, reduce-only: ökar aldrig |q|. Underskrids målet redan behålls q och fyllningen loggas hold."""
    E = acct.equity(M)
    q_star = solve_units(E, acct.q, P, M, w, c)
    hold = abs(q_star) > abs(acct.q) or q_star * acct.q < 0
    return _fill(acct, RISK, w, q_star, acct.q if hold else q_star, P, M, c, E, hold)
