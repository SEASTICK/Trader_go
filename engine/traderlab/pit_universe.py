"""Punkt-i-tid-underlag för Binance COIN-M-kvartalskontrakt.

Bygger en maskinläsbar tabell över varje kontraktsserie: när Binance offentligt meddelade listningen (daterad källa),
vilka underliggande som uttryckligen *inte* listades, vad dagsdatan visar (första/sista handlade stapel) och vad som är
verifierat respektive antaget. Inget pris- eller avkastningsurval används, och meddelanden daterade 2025 eller senare läses
inte. Körs: `python -m traderlab.pit_universe` från engine/ (läser research/coverage/*ann1* och *pit1*).
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .pit_observed import CUTOFF, expiry_of, is_last_friday_of_quarter_month, observed_all

SEVEN = ("ADA", "BCH", "BNB", "DOT", "LINK", "LTC", "XRP")
VANISHED = ("EOS", "ETC", "FIL", "TRX")          # listades 2020 men inte som 0625-serier: överlevnadsbias om de utelämnas
KNOWN = SEVEN + VANISHED + ("BTC", "ETH", "SOL")
NOT_TICKERS = {"USD", "COIN", "AND", "UTC", "COINM", "NOTES", "THE"}
GENERAL_SIZE_USD = 10      # Binances regel för altcoin-kontrakt (guide 2020-06-12). Kontraktsspecifik storlek saknas: ett ANTAGANDE.


def _tickers(segment: str) -> list[str]:
    return [t for t in re.findall(r"\b[A-Z]{2,5}\b", segment.replace("&amp;", "&")) if t not in NOT_TICKERS and t in KNOWN]


def resolve_expiry(mmdd: str, released: str) -> dt.date:
    """Första datum med denna månad och dag på eller efter meddelandedatumet."""
    r = dt.date.fromisoformat(released)
    month, day = int(mmdd[:2]), int(mmdd[2:])
    for year in (r.year, r.year + 1, r.year + 2):
        d = dt.date(year, month, day)
        if d >= r:
            return d
    raise ValueError(mmdd)


def parse_event(title: str, text: str, released: str, code: str) -> dict | None:
    """Läser ett listnings-/lanseringsmeddelande. Returnerar None om det inte är en COIN-M-kvartalslistning."""
    text = text.replace("&amp;", "&")
    underlyings, series = [], []
    m = re.search(r"(?i)will (?:launch|list) (.+?) (?:coin-margined )?quarterly (\d{4})(?: & (\d{4}))?", title.replace("&amp;", "&"))
    if m and re.search(r"(?i)quarterly (\d{4})", title) and "COIN-M" not in title and "USDⓈ-M" not in title:
        head = m.group(1)
        underlyings = re.findall(r"\b([A-Z]{2,5})USD\b", head) or _tickers(head)
        series = [m.group(2)] + ([m.group(3)] if m.group(3) else [])
    if not underlyings:   # texten: "will list BTC, ETH, ... Coin-margined Quarterly 0625"
        m = re.search(r"(?i)will list ([A-Z, &and]+?),? coin-?margined quarterly (\d{4})", text)
        if m:
            underlyings, series = _tickers(m.group(1)), [m.group(2)]
    if not underlyings:   # texten (2023-09 och senare): "COIN-M BTC, ETH, ... Quarterly 0329 Delivery Contracts"
        m = re.search(r"COIN-M ([A-Za-z, &]+?) Quarterly (\d{4}) Delivery Contracts", text)
        if m:
            underlyings, series = _tickers(m.group(1)), [m.group(2)]
    if not underlyings:
        return None
    not_listed = []
    n = re.search(r"(?i)notes?: ([A-Z, &and]+?) quarterly (\d{4}) contracts will not be listed", text)
    if n:
        not_listed = _tickers(n.group(1))
    return {"code": code, "released": released, "title": title, "underlyings": sorted(set(underlyings)),
            "series": [{"mmdd": s, "expiry": resolve_expiry(s, released).isoformat()} for s in series],
            "not_listed": sorted(set(not_listed))}


def load_events(coverage: Path) -> list[dict]:
    """Läser meddelandena (endast före 2025) ur ann1- och pit1-rapporterna."""
    ann = json.loads(sorted(coverage.glob("basis-sources-ann1-*.json"))[-1].read_text(encoding="utf-8"))["sources"]["binance_announcements"]
    pit = json.loads(sorted(coverage.glob("basis-sources-pit1-*.json"))[-1].read_text(encoding="utf-8"))["sources"]["binance_articles_pit"]
    texts = {a["code"]: a["text"] for a in pit["articles"] if a.get("text")}
    texts.update({a["code"]: a.get("text_head", "") for a in ann["articles"] if a["code"] not in texts})
    events = []
    for t in ann["titles"]:
        if t["released"] >= CUTOFF or t["code"] not in texts:
            continue
        ev = parse_event(t["title"], texts[t["code"]], t["released"], t["code"])
        if ev:
            events.append(ev)
    return sorted(events, key=lambda e: (e["released"], e["code"]))


def build_series(events: list[dict], obs: list[dict]) -> list[dict]:
    """En rad per (underliggande, förfall): meddelande + observerad data + vad som är verifierat eller antaget."""
    by_obs = {(o["underlying"], o["expiry"]): o for o in obs}
    announced: dict[tuple[str, str], dict] = {}
    not_listed: dict[tuple[str, str], dict] = {}
    for ev in events:
        for s in ev["series"]:
            for u in ev["underlyings"]:
                announced.setdefault((u, s["expiry"]), ev)       # det första (tidigaste) meddelandet gäller
            for u in ev["not_listed"]:
                not_listed.setdefault((u, s["expiry"]), ev)
    rows = []
    for key in sorted(set(announced) | set(not_listed) | {k for k in by_obs}, key=lambda k: (k[1], k[0])):
        u, expiry = key
        if u not in SEVEN + VANISHED:
            continue
        ev, o = announced.get(key), by_obs.get(key)
        if not ev and key not in not_listed and (o is None or not o["bars"]):
            continue    # tom mapp för en serie som börjar handlas först 2025 eller senare: ingen punkt-i-tid-uppgift före gränsen
        row = {"underlying": u, "expiry": expiry, "in_target_seven": u in SEVEN,
               "ordinary_expiry_rule": is_last_friday_of_quarter_month(dt.date.fromisoformat(expiry)),
               "announced_on": ev["released"] if ev else None, "announcement_code": ev["code"] if ev else None,
               "announcement_title": ev["title"] if ev else None,
               "explicitly_not_listed_on": not_listed[key]["released"] if key in not_listed else None,
               "contract_size_usd": GENERAL_SIZE_USD, "contract_size_status": "assumed_general_rule",
               "data_checked": o is not None}
        if o:
            row.update({k: o[k] for k in ("first_traded_bar", "last_traded_bar", "bars", "missing_days_between", "zero_volume_bars",
                                          "traded_runs", "missing_days", "zero_volume_days", "daily_filled_days", "gap_fill_unverified",
                                          "left_censored", "right_censored", "ended_before_expiry", "bars_after_expiry")})
            first = o["first_traded_bar"]
            row["days_from_announcement_to_first_trade"] = (
                (dt.date.fromisoformat(first) - dt.date.fromisoformat(ev["released"])).days if ev and first else None)
        row["status"] = _status(row, ev, o)
        rows.append(row)
    return rows


def _status(row: dict, ev: dict | None, o: dict | None) -> str:
    if row["explicitly_not_listed_on"] and not o:
        return "not_listed"
    if o and not o["bars"]:
        return "announced_no_bars_before_2025" if ev else "no_bars_no_announcement"
    if o and not ev:
        return "observed_without_announcement"
    if o and o["ended_before_expiry"]:
        return "ended_before_expiry"
    if o:
        return "announced_and_observed"
    return "announced_not_checked"


SOL_LAUNCH = "2024-08-14"     # SOLUSD COIN-M kvartal lanserades (meddelande d823b1df…, 2024-08-08): finns inte i de sju


def _has_traded_bar(r: dict, day: str) -> bool:
    """Sant bara om en verifierad stapel med volym > 0 finns *den dagen*. Intervallet mellan första och sista räcker inte:
    saknade dagar och nollvolymdagar innanför intervallet ger falskt, och en dag fylld ur dagsarkivet räknas bara om den
    verifierats (gapcheck.combined)."""
    return any(a <= day <= b for a, b in r.get("traded_runs") or [])


def _tradable(r: dict, day: str) -> bool:
    """Valbar först när serien var offentligt meddelad och en verifierad handelsstapel finns beslutsdagen."""
    return bool(r.get("data_checked") and r["status"] == "announced_and_observed" and r["announced_on"]
                and r["announced_on"] <= day and r["expiry"] > day and _has_traded_bar(r, day))


def no_verified_bar_reason(r: dict, day: str) -> str | None:
    """Varför en annonserad, aktiv serie ändå inte är valbar `day`: lucka, nollvolym eller oprövad luckfyllnad."""
    if not (r.get("data_checked") and r["announced_on"] and r["announced_on"] <= day < r["expiry"]):
        return None
    if r.get("first_traded_bar") and day < r["first_traded_bar"]:
        return "not_yet_traded"
    if _has_traded_bar(r, day):
        return None
    if day in (r.get("missing_days") or []):
        return "data_gap_unverified" if r.get("gap_fill_unverified") else "data_gap"
    if day in (r.get("zero_volume_days") or []):
        return "zero_volume"
    return "no_traded_bar"


def universe_at(rows: list[dict], day: str, underlyings: tuple[str, ...] = SEVEN) -> list[dict]:
    """Serier som kunde väljas vid beslutsdagen `day`, fail-closed: annonserade OCH redan handlade (första handlade stapel
    senast `day`), med granskad data, inte uttryckligen ej listade och inte utgångna. Annonserade men ännu ohandlade serier,
    serier utan granskad data och serier utan daterad annons returneras aldrig."""
    return [r for r in rows if r["underlying"] in underlyings and _tradable(r, day)]


def universe_report(rows: list[dict], day: str, underlyings: tuple[str, ...] = SEVEN) -> dict:
    """Som universe_at, men visar också vad som hölls utanför och om urvalet är ett efterhandsurval vid `day`."""
    chosen = universe_at(rows, day, underlyings)
    keys = {(r["underlying"], r["expiry"]) for r in chosen}
    sel = [r for r in rows if r["underlying"] in underlyings]
    return {
        "day": day, "tradable": chosen,
        "announced_not_yet_traded": [r for r in sel if no_verified_bar_reason(r, day) == "not_yet_traded"],
        # Aktiva, annonserade serier utan verifierad handelsstapel just den dagen: stoppar ett test som kräver dem
        "active_without_verified_bar": [{"underlying": r["underlying"], "expiry": r["expiry"], "reason": no_verified_bar_reason(r, day)}
                                        for r in sel if (r["underlying"], r["expiry"]) not in keys
                                        and no_verified_bar_reason(r, day) not in (None, "not_yet_traded")],
        "announced_without_checked_data": [r for r in rows if r["announced_on"] and r["announced_on"] <= day < r["expiry"]
                                           and not r.get("data_checked")],
        # Fyra underliggande (EOS, ETC, FIL, TRX) var aktiva t.o.m. 2021-03-26: de sju ensamma är då ett efterhandsurval.
        "hindsight_selection": hindsight_selection(rows, day, underlyings),
    }


def hindsight_selection(rows: list[dict], day: str, underlyings: tuple[str, ...] = SEVEN) -> bool:
    """Sant om en aktiv COIN-M-kvartalsserie hos en underliggande utanför urvalet fanns vid `day` (förutom BTC och ETH, som
    utesluts i förväg och inte av överlevnad). Gäller de fyra som försvann och SOL från lanseringen."""
    dropped = any(r["underlying"] in VANISHED and r["underlying"] not in underlyings and r["announced_on"]
                  and r["announced_on"] <= day < r["expiry"] for r in rows)
    return dropped or (day >= SOL_LAUNCH and "SOL" not in underlyings)


def hindsight_free_window(rows: list[dict]) -> tuple[str, str]:
    """Första beslutsdag utan efterhandsurval (efter sista aktiva förfall hos de fyra) och sista dag före SOL:s lansering."""
    last_vanished = max(r["expiry"] for r in rows if r["underlying"] in VANISHED and r["announced_on"])
    return last_vanished, SOL_LAUNCH


def summary(rows: list[dict]) -> dict:
    sev = [r for r in rows if r["in_target_seven"]]
    counts: dict[str, int] = {}
    for r in sev:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    first = {}
    for r in sev:
        if r["announced_on"] and (r["underlying"] not in first or r["announced_on"] < first[r["underlying"]]):
            first[r["underlying"]] = r["announced_on"]
    return {"series_seven": len(sev), "status_counts": counts, "first_announcement": first}


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    coverage = repo / "research" / "coverage"
    events = load_events(coverage)
    obs = observed_all(repo / "data", SEVEN)
    rows = build_series(events, obs)
    out = repo / "research" / "universe"
    out.mkdir(parents=True, exist_ok=True)
    (out / "coinm-pit-series.json").write_text(json.dumps({
        "kind": "coinm-pit-universe", "cutoff": CUTOFF, "summary": summary(rows),
        "hindsight_free_window": list(hindsight_free_window(rows)),
        "note": "Kontraktsstorlek är ett antagande (generell regel). Inget 2025+ och inget prisurval.", "series": rows},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    import csv
    with (out / "coinm-pit-series.csv").open("w", newline="", encoding="utf-8") as fh:
        cols = sorted({k for r in rows for k in r})
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows({k: (json.dumps(v) if isinstance(v, list) else v) for k, v in r.items()} for r in rows)
    (out / "coinm-pit-events.json").write_text(json.dumps(events, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary(rows), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
