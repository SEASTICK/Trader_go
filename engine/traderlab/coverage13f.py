"""Varför saknar H-0016 kurser? Täckningsdiagnos för research/13f-protokoll.md (avsnittet Datakrav).

Ändrar inga resultat och fyller inga luckor. För varje aktie som saknar kurs i H-0016 redovisas:
- hur mycket av förvaltarnas vikt den står för (genomsnitt över redovisningarna, approximativt),
- vad som sparats från tidigare Yahoo-svar,
- vad Yahoo svarar nu (en ny hämtning),
och luckan klassas som
- `hade_kurs`: kurs fanns redan (räknas inte som lucka),
- `fixad`: kurs saknades men finns nu, alltså ett fel i hämtningen eller en tillfällig spärr,
- `finns_inte`: Yahoo säger Not Found (avnoterat, uppköpt eller bytt symbol: en källbegränsning),
- `otillgänglig`: Yahoo svarar med spärr eller fel, ingen slutsats,
- `ingen_ticker`: CUSIP saknar ticker i kopplingen.
Luckorna räknas kvar i täckningen. Inget fylls med sista kända pris eller ersättare.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .copy13f import END, MANAGERS, TOP
from .data import ftd, sec13f, stocks

OUT = Path("research/coverage")


def collect(data_dir: Path, ciks=None) -> tuple[dict[str, float], dict[str, str], int]:
    """(summa vikt per CUSIP över alla redovisningar, namn per CUSIP, antal redovisningar)."""
    weight: dict[str, float] = {}
    names: dict[str, str] = {}
    n = 0
    for cik in ciks or MANAGERS:
        for f in sec13f.list_filings(cik, data_dir):
            if not ("2013-07-01" <= f.filed < END):
                continue
            rows = sec13f.holdings(f, data_dir)
            top = sec13f.top_weights(rows, TOP)
            if not top:
                continue
            n += 1
            for cu, w in top.items():
                weight[cu] = weight.get(cu, 0.0) + w
                names.setdefault(cu, rows[cu]["name"])
    return weight, names, n


def cached_answer(data_dir: Path, ticker: str) -> str | None:
    """Vad som låg i cachen från en tidigare körning (kan vara ett tomt svar som tidigare kod sparade)."""
    path = data_dir / "raw" / "yahoo" / f"{stocks.yahoo_symbol(ticker)}.json"
    if not path.exists():
        return None
    try:
        chart = json.loads(path.read_text()).get("chart") or {}
    except ValueError:
        return "oläsbart"
    if chart.get("result"):
        return "data"
    err = chart.get("error") or {}
    return f"tomt: {err.get('code') or 'utan felkod'}"


def refetch(data_dir: Path, ticker: str, opener=None) -> tuple[str, str]:
    """Ny hämtning utan att lita på en sparad tom fil. Returnerar (klass, förklaring)."""
    path = data_dir / "raw" / "yahoo" / f"{stocks.yahoo_symbol(ticker)}.json"
    if path.exists() and cached_answer(data_dir, ticker) != "data":
        path.unlink()
    try:
        df = stocks.load_prices(ticker, data_dir, opener)
    except stocks.PriceSourceUnavailable as exc:
        return "otillgänglig", str(exc)[:160]
    if df is None:
        return "finns_inte", "Yahoo svarar Not Found"
    return "fixad", f"{len(df)} dagar, {df.index[0].date()} till {df.index[-1].date()}"


def diagnose(repo: Path, data_dir: Path | None = None, only: list[str] | None = None, opener=None) -> dict:
    data_dir = data_dir or repo / "data"
    fmap = ftd.load_map(data_dir)
    weight, names, n = collect(data_dir)
    rows = []
    for cu, w in sorted(weight.items(), key=lambda kv: -kv[1]):
        t = fmap.get(cu)
        if only is not None and t not in only:
            continue
        row = {"cusip": cu, "ticker": t, "name": names[cu], "avg_weight_in_filings": round(w / max(n, 1), 5)}
        if not t:
            row.update(klass="ingen_ticker", detail="CUSIP saknar ticker i fails-to-deliver-kopplingen")
        else:
            row["cache_before"] = cached_answer(data_dir, t)
            if row["cache_before"] == "data":
                row.update(klass="hade_kurs", detail="kurs fanns redan i cachen")
            else:
                row["klass"], row["detail"] = refetch(data_dir, t, opener)
        rows.append(row)
    summary: dict[str, dict] = {}
    for r in rows:
        s = summary.setdefault(r["klass"], {"tickers": 0, "avg_weight": 0.0})
        s["tickers"] += 1
        s["avg_weight"] = round(s["avg_weight"] + r["avg_weight_in_filings"], 5)
    return {"hypothesis_id": "H-0016", "kind": "coverage-diagnosis", "filings": n,
            "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "summary": summary,
            "rows": rows, "note": "Diagnos, inget resultat. Luckor räknas kvar i täckningen."}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--only", nargs="*", help="Begränsa till dessa tickers (för prov)")
    a = ap.parse_args()
    d = diagnose(a.repo, only=a.only)
    folder = a.repo / OUT
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'H-0016-coverage-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(d["summary"], ensure_ascii=False))
    print(path)


if __name__ == "__main__":
    main()
