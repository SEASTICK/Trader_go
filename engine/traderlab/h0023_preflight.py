"""Datapreflight för H-0023 (Rullning B): vilka arkiv behövs, är de hämtade och verifierade, och klarar `load_panel` riktiga data?

Preflighten **räknar inga priser**: ingen basis, ingen avkastning, ingen t-statistik, inget beta, ingen `simulate`. Den
läser bara arkiv inom 2021-03 till 2024-09 (`DATA_END` är exklusiv gräns i läsarna) och skriver inget resultat för
strategin. Kärnan:

* `required_files` – exakt vilka månadsfiler (marknad, symbol, månad) som kalendern kräver, aldrig 2025 eller senare.
* `fetch_missing` – hämtar bara saknade filer från data.binance.vision (befintliga rörs inte, checksumma verifieras).
* `inventory` – per fil: finns den, finns checksumman, stämmer den, SHA-256.
* `probe` – `load_panel` på riktiga data, dagsfiler som använts för luckfyllnad, anmärkningar om **oprövad luckfyllnad**
  (dessa källor får aldrig gå vidare som verifierad data) och datakompletthet per mynt-cykel samt BTCUSDT på varje fönstergräns.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from . import h0023
from .data import binance as bn
from .h0022_coverage import DATA_END, DATA_START, _series_name, audit_coin_cycle, cycle_calendar, cycle_windows

OUT_JSON = Path("research/coverage/h0023-datapreflight.json")
OUT_MD = Path("research/universe/h0023-datapreflight.md")
LAST_MONTH = "2024-09"
LOOKBACK_DAYS = 45


def _month(day: str) -> str:
    return day[:7]


def _months_between(a: str, b: str) -> list[str]:
    return bn.months(a, b)


def required_files(cycles: list[dict]) -> dict[tuple[str, str], list[str]]:
    """{(marknad, symbol): [månader]}. Terminer och spot: från 45 dagar före beslutsdagen (20 handelsdagars volym) till utträdet; markpris: fyllning
    till utträde; BTCUSDT: månaderna för varje fönstergräns (F_k och T_k). Månader före 2021-03 klipps bort; efter 2024-09 är ett fel."""
    need: dict[tuple[str, str], set[str]] = {}
    first = DATA_START.strftime("%Y-%m")

    def add(market: str, sym: str, a: str, b: str) -> None:
        for m in _months_between(max(a, first), b):
            need.setdefault((market, sym), set()).add(m)
    for c in cycles:
        if c["flat"]:
            continue
        lookback = (pd.Timestamp(c["decision"]) - pd.Timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m")
        for coin in c["valid_coins"]:
            sym = _series_name(coin, c["expiry"])
            add("cm", sym, lookback, _month(c["exit"]))
            add("cm-mark", sym, _month(c["fill"]), _month(c["exit"]))
            add("spot", f"{coin}USDT", lookback, _month(c["exit"]))
    for a, b in cycle_windows([c for c in cycles if not c["flat"]]):
        for day in (a, b):
            need.setdefault(("spot", "BTCUSDT"), set()).add(_month(day))
    out = {k: sorted(v) for k, v in need.items()}
    late = sorted(f"{k[0]}:{k[1]}:{m}" for k, v in out.items() for m in v if m > LAST_MONTH)
    if late:
        raise ValueError(f"kalendern kräver arkiv efter {LAST_MONTH} (slutprovet får inte öppnas): {late[:5]}")
    return out


def _path(data_dir: Path, market: str, sym: str, month: str) -> Path:
    return data_dir / "raw" / "binance" / market / sym / "1d" / f"{sym}-1d-{month}.zip"


def fetch_missing(data_dir: Path, need: dict[tuple[str, str], list[str]], opener=bn._default_opener) -> dict[str, list[str]]:
    """Hämtar bara månader som saknas lokalt (aldrig något utanför `need`). Returnerar månader som Binance inte har."""
    missing: dict[str, list[str]] = {}
    for (market, sym), months in sorted(need.items()):
        todo = [m for m in months if not _path(data_dir, market, sym, m).exists()]
        for m in todo:
            res = bn.fetch(market, sym, "1d", m, m, data_dir, opener=opener)
            if res.missing:
                missing.setdefault(f"{market}:{sym}", []).extend(res.missing)
    return missing


def backfill_checksums(data_dir: Path, need: dict[tuple[str, str], list[str]], opener=bn._default_opener) -> dict[str, str]:
    """Lokala filer utan sparad checksumma: hämtar bara den publicerade `.CHECKSUM`, verifierar den befintliga zip-filen mot den och sparar checksumman.
    Själva filen ändras aldrig. Stämmer den inte lämnas inget skrivet (inventeringen redovisar då filen som ej verifierad). Returnerar {fil: utfall}."""
    out = {}
    for (market, sym), months in sorted(need.items()):
        for m in months:
            p = _path(data_dir, market, sym, m)
            chk = p.with_name(p.name + ".CHECKSUM")
            if not p.exists() or chk.exists():
                continue
            rel = str(p.relative_to(data_dir))
            try:
                published = opener(bn.kline_url(market, sym, "1d", m) + ".CHECKSUM")
                bn.verify_checksum(p.read_bytes(), published)
            except (ValueError, OSError) as exc:
                out[rel] = f"ej verifierad: {exc}"
                continue
            chk.write_bytes(published)
            out[rel] = "verifierad mot publicerad checksumma och sparad"
    return out


def inventory(data_dir: Path, need: dict[tuple[str, str], list[str]]) -> dict:
    """Per krävd fil: finns den, finns checksumman, stämmer den, SHA-256. Läser bara filer som `need` pekar ut."""
    import hashlib
    files, problems = {}, []
    for (market, sym), months in sorted(need.items()):
        for m in months:
            p = _path(data_dir, market, sym, m)
            rel = str(p.relative_to(data_dir))
            if not p.exists():
                problems.append({"file": rel, "problem": "filen saknas"})
                continue
            chk = p.with_name(p.name + ".CHECKSUM")
            raw = p.read_bytes()
            if not chk.exists():
                problems.append({"file": rel, "problem": "sparad checksumma saknas"})
                continue
            try:
                bn.verify_checksum(raw, chk.read_bytes())
            except ValueError as exc:
                problems.append({"file": rel, "problem": f"checksumman stämmer inte: {exc}"})
                continue
            files[rel] = hashlib.sha256(raw).hexdigest()
    return {"required": sum(len(v) for v in need.values()), "verified": len(files), "files": files, "problems": problems}


def _daily_fill_files(panel: h0023.Panel) -> dict[str, str]:
    """Dagsfiler (luckfyllnad) som faktiskt ligger i panelen, med SHA-256 ur manifestet (`verified_sha256`)."""
    out = {}
    for group, label in ((panel.fut, "cm-daily"), (panel.mark, "cm-mark-daily"), (panel.spot, "spot-daily")):
        for name, df in group.items():
            if df is not None and "source" in df.columns:
                for ts, row in df[df["source"] == "daily"].iterrows():
                    out[f"{label}/{name}/{ts.date().isoformat()}"] = row.get("verified_sha256")
    if panel.btc is not None and "source" in panel.btc.columns:
        for ts, row in panel.btc[panel.btc["source"] == "daily"].iterrows():
            out[f"spot-daily/BTCUSDT/{ts.date().isoformat()}"] = row.get("verified_sha256")
    return out


def btc_boundary_check(panel: h0023.Panel, cycles: list[dict]) -> dict:
    """BTCUSDT: verifierad stapel exakt 00:00 UTC med volym och ändligt positivt open på varje F_k och T_k (datakrav 8). Inga priser jämförs."""
    days = sorted({d for w in cycle_windows([c for c in cycles if not c["flat"]]) for d in w})
    bad = []
    for d in days:
        if not h0023._traded(panel.btc, d):
            bad.append({"day": d, "problem": "ingen verifierad stapel med volym exakt 00:00 UTC"})
            continue
        try:
            h0023._px(panel.btc, d, "open", "BTCUSDT spot")
        except h0023.InvalidRun as exc:
            bad.append({"day": d, "problem": str(exc)})
    return {"days": len(days), "problems": bad}


def probe(repo: Path) -> dict:
    """`load_panel` på riktiga data och datakompletthet per mynt-cykel. Anropar aldrig `simulate`."""
    rows = json.loads((repo / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
    cycles = cycle_calendar(rows, "rullning_b")
    panel, sizes = h0023.load_panel(repo, cycles)
    h0023.assert_before_holdout(panel)
    audits = []
    for c in cycles:
        if c["flat"]:
            continue
        for coin in c["valid_coins"]:
            sym = _series_name(coin, c["expiry"])
            a = audit_coin_cycle(cycle=c, fut=panel.fut.get(sym), mark=panel.mark.get(sym), spot=panel.spot.get(coin),
                                 implied_size_median=(sizes.get(sym) or {}).get("median"))
            a["coin"], a["series"] = coin, sym
            a["unverified"] = [k for k in (f"fut:{sym}", f"mark:{sym}", f"spot:{coin}") if k in panel.unverified]
            audits.append(a)
    latent = [{"coin": a["coin"], "cycle": a["cycle"], "missing": a["missing"], "off_midnight_bars": a["off_midnight_bars"], "unverified": a["unverified"]}
              for a in audits if (a["decision_possible"] and not a["data_complete"]) or a["unverified"]]
    return {"cycles": len(cycles), "coin_cycles_checked": len(audits), "unverified_sources": panel.unverified,
            "daily_fill_files": _daily_fill_files(panel), "btc_boundaries": btc_boundary_check(panel, cycles),
            "complete_coin_cycles": sum(1 for a in audits if a["decision_possible"] and a["data_complete"] and not a["unverified"]),
            "latent_invalid_if_decided": latent}


def run(repo: Path, *, fetch: bool = False, opener=bn._default_opener) -> dict:
    rows = json.loads((repo / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
    cycles = cycle_calendar(rows, "rullning_b")
    need = required_files(cycles)
    missing = fetch_missing(repo / "data", need, opener) if fetch else {}
    backfilled = backfill_checksums(repo / "data", need, opener) if fetch else {}
    inv = inventory(repo / "data", need)
    prb = probe(repo)
    ok = not inv["problems"] and not missing and not prb["unverified_sources"] and not prb["btc_boundaries"]["problems"]
    return {"kind": "h0023-datapreflight",
            "note": "Datapreflight före den registrerade körningen. Ingen basis, avkastning, t-statistik eller beta beräknad; `simulate` anropas aldrig; "
                    f"inga arkiv från 2025 eller senare öppnade (data till {LAST_MONTH}, läsargräns {DATA_END.date()} exklusiv).",
            "data_window": [str(DATA_START.date()), f"{DATA_END.date()} (exklusiv)"],
            "required_by_market": {f"{m}:{s}": v for (m, s), v in sorted(need.items())},
            "fetch_missing_from_source": missing, "checksum_backfill": backfilled, "inventory": inv, "probe": prb, "preflight_ok": ok}


def render(rep: dict) -> str:
    inv, prb = rep["inventory"], rep["probe"]
    lines = ["# H-0023 datapreflight", "",
             "Genererad ur `research/coverage/h0023-datapreflight.json`. **Ingen basis, avkastning, t-statistik eller beta är beräknad, `simulate` har inte körts och inga arkiv från 2025 eller senare har öppnats.**", "",
             f"* Resultat: **{'OK' if rep['preflight_ok'] else 'EJ OK'}**",
             f"* Krävda månadsfiler: {inv['required']}, verifierade mot sparad checksumma: {inv['verified']}, problem: {len(inv['problems'])}",
             f"* Månader som källan inte har: {sum(len(v) for v in rep['fetch_missing_from_source'].values())}",
             f"* Källor med oprövad luckfyllnad: {len(prb['unverified_sources'])}",
             f"* Dagsfiler använda för luckfyllnad (verifierade mot manifest): {len(prb['daily_fill_files'])}",
             f"* BTCUSDT-gränsdagar (F_k och T_k): {prb['btc_boundaries']['days']}, problem: {len(prb['btc_boundaries']['problems'])}",
             f"* Mynt-cykler kontrollerade: {prb['coin_cycles_checked']}, kompletta och möjliga att besluta: {prb['complete_coin_cycles']}",
             f"* Mynt-cykler som skulle ge OGILTIG om de beslutas (data ofullständig eller oprövad): {len(prb['latent_invalid_if_decided'])}", ""]
    for title, items in (("Problem i arkiven", inv["problems"]), ("BTCUSDT-problem", prb["btc_boundaries"]["problems"]),
                         ("Oprövad luckfyllnad", [{"source": k, "reason": v} for k, v in prb["unverified_sources"].items()]),
                         ("Skulle ge OGILTIG om beslutad", prb["latent_invalid_if_decided"])):
        lines += [f"## {title}", ""] + ([f"* `{json.dumps(i, ensure_ascii=False)}`" for i in items] or ["Inga."]) + [""]
    if rep.get("checksum_backfill"):
        lines += ["## Checksummor som kompletterats (filerna är oförändrade)", ""] + [f"* `{k}`: {v}" for k, v in rep["checksum_backfill"].items()] + [""]
    if rep["fetch_missing_from_source"]:
        lines += ["## Månader som källan saknar", ""] + [f"* `{k}`: {', '.join(v)}" for k, v in rep["fetch_missing_from_source"].items()] + [""]
    lines += ["## Reproduktion", "", "```bash", "cd engine", ".venv/bin/python -m traderlab.h0023_preflight --fetch   # hämtar saknade filer 2021-03..2024-09 och kör kontrollen", "```", ""]
    return "\n".join(lines)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="hämta saknade månadsfiler (bara 2021-03..2024-09) före kontrollen")
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    rep = run(repo, fetch=a.fetch)
    (repo / OUT_JSON).write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    (repo / OUT_MD).write_text(render(rep), encoding="utf-8")
    print(json.dumps({k: rep[k] for k in ("preflight_ok",)}, ensure_ascii=False), "krav:", rep["inventory"]["required"], "verifierade:", rep["inventory"]["verified"],
          "oprövade:", len(rep["probe"]["unverified_sources"]), "latent ogiltiga:", len(rep["probe"]["latent_invalid_if_decided"]))


if __name__ == "__main__":
    main()
