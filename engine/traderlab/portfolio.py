"""Portföljmotor för många instrument samtidigt (tvärsnitt).

Regler (CLAUDE.md):
- Vikterna för dag t beslutas vid stängningen av t och fylls vid öppningen av t+1.
- Mellan ombalanseringar ligger positionerna kvar och deras värde driver med priset.
- Kostnad på varje omsatt belopp (per sida). Finansieringsränta betalas av long och tas emot av short per avräkning.
- Ett instrument som saknar pris en dag (avnoterat) stängs på sin sista tillgängliga öppning.

opens: DataFrame (dag × instrument) med öppningspriser. weights: DataFrame med målvikter på
ombalanseringsdagar och NaN-rader (eller saknade dagar) däremellan. En rad som bara har 0 stänger allt.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .costs import CostModel


@dataclass
class PortfolioResult:
    equity: pd.Series         # kapital efter varje dag (start 1,0), indexerat på dagen innehavet hölls
    weights: pd.DataFrame     # faktiska vikter vid dagens början (efter eventuell ombalansering)
    turnover: pd.Series       # omsatt belopp per dag, i andel av kapitalet
    total_costs: float
    total_funding: float      # betald (+) eller mottagen (-), i andel av startkapitalet

    @property
    def bar_returns(self) -> pd.Series:
        return self.equity / self.equity.shift(1).fillna(1.0) - 1


def funding_per_day(index: pd.DatetimeIndex, funding: dict[str, pd.Series], columns) -> pd.DataFrame:
    """Summan av avräknade räntor i [öppning dag t, öppning dag t+1) per instrument."""
    out = pd.DataFrame(0.0, index=index, columns=columns)
    for sym, f in funding.items():
        if sym not in out.columns or f is None or f.empty:
            continue
        pos = index.searchsorted(f.index, side="right") - 1
        ok = (pos >= 0) & (pos < len(index))
        agg = pd.Series(f.to_numpy(dtype=float)[ok]).groupby(pos[ok]).sum()
        out.iloc[agg.index.to_numpy(), out.columns.get_loc(sym)] = agg.to_numpy()
    return out


def run(opens: pd.DataFrame, weights: pd.DataFrame, costs: CostModel,
        funding: dict[str, pd.Series] | None = None) -> PortfolioResult:
    opens = opens.sort_index()
    cols = list(opens.columns)
    idx = opens.index
    target = weights.reindex(index=idx, columns=cols)
    fund = funding_per_day(idx, funding or {}, cols).to_numpy()
    o = opens.to_numpy(dtype=float)
    tgt = target.to_numpy(dtype=float)
    has_row = ~np.all(np.isnan(tgt), axis=1)
    rate = costs.per_side
    n = len(idx)
    k = len(cols)
    notional = np.zeros(k)          # positionernas värde i kapitalenheter (negativt = short)
    equity = 1.0
    eq_out = np.full(n, np.nan)
    w_out = np.zeros((n, k))
    turn_out = np.zeros(n)
    tc = tf = 0.0
    for i in range(n - 1):
        # Beslut vid stängningen av dag i-1 fylls vid öppningen av dag i.
        traded = np.zeros(k)
        if i >= 1 and has_row[i - 1]:
            desired = np.nan_to_num(tgt[i - 1], nan=0.0) * equity
            desired[~np.isfinite(o[i])] = 0.0
            traded = np.abs(desired - notional)
            notional = desired
        # Saknat pris i dag: stäng på senaste kända öppning (positionen avvecklades när datan tog slut).
        gone = ~np.isfinite(o[i]) & (notional != 0)
        if gone.any():
            traded[gone] += np.abs(notional[gone])
            notional[gone] = 0.0
        c = traded.sum() * rate
        equity -= c
        tc += c
        turn_out[i] = traded.sum() / max(equity + c, 1e-12)
        w_out[i] = notional / equity if equity > 0 else 0.0
        # Avkastning från öppning i till öppning i+1. Saknas nästa öppning används ingen rörelse (stängs i morgon).
        r = np.where(np.isfinite(o[i]) & np.isfinite(o[i + 1]), o[i + 1] / o[i] - 1, 0.0)
        f = float(np.dot(notional, np.nan_to_num(fund[i])))
        pnl = float(np.dot(notional, r))
        equity += pnl - f
        tf += f
        notional = notional * (1 + r)
        if equity <= 0:   # konkurs: kontot är slut och kan inte återuppstå
            equity, notional = 0.0, np.zeros(k)
            tgt[i:] = 0.0
            has_row[i:] = False
        eq_out[i] = equity
    sl = slice(0, n - 1)
    return PortfolioResult(pd.Series(eq_out[sl], index=idx[sl], name="equity"),
                           pd.DataFrame(w_out[sl], index=idx[sl], columns=cols),
                           pd.Series(turn_out[sl], index=idx[sl], name="turnover"), tc, tf)


def funding_gaps(held: pd.DataFrame, funding: dict[str, pd.Series]) -> dict[str, int]:
    """Antal dagar per mynt där en position hölls men ingen finansieringsränta finns registrerad.

    Saknad ränta får inte bli gratis ränta (granskningsfynd P1): motorerna avbryter om det finns luckor.
    """
    out = {}
    for sym in held.columns:
        days = held.index[held[sym].abs() > 0]
        if len(days) == 0:
            continue
        f = funding.get(sym)
        have = set() if f is None or f.empty else set(f.index.floor("1D"))
        missing = sum(1 for d in days if d.floor("1D") not in have)
        if missing:
            out[sym] = missing
    return out


def check_no_lookahead(signal, panel: dict, cut_points: list[int], known_until: dict | None = None) -> None:
    """Vikterna fram till en dag får inte ändras när data efter den dagen tas bort.

    Dagsstaplar indexeras på öppningstid, så stapeln för dag t (till och med dess stängning) behålls. Händelser
    med egen tidsstämpel (till exempel finansieringsränta) behålls fram till dagens stängning: ange
    known_until={namn: pd.Timedelta(days=1)} för dem.
    """
    known_until = known_until or {}
    full = signal(panel)
    days = next(iter(panel.values())).index
    for k in cut_points:
        cut = days[k]
        part = signal({name: df[df.index < cut + known_until[name]] if name in known_until else df[df.index <= cut]
                       for name, df in panel.items()})
        a = full[full.index <= cut].fillna(-9).to_numpy()
        b = part.reindex(full.index[full.index <= cut]).fillna(-9).to_numpy()
        if not np.allclose(a, b):
            raise AssertionError(f"Vikterna före {cut} ändras när framtida data tas bort.")
