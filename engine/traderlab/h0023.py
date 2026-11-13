"""H-0023: kassa-och-termin på sju altcoins med Rullning B (strategimotor).

Implementerar exakt research/h0023-protokoll.md (förregistrerad, N = 23). Motorn är byggd med syntetiska tester (tests/test_h0023.py) och
**har inte körts mot historik**. `run()` kräver en uttrycklig bekräftelse och att hypotesen finns i det committade registret; ingen resultatfil skrivs annars.

Regel för regel (se också research/h0023-motor-regler.md):
* kalender och cykelfönster: `h0022_coverage.cycle_calendar(rows, "rullning_b")` och `cycle_windows`
* beslut bara med data till och med beslutsdagen `D_k`: `_decide_coin`, `basis_costs.liquidity_cap_usd`
* inträde/utträde vid 00:00 UTC `open`, separata spot- och terminspriser: `simulate`
* självfinansierande kassabok och 50 bp / 2,5×: `basis_costs.ledger_run`, `position_size`, `pre_expiry_cycle`
* markprisbaserat riskstopp: `simulate` (`basis_costs.margin_ratio`)
* datakrav som fail-closed: `InvalidRun` i `simulate`, `evaluate` (täckning och BTC-staplar)
* cykelstatistik, beta, CAGR och beslut: `evaluate`, `decide`
* inga arkiv från 2025 eller senare: `assert_before_holdout`, `h0022_coverage.DATA_END`
"""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import stats
from .basis_costs import (LEDGER_LIQUIDITY_FRACTION, LEDGER_MIN_SIZE, LEDGER_SLOTS, LEDGER_START_USD, LOCKED_FUT_TAKER,
                          LOCKED_SLIPPAGE, SPOT_FEE, STRESS, ledger_run, liquidity_cap_usd, margin_ratio, position_size, pre_expiry_cycle)
from .h0022_coverage import CONTRACT_USD, _series_name, cycle_calendar, cycle_windows, paired_observations
from .pit_universe import SEVEN
from .registry import require_registered

HYPOTHESIS = "H-0023"
RESULTS = Path("research/results")
HOLDOUT = "2025-01-01"
MMR = 0.5                    # antagen underhållsnivå (protokollet)
STOP_RATIO = 0.8             # riskstopp: marginalkvot vid dagens högsta markpris
MIN_COIN_CYCLES = 46         # av 91 möjliga (7 × 13)
MIN_CYCLES_WITH_FOUR = 10    # av 13 cykler med minst 4 handlade mynt
CASH_CAGR_LIMIT = 0.03
BETA_LIMIT = 0.2
LOCKED_ATTEMPTS = 23         # N i det frysta protokollet, oberoende av senare registerrader (H-0024 ... ändrar inte H-0023:s gräns)
LOCKED_T_REQUIRED = 3.45     # det frysta kravet på t över de 14 cyklerna (kvantilen 3,4452… avrundad enligt protokollet)
SIZE_RANGE = (9.5, 10.5)     # härledd kontraktsstorlek (USD) som krävs per serie


class InvalidRun(Exception):
    """Datakravet i protokollet är inte uppfyllt: körningen är OGILTIG (inget beslut, aldrig MORE_RESEARCH)."""


@dataclass(frozen=True)
class Costs:
    spot_fee: float = SPOT_FEE
    fut_taker: float = LOCKED_FUT_TAKER
    slippage: float = LOCKED_SLIPPAGE

    def stressed(self, k: float = STRESS) -> "Costs":
        return Costs(self.spot_fee * k, self.fut_taker * k, self.slippage * k)


@dataclass
class Panel:
    """Laddade dagsstaplar (index: UTC-midnatt). `fut`/`mark` per serie (`ADAUSD_210625`), `spot` per mynt (`ADA`), `btc` = BTCUSDT spot."""
    fut: dict[str, pd.DataFrame]
    mark: dict[str, pd.DataFrame]
    spot: dict[str, pd.DataFrame]
    btc: pd.DataFrame | None = None


