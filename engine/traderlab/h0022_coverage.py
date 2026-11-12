"""Datatäckningsgranskning för H-0022 (före strategimotor och körning).

Kontrollerar bara att nödvändiga staplar **finns** och går att verifiera: terminens last price, markpris och spot, samma `open_time` för båda
benen, volym > 0 på fyllningar, 20 handelsdagars volym före beslutsdagen och nästa öppning efter varje hållen dag. Ingen basis, avkastning,
t-statistik eller beta beräknas, inga låsta parametrar ändras och inga arkiv från 2025-01-01 eller senare öppnas.

Täckningen är **möjlig** täckning: kapital och likviditetstak beror på framtida PnL (kassabokens V), så rapporten visar bara vad som går att
förhandskontrollera, inte vilka positioner som faktiskt tas.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import statistics
from pathlib import Path

import pandas as pd

from .basis_costs import entry_fill_utc, exit_day, roll_decision_day
from .data import binance, gapcheck
from .pit_universe import SEVEN, universe_at

DATA_START = pd.Timestamp("2021-03-01", tz="UTC")
DATA_END = pd.Timestamp("2024-10-01", tz="UTC")      # exklusiv gräns: inget arkiv från 2024-10 eller senare öppnas
FIRST_DECISION = "2021-03-26"
LAST_EXPIRY = "2024-09-27"
MIN_SIZE_USD = 10_000.0
LIQUIDITY_FRACTION = 0.02
MIN_MEDIAN20_USD = MIN_SIZE_USD / LIQUIDITY_FRACTION          # 500 000: minsta median som släpper in en position på 10 000 USD
START_SIZE_MEDIAN20_USD = (140_000.0 / 7) / LIQUIDITY_FRACTION      # 1 000 000: medianen som släpper in startstorleken 20 000 USD
CONTRACT_USD = 10.0


def _day(ts) -> str:
    return pd.Timestamp(ts).date().isoformat()


def cycle_calendar(rows: list[dict]) -> list[dict]:
    """Cykelkalendern ur protokollet (research/h0022-protokoll.md), genererad ur universumtabellen: inga priser."""
    expiries = [e for e in sorted({r["expiry"] for r in rows if r["in_target_seven"]}) if "2021-06-25" <= e <= LAST_EXPIRY]
    cycles, prev_exit = [], None
    for k, e in enumerate(expiries, 1):
        expiry = dt.date.fromisoformat(e)
        x = exit_day(expiry)
        if prev_exit is None:
            decision = dt.date.fromisoformat(FIRST_DECISION)
            fill = entry_fill_utc(decision).date()
        else:
            fill = prev_exit
            decision = roll_decision_day(fill)
        valid = sorted({r["underlying"] for r in universe_at(rows, decision.isoformat()) if r["expiry"] == e})
        cycles.append({"cycle": k, "expiry": e, "decision": decision.isoformat(), "fill": fill.isoformat(), "exit": x.isoformat(),
                       "valid_coins": valid, "flat": not valid})
        prev_exit = x
    return cycles


def _days(a: str, b: str) -> list[str]:
    """Kalenderdagar från a till och med b (ISO)."""
    d, out = dt.date.fromisoformat(a), []
    while d <= dt.date.fromisoformat(b):
        out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def required_days(cycle: dict) -> dict:
    """Vilka dagar som måste ha staplar för en position i cykeln."""
    fill, x = cycle["fill"], cycle["exit"]
    held = _days(fill, (dt.date.fromisoformat(x) - dt.timedelta(days=1)).isoformat())
    return {"decision": cycle["decision"], "fill": fill, "exit": x, "held": held,
            "next_open": _days((dt.date.fromisoformat(fill) + dt.timedelta(days=1)).isoformat(), x)}


def _exact_midnight(df: pd.DataFrame | None) -> pd.DatetimeIndex:
    """Bara staplar med `open_time` exakt 00:00:00 UTC räknas som en dagsstapel. En stapel stämplad t.ex. 01:00 hör inte till dagens öppning."""
    if df is None or df.empty:
        return pd.DatetimeIndex([], tz="UTC")
    return df.index[df.index == df.index.normalize()]


def _index_days(df: pd.DataFrame | None) -> set[str]:
    return {d.date().isoformat() for d in _exact_midnight(df)}


def _off_midnight(df: pd.DataFrame | None, days: list[str]) -> list[str]:
    """Dagar i `days` som har en stapel vars `open_time` inte är exakt 00:00 UTC (diagnostik)."""
    if df is None or df.empty:
        return []
    off = {d.date().isoformat() for d in df.index if d != d.normalize()}
    return [t for t in days if t in off]


def _traded_days(df: pd.DataFrame | None) -> set[str]:
    if df is None or df.empty:
        return set()
    sel = df[(df["volume"] > 0) & (df.index == df.index.normalize())]
    return {d.date().isoformat() for d in sel.index}


def audit_coin_cycle(*, cycle: dict, fut: pd.DataFrame | None, mark: pd.DataFrame | None, spot: pd.DataFrame | None,
                     implied_size_median: float | None) -> dict:
    """Granskar ett mynt i en cykel mot de data som finns. Rena funktioner av staplarna, utan priser i något beslut."""
    req = required_days(cycle)
    fut_days, fut_traded = _index_days(fut), _traded_days(fut)
    spot_days, spot_traded = _index_days(spot), _traded_days(spot)
    mark_days = _index_days(mark)
    d, f, x = req["decision"], req["fill"], req["exit"]
    # 20 handelsdagars volym till och med beslutsdagen
    median20 = None
    n_traded = 0
    if fut is not None and not fut.empty:
        upto = fut[(fut["volume"] > 0) & (fut.index == fut.index.normalize()) & (fut.index <= pd.Timestamp(d, tz="UTC"))]
        n_traded = int(len(upto))
        if n_traded >= 20:
            median20 = float(statistics.median(upto["volume"].iloc[-20:] * CONTRACT_USD))
    # samma open_time: båda benen måste ha en stapel exakt 00:00:00 UTC på fyllnings- och utträdesdagen
    aligned = all(day in fut_days and day in spot_days for day in (f, x))
    missing = {
        "fut_decision_bar": [] if d in fut_traded else [d],
        "fut_fill_bar": [] if f in fut_traded else [f],
        "fut_exit_bar": [] if x in fut_traded else [x],
        "spot_decision_bar": [] if d in spot_traded else [d],
        "spot_fill_bar": [] if f in spot_traded else [f],
        "spot_exit_bar": [] if x in spot_traded else [x],
        "mark_held_days": [t for t in req["held"] if t not in mark_days],
        "fut_next_open_days": [t for t in req["next_open"] if t not in fut_days],
        "spot_next_open_days": [t for t in req["next_open"] if t not in spot_days],
    }
    off_midnight = {"fut": _off_midnight(fut, [f, x] + req["next_open"]), "spot": _off_midnight(spot, [f, x] + req["next_open"]),
                    "mark": _off_midnight(mark, req["held"])}
    size_ok = implied_size_median is not None and 9.5 <= implied_size_median <= 10.5
    decision_possible = (not missing["fut_decision_bar"] and not missing["spot_decision_bar"] and n_traded >= 20 and size_ok)
    # saknade fyllnings-, utträdes-, markpris- eller (stopp-)nästa-öppningsstaplar för ett beslutat mynt gör körningen OGILTIG
    fill_complete = not any(missing[k] for k in ("fut_fill_bar", "fut_exit_bar", "spot_fill_bar", "spot_exit_bar"))
    held_complete = not missing["mark_held_days"] and not missing["fut_next_open_days"] and not missing["spot_next_open_days"]
    return {
        "coin": None, "cycle": cycle["cycle"], "expiry": cycle["expiry"], "decision": d, "fill": f, "exit": x,
        "n_held_days": len(req["held"]), "missing": {k: v for k, v in missing.items() if v},
        "open_time_aligned_fill_exit": aligned, "off_midnight_bars": {k: v for k, v in off_midnight.items() if v},
        "traded_days_before_decision": n_traded, "median20_usd": median20, "implied_size_median": implied_size_median,
        "contract_size_ok": size_ok, "decision_possible": decision_possible,
        "fill_exit_bars_complete": fill_complete, "held_days_complete": held_complete,
        # fail-closed enligt protokollet: exakt gemensam open_time, fyllnings- och utträdesstaplar, markpris varje hållen dag och nästa öppning för både termin och spot
        "data_complete": fill_complete and held_complete and aligned,
        "ogiltig_if_traded": decision_possible and not (fill_complete and held_complete and aligned),
        "liquidity_min_ok": median20 is not None and median20 >= MIN_MEDIAN20_USD,
        "liquidity_start_ok": median20 is not None and median20 >= START_SIZE_MEDIAN20_USD,
    }


def possible_coverage(audits: list[dict], cycles: list[dict]) -> dict:
    """Aggregerar mot datakrav 4 i protokollet: minst 46 av 91 mynt-cykler och minst 10 av 13 cykler med minst 4 mynt."""
    def ok(a: dict, strict: str) -> bool:
        return a["decision_possible"] and a["data_complete"] and a[strict]
    out = {}
    for label, key in (("minsta_storlek_10000", "liquidity_min_ok"), ("startstorlek_20000", "liquidity_start_ok")):
        per_cycle: dict[int, int] = {}
        total = 0
        for a in audits:
            if ok(a, key):
                total += 1
                per_cycle[a["cycle"]] = per_cycle.get(a["cycle"], 0) + 1
        tradable_cycles = [c["cycle"] for c in cycles if not c["flat"]]
        out[label] = {"mynt_cykler_mojliga": total, "mynt_cykler_krav": 46, "av_mojliga": 7 * len(tradable_cycles),
                      "cykler_med_minst_4_mynt": sum(1 for c in tradable_cycles if per_cycle.get(c, 0) >= 4), "cykler_krav": 10,
                      "av_cykler": len(tradable_cycles), "krav_uppfyllda": total >= 46 and sum(1 for c in tradable_cycles if per_cycle.get(c, 0) >= 4) >= 10,
                      "mynt_per_cykel": {str(c): per_cycle.get(c, 0) for c in tradable_cycles}}
    out["ogiltig_om_handlad"] = [(a["coin"], a["cycle"]) for a in audits if a["ogiltig_if_traded"]]
    return out


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_file(path: Path) -> dict:
    """Kontrollerar en nedladdad zip mot den sparade `.CHECKSUM`. Ingen checksumma eller fel summa ger `ok` falskt."""
    chk = path.with_suffix(".zip.CHECKSUM")
    if not chk.exists():
        return {"ok": False, "reason": "ingen .CHECKSUM sparad", "sha256": sha256_of(path)}
    expected = chk.read_text().split()[0].strip().lower()
    actual = sha256_of(path)
    return {"ok": expected == actual, "sha256": actual, "reason": "" if expected == actual else f"väntade {expected}"}


# ------------------------------------------------------------------ hämtning, laddning och körning (CLI)
def _series_name(coin: str, expiry: str) -> str:
    return f"{coin}USD_{expiry[2:4]}{expiry[5:7]}{expiry[8:]}"


def fetch_plan(cycles: list[dict]) -> dict:
    """Vilka månadsfiler som behövs: markpris per serie (inträdesmånad till utträdesmånad) och spot per mynt 2021-03 till 2024-09."""
    mark: dict[str, list[str]] = {}
    for c in cycles:
        if c["flat"]:
            continue
        months = binance.months(c["fill"][:7], c["exit"][:7])
        for coin in c["valid_coins"]:
            mark[_series_name(coin, c["expiry"])] = months
    return {"mark": mark, "spot": {f"{u}USDT": binance.months("2021-03", "2024-09") for u in SEVEN}}


def run_fetch(data_dir: Path, plan: dict, workers: int = 6) -> dict:
    """Hämtar saknade filer med checksumma (befintliga filer rörs inte). Returnerar saknade månader per symbol."""
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor
    lock, orig = threading.Lock(), binance._append_manifest

    def locked(*a, **k):
        with lock:
            return orig(*a, **k)
    binance._append_manifest = locked
    missing: dict[str, list[str]] = {}

    def one(item):
        market, sym, months = item
        for attempt in range(4):
            try:
                res = binance.fetch(market, sym, "1d", months[0], months[-1], data_dir)
                if res.missing:
                    missing[f"{market}:{sym}"] = res.missing
                return
            except OSError:
                time.sleep(3 * (attempt + 1))
        missing[f"{market}:{sym}"] = ["hämtning misslyckades"]
    items = [("cm-mark", s, m) for s, m in plan["mark"].items()] + [("spot", s, m) for s, m in plan["spot"].items()]
    try:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(one, items))
    finally:
        binance._append_manifest = orig
    return missing


MARK_GAP_MANIFEST = "research/coverage/h0022-mark-gap-2023-08.json"


def load_mark_manifest(repo: Path) -> dict[str, str]:
    """SHA-256 per verifierad dagsfil för markpris (augustiluckan 2023), ur den incheckade filen. Saknas filen: tomt, och luckfyllnad nekas."""
    path = repo / MARK_GAP_MANIFEST
    return json.loads(path.read_text(encoding="utf-8"))["files"] if path.exists() else {}


def fetch_mark_gap(repo: Path, series: list[str]) -> dict:
    """Hämtar dagsfiler (checksumma verifierad) för gapdagarna och grannedagarna i markprisarkivet, kontrollerar giltighet och att grannedagarna
    är exakt lika med månadsfilen, och skriver manifestet (SHA-256) som luckfyllnaden senare verifieras mot. Ingen prisanalys."""
    data_dir = repo / "data"
    files, checks = {}, {}
    for sym in series:
        try:
            monthly = binance.load("cm-mark", sym, "1d", data_dir, start=DATA_START, end=DATA_END)
        except FileNotFoundError:
            checks[sym] = {"error": "månadsfiler saknas"}
            continue
        rows = {}
        for day in (*gapcheck.NEIGHBOR_DAYS[:2], *gapcheck.GAP_DAYS, *gapcheck.NEIGHBOR_DAYS[2:]):
            dest = data_dir / "raw" / "binance" / "cm-mark-daily" / sym / "1d" / f"{sym}-1d-{day}.zip"
            meta = gapcheck.fetch_verified(gapcheck.daily_url("cm-mark", sym, day), dest)
            row = {"status": meta["status"], "in_monthly": pd.Timestamp(day, tz="UTC") in monthly.index}
            if meta["status"] == "ok":
                df = gapcheck.read_daily(dest)
                row["sanity"] = gapcheck.sanity(day, df)
                row["vs_monthly"] = gapcheck.compare_with_monthly(df, monthly, day)
                files[dest.name] = meta["sha256"]
            rows[day] = row
        checks[sym] = rows
    out = repo / MARK_GAP_MANIFEST
    out.write_text(json.dumps({"kind": "h0022-mark-gap-2023-08", "note": "Verifierade dagsfiler för markpris 2023-08-28..31 och grannedagar. Inga priser analyserade.",
                               "files": files, "checks": checks}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"files": len(files), "series": len(series)}


def series_missing_gap(data_dir: Path, plan_mark: dict[str, list[str]]) -> list[str]:
    """Markprisserier vars månadsfiler saknar gapdagarna 2023-08-28..31 men som hålls över dem (kontrolleras mot hållna dagar)."""
    out = []
    for sym in plan_mark:
        df, _ = _load("cm-mark", sym, data_dir, {}, gap_fill=False)
        if df is None or df.empty:
            continue
        gap = [pd.Timestamp(d, tz="UTC") for d in gapcheck.GAP_DAYS]
        if df.index.min() <= gap[0] and df.index.max() >= gap[-1] and any(g not in df.index for g in gap):
            out.append(sym)
    return out


def _load(market: str, sym: str, data_dir: Path, manifest: dict, gap_fill: bool) -> tuple[pd.DataFrame | None, str | None]:
    try:
        df = binance.load(market, sym, "1d", data_dir, start=DATA_START, end=DATA_END)
    except FileNotFoundError:
        return None, "filer saknas"
    if gap_fill:
        try:
            df = gapcheck.combined(df, data_dir, market, sym, manifest)
        except gapcheck.UnverifiedGapFill as exc:
            return df, f"oprövad luckfyllnad: {exc}"
    return df, None


def files_used(data_dir: Path, market: str, sym: str) -> list[Path]:
    folder = data_dir / "raw" / "binance" / market / sym / "1d"
    return [p for p in sorted(folder.glob(f"{sym}-1d-*.zip")) if "2021-03" <= p.stem[-7:] <= "2024-09"]


def run_audit(repo: Path) -> dict:
    data_dir = repo / "data"
    rows = json.loads((repo / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
    sizes = {r["contract"]: r for r in json.loads((repo / "research" / "universe" / "coinm-implied-contract-size.json").read_text(encoding="utf-8"))["series"]}
    manifest = gapcheck.load_manifest(repo)
    mark_manifest = load_mark_manifest(repo)
    cycles = cycle_calendar(rows)
    audits, notes, files = [], [], {}
    spot_cache: dict[str, tuple] = {}
    for c in cycles:
        if c["flat"]:
            continue
        for coin in c["valid_coins"]:
            sym = _series_name(coin, c["expiry"])
            fut, fnote = _load("cm", sym, data_dir, manifest, gap_fill=True)
            mark, mnote = _load("cm-mark", sym, data_dir, mark_manifest, gap_fill=True)
            if f"{coin}USDT" not in spot_cache:
                spot_cache[f"{coin}USDT"] = _load("spot", f"{coin}USDT", data_dir, manifest, gap_fill=True)
            spot, snote = spot_cache[f"{coin}USDT"]
            a = audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=(sizes.get(sym) or {}).get("median"))
            a["coin"] = coin
            a["series"] = sym
            a["notes"] = [n for n in (fnote, mnote, snote) if n]
            audits.append(a)
            for market, s in (("cm", sym), ("cm-mark", sym), ("spot", f"{coin}USDT")):
                for p in files_used(data_dir, market, s):
                    files[str(p.relative_to(data_dir))] = None
            for frame, folder, name in ((fut, "cm-daily", sym), (mark, "cm-mark-daily", sym), (spot, "spot-daily", f"{coin}USDT")):
                if frame is not None and "source" in frame.columns and "daily" in set(frame["source"]):
                    for day in gapcheck.GAP_DAYS + gapcheck.NEIGHBOR_DAYS:
                        pth = data_dir / "raw" / "binance" / folder / name / "1d" / f"{name}-1d-{day}.zip"
                        if pth.exists():
                            files[str(pth.relative_to(data_dir))] = None
    verification = {}
    for rel in sorted(files):
        verification[rel] = verify_file(data_dir / rel)
    bad = {k: v for k, v in verification.items() if not v["ok"]}
    return {"kind": "h0022-data-coverage", "note": "Möjlig täckning före strategimotor. Ingen basis, avkastning, t-statistik eller beta beräknad; inga 2025+-arkiv öppnade.",
            "data_window": [str(DATA_START.date()), str(DATA_END.date()) + " (exklusiv)"],
            "cycles": cycles, "audits": audits, "coverage": possible_coverage(audits, cycles),
            "files": {k: v["sha256"] for k, v in verification.items()}, "checksum_failures": bad}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--tables", action="store_true", help="skriv bara tabellerna ur den sparade JSON-filen")
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    if a.tables:
        print(write_report_tables(repo))
        return
    rows = json.loads((repo / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
    if a.fetch:
        plan = fetch_plan(cycle_calendar(rows))
        missing = run_fetch(repo / "data", plan)
        gap_series = series_missing_gap(repo / "data", plan["mark"])
        print(json.dumps({"mark_serier": len(plan["mark"]), "spot": len(plan["spot"]), "missing": missing,
                          "mark_gap": fetch_mark_gap(repo, gap_series) if gap_series else "inga markprisluckor"}, ensure_ascii=False))
    out = run_audit(repo)
    path = repo / "research" / "coverage" / "h0022-datatackning.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out["coverage"], ensure_ascii=False)[:1500])
    print("checksummafel:", len(out["checksum_failures"]), path)



# ------------------------------------------------------------------ rapport ur den sparade JSON-filen (inga siffror för hand)
def render_report(rep: dict) -> str:
    cycles, audits, cov = rep["cycles"], rep["audits"], rep["coverage"]
    coins = list(SEVEN)
    by: dict[int, dict[str, dict]] = {}
    for a in audits:
        by.setdefault(a["cycle"], {})[a["coin"]] = a
    lines = ["| Cykel | Serie (förfall) | Fyllning | Utträde | Mynt i universum | Data kompletta | Median 20 d ≥ 500 000 USD | Median 20 d ≥ 1 000 000 USD |", "|---|---|---|---|---|---|---|---|"]
    for c in cycles:
        if c["flat"]:
            lines.append(f"| {c['cycle']} | {c['expiry']} | {c['fill']} | {c['exit']} | 0 (platt: ingen daterad annons) | – | – | – |")
            continue
        a = by[c["cycle"]]
        n = len(a)
        lines.append(f"| {c['cycle']} | {c['expiry']} | {c['fill']} | {c['exit']} | {n} | {sum(1 for x in a.values() if x['data_complete'] and x['decision_possible'])} | "
                     f"{sum(1 for x in a.values() if x['liquidity_min_ok'] and x['data_complete'])} | {sum(1 for x in a.values() if x['liquidity_start_ok'] and x['data_complete'])} |")
    t1 = "\n".join(lines)
    lines = ["| Cykel | Fyllning | " + " | ".join(coins) + " |", "|---|---|" + "---|" * len(coins)]
    for c in cycles:
        if c["flat"]:
            continue
        cells = []
        for u in coins:
            m = by[c["cycle"]][u]["median20_usd"]
            cells.append("–" if m is None else f"{m / 1000:,.0f}".replace(",", " "))
        lines.append(f"| {c['cycle']} | {c['fill']} | " + " | ".join(cells) + " |")
    t2 = "\n".join(lines)
    files = rep["files"]
    kinds = {"COIN-M last price (månadsfiler)": lambda k: "/cm/" in k, "COIN-M markpris (månadsfiler)": lambda k: "/cm-mark/" in k,
             "COIN-M markpris, verifierade dagsfiler (augusti 2023)": lambda k: "/cm-mark-daily/" in k, "COIN-M last price, verifierade dagsfiler": lambda k: "/cm-daily/" in k,
             "Spot (månadsfiler)": lambda k: "/spot/" in k, "Spot, verifierade dagsfiler": lambda k: "/spot-daily/" in k}
    rows_f = [f"| {name} | {sum(1 for k in files if fn(k))} |" for name, fn in kinds.items()]
    t3 = "| Källa | Filer verifierade mot sparad checksumma |\n|---|---|\n" + "\n".join(rows_f) + f"\n| **Totalt** | **{len(files)}** (checksummafel: {len(rep['checksum_failures'])}) |"
    r1, r2 = cov["minsta_storlek_10000"], cov["startstorlek_20000"]
    t4 = ("| Datakrav 4 (protokollet) | Krav | Möjligt vid minsta storlek 10 000 USD | Möjligt vid startstorlek 20 000 USD |\n|---|---|---|---|\n"
          f"| Mynt-cykler handlade (av {r1['av_mojliga']}) | minst 46 | {r1['mynt_cykler_mojliga']} | {r2['mynt_cykler_mojliga']} |\n"
          f"| Cykler med minst 4 handlade mynt (av {r1['av_cykler']}) | minst 10 | **{r1['cykler_med_minst_4_mynt']}** | **{r2['cykler_med_minst_4_mynt']}** |\n"
          f"| Kravet uppfyllt | | **{'ja' if r1['krav_uppfyllda'] else 'nej'}** | **{'ja' if r2['krav_uppfyllda'] else 'nej'}** |")
    t5 = "| Cykel | " + " | ".join(str(c) for c in r1["mynt_per_cykel"]) + " |\n|---|" + "---|" * len(r1["mynt_per_cykel"]) + "\n| Mynt vid minsta storlek | " + " | ".join(str(v) for v in r1["mynt_per_cykel"].values()) + " |\n| Mynt vid startstorlek | " + " | ".join(str(v) for v in r2["mynt_per_cykel"].values()) + " |"
    return "\n\n".join([t1, t2, t3, t4, t5])


def write_report_tables(repo: Path) -> Path:
    rep = json.loads((repo / "research" / "coverage" / "h0022-datatackning.json").read_text(encoding="utf-8"))
    out = repo / "research" / "universe" / "h0022-datatackning-tabeller.md"
    out.write_text("# H-0022 datatäckning: tabeller (genererade, ändras inte för hand)\n\nGenererade av `python -m traderlab.h0022_coverage --tables` ur `research/coverage/h0022-datatackning.json`.\n\n" + render_report(rep) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
