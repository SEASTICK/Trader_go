"""Datapreflight för H-0024 (månadsskiftet i SPY): kontrollerar bara protokollets datakrav, aldrig något annat.

Preflighten **räknar inga priser**: ingen avkastning, ingen Sharpe, inget t-värde, ingen placebo, inget beslut och ingen registerrad. Den hämtar SPY (Yahoo chart-API, den källa
protokollet föreskriver, justerad öppning och stängning), kapar vid 2025-01-01 **innan första kontroll** och skriver bara täcknings- och datakvalitetsutfall (antal, datum som
saknas, sant/falskt per krav). Inga kurser skrivs, loggas eller returneras. Det som sparas på disk är den redan kapade serien (data/raw/, ingår inte i Git), aldrig något från 2025-01-01 eller senare.

Slutprovet skyddas i tre led: (1) begäran till Yahoo slutar vid 2025-01-01 (`period2`), så rader därefter inte ens skickas; (2) `parse_cut` bestämmer vad som kapas ur tidsstämplarna
**innan** något värde läses, så värdena på kapade rader används aldrig; (3) resultatet innehåller bara antal (`rows_cut_holdout`), aldrig värden, och en test visar att giftiga värden
efter gränsen inte ändrar utfallet.

Källan ändras inte här: protokollet kräver Yahoo via samma API som `data/stocks.py`. Skillnaden mot `load_prices` är bara förfrågans tidsfönster (2006-01-01 till 2025-01-01 i stället för
2012 till idag), eftersom `load_prices` startar 2012 och därför aldrig kan täcka 2006–2011.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from . import nyse_sessions, tom

SYMBOL = "SPY"
PERIOD1 = pd.Timestamp("2006-01-01", tz="UTC")
PERIOD2 = tom.HOLDOUT.tz_localize("UTC")                       # exklusiv: Yahoo skickar inget från och med 2025-01-01
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
CACHE_DIR = Path("data/raw/h0024")
OUT_JSON = Path("research/coverage/h0024-datapreflight.json")
OUT_MD = Path("research/coverage/h0024-datapreflight.md")
# Det enda som får skrivas i resultatet: täckning och datakvalitet. Inga kurser, ingen avkastning.
ALLOWED_RESULT_KEYS = {"hypothesis", "kind", "status", "source", "request", "rows_cut_holdout", "rows_in_period", "requirements", "invalid_reasons", "per_year_days", "months_below_minimum",
                       "missing_sessions", "unexpected_days", "rows_with_missing_fields", "cycles_expected", "cycles_complete", "incomplete_cycles", "calendar_verification",
                       "dates_sha256", "value_stability", "fetched_at_utc", "note", "blocker"}


class SourceUnavailable(RuntimeError):
    """Yahoo svarar inte med data (blockerad, gräns nådd eller oväntat svar). Inget sparas och inget kringgås."""


def request_url(sym: str = SYMBOL) -> str:
    return URL.format(sym=sym, p1=int(PERIOD1.timestamp()), p2=int(PERIOD2.timestamp()))


def parse_cut(raw: bytes) -> tuple[pd.DataFrame, int]:
    """Yahoo-svaret som justerade dagsstaplar (`open`, `close`, båda justerade med `adjclose/close`), **kapat vid 2025-01-01 innan något värde läses**.

    Bara tidsstämplarna används för att bestämma vad som kapas; värdena på kapade rader rörs aldrig. Rader med saknade fält behålls som NaN (så att preflighten kan räkna dem i stället
    för att tyst tappa dem). Returnerar (serie, antal kapade rader)."""
    res = (json.loads(raw).get("chart") or {}).get("result") or []
    if not res or not res[0].get("timestamp"):
        raise SourceUnavailable("svaret saknar data")
    r = res[0]
    tz = (r.get("meta") or {}).get("exchangeTimezoneName") or "America/New_York"
    days = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(tz).normalize().tz_localize(None)
    keep = np.asarray(days < tom.HOLDOUT)                                  # 1. kapa på indexet
    n_cut = int((~keep).sum())
    q = r["indicators"]["quote"][0]
    adj = (r["indicators"].get("adjclose") or [{}])[0].get("adjclose") or q["close"]

    def take(values):                                                      # 2. först nu läses värdena, bara de behållna raderna (kapade värden rörs aldrig)
        return np.array([np.nan if v is None else v for v, k in zip(values, keep) if k], dtype=float)
    o, c, a = take(q["open"]), take(q["close"]), take(adj)
    with np.errstate(divide="ignore", invalid="ignore"):
        factor = a / c
    df = pd.DataFrame({"open": o * factor, "close": a}, index=pd.DatetimeIndex(days[keep], name="date"))
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df, n_cut


def fetch(opener=None, cache_dir: Path | None = None) -> tuple[pd.DataFrame, int]:
    """Hämtar SPY 2006-01-01..2025-01-01 (exklusivt) från Yahoo. Returnerar (kapad serie, antal kapade rader). Ingen hash över det råa svaret beräknas eller sparas (den skulle bero på rader efter gränsen).

    Det råa svaret sparas **inte** (det kan i teorin innehålla rader efter gränsen); den kapade serien sparas som CSV och används vid omkörning. Svarar källan inte, kastas `SourceUnavailable`."""
    url = request_url()
    req = urllib.request.Request(url, headers={"User-Agent": "TraderGo research"})
    try:
        raw = opener(req) if opener else _read(req)
    except urllib.error.HTTPError as exc:
        raise SourceUnavailable(f"Yahoo svarade {exc.code}") from exc
    except OSError as exc:
        raise SourceUnavailable(f"Yahoo svarar inte: {exc}") from exc
    try:
        df, n_cut = parse_cut(raw)
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceUnavailable(f"oväntat svar från Yahoo: {raw[:60]!r}") from exc
    cache_dir = CACHE_DIR if cache_dir is None else cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_dir / f"{SYMBOL}-{PERIOD1.date()}-{PERIOD2.date()}-cut.csv")
    return df, n_cut


def _read(req) -> bytes:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError:
            raise
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 * 2 ** attempt)
    raise OSError("oåtkomlig")


def dates_sha256(df: pd.DataFrame) -> str:
    """SHA-256 över de datum som har både justerad öppning och stängning (ISO-datum, en per rad). Ett täckningsfingeravtryck utan några värden. Värdena själva hashas inte: Yahoos justerade
    värden är inte bitvis stabila mellan anrop (mätt, se `stability`), så en värdehash skulle inte vara reproducerbar."""
    ok = df[["open", "close"]].dropna().index
    return hashlib.sha256("\n".join(pd.DatetimeIndex(ok).strftime("%Y-%m-%d")).encode()).hexdigest()


def stability(first: pd.DataFrame, second: pd.DataFrame) -> dict:
    """Hur lika två hämtningar är (samma period, båda redan kapade). Inga kurser, bara skillnaden.

    Saknade eller icke-finita värden (NaN, inf) och datum som bara finns i den ena hämtningen blir **aldrig** noll skillnad: de räknas och redovisas separat, paret räknas inte som lika, och
    mätningen markeras `sufficient=False` (otillräcklig) så snart något saknas. Den relativa skillnaden räknas bara över par där båda värdena är finita."""
    only_first = first.index.difference(second.index)
    only_second = second.index.difference(first.index)
    both = first.index.intersection(second.index)
    a = first.loc[both, ["open", "close"]].to_numpy(dtype=float)
    b = second.loc[both, ["open", "close"]].to_numpy(dtype=float)
    finite = np.isfinite(a) & np.isfinite(b)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.abs(a - b) / np.abs(a)
    rel_ok = finite & np.isfinite(rel)                                              # delning med noll i första hämtningen är också ett par utan giltig skillnad
    bad_cells = int((~rel_ok).sum())
    return {"same_dates": bool(len(only_first) == 0 and len(only_second) == 0), "rows_compared": int(len(both)),
            "dates_only_in_first": int(len(only_first)), "dates_only_in_second": int(len(only_second)),
            "non_finite_cells": bad_cells, "rows_with_non_finite": int((~rel_ok).any(axis=1).sum()) if rel_ok.size else 0,
            "sufficient": bool(len(only_first) == 0 and len(only_second) == 0 and len(both) > 0 and bad_cells == 0),
            "max_relative_difference": float(f"{float(rel[rel_ok].max()):.3g}") if rel_ok.any() else None,
            "rows_differing_over_1e-9": int(((np.where(rel_ok, rel, 0.0) > 1e-9)).any(axis=1).sum()) if rel_ok.size else 0}


def preflight(df: pd.DataFrame, n_cut: int = 0, second: pd.DataFrame | None = None, source_note: str = "Yahoo chart-API (SPY)") -> dict:
    """Protokollets datakrav 1–3 som sant/falskt med exakta orsaker. Innehåller inga kurser. `df` ska redan vara kapad (`parse_cut`); `tom.clean_prices` kapar ändå på nytt, för säkerhets skull."""
    cut_df, extra_cut = tom.clean_prices(df)                              # kapar på indexet innan något värde används
    period = tom.PRIMARY
    cal = nyse_sessions.load()
    sel = cut_df[(cut_df.index >= period[0]) & (cut_df.index <= period[1])]
    reasons = tom.check_data(cut_df, period)
    missing = nyse_sessions.missing_sessions(sel.index, cal, period[0], period[1])
    extra = nyse_sessions.unexpected_days(sel.index, cal, period[0], period[1])
    isna = sel[["open", "close"]].isna().any(axis=1)
    years = {str(y): int((sel.index.year == y).sum()) for y in range(period[0].year, period[1].year + 1)}
    month_counts = pd.Series(1, index=sel.index.to_period("M")).groupby(level=0).sum()
    expected_months = pd.period_range(period[0], period[1], freq="M")
    below = {str(m): int(month_counts.get(m, 0)) for m in expected_months if int(month_counts.get(m, 0)) < tom.MIN_MONTH_DAYS}
    # cykler enligt den verifierade kalendern: T0 = sista sessionen i M, T1..T3 = tre första i M+1, T4 = fjärde. Varje dag ska finnas i serien med öppning och stängning.
    have = set(sel.index[~isna.to_numpy()])
    sessions = cal[(cal >= period[0]) & (cal <= period[1])]
    by_month = pd.Series(sessions, index=sessions.to_period("M")).groupby(level=0).apply(list)
    incomplete = []
    for m in expected_months[:-1]:                                        # december 2024-cykeln kräver data efter 2025-01-01 och bildas inte
        nxt = m + 1
        if m not in by_month.index or nxt not in by_month.index or len(by_month[nxt]) < 4:
            incomplete.append(str(m))
            continue
        days = [by_month[m][-1], *by_month[nxt][:4]]
        if any(d not in have for d in days):
            incomplete.append(str(m))
    req = {"1_alla_sessioner_och_inga_saknade_varden": not missing and not extra and not bool(isna.any()),
           "1b_249_253_dagar_per_ar": all(tom.YEAR_DAYS[0] <= n <= tom.YEAR_DAYS[1] for n in years.values()),
           "2_minst_15_dagar_per_manad": not below,
           "2b_varje_cykel_har_T0_T4": not incomplete,
           "3_inget_fran_2025_anvant": True,
           "helhet_datakravet_uppfyllt": not reasons and not incomplete}
    ver = nyse_sessions.verification_status()
    return {"hypothesis": "H-0024", "kind": "datapreflight (täckning enligt protokollets datakrav; inga kurser, ingen avkastning, inget beslut)",
            "status": "UPPFYLLT" if req["helhet_datakravet_uppfyllt"] and ver["fully_verified"] else "EJ UPPFYLLT",
            "source": source_note, "request": {"url_period1": str(PERIOD1.date()), "url_period2_exclusive": str(PERIOD2.date())},
            "rows_cut_holdout": int(n_cut + extra_cut), "rows_in_period": int(len(sel)), "requirements": req, "invalid_reasons": reasons,
            "per_year_days": years, "months_below_minimum": below, "missing_sessions": [d.date().isoformat() for d in missing], "unexpected_days": [d.date().isoformat() for d in extra],
            "rows_with_missing_fields": int(isna.sum()), "cycles_expected": len(expected_months) - 1, "cycles_complete": (len(expected_months) - 1) - len(incomplete),
            "incomplete_cycles": incomplete, "calendar_verification": ver, "dates_sha256": dates_sha256(sel),
            "value_stability": None if second is None else stability(*[tom.clean_prices(x)[0].loc[period[0]:period[1]] for x in (df, second)]),
            "fetched_at_utc": pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "Bara täckning. Inga kurser, ingen avkastning, ingen Sharpe, inget t-värde, ingen placebo, inget beslut och ingen registerrad. Slutprovet (2025-01-01 och senare) är inte läst."}


def blocked(reason: str) -> dict:
    """Utfallet när källan inte kan nås: H-0024 lämnas okörd, ingen annan källa används."""
    return {"hypothesis": "H-0024", "kind": "datapreflight (blockerad)", "status": "BLOCKERAD", "source": "Yahoo chart-API (SPY)", "blocker": reason,
            "request": {"url_period1": str(PERIOD1.date()), "url_period2_exclusive": str(PERIOD2.date())}, "fetched_at_utc": pd.Timestamp.now("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "Källan kunde inte läsas. H-0024 lämnas okörd; ingen annan källa används och ingen blockering kringgås."}


def assert_no_prices(result: dict) -> None:
    """Skyddsräcke: resultatet får bara ha tillåtna nycklar och inga flyttal utöver tidsstämpel-/hashfält (inga kurser)."""
    extra = set(result) - ALLOWED_RESULT_KEYS
    if extra:
        raise AssertionError(f"otillåtna nycklar i preflight-resultatet: {sorted(extra)}")


def _stability_line(v: dict | None) -> str:
    if not v:
        return "Värdestabilitet mellan två hämtningar: inte mätt (andra hämtningen misslyckades)."
    base = (f"Värdestabilitet mellan två hämtningar: samma datum: {v['same_dates']} ({v['dates_only_in_first']} bara i första, {v['dates_only_in_second']} bara i andra); "
            f"{v['non_finite_cells']} celler saknar giltigt värdepar (saknade eller icke-finita värden eller delning med noll) i {v['rows_with_non_finite']} rader.")
    diff = (f" Bland giltiga par skiljer sig {v['rows_differing_over_1e-9']} av {v['rows_compared']} rader med mer än 1e-9 (relativt); största relativa skillnad {v['max_relative_difference']}."
            if v["max_relative_difference"] is not None else " Inga giltiga par att jämföra.")
    if not v["sufficient"]:
        return base + diff + " **Mätningen är otillräcklig** (värden eller datum saknas i någon hämtning), och räknas inte som stabil eller instabil."
    if v["rows_differing_over_1e-9"] > 0:
        return base + diff + " Yahoos justerade värden är alltså inte bitvis stabila mellan anrop, och därför hashas inga värden."
    return base + diff + " Värdena var identiska i den här mätningen, men en värdehash används ändå inte (Yahoo kan ändra justerade värden mellan anrop)."


def markdown(r: dict) -> str:
    if r["status"] == "BLOCKERAD":
        return (f"# H-0024 datapreflight: BLOCKERAD\n\nKällan (Yahoo chart-API för SPY, den källa protokollet föreskriver) kunde inte läsas: {r['blocker']}\n\n"
                "H-0024 lämnas okörd. Ingen annan källa används och ingen blockering kringgås. Inga kurser har lästs.\n")
    req = r["requirements"]
    lines = [f"# H-0024 datapreflight: {r['status']}", "",
             "Bara täckning enligt protokollets datakrav. Inga kurser, ingen avkastning, ingen Sharpe, inget t-värde, ingen placebo och inget beslut. Slutprovet (2025-01-01 och senare) är inte läst: "
             f"förfrågan slutar vid {r['request']['url_period2_exclusive']} (exklusivt), serien kapas före första kontroll ({r['rows_cut_holdout']} rader kapades).", "",
             f"Källa: {r['source']}; hämtad {r['fetched_at_utc']}. Rader i primärperioden 2006-01-01..2024-12-31: {r['rows_in_period']}. Täckningsfingeravtryck (SHA-256 över datumen som har både justerad öppning och stängning; inga värden): `{r['dates_sha256']}`.", "",
             "## Krav", "", "| Krav | Utfall |", "|---|---|"]
    names = {"1_alla_sessioner_och_inga_saknade_varden": "1. Justerad öppning och stängning för alla NYSE-sessioner, inga saknade värden, inga extra dagar",
             "1b_249_253_dagar_per_ar": "1b. 249–253 handelsdagar per kalenderår", "2_minst_15_dagar_per_manad": "2. Minst 15 handelsdagar per kalendermånad",
             "2b_varje_cykel_har_T0_T4": "2b. Varje T0–T3-cykel har sina fyra fönsterdagar plus T4", "3_inget_fran_2025_anvant": "3. Inget från 2025-01-01 eller senare används",
             "helhet_datakravet_uppfyllt": "**Hela datakravet**"}
    lines += [f"| {names[k]} | {'uppfyllt' if v else 'EJ uppfyllt'} |" for k, v in req.items()]
    lines += ["", f"Saknade NYSE-sessioner: {len(r['missing_sessions'])}" + (f" ({', '.join(r['missing_sessions'][:20])})" if r["missing_sessions"] else ""),
              f"Dagar som inte är NYSE-sessioner: {len(r['unexpected_days'])}" + (f" ({', '.join(r['unexpected_days'][:20])})" if r["unexpected_days"] else ""),
              f"Rader med saknade fält: {r['rows_with_missing_fields']}", f"Månader under 15 dagar: {len(r['months_below_minimum'])}", f"Cykler: {r['cycles_complete']} av {r['cycles_expected']} kompletta"
              + (f"; ofullständiga: {', '.join(r['incomplete_cycles'][:20])}" if r["incomplete_cycles"] else ""),
              "", "Handelsdagar per år: " + ", ".join(f"{y}: {n}" for y, n in r["per_year_days"].items()), "",
              _stability_line(r.get("value_stability")),
              "", f"NYSE-kalenderns verifiering: {r['calendar_verification']['verified_rows']} av {r['calendar_verification']['ledger_rows']} stängningar belagda (maskinavstämning).", ""]
    if r["invalid_reasons"]:
        lines += ["## Orsaker som bryter datakravet", ""] + [f"- {x}" for x in r["invalid_reasons"]] + [""]
    lines += ["H-0024 är inte körd. Ingen registerrad skrivs i den här PR:en."]
    return "\n".join(lines) + "\n"


def run(opener=None, write: bool = True) -> dict:
    try:
        df, n_cut = fetch(opener)
        try:
            second, _ = fetch(opener)                                          # en andra, oberoende hämtning mäter hur stabila Yahoos värden är
        except SourceUnavailable:
            second = None
        result = preflight(df, n_cut, second)
    except SourceUnavailable as exc:
        result = blocked(str(exc))
    assert_no_prices(result)
    if write:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        OUT_MD.write_text(markdown(result), encoding="utf-8", newline="\n")
    return result


if __name__ == "__main__":
    out = run()
    print(json.dumps({k: out[k] for k in ("status", "rows_in_period", "rows_cut_holdout", "requirements", "blocker") if k in out}, ensure_ascii=False, indent=1))