@dataclass
class SimResult:
    start_capital: float
    v_final: float
    cycles: list[dict]
    stops: list[dict]
    daily: pd.Series
    traded_coin_cycles: int = 0
    windows: list[tuple[str, str]] = field(default_factory=list)


def _ts(day: str) -> pd.Timestamp:
    return pd.Timestamp(day, tz="UTC")


def _bar(df: pd.DataFrame | None, day: str):
    """Dagsstapeln med `open_time` exakt 00:00:00 UTC den dagen, annars None (en stapel stämplad 01:00 är ingen dagsstapel)."""
    if df is None or df.empty:
        return None
    ts = _ts(day)
    return df.loc[ts] if ts in df.index else None


def _traded(df: pd.DataFrame | None, day: str) -> bool:
    b = _bar(df, day)
    return b is not None and float(b["volume"]) > 0


def _px(df: pd.DataFrame | None, day: str, col: str, what: str) -> float:
    """Ett **använt** prisfält: stapeln måste finnas och värdet vara ändligt och > 0. Annars `InvalidRun` (OGILTIG), aldrig tyst platt eller NaN i beräkningen."""
    b = _bar(df, day)
    if b is None:
        raise InvalidRun(f"{what}: stapel saknas {day}")
    try:
        v = float(b[col])
    except (KeyError, TypeError, ValueError):
        raise InvalidRun(f"{what}: fältet {col} saknas eller är ogiltigt {day}") from None
    if not math.isfinite(v) or v <= 0:
        raise InvalidRun(f"{what}: {col} är inte ett ändligt positivt pris ({v}) {day}")
    return v


def _mark_bar(df: pd.DataFrame | None, day: str, what: str) -> float:
    """Markprisstapel för en hållen dag: open, high, low och close ändliga och > 0, och high/low förenliga med de andra fälten. Returnerar high."""
    o, hi, lo, cl = (_px(df, day, c, what) for c in ("open", "high", "low", "close"))
    if hi < max(o, cl, lo) or lo > min(o, cl, hi):
        raise InvalidRun(f"{what}: markprisets high/low är inte förenliga med open/close ({o}, {hi}, {lo}, {cl}) {day}")
    return hi


def _days(a: str, b: str) -> list[str]:
    d, out, end = pd.Timestamp(a), [], pd.Timestamp(b)
    while d <= end:
        out.append(d.date().isoformat())
        d += pd.Timedelta(days=1)
    return out


def _next(day: str, n: int = 1) -> str:
    return (pd.Timestamp(day) + pd.Timedelta(days=n)).date().isoformat()


def assert_before_holdout(panel: Panel) -> None:
    """Inga staplar från 2025-01-01 eller senare får finnas i panelen (slutprovet läses aldrig)."""
    for group in (panel.fut, panel.mark, panel.spot):
        for name, df in group.items():
            if df is not None and not df.empty and df.index.max() >= _ts(HOLDOUT):
                raise InvalidRun(f"{name}: innehåller staplar från slutprovet ({HOLDOUT} eller senare)")
    if panel.btc is not None and not panel.btc.empty and panel.btc.index.max() >= _ts(HOLDOUT):
        raise InvalidRun("BTCUSDT: innehåller staplar från slutprovet")


def _volumes(df: pd.DataFrame | None) -> dict[str, float]:
    if df is None or df.empty:
        return {}
    return {d.date().isoformat(): float(v) for d, v in df["volume"].items() if d == d.normalize()}


