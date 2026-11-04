"""H-0017 konservativ intrastapel-drawdown-bound, mom-bound/1.0.0 (research/h0017-protokoll.md §10.2, §13.1–§13.2,
D21; C6-01-tillägget docs/momentum-C6-01-edwins-beslut.md).

En separat hypotetisk kapitalserie för huvudmodellen (long/platt, ett scenario), byggd ur samma obrutna
process_bar-förlopp som §10.1-loggen (momentum_event.RunLog). Bounden styr ingenting: den matar aldrig close-peak,
day_start, stopp, avsikter, fyllningar eller marginalbeslut, och den bokför ingen funding.

Punkter per stapel, med egen löpande peak från startkapitalet 100 000 (peak uppdateras före varje drawdown):
  levande utan träff:  open (E(mark_open) på ingående C/q före A-funding och fyllning), trade (E_trade), post (E_post;
                       i A lika med E_trade), high, low, close (faktisk ledger efter alla mellanhändelser).
                       high: C_high = C_post − Σmin(p_i, 0), low: C_low = C_post − Σmax(p_i, 0), med q efter öppningen
                       och p_i stapelns mellanevent (positiv betalas). High före low (ogynnsam ordning för long).
  terminalstapeln:     open, trade, post och terminalt kapital, som räknas en gång. Inga extremer med den stängda
                       positionen.
  intrastapelträff:    open, trade, post, high, low enligt samma regel med alla olösta mellanevent enbart hypotetiskt
                       (H1), oklippta även under noll (I1), sedan likvidationsnollan (P1).
  gapträff:            open och, om A-funding bokfördes, prövningskapitalet efter den (G1, oklippta), sedan
                       likvidationsnollan; inga trade/post/high/low.
  likviderat konto:    en absorberande nolla per stapel, vid terminal terminalpunkten 0.
Punktordningen är hypotetisk och påstår ingen tidsordning mellan träff, extremer och funding. Med negativt kapital
gör en högre peak drawdown mindre negativ; bounden påstås inte vara strängast under −100 %.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, replace

import pandas as pd

from . import momentum_event as ev
from . import stats
from .momentum_ledger import _out

VERSION = "mom-bound/1.0.0"
TOL = 1e-12                       # relativ tolerans för korskontroll mot eventlagrets marginalunderlag

_ISSUING = contextvars.ContextVar("mom_bound_issuing", default=False)


class BoundError(ev.EventError):
    """Fel i boundlagret. Inget ändras."""


@contextmanager
def _issuing():
    token = _ISSUING.set(True)
    try:
        yield
    finally:
        _ISSUING.reset(token)


@dataclass(frozen=True)
class BoundPoint:
    phase: str                    # start, open, gap_check, trade, post, high, low, close, terminal, liquidation, absorbed
    bar_open: pd.Timestamp | None
    time: object                  # pd.Timestamp eller momentum_event.UNKNOWN_TIME
    account_key: str
    scenario: str
    C: float                      # kontant i punktens (hypotetiska) bas
    q: float
    E: float
    M: float | None = None
    source: str | None = None
    hypothetical_funding: float = 0.0   # summa mellanfunding som bara ingår hypotetiskt i punkten (positiv betald)
    peak: float = 0.0
    drawdown: float = 0.0
    versions: tuple = (VERSION, ev.VERSION, ev.PROTOCOL)


def _point(r, phase, C, q, E, time, M=None, source=None, hypo=0.0) -> dict:
    s = r.state.scenario
    return dict(phase=phase, bar_open=r.bar_open, time=time, account_key=s.account_key, scenario=s.label,
                C=float(C), q=float(q), E=_out(f"E för {phase}", E), M=M, source=source, hypothetical_funding=hypo)


def _one(r, phase):
    hits = [t for t in r.trace if t.phase == phase]
    if len(hits) != 1:
        raise BoundError(f"Stapeln {r.bar_open}: väntade exakt en {phase}-post i eventspåret, fick {len(hits)}.")
    return hits[0]


def bar_points(r: ev.BarResult) -> tuple[dict, ...]:
    """Boundpunkterna för en stapel, utan peak och drawdown (de beror på förloppet och sätts av BoundLog)."""
    if not isinstance(r, ev.BarResult):
        raise BoundError("bar_points kräver ett BarResult från momentum_event.process_bar.")
    b, T = r.bar, r.bar_open
    if r.prev_state.margin_state.liquidated:                      # absorberande noll
        return (_point(r, "terminal" if r.state.terminated else "absorbed", 0.0, 0.0, 0.0, T),)
    gap = _one(r, "gap")
    out = [_point(r, "open", gap.C, gap.q, gap.E, T, b.mark_open, "mark_open")]
    liq = [t for t in r.trace if t.phase == "liquidation"]
    if liq and liq[0].source == "mark_open":                      # gapträff (G1): bara steg som faktiskt skett
        if any(t.phase == "funding_A" for t in r.trace):          # prövningskapital efter A-funding, oklippt
            rec = r.state.margin_state.record
            out.append(_point(r, "gap_check", rec.C_old, rec.q_old, rec.E_before, T, rec.m, rec.price_source))
        out.append(_point(r, "liquidation", 0.0, 0.0, 0.0, T))
        if r.state.terminated:
            out.append(_point(r, "terminal", 0.0, 0.0, 0.0, T))
        return tuple(out)
    trade = _one(r, "after_trade")
    post = _one(r, "after_funding_B") if r.state.scenario.order == "B" else trade
    out.append(_point(r, "trade", trade.C, trade.q, trade.E, T, b.mark_open, "mark_open"))
    out.append(_point(r, "post", post.C, post.q, post.E, T, b.mark_open, "mark_open"))
    if r.state.terminated:                                        # terminal: stängd position, terminalpunkt en gång
        out.append(_point(r, "terminal", r.state.account.C, r.state.account.q, r.terminal_point[1], T))
        return tuple(out)
    hit = bool(liq)
    phases = (ev.UNRESOLVED,) if hit else ("funding_interior",)
    p = [t.funding for t in r.trace if t.phase in phases]
    paid = _out("betald mellanfunding", sum(x for x in p if x > 0))
    received = _out("mottagen mellanfunding", sum(-x for x in p if x < 0))
    C_post, q_open = post.C, post.q
    C_high, C_low = _out("C_high", C_post + received), _out("C_low", C_post - paid)
    E_high, E_low = C_high + q_open * b.mark_high, C_low + q_open * b.mark_low
    if r.margin_basis is not None and abs(E_low - r.margin_basis[1]) > TOL * max(1.0, abs(E_low), abs(C_low)):
        raise BoundError(f"Stapeln {T}: boundens low {E_low} skiljer sig från marginalunderlaget {r.margin_basis[1]}.")
    out.append(_point(r, "high", C_high, q_open, E_high, ev.UNKNOWN_TIME, b.mark_high, "mark_high", -received))
    out.append(_point(r, "low", C_low, q_open, E_low, ev.UNKNOWN_TIME, b.mark_low, "mark_low", paid))
    if hit:                                                       # P1: nollan efter low, oklippta värden (I1)
        out.append(_point(r, "liquidation", 0.0, 0.0, 0.0, ev.UNKNOWN_TIME))
    else:
        a = r.state.account
        out.append(_point(r, "close", a.C, a.q, a.equity(b.mark_close), T, b.mark_close, "mark_close"))
    return tuple(out)


@dataclass(frozen=True)
class BoundLog:
    """§10.2-serien för ett obrutet förlopp från startläget, bunden via momentum_event.RunLog (samma kedjekontroll:
    ingen dubblett, lucka, bakåtsteg, främmande förlopp eller tillägg efter terminal). Skapas bara av begin/add."""
    run: ev.RunLog
    points: tuple = ()
    peak: float = ev.INITIAL
    max_dd_bound: float = 0.0      # negativ (eller 0); kan vara < −1 vid oklippt negativt kapital (C6-01, I1/G1)

    def __post_init__(self) -> None:
        if not _ISSUING.get():
            raise BoundError("BoundLog skapas bara av BoundLog.begin och add; replace eller direkt konstruktion avvisas.")

    @classmethod
    def begin(cls, state: ev.EngineState) -> "BoundLog":
        run = ev.RunLog.begin(state)                              # kräver exakt startläge
        s = state.scenario
        start = BoundPoint("start", None, ev.START, s.account_key, s.label, ev.INITIAL, 0.0, ev.INITIAL,
                           peak=ev.INITIAL, drawdown=0.0)
        with _issuing():
            return cls(run=run, points=(start,))

    def add(self, result: ev.BarResult) -> "BoundLog":
        run = self.run.add(result)                                # kedjekontroll först; inget ändras vid fel
        peak, mdd, pts = self.peak, self.max_dd_bound, []
        for kw in bar_points(result):
            peak = max(peak, kw["E"])
            dd = _out("drawdown", kw["E"] / peak - 1.0)
            mdd = min(mdd, dd)
            pts.append(BoundPoint(**kw, peak=peak, drawdown=dd))
        with _issuing():
            return replace(self, run=run, points=self.points + tuple(pts), peak=peak, max_dd_bound=mdd)

    @property
    def max_dd_bound_mag(self) -> float:
        return -self.max_dd_bound

    @property
    def max_dd_close(self) -> float:
        """§10.1 via den oförändrade stats.max_drawdown, på closeserien som redan börjar med 100 000."""
        return stats.max_drawdown([cp[2] for cp in self.run.close_points])

    @property
    def max_dd_close_mag(self) -> float:
        return -self.max_dd_close
