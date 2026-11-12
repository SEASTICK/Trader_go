"""Kartläggning av källor för en oberoende uppföljning av kassa-och-termin-idén (basis, H-0020).

Frågan: vilka daterade terminer (med fast förfall) och vilken spot-referens kan hämtas **utan betaltjänst**, med
tidsstämplade priser, och hur stor är täckningen punktvis? Modulen hämtar bara kontraktslistor och täckning
(månadsfiler, första och sista dag, luckor). Den hämtar inga priser för analys, kör inget backtest och läser inget
slutprov. Resultatet är ett underlag för beslut, inte en strategi.

Varje källa är en funktion som tar `opener(url) -> bytes` och returnerar en ordbok, så att allt kan testas utan nätverk.
Källor som inte nås anges som `reachable: false` med felet, och gissas aldrig fram.

Körs: `python -m traderlab.data.basis_sources --sources binance deribit bitmex bybit bitstamp fred okx`.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?delimiter=/&prefix="
MONTHS_RE = re.compile(r"-(\d{4})-(\d{2})\.zip$")
EXPIRY_RE = re.compile(r"^(?P<base>[A-Z0-9]+?)(?P<quote>USDT|USD)_(?P<ymd>\d{6})$")   # BNBUSD är BNB mot USD, inte BN mot BUSD


def default_opener(url: str, headers: dict | None = None, tries: int = 4) -> bytes:
    """Hämtar en URL med omförsök vid tillfälliga nätverksfel (2, 4, 8 s). HTTP-fel (till exempel 404) försöks inte om."""
    req = urllib.request.Request(url, headers={"User-Agent": "TraderGo research (data survey)", **(headers or {})})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError:
            raise
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(2 * 2 ** attempt)
    raise RuntimeError("oåtkomlig")


def _attempt(fn, *a, **k) -> dict:
    """Kör en källprob; fel blir ett resultat (`reachable: false`), inte ett avbrott."""
    try:
        return {"reachable": True, **fn(*a, **k)}
    except Exception as exc:   # noqa: BLE001 - alla nätverksfel ska redovisas
        return {"reachable": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


# ------------------------------------------------------------------ Binance (data.binance.vision)

def s3_list(prefix: str, opener=default_opener) -> tuple[list[str], list[str]]:
    """(delprefix, nycklar) under ett prefix i Binances publika arkiv, med sidindelning."""
    prefixes, keys, marker = [], [], ""
    while True:
        xml = opener(LIST + urllib.parse.quote(prefix) + (f"&marker={urllib.parse.quote(marker)}" if marker else "")).decode()
        pre = re.findall(r"<Prefix>([^<]+)</Prefix>", xml)
        pre = [p for p in pre if p != prefix]
        ks = re.findall(r"<Key>([^<]+)</Key>", xml)
        prefixes += pre
        keys += ks
        if "<IsTruncated>true</IsTruncated>" in xml and (pre or ks):
            marker = (ks or pre)[-1]
        else:
            return prefixes, keys


def month_span(keys: list[str]) -> dict:
    """Första och sista månad och antal saknade månader (luckor) ur en lista av .zip-nycklar."""
    ms = sorted({(int(m.group(1)), int(m.group(2))) for k in keys if (m := MONTHS_RE.search(k))})
    if not ms:
        return {"files": 0}
    expected = (ms[-1][0] - ms[0][0]) * 12 + ms[-1][1] - ms[0][1] + 1
    return {"files": len(ms), "first_month": f"{ms[0][0]}-{ms[0][1]:02d}", "last_month": f"{ms[-1][0]}-{ms[-1][1]:02d}",
            "missing_months": expected - len(ms)}


def expiry_date(ymd: str) -> str:
    return f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:]}"


def binance_market(market: str, opener=default_opener) -> dict:
    """Daterade terminer i USDⓈ-M (`um`) eller COIN-M (`cm`): per underliggande: kontrakt, förfall och dagsfilernas täckning."""
    base = f"data/futures/{market}/monthly/klines/"
    syms, _ = s3_list(base, opener)
    dated: dict[str, list[str]] = {}
    for p in syms:
        name = p[len(base):].strip("/")
        m = EXPIRY_RE.match(name)
        if m:
            dated.setdefault(m.group("base"), []).append(name)
    out = {}
    for und, names in sorted(dated.items()):
        names.sort(key=lambda n: n.rsplit("_", 1)[1])
        cover, short = [], []
        for n in names:
            _, keys = s3_list(f"{base}{n}/1d/", opener)
            span = month_span([k for k in keys if k.endswith(".zip")])
            cover.append({"contract": n, "expiry": expiry_date(n.rsplit("_", 1)[1]), **span})
            if span.get("missing_months"):
                short.append(n)
        out[und] = {"contracts": len(names), "first_expiry": cover[0]["expiry"], "last_expiry": cover[-1]["expiry"],
                    "contracts_with_missing_months": short, "coverage": cover}
    return {"market": market, "underlyings": out}


def binance_spot_reference(underlyings: list[str], opener=default_opener) -> dict:
    """Finns spot-referens (USDT-par) med dagsfiler, och från vilken månad?"""
    res = {}
    for und in underlyings:
        _, keys = s3_list(f"data/spot/monthly/klines/{und}USDT/1d/", opener)
        res[und] = month_span([k for k in keys if k.endswith(".zip")])
    return res


def binance(opener=default_opener) -> dict:
    um, cm = binance_market("um", opener), binance_market("cm", opener)
    und = sorted(set(um["underlyings"]) | set(cm["underlyings"]))
    return {"um_dated_futures": um, "cm_dated_futures": cm, "spot_reference": binance_spot_reference(und, opener)}


# ------------------------------------------------------------------ Deribit (publikt API)

def _ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def deribit(opener=default_opener, currencies=("BTC", "ETH"), pause: float = 0.2) -> dict:
    """Utgångna och aktiva daterade terminer i Deribit, och om dagsstaplar finns för ett utgånget kontrakt."""
    out = {}
    for cur in currencies:
        url = f"https://www.deribit.com/api/v2/public/get_instruments?currency={cur}&kind=future&expired=true"
        res = json.loads(opener(url))["result"]
        dated = [r for r in res if not r["instrument_name"].endswith("PERPETUAL")]
        dated.sort(key=lambda r: r["expiration_timestamp"])
        sample = {}
        if dated:
            r = dated[len(dated) // 2]
            q = (f"https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name={r['instrument_name']}"
                 f"&start_timestamp={r['creation_timestamp']}&end_timestamp={r['expiration_timestamp']}&resolution=1D")
            time.sleep(pause)
            d = json.loads(opener(q))["result"]
            ticks = d.get("ticks", [])
            life_days = max(1, (r["expiration_timestamp"] - r["creation_timestamp"]) // 86_400_000)
            sample = {"instrument": r["instrument_name"], "life_days": life_days, "daily_bars": len(ticks),
                      "first_bar": _ts(ticks[0]) if ticks else None, "last_bar": _ts(ticks[-1]) if ticks else None,
                      "has_ohlcv": all(k in d for k in ("open", "high", "low", "close", "volume"))}
        out[cur] = {"expired_dated_contracts": len(dated),
                    "first_expiry": _ts(dated[0]["expiration_timestamp"]) if dated else None,
                    "last_expiry": _ts(dated[-1]["expiration_timestamp"]) if dated else None,
                    "sample_coverage": sample}
    return {"currencies": out}


# ------------------------------------------------------------------ BitMEX (publikt API och publik datalagring)

def _head(url: str) -> tuple[int, int | None]:
    """(statuskod, längd) för en HEAD-förfrågan, utan att hämta filen."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "TraderGo research (data survey)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, int(r.headers.get("Content-Length") or 0) or None