def _decide_coin(panel: Panel, cycle: dict, coin: str, sizes: dict, *, fraction: float = LEDGER_LIQUIDITY_FRACTION) -> tuple[bool, str, float]:
    """Valbar på beslutsdagen? Använder **bara data till och med beslutsdagen** (dagen före fyllningen): universum (`valid_coins`), seriens och spotens
    verifierade handelsstapel beslutsdagen, 20 handelsdagars volym, kontraktsstorlek. Fyllnings- och utträdesdagens staplar läses aldrig här.
    Returnerar (valbar, orsak, likviditetstak i USD)."""
    series = _series_name(coin, cycle["expiry"])
    d = cycle["decision"]
    if coin not in cycle["valid_coins"]:
        return False, "ej i universum (ingen daterad annons eller ej handlad)", 0.0
    fut, spot = panel.fut.get(series), panel.spot.get(coin)
    if not _traded(fut, d):
        return False, "ingen verifierad terminsstapel med volym beslutsdagen", 0.0
    if not _traded(spot, d):
        return False, "ingen verifierad spotstapel med volym beslutsdagen", 0.0
    size_med = (sizes.get(series) or {}).get("median")
    if size_med is None or not (SIZE_RANGE[0] <= size_med <= SIZE_RANGE[1]):
        return False, "kontraktsstorlek utanför 9,5–10,5 USD", 0.0
    cap = liquidity_cap_usd(_volumes(fut), pd.Timestamp(cycle["fill"]).date(), fraction=fraction)
    if cap is None:
        return False, "färre än 20 handelsdagar före beslutsdagen", 0.0
    return True, "", cap


def _fill_prices(panel: Panel, coin: str, series: str, cycle: dict) -> dict:
    """Priser och dagskontroller för en **redan beslutad** position. Varje brist är `InvalidRun` (OGILTIG), aldrig dold som platt."""
    f, x, held = cycle["fill"], cycle["exit"], _days(cycle["fill"], _next(cycle["exit"], -1))
    fut, spot, mark = panel.fut.get(series), panel.spot.get(coin), panel.mark.get(series)
    for label, df in (("terminen", fut), ("spoten", spot)):
        for day in (f, cycle["exit"]):
            if not _traded(df, day):
                raise InvalidRun(f"{coin} {series}: saknad stapel eller nollvolym för {label} på fyllningsdagen {day} (beslutad position)")
    for day in _days(f, cycle["exit"]):                 # alla öppningar som används: fyllning, nästa öppning varje dag (stopp, dagsvärde) och utträde
        _px(fut, day, "open", f"{coin} {series} termin")
        _px(spot, day, "open", f"{coin} spot")
    for day in held:
        _mark_bar(mark, day, f"{coin} {series} markpris")
    return {"spot0": _px(spot, f, "open", f"{coin} spot"), "fut0": _px(fut, f, "open", f"{coin} {series} termin"),
            "spot_exit": _px(spot, x, "open", f"{coin} spot"), "fut_exit": _px(fut, x, "open", f"{coin} {series} termin"), "held": held}


def _check_cycle(c: dict) -> None:
    """Kalenderns invarianter: fyllning = beslutsdag + 1 dag (nästa 00:00 UTC) och utträde efter fyllning. Annars är kalendern inte Rullning B."""
    if _next(c["decision"]) != c["fill"] or not (c["fill"] < c["exit"]):
        raise ValueError(f"cykel {c['cycle']}: beslut {c['decision']}, fyllning {c['fill']}, utträde {c['exit']} följer inte protokollet")


