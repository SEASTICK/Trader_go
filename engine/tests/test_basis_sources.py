"""Offline-tester för kartläggningen av basis-källor (inget nätverk)."""
import json

from traderlab.data import basis_sources as b


def _xml(prefixes=(), keys=(), truncated=False):
    return ("<ListBucketResult>" + "".join(f"<Prefix>{p}</Prefix>" for p in prefixes) + "".join(f"<Key>{k}</Key>" for k in keys)
            + f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated></ListBucketResult>").encode()


def test_month_span_counts_missing_months():
    keys = [f"data/x/SYM-1d-{m}.zip" for m in ("2021-01", "2021-02", "2021-04")] + ["data/x/SYM-1d-2021-02.zip.CHECKSUM"]
    s = b.month_span(keys)
    assert s == {"files": 3, "first_month": "2021-01", "last_month": "2021-04", "missing_months": 1}
    assert b.month_span([]) == {"files": 0}


def test_s3_list_follows_pagination():
    pages = {"": _xml(keys=["a-2021-01.zip"], truncated=True), "a-2021-01.zip": _xml(keys=["a-2021-02.zip"])}

    def opener(url):
        marker = url.split("&marker=")[1] if "&marker=" in url else ""
        return pages[marker.replace("%2F", "/")]
    _, keys = b.s3_list("p/", opener)
    assert keys == ["a-2021-01.zip", "a-2021-02.zip"]


def test_binance_market_groups_dated_contracts_and_ignores_perpetuals():
    base = "data/futures/cm/monthly/klines/"
    listing = {base: _xml(prefixes=[base + "BTCUSD_210326/", base + "BTCUSD_210625/", base + "BTCUSD_PERP/", base + "ETHUSD_210326/"]),
               base + "BTCUSD_210326/1d/": _xml(keys=[f"{base}BTCUSD_210326/1d/BTCUSD_210326-1d-2021-0{m}.zip" for m in (1, 2, 3)]),
               base + "BTCUSD_210625/1d/": _xml(keys=[f"{base}BTCUSD_210625/1d/BTCUSD_210625-1d-2021-0{m}.zip" for m in (3, 6)]),
               base + "ETHUSD_210326/1d/": _xml(keys=[])}

    def opener(url):
        from urllib.parse import unquote
        return listing[unquote(url.split("&prefix=")[1])]
    r = b.binance_market("cm", opener)["underlyings"]
    assert set(r) == {"BTC", "ETH"} and r["BTC"]["contracts"] == 2 and r["BTC"]["first_expiry"] == "2021-03-26"
    assert r["BTC"]["contracts_with_missing_months"] == ["BTCUSD_210625"]   # mars och juni utan april och maj
    assert r["ETH"]["coverage"][0]["files"] == 0


def test_unreachable_source_is_reported_not_guessed():
    def boom(url):
        raise OSError("blockerad")
    r = b.survey(["fred"], boom)["sources"]["fred"]
    assert r["reachable"] is False and "blockerad" in r["error"]


def test_deribit_parser_counts_expired_dated_futures_and_checks_bars():
    day = 86_400_000
    inst = [{"instrument_name": f"BTC-{n}", "creation_timestamp": 1_600_000_000_000, "expiration_timestamp": 1_600_000_000_000 + (i + 1) * 90 * day}
            for i, n in enumerate(["26MAR21", "25JUN21", "24SEP21"])] + [{"instrument_name": "BTC-PERPETUAL", "creation_timestamp": 0, "expiration_timestamp": 32503680000000}]

    def opener(url):
        if "get_instruments" in url:
            return json.dumps({"result": inst}).encode()
        ticks = [1_600_000_000_000 + i * day for i in range(80)]
        return json.dumps({"result": {"ticks": ticks, "open": [1] * 80, "high": [1] * 80, "low": [1] * 80, "close": [1] * 80, "volume": [1] * 80}}).encode()
    r = b.deribit(opener, currencies=("BTC",), pause=0)["currencies"]["BTC"]
    assert r["expired_dated_contracts"] == 3 and r["sample_coverage"]["has_ohlcv"] and r["sample_coverage"]["daily_bars"] == 80
    assert r["sample_coverage"]["life_days"] == 180


def test_bitmex_parser_groups_by_root_and_reports_public_trade_files():
    rows = [{"symbol": "XBTH20", "rootSymbol": "XBT", "expiry": "2020-03-27T12:00:00.000Z", "listing": "2019-09-27T12:00:00.000Z"},
            {"symbol": "XBTM20", "rootSymbol": "XBT", "expiry": "2020-06-26T12:00:00.000Z", "listing": "2019-12-27T12:00:00.000Z"},
            {"symbol": "ETHH21", "rootSymbol": "ETH", "expiry": "2021-03-26T12:00:00.000Z", "listing": "2020-09-25T12:00:00.000Z"}]

    def opener(url):
        if "/instrument?" in url:
            return json.dumps(rows).encode()
        if "trade/bucketed" in url:
            return json.dumps([{"timestamp": "2019-12-28T00:00:00.000Z"}] * 3).encode()
        if url.endswith("20170331.csv.gz"):
            raise OSError("nej")
        return b"gz"
    r = b.bitmex_api(opener, pause=0)
    assert r["dated_contracts_by_root"]["XBT"]["contracts"] == 2 and r["sample_daily_coverage"]["daily_bars"] == 3


def test_bitmex_files_report_availability_and_failures():
    def head(url):
        if "20170331" in url:
            raise OSError("403")
        return 200, 123
    r = b.bitmex_files(head)["public_trade_files"]
    assert r["20170331"]["available"] is False and r["20200327"] == {"available": True, "bytes": 123}
