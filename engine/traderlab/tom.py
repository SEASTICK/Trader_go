"""H-0024: månadsskiftet (turn of the month) i SPY, enligt research/tom-protokoll.md (låst före koden).

Fönstret är fyra handelsdagar: `T0` (månadens sista handelsdag) och `T1`, `T2`, `T3` (de tre första i nästa månad). Strategin äger SPY från öppningen `T0`
till öppningen `T4` (fjärde handelsdagen i nästa månad) och håller annars kontanter (0 %). Dagsavkastningen för dag `t` är `open(t+1) / open(t) − 1`
(öppning-till-öppning, projektets standard: beslut på stängd stapel, fyllning vid nästa öppning). Kostnaden är 10 bp per sida, en gång vid köpet (dag `T0`)
och en gång vid försäljningen (dag `T3`, den sista hållna dagen), stress 2,5 gånger.

Mått (protokollets "Mått och beslutskriterier"): per dag `d_t = r_strategi − c · r_köp-och-behåll`, där `c` är fönsterandelen av handelsdagarna i perioden. `d_t`
summeras per kalendermånad (`D_m`). Fem kriterier ger `MORE_RESEARCH`, annars `REJECT`; ett brutet datakrav ger `OGILTIG` utan beslut.

Den här modulen innehåller bara beräkningarna och deras kontroller. Den hämtar ingen data (ingen Yahoo, inga filer), skriver inga resultat och körs inte på riktiga
SPY-kurser förrän koden är granskad och en datapreflight är gjord. Rader från 2025-01-01 och senare kapas (eller avvisas med `strict=True`) **innan** någon
beräkning, så slutprovet kan aldrig påverka ett mått.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import stats

HYPOTHESIS_ID = "H-0024"
ATTEMPTS = 24                                            # N vid registreringen
T_REQUIRED = 2.87                                        # protokollet: t ≥ 2,87 (N=24); stats.t_krav(24) = 2,865 avrundat
HOLDOUT = pd.Timestamp("2025-01-01")                     # exklusiv gräns: rader från detta datum läses aldrig
PRIMARY = (pd.Timestamp("2006-01-01"), pd.Timestamp("2024-12-31"))
SECONDARY = (pd.Timestamp("1993-02-01"), pd.Timestamp("2005-12-31"))
HALVES = ((pd.Timestamp("2006-01-01"), pd.Timestamp("2014-12-31")), (pd.Timestamp("2015-01-01"), pd.Timestamp("2024-12-31")))
SIDE_COST = 0.0010                                       # 10 bp per sida
STRESS = 2.5
WINDOW = 4                                               # T0..T3; utträdet vid öppningen T4
SHIFTS = tuple(range(-10, 11))                           # placebo-förskjutningar i handelsdagar, 0 = verkligt fönster
YEAR_DAYS = (249, 253)                                   # handelsdagar per kalenderår i primärperioden
MIN_MONTH_DAYS = 15
TRADING_DAYS = 252


class HoldoutError(Exception):
    """Data från 2025-01-01 eller senare finns i indata och `strict=True` kräver att de avvisas."""


class InvalidRun(Exception):
    """Indata kan inte tolkas (till exempel dubbletter i index). Körningen är OGILTIG."""


def clean_prices(prices: pd.DataFrame, strict: bool = False) -> tuple[pd.DataFrame, int]:
    """Kolumnerna `open` och `close` (justerade), index med datum. Kapar rader från 2025-01-01 **innan** något värde används.

    Returnerar (rensade priser, antal kapade rader). Med `strict=True` kastas `HoldoutError` om någon rad skulle kapas. Värdena på de kapade raderna läses aldrig:
    bara indexet används för att bestämma vad som kapas.
    """
    idx = pd.DatetimeIndex(prices.index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    idx = idx.normalize()
    keep = np.asarray(idx < HOLDOUT)
    n_cut = int((~keep).sum())
    if strict and n_cut:
        raise HoldoutError(f"{n_cut} rader från {HOLDOUT.date()} eller senare i indata: slutprovet läses inte")
    kept = prices.loc[keep, ["open", "close"]].copy()            # de kapade raderna rörs aldrig efter detta
    kept.index = idx[keep]
    if kept.index.has_duplicates:
        raise InvalidRun("dubbletter i datumindex")
    kept = kept.sort_index().astype(float)
    return kept, n_cut


def month_end_positions(index: pd.DatetimeIndex) -> np.ndarray:
    """Positioner `i0` för varje kalendermånads sista handelsdag `T0` som syns i serien. Den allra sista raden räknas inte (ingen följande dag att jämföra med)."""
    month = index.to_period("M")
    return np.flatnonzero(np.asarray(month[:-1] != month[1:]))


def window_cycles(index: pd.DatetimeIndex, period: tuple[pd.Timestamp, pd.Timestamp]) -> list[int]:
    """`T0`-positioner vars datum ligger i perioden och som har hela fönstret plus `T4` i serien (`i0 + 4` finns). Cykler som kräver data efter kapningen bildas inte."""
    start, end = period
    i0s = month_end_positions(index)
    return [int(i) for i in i0s if start <= index[i] <= end and i + WINDOW <= len(index) - 1]


def open_to_open(df: pd.DataFrame) -> pd.Series:
    """Dagsavkastning med etikett `t`: `open(t+1) / open(t) − 1` (hållen från öppningen `t` till öppningen `t+1`). Sista raden saknar värde."""
    return df["open"].shift(-1) / df["open"] - 1.0


def close_to_close(df: pd.DataFrame) -> pd.Series:
    """Sekundärt utförande B (marknad-vid-stängning): `close(t) / close(t−1) − 1` med etikett `t`."""
    return df["close"] / df["close"].shift(1) - 1.0


def strategy_returns(df: pd.DataFrame, cycles: list[int], shift: int = 0, side_cost: float = SIDE_COST, execution: str = "A") -> pd.Series:
    """Strategins nettodagsavkastning: 0 utanför fönstret, fönsterdagarnas avkastning med kostnad på första och sista hållna dagen.

    Fönstret för cykel `i0` med förskjutning `shift` är etiketterna `i0+shift .. i0+shift+3`. Köpet ligger i början av första dagen och försäljningen i slutet av den sista
    (så att dagsavkastningarnas produkt är exakt fönstrets nettoavkastning). A: öppning-till-öppning. B: stängning-till-stängning.
    """
    r = open_to_open(df) if execution == "A" else close_to_close(df)
    out = pd.Series(0.0, index=df.index)
    n = len(df)
    for i0 in cycles:
        s = i0 + shift
        if s < 0 or s + WINDOW > n - 1 or (execution == "B" and s < 1):
            continue
        for k in range(WINDOW):
            t = s + k
            val = r.iloc[t]
            if k == 0:
                val = (1.0 + val) * (1.0 - side_cost) - 1.0
            if k == WINDOW - 1:
                val = (1.0 + val) * (1.0 - side_cost) - 1.0
            out.iloc[t] = val
    return out


def _sharpe(x: pd.Series) -> float:
    x = x.dropna()
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(TRADING_DAYS)) if len(x) > 2 and sd > 0 else 0.0


def _period_mask(index: pd.DatetimeIndex, r: pd.Series, period) -> np.ndarray:
    return np.asarray((index >= period[0]) & (index <= period[1]) & r.notna().to_numpy())


def window_metrics(df: pd.DataFrame, period=PRIMARY, execution: str = "A", cost_mult: float = 1.0) -> dict:
    """Alla mått för en period och ett utförande utan att fatta något beslut. `df` ska redan vara rensad (`clean_prices`)."""
    r = open_to_open(df) if execution == "A" else close_to_close(df)
    cycles = window_cycles(df.index, period)
    mask = _period_mask(df.index, r, period)
    n_days = int(mask.sum())
    cost = SIDE_COST * cost_mult
    base = strategy_returns(df, cycles, 0, cost, execution)
    c = (WINDOW * len(cycles)) / n_days if n_days else 0.0                # fönsterandel av handelsdagarna, gemensam för alla förskjutningar
    d = (base - c * r)[mask]
    months = d.index.to_period("M")
    d_m = d.groupby(months).sum()
    placebo = {}
    for u in SHIFTS:
        du = (strategy_returns(df, cycles, u, cost, execution) - c * r)[mask]
        placebo[u] = float(du.mean())
    others = [v for u, v in placebo.items() if u != 0]
    halves = {}
    for name, h in zip(("first", "second"), HALVES):
        sel = (d_m.index.to_timestamp() >= h[0]) & (d_m.index.to_timestamp() <= h[1])
        halves[name] = float(d_m[sel].mean()) if sel.any() else float("nan")
    return {"execution": execution, "period": [str(period[0].date()), str(period[1].date())], "cost_mult": cost_mult, "cycles": len(cycles), "days": n_days, "window_share_c": c,
            "months": int(len(d_m)), "t_D": stats.t_stat(d_m), "mean_D_m": float(d_m.mean()) if len(d_m) else float("nan"),
            "sharpe_strategy": _sharpe(base[mask]), "sharpe_buy_and_hold": _sharpe(r[mask]),
            "placebo_mean_d": {str(u): v for u, v in placebo.items()}, "window_is_best_of_21": bool(placebo[0] > max(others)),
            "placebo_rank": int(1 + sum(v >= placebo[0] for v in others)), "halves_mean_D_m": halves}


def check_data(df: pd.DataFrame, period=PRIMARY) -> list[str]:
    """Protokollets datakrav 1 och 2 för primärperioden. Tom lista = uppfyllt. Datakrav 3 (inget slutprov) är uppfyllt av `clean_prices`."""
    reasons: list[str] = []
    sel = df[(df.index >= period[0]) & (df.index <= period[1])]
    if sel.empty:
        return ["inga rader i perioden"]
    if sel[["open", "close"]].isna().any().any():
        reasons.append("saknade värden i justerad öppning eller stängning")
    for year in range(period[0].year, period[1].year + 1):
        n = int((sel.index.year == year).sum())
        if not YEAR_DAYS[0] <= n <= YEAR_DAYS[1]:
            reasons.append(f"{year}: {n} handelsdagar (krav {YEAR_DAYS[0]}–{YEAR_DAYS[1]})")
    month_counts = pd.Series(1, index=sel.index.to_period("M")).groupby(level=0).sum()
    expected = pd.period_range(period[0], period[1], freq="M")
    for m in expected:
        if int(month_counts.get(m, 0)) < MIN_MONTH_DAYS:
            reasons.append(f"{m}: {int(month_counts.get(m, 0))} handelsdagar (krav minst {MIN_MONTH_DAYS})")
    cycles = window_cycles(df.index, period)
    if len(cycles) != len(expected) - 1:
        reasons.append(f"{len(cycles)} fullständiga cykler (krav {len(expected) - 1}: T0..T3 och T4 för varje månad utom den sista)")
    return reasons


def decide(valid: bool, criteria: dict | None) -> str:
    """`OGILTIG` om datakravet brutits (aldrig MORE_RESEARCH), annars `MORE_RESEARCH` bara om alla fem kriterier är uppfyllda, annars `REJECT`."""
    if not valid or criteria is None:
        return "OGILTIG"
    return "MORE_RESEARCH" if all(criteria.values()) else "REJECT"


def evaluate(prices: pd.DataFrame, strict: bool = False) -> dict:
    """Hela beslutet för primärperioden med utförande A. Kapar (eller avvisar) data från 2025-01-01 före all beräkning. Skriver ingenting."""
    df, n_cut = clean_prices(prices, strict=strict)
    base = {"hypothesis": HYPOTHESIS_ID, "rows_cut_holdout": n_cut, "t_required": T_REQUIRED, "attempts": ATTEMPTS}
    reasons = check_data(df)
    if reasons:
        return {**base, "valid": False, "invalid_reasons": reasons, "decision": decide(False, None),
                "note": "Datakravet i research/tom-protokoll.md är inte uppfyllt. Inget beslut, aldrig MORE_RESEARCH."}
    m = window_metrics(df, PRIMARY, "A", 1.0)
    stressed = window_metrics(df, PRIMARY, "A", STRESS)
    criteria = {"t_at_least_required": bool(m["t_D"] >= T_REQUIRED),
                "stressed_costs_positive": bool(stressed["mean_D_m"] > 0),
                "sharpe_above_buy_and_hold": bool(m["sharpe_strategy"] > m["sharpe_buy_and_hold"]),
                "window_best_of_21_placebo": bool(m["window_is_best_of_21"]),
                "stable_in_both_halves": bool(m["halves_mean_D_m"]["first"] > 0 and m["halves_mean_D_m"]["second"] > 0)}
    return {**base, "valid": True, "criteria": criteria, "decision": decide(True, criteria), "metrics": m, "stressed": {k: stressed[k] for k in ("t_D", "mean_D_m", "cost_mult")}}