def simulate(panel: Panel, cycles: list[dict], sizes: dict, *, costs: Costs | None = None, stop_ratio: float = STOP_RATIO, mmr: float = MMR,
             start_capital: float = LEDGER_START_USD, slots: int = LEDGER_SLOTS, min_size: float = LEDGER_MIN_SIZE) -> SimResult:
    """Kör kassaboken genom alla cykler. Kastar `InvalidRun` vid varje brist i data för en beslutad position."""
    costs = costs or Costs()
    assert_before_holdout(panel)
    for c in cycles:
        _check_cycle(c)
    v, records, stops, traded_total = start_capital, [], [], 0
    daily_points: dict[str, float] = {}
    for c in cycles:
        infos = {coin: _decide_coin(panel, c, coin, sizes) for coin in SEVEN}
        sized = {coin: position_size(v, slots=slots, valid=infos[coin][0], cap=infos[coin][2], min_size=min_size) for coin in SEVEN}
        slot_list, pos_meta = [], []
        for coin in SEVEN:
            series, size = _series_name(coin, c["expiry"]), sized[coin]
            if size <= 0:
                slot_list.append({"valid": False, "cap": 0.0, "spot0": 1.0, "fut0": 1.0, "fut_exit": 1.0, "spot_exit": 1.0, "contract_usd": CONTRACT_USD})
                pos_meta.append(None)
                continue
            px = _fill_prices(panel, coin, series, c)
            base = pre_expiry_cycle(capital_usd=size, spot0=px["spot0"], fut0=px["fut0"], fut_exit=px["fut_exit"], spot_exit=px["spot_exit"],
                                    contract_usd=CONTRACT_USD, spot_fee=costs.spot_fee, fut_taker=costs.fut_taker, slippage=costs.slippage)
            stop_day, exit_day = None, c["exit"]
            for day in px["held"]:
                ratio = margin_ratio(margin_coins=base.margin_coins, contracts=base.contracts, contract_usd=CONTRACT_USD, entry=px["fut0"],
                                     mark=_mark_bar(panel.mark[series], day, f"{coin} {series} markpris"), mmr=mmr)
                if ratio >= stop_ratio:
                    stop_day, exit_day = day, _next(day)
                    stops.append({"cycle": c["cycle"], "coin": coin, "series": series, "day": day, "ratio": ratio, "exit_day": exit_day})
                    break
            if stop_day is not None:      # stopp: båda benen stängs vid nästa öppning med full kostnad, myntet är platt resten av cykeln
                px["fut_exit"] = float(_bar(panel.fut[series], exit_day)["open"])
                px["spot_exit"] = float(_bar(panel.spot[coin], exit_day)["open"])
            slot_list.append({"valid": True, "cap": infos[coin][2], "spot0": px["spot0"], "fut0": px["fut0"], "fut_exit": px["fut_exit"],
                              "spot_exit": px["spot_exit"], "contract_usd": CONTRACT_USD})
            pos_meta.append({"coin": coin, "series": series, "exit_day": exit_day, "stopped": stop_day is not None, "px": px, "margin_coins": base.margin_coins})
        led = ledger_run(cycles=[slot_list], start_capital=v, slots=slots, min_size=min_size, spot_fee=costs.spot_fee, fut_taker=costs.fut_taker,
                         slippage=costs.slippage)["cycles"][0]
        positions = []
        for coin, meta, pos in zip(SEVEN, pos_meta, led["positions"]):
            if meta is None:
                assert pos["size"] == 0.0
                continue
            assert abs(pos["size"] - sized[coin]) < 1e-9, "storleken ska vara densamma i motorn och kassaboken"
            px = meta["px"]
            positions.append({"coin": coin, "series": meta["series"], "size": pos["size"], "contracts": pos["contracts"], "usd_end": pos["usd_end"],
                              "ret": pos["ret"], "stopped": meta["stopped"], "exit_day": meta["exit_day"],
                              "entry_basis": px["fut0"] / px["spot0"] - 1, "exit_basis": px["fut_exit"] / px["spot_exit"] - 1})
        traded_total += len(positions)
        # dagsvärde (öppning till öppning): positioner marknadsvärderas, kontanter är oförändrade, efter utträdet kontanter
        cash_rest = v - sum(p["size"] for p in positions)
        end_day = _next(c["exit"], 0)
        for day in _days(c["fill"], c["exit"]):
            total = cash_rest
            for meta, p in ((m, q) for m in pos_meta if m for q in positions if q["coin"] == m["coin"]):
                if day >= meta["exit_day"]:
                    total += p["usd_end"]
                else:
                    series, coin = meta["series"], meta["coin"]
                    fut_now, spot_now = float(_bar(panel.fut[series], day)["open"]), float(_bar(panel.spot[coin], day)["open"])
                    coins_now = meta["margin_coins"] + p["contracts"] * CONTRACT_USD * (1 / fut_now - 1 / meta["px"]["fut0"])
                    total += coins_now * spot_now
            daily_points[day] = total
        daily_points[end_day] = led["v_end"]
        records.append({"cycle": c["cycle"], "expiry": c["expiry"], "decision": c["decision"], "fill": c["fill"], "exit": c["exit"], "flat": c["flat"],
                        "v_start": v, "v_end": led["v_end"], "r": led["v_end"] / v - 1, "invested": led["invested"], "cash_idle": led["cash_idle"],
                        "positions": positions, "not_traded": {coin: (infos[coin][1] or "under minsta storlek (tak eller kassa)") for coin in SEVEN if sized[coin] <= 0}})
        v = led["v_end"]
    windows = cycle_windows(cycles)
    daily = _daily_series(daily_points, records, windows, start_capital)
    return SimResult(start_capital, v, records, stops, daily, traded_total, windows)


