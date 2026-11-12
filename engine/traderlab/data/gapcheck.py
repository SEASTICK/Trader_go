"""Kan luckan 2023-08-28 till 2023-08-31 i COIN-M:s månadsfiler återfinnas i Binances separata dagsarkiv?

Frågan kommer från granskningen av PR #112. Modulen använder bara Binances originalfiler (data.binance.vision), verifierar
varje fil mot dess publicerade SHA-256-checksumma och bevarar proveniens per stapel (`monthly` eller `daily`). Ingen
interpolation, inget sista-kända-pris och ingen annan börs används som ersättare. Inget från 2025 eller senare läses, och
inget backtest körs.

Kontroller per kontrakt och dag:
- finns en originalstapel i dagsarkivet (HTTP 200, annars saknas den),
- stämmer checksumman,
- är tidsstämpeln exakt dagens start (00:00 UTC), är OHLC konsistent (low <= open/close <= high) och volymen >= 0,
- stämmer dagsfilen exakt med månadsfilen på de dagar som finns i bägge (grannarna 2023-08-26/27 och 2023-09-01/02),
- hänger öppningen ihop med föregående stängning (bara som information, inte ett villkor).
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import binance as bn
from .basis_sources import default_opener

BASE = "https://data.binance.vision/data"
GAP_DAYS = ("2023-08-28", "2023-08-29", "2023-08-30", "2023-08-31")
NEIGHBOR_DAYS = ("2023-08-26", "2023-08-27", "2023-09-01", "2023-09-02")
SPOT_PAIRS = ("BTCUSDT", "ETHUSDT", "ADAUSDT", "BCHUSDT", "BNBUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "XRPUSDT")
OUT = Path("research/coverage")


def daily_url(market: str, symbol: str, day: str) -> str:
    kind = "futures/cm" if market == "cm" else "spot"
    return f"{BASE}/{kind}/daily/klines/{symbol}/1d/{symbol}-1d-{day}.zip"


def fetch_verified(url: str, dest: Path, opener=default_opener) -> dict:
    """Hämtar en originalfil och dess checksumma, verifierar och sparar båda. En 404 betyder att filen saknas."""
    import urllib.error
    try:
        raw = opener(url)
    except urllib.error.HTTPError as exc:
        return {"url": url, "status": "saknas" if exc.code == 404 else f"http {exc.code}"}
    try:
        checksum = opener(url + ".CHECKSUM")
        bn.verify_checksum(raw, checksum)
    except Exception as exc:   # noqa: BLE001 - en fil utan giltig checksumma används aldrig
        return {"url": url, "status": "checksumma ogiltig", "error": f"{type(exc).__name__}: {str(exc)[:120]}"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    dest.with_name(dest.name + ".CHECKSUM").write_bytes(checksum)
    return {"url": url, "status": "ok", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def read_daily(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.endswith(".csv")]
        return bn.parse_klines_csv(z.read(names[0]))


def sanity(day: str, df: pd.DataFrame) -> dict:
    """Tidsstämpel, OHLC och volym för en enstaka dagsfil."""
    if len(df) != 1:
        return {"rows": len(df), "ok": False, "problem": "förväntade exakt en stapel"}
    ts, r = df.index[0], df.iloc[0]
    problems = []
    if ts != pd.Timestamp(day, tz="UTC"):
        problems.append(f"tidsstämpel {ts} är inte dagens start")
    if not (r["low"] <= min(r["open"], r["close"]) and r["high"] >= max(r["open"], r["close"])):
        problems.append("OHLC är inte konsistent")
    if r["volume"] < 0:
        problems.append("negativ volym")
    return {"rows": 1, "ok": not problems, "problem": "; ".join(problems)}


def compare_with_monthly(daily: pd.DataFrame, monthly: pd.DataFrame, day: str) -> dict | None:
    """Exakt jämförelse med månadsfilen för samma dag. None om månadsfilen saknar dagen (gapdagar)."""
    ts = pd.Timestamp(day, tz="UTC")
    if ts not in monthly.index or ts not in daily.index:
        return None
    a, b = daily.loc[ts], monthly.loc[ts]
    diff = {c: [float(a[c]), float(b[c])] for c in ("open", "high", "low", "close", "volume") if a[c] != b[c]}
    return {"equal": not diff, "differences": diff}


def _check_symbol(market: str, sym: str, monthly: pd.DataFrame, data_dir: Path, opener, workers_days) -> dict:
    sub = "cm-daily" if market == "cm" else "spot-daily"
    rows = {}
    frames = {}
    for day in (*NEIGHBOR_DAYS[:2], *GAP_DAYS, *NEIGHBOR_DAYS[2:]):
        dest = data_dir / "raw" / "binance" / sub / sym / "1d" / f"{sym}-1d-{day}.zip"
        meta = fetch_verified(daily_url(market, sym, day), dest, opener)
        row = {"daily": meta, "in_monthly": pd.Timestamp(day, tz="UTC") in monthly.index, "is_gap_day": day in GAP_DAYS}
        if meta["status"] == "ok":
            df = read_daily(dest)
            frames[day] = df
            row["sanity"] = sanity(day, df)
            row["vs_monthly"] = compare_with_monthly(df, monthly, day)
        rows[day] = row
    # Sammanhang: öppning mot föregående stängning (information).
    order = [d for d in (*NEIGHBOR_DAYS[:2], *GAP_DAYS, *NEIGHBOR_DAYS[2:]) if d in frames]
    for prev, cur in zip(order, order[1:]):
        if (pd.Timestamp(cur) - pd.Timestamp(prev)).days == 1:
            rows[cur]["open_vs_previous_close"] = float(frames[cur]["open"].iloc[0] / frames[prev]["close"].iloc[0] - 1)
    return rows


class UnverifiedGapFill(ValueError):
    """En dagsstapel kan inte verifieras (checksumma, manifest, tidsstämpel/OHLC/volym eller grannkontroll). Sammanslagningen stoppas."""


def manifest_from_report(rep: dict) -> dict[str, str]:
    """{filnamn: sha256} för alla verifierade dagsfiler i en rapport (cm och spot). Rapporten är incheckad i Git och fungerar
    därmed som en förtroendeankare som en senare körning kan jämföra de lokala filerna mot."""
    out = {}
    for group in ("cm", "spot"):
        for days in rep.get(group, {}).values():
            for day, r in days.items():
                meta = r.get("daily", {}) if isinstance(r, dict) and not day.startswith("_") else {}
                if meta.get("status") == "ok":
                    out[meta["url"].rsplit("/", 1)[1]] = meta["sha256"]
    return out


def load_manifest(repo: Path) -> dict[str, str]:
    return manifest_from_report(json.loads((repo / OUT / "cm-gap-2023-08.json").read_text(encoding="utf-8")))


def _verified_bar(path: Path, day: str, manifest: dict[str, str]) -> pd.DataFrame:
    """Läser en lokal dagsfil bara efter att den verifierats på nytt. Annars UnverifiedGapFill."""
    checksum_path = path.with_name(path.name + ".CHECKSUM")
    if not checksum_path.exists():
        raise UnverifiedGapFill(f"{path.name}: sparad checksumma saknas")
    raw = path.read_bytes()
    try:
        bn.verify_checksum(raw, checksum_path.read_bytes())
    except ValueError as exc:
        raise UnverifiedGapFill(f"{path.name}: {exc}") from exc
    expected = manifest.get(path.name)
    if expected is None:
        raise UnverifiedGapFill(f"{path.name}: finns inte i manifestet över verifierade filer")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise UnverifiedGapFill(f"{path.name}: SHA-256 stämmer inte med manifestet")
    df = read_daily(path)
    check = sanity(day, df)
    if not check["ok"]:
        raise UnverifiedGapFill(f"{path.name}: {check['problem'] or 'ogiltig stapel'}")
    return df


def combined(monthly: pd.DataFrame, data_dir: Path, market: str, sym: str, manifest: dict[str, str]) -> pd.DataFrame:
    """Månadsstaplar plus **verifierade** dagsstaplar för gapdagarna, med proveniens per stapel (`source`).

    Fail-closed. En dagsstapel läggs bara in om (a) dess sparade checksumma stämmer, (b) dess SHA-256 stämmer med
    `manifest`, (c) tidsstämpel, OHLC och volym är giltiga, och (d) grannkontrollen är uppfylld: varje grannedag som
    månadsfilen har måste finnas som verifierad dagsfil och vara exakt lika med månadsfilen. Annars kastas
    `UnverifiedGapFill`, och ingen serie returneras. En gapdag utan dagsfil förblir en lucka (inget fylls)."""
    sub = "cm-daily" if market == "cm" else "spot-daily"
    folder = data_dir / "raw" / "binance" / sub / sym / "1d"

    def path(day: str) -> Path:
        return folder / f"{sym}-1d-{day}.zip"

    out = monthly.copy()
    out["source"] = "monthly"
    todo = [d for d in GAP_DAYS if pd.Timestamp(d, tz="UTC") not in monthly.index and path(d).exists()]
    if not todo:
        return out
    for nd in NEIGHBOR_DAYS:   # grannkontrollen gäller så snart något ska fyllas
        if pd.Timestamp(nd, tz="UTC") not in monthly.index:
            continue
        if not path(nd).exists():
            raise UnverifiedGapFill(f"{path(nd).name}: grannedagens dagsfil saknas, så dagsarkivet kan inte jämföras med månadsfilen")
        cmp = compare_with_monthly(_verified_bar(path(nd), nd, manifest), monthly, nd)
        if cmp is None or not cmp["equal"]:
            raise UnverifiedGapFill(f"{path(nd).name}: dagsfilen är inte lika med månadsfilen ({cmp['differences'] if cmp else 'ingen jämförelse'})")
    for day in todo:
        df = _verified_bar(path(day), day, manifest).copy()
        df["source"] = "daily"
        df["verified_sha256"] = manifest[path(day).name]
        out = pd.concat([out, df])
    return out.sort_index()


def contracts_with_gap(data_dir: Path, symbols: list[str]) -> dict[str, pd.DataFrame]:
    """Kontrakt vars månadsfiler spänner över luckan men saknar minst en gapdag."""
    lo, hi = pd.Timestamp("2020-09-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")
    out = {}
    for sym in symbols:
        try:
            df = bn.load("cm", sym, "1d", data_dir, start=lo, end=hi)
        except FileNotFoundError:
            continue
        if df.index[0] <= pd.Timestamp("2023-08-27", tz="UTC") and df.index[-1] >= pd.Timestamp("2023-09-01", tz="UTC"):
            if any(pd.Timestamp(d, tz="UTC") not in df.index for d in GAP_DAYS):
                out[sym] = df
    return out


def run(data_dir: Path, opener=default_opener, workers: int = 6) -> dict:
    syms = sorted(p.name for p in (data_dir / "raw" / "binance" / "cm").iterdir())
    cm = contracts_with_gap(data_dir, syms)
    lo, hi = "2023-08", "2023-09"
    spot_monthly = {}
    for pair in SPOT_PAIRS:   # spot-månadsfiler för 2023-08 och 2023-09 (checksummeverifierade av binance.fetch)
        bn.fetch("spot", pair, "1d", lo, hi, data_dir)
        spot_monthly[pair] = bn.load("spot", pair, "1d", data_dir, start=pd.Timestamp("2023-08-01", tz="UTC"), end=pd.Timestamp("2023-10-01", tz="UTC"))
    with ThreadPoolExecutor(workers) as ex:
        cm_res = dict(zip(cm, ex.map(lambda s: _check_symbol("cm", s, cm[s], data_dir, opener, None), cm)))
        sp_res = dict(zip(SPOT_PAIRS, ex.map(lambda s: _check_symbol("spot", s, spot_monthly[s], data_dir, opener, None), SPOT_PAIRS)))
    manifest = manifest_from_report({"cm": cm_res, "spot": sp_res})
    for sym, df in cm.items():   # serien efter att verifierade dagsstaplar lagts in, med proveniens
        c = combined(df, data_dir, "cm", sym, manifest)
        exp = pd.Timestamp("20" + sym.rsplit("_", 1)[1], tz="UTC")
        span = c[c.index <= exp]
        full = pd.date_range(span.index[0], span.index[-1], freq="1D", tz="UTC")
        cm_res[sym]["_after_fill"] = {"monthly_bars": len(df), "bars_after": len(c), "daily_bars_added": int((c["source"] == "daily").sum()),
                                     "missing_days_to_expiry": int(len(full.difference(span.index)))}
    summary = summarize(cm_res, sp_res)
    return {"kind": "cm-gap-2023-08", "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "gap_days": list(GAP_DAYS), "contracts_with_gap": sorted(cm), "summary": summary, "cm": cm_res, "spot": sp_res,
            "note": "Bara Binances originalfiler med verifierad checksumma. Ingen interpolation, inget sista-kända-pris, ingen annan börs. Inget från 2025+, inget backtest."}


def summarize(cm_res: dict, sp_res: dict) -> dict:
    def cells(res, gap_only):
        return [(s, d, r) for s, days in res.items() for d, r in days.items() if not d.startswith("_") and (d in GAP_DAYS) == gap_only]
    gap = cells(cm_res, True)
    neighbors = cells(cm_res, False)
    spot_gap = cells(sp_res, True)
    bad = [(s, d) for s, d, r in gap if r["daily"]["status"] != "ok" or not r.get("sanity", {}).get("ok")]
    mism = [(s, d) for s, d, r in neighbors if r.get("vs_monthly") and not r["vs_monthly"]["equal"]]
    compared = [(s, d) for s, d, r in neighbors if r.get("vs_monthly")]
    spot_mism = [(s, d) for s, d, r in cells(sp_res, False) if r.get("vs_monthly") and not r["vs_monthly"]["equal"]]
    return {"cm_gap_contract_days": len(gap), "cm_gap_days_with_verified_original": len(gap) - len(bad),
            "cm_gap_days_missing_or_failed": bad, "cm_neighbor_days_compared_with_monthly": len(compared),
            "cm_neighbor_mismatches": mism, "spot_gap_days": len(spot_gap),
            "spot_gap_days_in_monthly": sum(1 for s, d, r in spot_gap if r["in_monthly"]),
            "spot_gap_days_with_verified_daily": sum(1 for s, d, r in spot_gap if r["daily"]["status"] == "ok"),
            "spot_gap_days_equal_to_monthly": sum(1 for s, d, r in spot_gap if r.get("vs_monthly") and r["vs_monthly"]["equal"]),
            "cm_missing_days_to_expiry_after_fill": sum(days["_after_fill"]["missing_days_to_expiry"] for days in cm_res.values() if "_after_fill" in days),
            "spot_mismatches_vs_monthly": spot_mism}


def markdown_tables(rep: dict) -> str:
    """Tabeller för research/cm-lucka-2023-08.md, direkt ur rapportfilen."""
    rows = ["| Kontrakt | Gapdagar med verifierad originalstapel | Checksumma ok | Konsistent stapel | Grannar lika med månadsfil | Kvarvarande luckor till förfall |",
            "|---|---|---|---|---|---|"]
    for sym, days in rep["cm"].items():
        gap = [days[d] for d in GAP_DAYS]
        ok = sum(1 for r in gap if r["daily"]["status"] == "ok")
        sane = sum(1 for r in gap if r.get("sanity", {}).get("ok"))
        nb = [r for d, r in days.items() if not d.startswith("_") and d not in GAP_DAYS and r.get("vs_monthly")]
        eq = sum(1 for r in nb if r["vs_monthly"]["equal"])
        rows.append(f"| {sym} | {ok}/4 | {ok}/4 | {sane}/4 | {eq}/{len(nb)} | {days['_after_fill']['missing_days_to_expiry']} |")
    sp = ["| Spot | Gapdagar i månadsfilen | Gapdagar med verifierad dagsfil | Grannar lika med månadsfil |", "|---|---|---|---|"]
    for sym, days in rep["spot"].items():
        gap = [days[d] for d in GAP_DAYS]
        nb = [r for d, r in days.items() if d not in GAP_DAYS and r.get("vs_monthly")]
        sp.append(f"| {sym} | {sum(1 for r in gap if r['in_monthly'])}/4 | {sum(1 for r in gap if r['daily']['status'] == 'ok')}/4 | "
                  f"{sum(1 for r in nb if r['vs_monthly']['equal'])}/{len(nb)} |")
    return "\n".join(rows) + "\n\n" + "\n".join(sp)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    a = ap.parse_args()
    rep = run(a.repo / "data")
    folder = a.repo / OUT
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "cm-gap-2023-08.json"
    path.write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(rep["summary"], ensure_ascii=False))
    print(path)


if __name__ == "__main__":
    main()
