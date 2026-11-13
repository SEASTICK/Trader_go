"""Snabb dagsbacktest för portföljvikter. Beslut på stängningen av dag t, fyllning vid öppningen dag t+1, hålls till öppningen t+2.

Kostnader per sida (avgift + glidning) på omsättningen, finansieringsränta för perpar, hävstångstak. Inga framtida data i beräkningen.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import Panel, period_slice

COST_PER_SIDE = 0.0010          # 0,05 % avgift + 5 bp glidning, samma antagande som övriga projektet
LEV_CAP = 3.0


class CoverageInvalid(Exception):
    """En exponerad position saknar nödvändig data (nästa öppningskurs eller finansiering). Utvärderingen är ogiltig: saknad data blir aldrig tyst noll."""


COVERAGE_TOL = 0.01             # högst 1 % av bruttoexponeringen får vila på okänd data, annars är utvärderingen OGILTIG (bestämd i förväg)
FUNDING_PENALTY = 0.003         # okänd finansiering debiteras 0,3 % per dag och exponeringsenhet, alltid till nackdel (ungefär en extrem dag)
MISSING_PRICE_LOSS = -1.0       # okänt utträdespris utan något senare pris (avnotering, utgången leverans) räknas som totalförlust på positionens vikt, en gång (konservativt, aldrig noll)
EXIT_FILL_LIMIT = 5             # saknas öppning t+2 men en senare öppning finns inom 5 dagar värderas positionen mot den (en datalucka, inte okänt)


@dataclass
class BT:
    ret: pd.Series              # nettoavkastning per dag (index = dagen positionen hålls)
    gross: pd.Series            # före kostnader och finansiering
    cost: pd.Series
    funding: pd.Series
    turnover: pd.Series
    exposure: pd.Series         # bruttoexponering per dag
    coverage: dict | None = None


def coverage(panel: Panel, W: pd.DataFrame) -> dict:
    """Hur stor del av bruttoexponeringen vilar på okänd data?
    (a) *blockerad*: ingen öppningskurs t+1, så positionen kan inte öppnas eller hållas (kontraktet handlas inte vid fyllningen),
    (b) *okänt utträde*: öppning t+1 finns men t+2 saknas och inget senare pris finns inom `EXIT_FILL_LIMIT` dagar (avnotering, utgången leverans),
    (b2) *luckfyllt*: t+2 saknas men ett senare pris finns, så positionen värderas mot det (rapporteras, men räknas inte som okänt),
    (c) *okänd finansiering* under hållperioden.
    De två sista raderna ingår inte (de har ingen framtid att värderas mot)."""
    W = W.reindex(index=panel.close.index, columns=panel.close.columns).fillna(0.0).iloc[:-2]
    A = W.abs()
    px1 = panel.open.shift(-1).iloc[:-2].isna()
    fwd_na = panel.fwd().iloc[:-2].isna()
    exit_next = panel.open.bfill(limit=EXIT_FILL_LIMIT).shift(-2).iloc[:-2].notna()          # ett senare pris inom gränsen finns
    fk = panel.funding_known.shift(-1, fill_value=False).iloc[:-2].astype(bool)
    total = float(A.values.sum())
    blocked = float(A.where(px1, 0.0).values.sum())
    gap_filled = float(A.where(~px1 & fwd_na & exit_next, 0.0).values.sum())
    exit_unknown = float(A.where(~px1 & fwd_na & ~exit_next, 0.0).values.sum())
    uf = float(A.where(~fk, 0.0).values.sum())
    anyu = float(A.where(px1 | (fwd_na & ~exit_next) | ~fk, 0.0).values.sum())
    sh = lambda x: x / total if total else 0.0
    return {"gross_exposure": total, "blocked_exposure": blocked, "gap_filled_exposure": gap_filled, "unknown_exit_exposure": exit_unknown, "unknown_funding_exposure": uf,
            "blocked_share": sh(blocked), "gap_filled_share": sh(gap_filled), "unknown_exit_share": sh(exit_unknown), "missing_price_share": sh(blocked + exit_unknown), "unknown_funding_share": sh(uf),
            "any_unknown_share": sh(anyu), "symbol_days_missing_price": int((((A > 0) & (px1 | fwd_na)).values.sum())), "symbol_days_unknown_funding": int(((A > 0) & ~fk).values.sum())}


def run(panel: Panel, W: pd.DataFrame, *, cost: float = COST_PER_SIDE, funding: bool = True, lev_cap: float = LEV_CAP, delay: int = 0, strict: bool = True,
        penalize: bool = True) -> BT:
    """`delay` > 0 fördröjer utförandet med så många dagar (kostnadsagentens utförandetest).
    `strict`: okänd data (se `coverage`) över `COVERAGE_TOL` av bruttoexponeringen gör utvärderingen ogiltig (`CoverageInvalid`). Under toleransen **debiteras** okänd data
    konservativt (`MISSING_PRICE_LOSS`, `FUNDING_PENALTY`) i stället för att tyst bli noll. `penalize=False` återger den gamla motorn (bara för auditen av R001-R004)."""
    W = W.reindex(index=panel.close.index, columns=panel.close.columns).fillna(0.0)
    cov = coverage(panel, W.shift(delay).fillna(0.0) if delay else W)
    if strict and (cov["missing_price_share"] > COVERAGE_TOL or (funding and cov["unknown_funding_share"] > COVERAGE_TOL)):
        raise CoverageInvalid(f"okänd data under exponerad position: saknad öppningskurs {cov['missing_price_share']:.2%}, okänd finansiering {cov['unknown_funding_share']:.2%} "
                              f"av bruttoexponeringen (gräns {COVERAGE_TOL:.1%})")
    if delay:
        W = W.shift(delay).fillna(0.0)
    g = W.abs().sum(axis=1)
    scale = (lev_cap / g).clip(upper=1.0).where(g > 0, 1.0)
    W = W.mul(scale, axis=0)
    fwd = panel.fwd()
    if penalize:                                         # lucka i utträdesdagens pris: värdera mot nästa tillgängliga öppning (högst EXIT_FILL_LIMIT dagar), annars okänt utträde
        fwd = panel.open.bfill(limit=EXIT_FILL_LIMIT).shift(-2) / panel.open.shift(-1) - 1.0
    if penalize:                                         # körbarhetsregel: ett kontrakt utan öppningskurs vid fyllningen (t+1) kan inte öppnas eller hållas: vikten blir noll och mäts i `coverage`
        W = W.mask(panel.open.shift(-1).isna(), 0.0)
    held = W.abs() > 0
    inside = pd.Series(np.arange(len(W)) < len(W) - 2, index=W.index)   # de två sista raderna saknar framtid i panelen (ingen datalucka), de straffas inte
    miss = fwd.isna() & held & inside.to_numpy()[:, None]            # öppning t+1 finns men t+2 saknas: utträdespriset är okänt
    pnl = (W * fwd.fillna(0.0)).sum(axis=1)
    if penalize:                                         # okänt utträde: en FÖRLUST på positionens storlek (oavsett long eller short), aldrig en vinst och aldrig noll
        pnl = pnl + (W.abs().where(miss, 0.0).sum(axis=1) * MISSING_PRICE_LOSS)
    turn = W.diff().abs().sum(axis=1)
    turn.iloc[0] = W.iloc[0].abs().sum()
    c = turn * cost
    if funding:
        unk = (~panel.funding_known.shift(-1, fill_value=False).astype(bool)) & held
        f = (W * panel.fwd_funding().where(~unk, 0.0)).sum(axis=1) + ((W.abs().where(unk, 0.0).sum(axis=1) * FUNDING_PENALTY) if penalize else 0.0)
    else:
        f = pd.Series(0.0, index=W.index)
    net = pnl - c - f
    # avkastning på dag t+1 (positionen hålls dag t+1): flytta ett steg
    sh = lambda s: s.shift(1)
    return BT(sh(net), sh(pnl), sh(c), sh(f), sh(turn), sh(W.abs().sum(axis=1)), cov)


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    n = len(r)
    if n < 20 or r.std() == 0:
        return {"n": n, "sharpe": 0.0, "ann_ret": 0.0, "ann_vol": 0.0, "max_dd": 0.0, "hit": 0.0, "cvar5": 0.0, "skew": 0.0, "total": 0.0}
    eq = (1 + r).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    k = np.sort(r.values)[: max(1, int(0.05 * n))]
    return {"n": n, "sharpe": float(r.mean() / r.std() * np.sqrt(365)), "ann_ret": float(r.mean() * 365), "ann_vol": float(r.std() * np.sqrt(365)),
            "max_dd": dd, "hit": float((r > 0).mean()), "cvar5": float(k.mean()), "skew": float(r.skew()), "total": float(eq.iloc[-1] - 1)}


def by_period(r: pd.Series, names=("disc", "valid", "final")) -> dict:
    return {p: metrics(r[period_slice(r.index, p)]) for p in names}


def sharpe(r: pd.Series) -> float:
    return metrics(r)["sharpe"]


def baselines(panel: Panel) -> dict[str, pd.Series]:
    """Enkla jämförelser: köp-och-behåll BTC, lika viktad korg av de likvidaste, och 30-dagars tvärsnittsmomentum."""
    idx = panel.close.index
    btc = pd.DataFrame(0.0, index=idx, columns=panel.close.columns)
    if "BTCUSDT" in btc.columns:
        btc["BTCUSDT"] = 1.0
    uni = panel.universe(20)
    ew = uni.astype(float).div(uni.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return {"bh_btc": run(panel, btc, funding=True).ret, "ew_basket": run(panel, ew, funding=True).ret}