def _daily_series(points: dict[str, float], records: list[dict], windows: list[tuple[str, str]], start_capital: float) -> pd.Series:
    """Portföljvärdet varje kalenderdag från första inträdet till sista utträdet. Kontanter mellan cyklerna är oförändrade (ingen ränta)."""
    if not records:
        return pd.Series(dtype=float)
    first, last = records[0]["fill"], records[-1]["exit"]
    out, cur, per_cycle = {}, start_capital, {r["fill"]: r for r in records}
    for day in _days(first, last):
        if day in per_cycle and day not in points:
            cur = per_cycle[day]["v_start"]
        if day in points:
            cur = points[day]
        out[day] = cur
    return pd.Series(out, dtype=float)


def decide(criteria: dict[str, bool]) -> str:
    """`MORE_RESEARCH` om **alla** kriterier gäller, annars `REJECT`. (OGILTIG avgörs före, av datakraven.)"""
    return "MORE_RESEARCH" if all(criteria.values()) else "REJECT"


def t_required(attempts: int, n_cycles: int) -> float:
    """Kravet: max(Bonferroni för N försök, Student-t-kvantilen med n−1 frihetsgrader för p = 0,05/N). N = 23 och n = 14 ger 3,4452."""
    return max(stats.t_krav(attempts), float(sps.t.ppf(1 - 0.05 / attempts, n_cycles - 1)))


def cycle_t(r: list[float]) -> float:
    """t över cykelavkastningarna: medelvärde / (std / √n), n−1 frihetsgrader."""
    n, mean = len(r), statistics.fmean(r)
    sd = statistics.stdev(r) if n > 1 else 0.0
    if sd == 0:
        return math.inf if mean > 0 else (-math.inf if mean < 0 else 0.0)
    return mean / (sd / math.sqrt(n))


