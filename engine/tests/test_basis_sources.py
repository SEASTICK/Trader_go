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


def test_expiry_pattern_reads_bnb_as_bnb_not_bn_busd():
    m = b.EXPIRY_RE.match("BNBUSD_201225")
    assert m.group("base") == "BNB" and m.group("quote") == "USD"
    assert b.EXPIRY_RE.match("BTCUSDT_210326").group("quote") == "USDT"
    assert b.EXPIRY_RE.match("BTCUSD_PERP") is None


def test_binance_api_probe_reports_blocks_per_contract():
    import urllib.error

    def opener(url):
        if "BTCUSD" in url:
            return json.dumps([[1693180800000], [1693267200000]]).encode()
        raise urllib.error.HTTPError(url, 451, "restricted", {}, None)
    r = b.binance_api(opener)["gap_fill_probe"]
    assert r["BTCUSD_230929"] == {"bars": 2, "first": "2023-08-28", "last": "2023-08-29"}
    assert "451" in r["ETHUSD_230929"]["error"]


def test_report_tables_are_built_from_the_report_files():
    from traderlab.data import basis_report as r
    binance = {"um_dated_futures": {"underlyings": {"BTC": {"contracts": 2, "first_expiry": "2021-03-26", "last_expiry": "2021-06-25", "contracts_with_missing_months": []}}},
               "cm_dated_futures": {"underlyings": {"ADA": {"contracts": 3, "first_expiry": "2020-09-25", "last_expiry": "2021-03-26", "contracts_with_missing_months": ["x"]}}},
               "spot_reference": {"BTC": {"first_month": "2017-08"}, "ADA": {}}}
    t = r.dated_table(binance)
    assert "| USDⓈ-M | BTC | 2 | 2021-03-26 | 2021-06-25 | 0 | 2017-08 |" in t
    assert "| COIN-M | ADA | 3 | 2020-09-25 | 2021-03-26 | 1 | – |" in t
    liq = {u: {"contracts_with_data": 1, "bars": 10, "missing_days": 0, "front_contract_days": 5, "front_median_daily_usd_volume": 1_234_567.0,
               "front_p10_daily_usd_volume": 1000.0, "front_share_zero_volume_days": 0.0} for u in b.CM_UNDERLYINGS}
    assert "1 234 567" in r.liquidity_table(liq)
    reps = [{"sources": {"okx": {"reachable": True, "live_dated_contracts_btc_usd": 11, "expired_contract_candles": 0},
                          "bitmex": {"reachable": False, "error": "HTTPError: 403"}}}]
    st = r.sources_table(reps)
    assert "| bitmex | nej | HTTPError: 403 |" in st and "0 dagsstaplar för utgånget kontrakt" in st


def test_binance_docs_returns_excerpts_and_reports_unreadable_pages():
    import urllib.error

    def opener(url):
        if "developers.binance.com" in url:
            return b"<html><script>var a=1;</script><p>The contractSize is 100 for BTC. Liquidation uses the Mark Price.</p></html>"
        if "3a55" in url:
            body = json.dumps([{"node": "element", "child": [{"node": "text", "text": "Unrealized PnL of a short"}, {"node": "text", "text": "&nbsp;is in coin"}]}])
            return json.dumps({"data": {"body": body}}).encode()
        raise urllib.error.HTTPError(url, 451, "restricted", {}, None)
    r = b.binance_docs(opener, window=30)
    assert r["developers_exchange_information"]["readable"] and "contractSize" in r["developers_exchange_information"]["excerpts"]
    assert "var a=1" not in json.dumps(r["developers_exchange_information"])
    assert r["faq_pnl"]["readable"] and "Unrealized" in r["faq_pnl"]["excerpts"]
    assert "node" not in r["faq_pnl"]["excerpts"]["Unrealized"][0]   # ren text, inga JSON-tecken
    assert r["faq_margin_liquidation"]["readable"] is False and "451" in r["faq_margin_liquidation"]["error"]


def test_announcements_filtrerar_och_läser_relevanta_artiklar():
    import json as _json
    from traderlab.data import basis_sources as bs

    def opener(url, headers=None, tries=4):
        if "list/query" in url:
            page = int(url.split("pageNo=")[1].split("&")[0])
            if "catalogId=49" in url and page == 1:
                arts = [{"title": "Binance Futures Will Launch COIN-Margined ADAUSD Quarterly Contracts", "code": "abc", "releaseDate": 1600000000000},
                        {"title": "Binance Will List FOO", "code": "zzz", "releaseDate": 1600000000000}]
                return _json.dumps({"data": {"catalogs": [{"articles": arts}]}}).encode()
            return _json.dumps({"data": {"catalogs": [{"articles": []}]}}).encode()
        body = _json.dumps({"node": "root", "child": [{"node": "text", "text": "Each contract is worth 10 USD. Launch tomorrow."}]})
        return _json.dumps({"data": {"body": body}}).encode()

    out = bs.binance_announcements(opener, max_pages=3)
    assert out["matching_titles"] == 1 and out["read"] == 1
    art = out["articles"][0]
    assert art["released"] == "2020-09-13" and any("10 USD" in e for e in art["excerpts"])