def bitmex_files(head=_head) -> dict:
    """Finns BitMEX publika dagsfiler med alla affärer (inklusive utgångna terminer)? Bara förekomst och storlek."""
    out = {}
    for day in ("20170331", "20200327", "20241227"):
        url = f"https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data/trade/{day}.csv.gz"
        try:
            status, length = head(url)
            out[day] = {"available": status == 200, "bytes": length}
        except Exception as exc:   # noqa: BLE001
            out[day] = {"available": False, "error": f"{type(exc).__name__}: {str(exc)[:100]}"}
    return {"public_trade_files": out,
            "note": "Affärsfiler, inte dagsstaplar: dagsstaplar för daterade terminer måste byggas ur alla affärer."}


def bitmex_api(opener=default_opener, pause: float = 2.5) -> dict:
    """Publika API:et (kan svara 403 från vissa servrar; det kringgås aldrig)."""
    flt = urllib.parse.quote(json.dumps({"typ": "FFCCSX"}))
    rows = json.loads(opener(f"https://www.bitmex.com/api/v1/instrument?filter={flt}&columns=symbol,rootSymbol,expiry,listing,state,underlying&count=500"))
    rows = [r for r in rows if r.get("expiry")]
    rows.sort(key=lambda r: r["expiry"])
    by_root: dict[str, list] = {}
    for r in rows:
        by_root.setdefault(r.get("rootSymbol", "?"), []).append(r)
    sample = {}
    old = [r for r in rows if r["expiry"] < "2021-01-01"]
    if old:
        r = old[len(old) // 2]
        time.sleep(pause)
        q = (f"https://www.bitmex.com/api/v1/trade/bucketed?binSize=1d&partial=false&symbol={r['symbol']}"
             f"&count=500&reverse=false&startTime={urllib.parse.quote(r.get('listing') or r['expiry'])}")
        bars = json.loads(opener(q))
        sample = {"instrument": r["symbol"], "listing": r.get("listing"), "expiry": r["expiry"], "daily_bars": len(bars),
                  "first_bar": bars[0]["timestamp"] if bars else None, "last_bar": bars[-1]["timestamp"] if bars else None}
    return {"dated_contracts_by_root": {k: {"contracts": len(v), "first_expiry": v[0]["expiry"][:10], "last_expiry": v[-1]["expiry"][:10]}
                                        for k, v in by_root.items()}, "sample_daily_coverage": sample}


# ------------------------------------------------------------------ Binance COIN-M: täckning och handelsbarhet

CM_UNDERLYINGS = ("BTC", "ETH", "ADA", "BCH", "BNB", "DOT", "LINK", "LTC", "XRP")   # minst 20 daterade kontrakt vardera
CONTRACT_USD = {"BTC": 100.0}                                                       # övriga 10 USD per kontrakt (Binance dokumentation, ej hämtad här)
CM_START, CM_END = "2020-08", "2024-12"                                             # månader som hämtas. Slutprovet (2025+) hämtas aldrig.
FRONT_MIN_DAYS = 14                                                                  # som H-0020: närmaste kontrakt med mer än 14 dagar kvar


def _cm(survey: dict) -> dict:
    """COIN-M-delen ur Binance-kartläggningen (antingen hela rapporten eller bara binance-källan)."""
    src = survey.get("sources", {}).get("binance", survey)
    return src["cm_dated_futures"]["underlyings"]


def fetch_cm(data_dir: Path, survey: dict, workers: int = 6) -> None:
    """Hämtar dagsfiler (1d) för COIN-M-kontrakten i `survey` (binance.cm_dated_futures), bara till och med 2024-12."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from . import binance as bn
    lock, orig = threading.Lock(), bn._append_manifest

    def locked(*a, **k):
        with lock:
            return orig(*a, **k)
    bn._append_manifest = locked
    names = [c["contract"] for u in CM_UNDERLYINGS for c in _cm(survey)[u]["coverage"] if c["expiry"] < "2026-01-01"]

    def one(n):
        for attempt in range(4):
            try:
                bn.fetch("cm", n, "1d", CM_START, CM_END, data_dir)
                return
            except OSError:
                time.sleep(3 * (attempt + 1))
    try:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(one, names))
    finally:
        bn._append_manifest = orig


def cm_liquidity(data_dir: Path, survey: dict) -> dict:
    """Per underliggande: kontrakt, dagsstaplar, luckor och handelsbarhet för det närmaste kontraktet (volym i USD)."""
    import numpy as np
    import pandas as pd

    from . import binance as bn
    lo, hi = pd.Timestamp("2020-09-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")
    out = {}
    for und in CM_UNDERLYINGS:
        size = CONTRACT_USD.get(und, 10.0)
        frames, per_contract = {}, []
        for c in _cm(survey)[und]["coverage"]:
            try:
                df = bn.load("cm", c["contract"], "1d", data_dir, start=lo, end=hi)
            except FileNotFoundError:
                per_contract.append({"contract": c["contract"], "bars": 0})
                continue
            full = (df.index[-1] - df.index[0]).days + 1
            frames[c["contract"]] = df
            per_contract.append({"contract": c["contract"], "bars": len(df), "first_bar": str(df.index[0].date()),
                                 "last_bar": str(df.index[-1].date()), "missing_days": int(full - len(df)),
                                 "zero_volume_days": int((df["volume"] == 0).sum())})
        # Närmaste kontrakt med mer än 14 dagar kvar, per dag: dagens volym i USD (kontrakt × kontraktsstorlek).
        days = sorted({d for df in frames.values() for d in df.index})
        front_usd = []
        for d in days:
            live = [(pd.Timestamp(expiry_date(n.rsplit("_", 1)[1]), tz="UTC"), n) for n, df in frames.items() if d in df.index]
            live = sorted(x for x in live if (x[0] - d).days > FRONT_MIN_DAYS)
            if live:
                front_usd.append(float(frames[live[0][1]].at[d, "volume"]) * size)
        a = np.array(front_usd) if front_usd else np.array([0.0])
        out[und] = {"contracts": len(per_contract), "contracts_with_data": len(frames), "bars": int(sum(x["bars"] for x in per_contract)),
                    "missing_days": int(sum(x.get("missing_days", 0) for x in per_contract)),
                    "front_contract_days": len(front_usd), "front_median_daily_usd_volume": float(np.median(a)),
                    "front_p10_daily_usd_volume": float(np.percentile(a, 10)), "front_share_zero_volume_days": float((a == 0).mean()),
                    "assumed_contract_size_usd": size, "contracts_detail": per_contract}
    return out


def binance_api(opener=default_opener) -> dict:
    """Kan Binances officiella API fylla arkivets lucka 2023-08-28 till 2023-08-31 för ett utgånget COIN-M-kontrakt?
    (Från vissa platser svarar API:et 451; det kringgås aldrig.)"""
    out = {}
    for sym in ("BTCUSD_230929", "ETHUSD_230929"):
        url = (f"https://dapi.binance.com/dapi/v1/klines?symbol={sym}&interval=1d&startTime=1693094400000&endTime=1693699200000")
        try:
            rows = json.loads(opener(url))
            out[sym] = {"bars": len(rows), "first": _ts(rows[0][0]) if rows else None, "last": _ts(rows[-1][0]) if rows else None}
        except Exception as exc:   # noqa: BLE001
            out[sym] = {"error": f"{type(exc).__name__}: {str(exc)[:100]}"}
    return {"gap_fill_probe": out}


DOC_PAGES = {
    "developers_exchange_information": "https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api/Exchange-Information",
    "faq_pnl": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=3a55a23768cb416fb404f06ffedde4b2",
    "faq_margin_liquidation": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=be2c7d9d95b04a7e8044ed02dd7dfe5c",
    "faq_margin_liquidation_in": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=ceccfcfb4e3a45e3b48b0b1bb1a8ae46",
    "faq_delivery_settlement": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=a3401595e1734084959c61491bc0dbe3",
    "guide_coinm_2020": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=d33f37e2c7fe4da3b35ffc904e8fbab5",
    "explainer_coinm_2021": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=85eac2bba0b342819122dc9bd4745e9b",
    "announcement_fee_change_2023": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f4433fc2964b4c92998132f433edff7c",
}
DOC_KEYWORDS = ("contractSize", "deliveryDate", "CURRENT_QUARTER", "delist", "Contract Multiplier", "Unrealized", "unrealized", "Realized",
                "Mark Price", "Maintenance Margin", "Liquidation Price", "Margin Ratio", "Cross", "Isolated", "COIN-margined", "COIN-M",
                "Settlement Price", "settlement price", "Delivery", "delivery", "Contract Size", "contract size", "Index Price", "maker", "Maker", "taker", "Taker")


def _node_text(obj) -> str:
    """Löper igenom Binances artikelträd (`{"node": ..., "text"/"child": ...}`) och samlar ren text."""
    if isinstance(obj, list):
        return " ".join(_node_text(x) for x in obj)
    if isinstance(obj, dict):
        if obj.get("node") == "text":
            return obj.get("text", "")
        return _node_text(obj.get("child", []))
    return ""


def _strip(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text).replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text)


def _page_text(raw: str) -> str:
    if raw.lstrip().startswith("{"):
        try:
            data = json.loads(raw).get("data") or {}
            body = data.get("body")
            if isinstance(body, str):
                try:
                    return re.sub(r"\s+", " ", _node_text(json.loads(body))).strip()
                except ValueError:
                    return _strip(body)
            return re.sub(r"\s+", " ", json.dumps(data, ensure_ascii=False))
        except ValueError:
            pass
    return _strip(raw)


def binance_docs(opener=default_opener, window: int = 260, max_hits: int = 3, full_text: bool = False) -> dict:
    """Hämtar Binances egna dokumentationssidor och sparar korta utdrag (ren text) runt nyckelorden, så att
    faktapåståenden kan beläggas med primär källa. Svarar en sida med fel (till exempel 451) redovisas det, och inget gissas."""
    out = {}
    for name, url in DOC_PAGES.items():
        try:
            raw = opener(url).decode("utf-8", "replace")
        except Exception as exc:   # noqa: BLE001
            out[name] = {"url": url, "readable": False, "error": f"{type(exc).__name__}: {str(exc)[:100]}"}
            continue
        text = _page_text(raw)
        hits = {}
        for kw in DOC_KEYWORDS:
            idxs = [m.start() for m in re.finditer(re.escape(kw), text)][:max_hits]
            if idxs:
                hits[kw] = [text[max(0, i - window):i + window].strip() for i in idxs]
        out[name] = {"url": url, "readable": True, "characters": len(text), "excerpts": hits}
        if full_text:   # bara för läsning av granskaren, checkas inte in
            out[name]["text"] = text
    return out


# ------------------------------------------------------------------ Bybit, Bitstamp, FRED, OKX

def bybit(opener=default_opener) -> dict:
    html = opener("https://public.bybit.com/trading/").decode("utf-8", "replace")
    names = sorted(set(re.findall(r'href="([A-Z0-9\-]+)/"', html)))
    dated = [n for n in names if re.search(r"\d{2}$", n) and re.search(r"(H|M|U|Z)\d{2}$|-\d{2}[A-Z]{3}\d{2}$", n)]
    return {"symbols_listed": len(names), "dated_looking_symbols": dated[:40], "dated_count": len(dated)}


def bitstamp(opener=default_opener) -> dict:
    raw = json.loads(opener("https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=3&start=1315872000"))
    d = (raw.get("data") or {}).get("ohlc") or []
    return {"btcusd_first_daily_bar_from_2011-09-13": _ts(int(d[0]["timestamp"]) * 1000) if d else None, "bars_returned": len(d)}


def fred(opener=default_opener) -> dict:
    rows = opener("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3").decode().strip().splitlines()[1:]
    return {"series": "DTB3 (3-månaders amerikansk statsväxel)", "first": rows[0].split(",")[0], "last": rows[-1].split(",")[0], "rows": len(rows)}


def fred_text(opener=default_opener) -> dict:
    """Samma serie som ren text, om csv-sidan inte svarar."""
    lines = [l for l in opener("https://fred.stlouisfed.org/data/DTB3.txt").decode().splitlines() if re.match(r"^\d{4}-\d{2}-\d{2}", l)]
    return {"series": "DTB3 (3-månaders amerikansk statsväxel)", "first": lines[0].split()[0], "last": lines[-1].split()[0], "rows": len(lines)}


def okx(opener=default_opener) -> dict:
    live = json.loads(opener("https://www.okx.com/api/v5/public/instruments?instType=FUTURES&uly=BTC-USD"))["data"]
    try:
        old = json.loads(opener("https://www.okx.com/api/v5/market/history-candles?instId=BTC-USD-210326&bar=1D&limit=3"))["data"]
    except Exception as exc:   # noqa: BLE001
        old = f"{type(exc).__name__}"
    return {"live_dated_contracts_btc_usd": len(live), "expired_contract_candles": old if isinstance(old, str) else len(old)}


SOURCES = {"binance": binance, "binance_api": binance_api, "binance_docs": binance_docs, "binance_docs_text": lambda opener=default_opener: binance_docs(opener, full_text=True), "deribit": deribit, "bitmex_api": bitmex_api, "bitmex_files": lambda opener=None: bitmex_files(),
           "bybit": bybit, "bitstamp": bitstamp, "fred": fred, "fred_text": fred_text, "okx": okx}


def survey(sources: list[str], opener=default_opener) -> dict:
    return {"kind": "basis-source-survey", "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "Kartläggning av täckning, inga priser hämtade för analys och inget backtest. Slutprov (2025+) läses inte.",
            "sources": {s: _attempt(SOURCES[s], opener) for s in sources}}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--sources", nargs="+", default=list(SOURCES), choices=list(SOURCES))
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    d = survey(a.sources)
    folder = a.repo / "research" / "coverage"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'basis-sources{("-" + a.tag) if a.tag else ""}-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    path.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v.get("reachable") for k, v in d["sources"].items()}))
    print(path)


if __name__ == "__main__":
    main()