def evaluate(ordinary: SimResult, stressed: SimResult, panel: Panel, cycles: list[dict], *, seed: int = 0, n_boot: int = 10000,
             min_coin_cycles: int = MIN_COIN_CYCLES, min_cycles_four: int = MIN_CYCLES_WITH_FOUR) -> dict:
    """Datakrav (fail-closed) och därefter cykelstatistik och beslut. En ogiltig körning ger **inga prestandasiffror**, bara orsaker och täckningsdiagnos."""
    reasons: list[str] = []
    non_flat = [c for c in cycles if not c["flat"]]
    per_cycle = {r["cycle"]: len(r["positions"]) for r in ordinary.cycles}
    with_four = sum(1 for c in non_flat if per_cycle.get(c["cycle"], 0) >= 4)
    possible = 7 * len(non_flat)
    if ordinary.traded_coin_cycles < min_coin_cycles:       # standard = protokollets 46 av 91; parametern finns bara för syntetiska tester
        reasons.append(f"Datakrav 4: {ordinary.traded_coin_cycles} handlade mynt-cykler av {possible} (krav minst {min_coin_cycles})")
    if with_four < min_cycles_four:                          # standard = protokollets 10 av 13
        reasons.append(f"Datakrav 4: {with_four} av {len(non_flat)} cykler med minst 4 handlade mynt (krav minst {min_cycles_four})")
    windows = ordinary.windows
    for day in sorted({d for w in windows for d in w}):
        if not _traded(panel.btc, day):
            reasons.append(f"Datakrav 8: ingen verifierad BTCUSDT-spotstapel exakt 00:00 UTC med volym {day}")
        else:
            try:
                _px(panel.btc, day, "open", "BTCUSDT spot")
            except InvalidRun as exc:
                reasons.append(f"Datakrav 8: {exc}")
    base = {"hypothesis_id": HYPOTHESIS, "attempts": LOCKED_ATTEMPTS, "n_cycles": len(cycles),
            "coverage_diagnostic": {"traded_coin_cycles": ordinary.traded_coin_cycles, "possible_coin_cycles": possible, "cycles_with_four": with_four,
                                    "non_flat_cycles": len(non_flat)}}
    if reasons:
        return {**base, "valid": False, "decision": "OGILTIG", "invalid_reasons": reasons,
                "note": "Datakravet i research/h0023-protokoll.md är inte uppfyllt. Inget beslut, aldrig MORE_RESEARCH. Inga prestandasiffror redovisas."}
    r = [rec["r"] for rec in ordinary.cycles]
    n = len(r)
    t, t_req = cycle_t(r), LOCKED_T_REQUIRED          # frysta gränsen; aldrig dagens register och aldrig den oavrundade kvantilen
    port_values = {}
    for rec in ordinary.cycles:
        port_values[rec["fill"]] = rec["v_start"]
    port_values[windows[-1][1]] = ordinary.cycles[-1]["v_end"]          # T_14 = X_14 (ingen F_15)
    btc_open = {d: float(_bar(panel.btc, d)["open"]) for w in windows for d in w}
    pairs = paired_observations(windows, port_values, btc_open)
    pr, br = np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])
    beta = float(np.cov(pr, br, ddof=1)[0, 1] / np.var(br, ddof=1)) if np.var(br, ddof=1) > 0 else math.nan
    span_days = (pd.Timestamp(windows[-1][1]) - pd.Timestamp(ordinary.cycles[0]["fill"])).days
    cagr = (ordinary.v_final / ordinary.start_capital) ** (365 / span_days) - 1 if ordinary.v_final > 0 else -1.0
    stressed_total = stressed.v_final / stressed.start_capital - 1
    criteria = {"t_over_cycles_at_least_required": bool(t >= t_req), "stressed_costs_positive": bool(stressed_total > 0),
                "abs_beta_btc_at_most_limit": bool(not math.isnan(beta) and abs(beta) <= BETA_LIMIT), "cagr_above_cash": bool(cagr > CASH_CAGR_LIMIT),
                "no_risk_stop": bool(len(ordinary.stops) == 0)}
    rng = np.random.default_rng(seed)
    boots = [float(np.mean(rng.choice(r, size=n, replace=True))) for _ in range(n_boot)]
    daily_ret = ordinary.daily.pct_change().dropna()
    return {**base, "valid": True, "decision": decide(criteria), "criteria": criteria, "meets_all_criteria": all(criteria.values()),
            "t_over_cycles": t, "t_required": t_req, "t_bonferroni": stats.t_krav(LOCKED_ATTEMPTS), "t_quantile_unrounded": t_required(LOCKED_ATTEMPTS, n), "beta_btc": beta, "cagr": cagr, "span_days": span_days,
            "stressed_total_return": stressed_total, "total_return": ordinary.v_final / ordinary.start_capital - 1,
            "cycle_returns": r, "positive_cycles": int(sum(1 for x in r if x > 0)), "mean_cycle_return": statistics.fmean(r),
            "mean_cycle_return_ci": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "t_daily_nw_not_decisive": float(stats.newey_west_t(daily_ret)) if len(daily_ret) > 5 else None,
            "risk_stops": ordinary.stops, "positions": [p for rec in ordinary.cycles for p in ({**q, "cycle": rec["cycle"]} for q in rec["positions"])]}


def load_panel(repo: Path, cycles: list[dict]) -> tuple[Panel, dict]:
    """Läser staplarna för de serier och mynt som kalendern behöver. Alla läsare skickar periodgränser (aldrig 2025 eller senare) och luckor fylls
    bara med verifierade dagsfiler (checksumma, manifest). Saknade filer ger None (då blir mynt-cykeln platt eller, för en beslutad position, OGILTIG)."""
    from . import h0022_coverage as hc
    from .data import gapcheck
    data_dir = repo / "data"
    manifest, mark_manifest = gapcheck.load_manifest(repo), hc.load_mark_manifest(repo)
    sizes = {r["contract"]: r for r in json.loads((repo / "research" / "universe" / "coinm-implied-contract-size.json").read_text(encoding="utf-8"))["series"]}
    fut, mark, spot = {}, {}, {}
    for c in cycles:
        for coin in c["valid_coins"]:
            sym = _series_name(coin, c["expiry"])
            fut[sym], _ = hc._load("cm", sym, data_dir, manifest, gap_fill=True)
            mark[sym], _ = hc._load("cm-mark", sym, data_dir, mark_manifest, gap_fill=True)
            if coin not in spot:
                spot[coin], _ = hc._load("spot", f"{coin}USDT", data_dir, manifest, gap_fill=True)
    btc, _ = hc._load("spot", "BTCUSDT", data_dir, manifest, gap_fill=True)
    return Panel(fut, mark, spot, btc), {k: {"median": v.get("median")} for k, v in sizes.items()}


def run(repo: Path, *, confirm_registered_run: bool = False) -> Path:
    """Den registrerade körningen. Kräver (1) uttrycklig bekräftelse, (2) att H-0023 finns i det committade registret. Skriver en resultatfil."""
    if not confirm_registered_run:
        raise RuntimeError("Körningen kräver --confirm-registered-run: H-0023 ska bara köras en gång, efter granskning av motorn.")
    reg = require_registered(HYPOTHESIS, repo)
    rows = json.loads((repo / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
    cycles = cycle_calendar(rows, "rullning_b")
    panel, sizes = load_panel(repo, cycles)
    base = {"hypothesis_id": HYPOTHESIS, "registry_commit": reg.registry_commit, "phase": "rullning_b", "track": "C",
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        ordinary = simulate(panel, cycles, sizes)
        stressed = simulate(panel, cycles, sizes, costs=Costs().stressed())
        out = {**base, **evaluate(ordinary, stressed, panel, cycles), "registry_attempts_now": reg.attempts}
    except InvalidRun as exc:
        out = {**base, "valid": False, "decision": "OGILTIG", "invalid_reasons": [str(exc)],
               "note": "Datakravet i research/h0023-protokoll.md är inte uppfyllt. Inget beslut, aldrig MORE_RESEARCH. Inga prestandasiffror redovisas."}
    return _save(repo, out)


def _save(repo: Path, out: dict) -> Path:
    folder = repo / RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{HYPOTHESIS}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    return path


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="H-0023 (Rullning B). Körs inte mot historik före granskning.")
    ap.add_argument("--confirm-registered-run", action="store_true")
    a = ap.parse_args()
    print(run(Path(__file__).resolve().parents[2], confirm_registered_run=a.confirm_registered_run))


if __name__ == "__main__":
    main()
