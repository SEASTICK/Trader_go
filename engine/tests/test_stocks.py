import json

from traderlab.data import stocks


def test_tiingo_used_when_key_present(tmp_path, monkeypatch):
    monkeypatch.setenv("TIINGO_API_KEY", "k")
    monkeypatch.setenv("TIINGO_SLEEP", "0")
    seen = []
    def opener(req):
        seen.append(req.full_url)
        return (b"date,close,high,low,open,volume,adjClose,adjHigh,adjLow,adjOpen,adjVolume,divCash,splitFactor\n"
                b"2024-01-02T00:00:00.000Z,10,11,9,10,100,5,5.5,4.5,5,200,0,1\n")
    df = stocks.load_prices("BRK.B", tmp_path, opener)
    assert "tiingo/daily/BRK-B/prices" in seen[0] and "token=k" in seen[0]
    assert df.iloc[0].to_dict() == {"open": 5.0, "high": 5.5, "low": 4.5, "close": 5.0, "volume": 200.0}
    assert str(df.index.tz) == "UTC"


def test_prices_parse_and_cache(tmp_path, monkeypatch):
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    monkeypatch.setenv("PRICE_SOURCE", "stooq")
    calls = []
    def opener(req):
        calls.append(req.full_url)
        if "aapl" in req.full_url:
            return b"Date,Open,High,Low,Close,Volume\n2024-01-02,10,11,9,10.5,100\n2024-01-03,10.5,12,10,11,200\n"
        return b"No data"
    df = stocks.load_prices("AAPL", tmp_path, opener)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"] and len(df) == 2
    assert str(df.index.tz) == "UTC"
    assert stocks.load_prices("XXXX", tmp_path, opener) is None
    stocks.load_prices("AAPL", tmp_path, opener)
    assert len(calls) == 2   # cachad


def test_brk_b_symbol():
    assert stocks.stooq_symbol("BRK/B") == "brk-b"


def test_map_cusips_batches_and_caches(tmp_path):
    sent = []
    def opener(req):
        body = json.loads(req.data)
        sent.append(len(body))
        return json.dumps([{"data": [{"ticker": "T" + b["idValue"][:3], "marketSector": "Equity"}]} if b["idValue"] != "BAD"
                           else {"warning": "No identifier found."} for b in body]).encode()
    cus = [f"{i:03d}000000" for i in range(12)] + ["BAD"]
    m = stocks.map_cusips(cus, tmp_path, opener)
    assert sent == [10, 3] and m["BAD"] is None and m["000000000"] == "T000"
    stocks.map_cusips(cus, tmp_path, opener)
    assert sent == [10, 3]


def test_limit_message_is_not_cached(tmp_path, monkeypatch):
    import pytest
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    monkeypatch.setenv("PRICE_SOURCE", "stooq")
    def opener(req):
        return b"Exceeded the daily hits limit"
    with pytest.raises(stocks.PriceSourceUnavailable):
        stocks.load_prices("AAPL", tmp_path, opener)
    assert not (tmp_path / "raw" / "stooq" / "aapl.csv").exists()


def test_network_error_means_source_unavailable(tmp_path, monkeypatch):
    import pytest
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    monkeypatch.setenv("PRICE_SOURCE", "stooq")
    def opener(req):
        raise TimeoutError("timed out")
    with pytest.raises(stocks.PriceSourceUnavailable):
        stocks.load_prices("AAPL", tmp_path, opener)


def _yahoo(ts, o, c, adj):
    return json.dumps({"chart": {"result": [{"meta": {"exchangeTimezoneName": "America/New_York"}, "timestamp": ts,
        "indicators": {"quote": [{"open": o, "high": o, "low": o, "close": c, "volume": [100] * len(ts)}],
                       "adjclose": [{"adjclose": adj}]}}], "error": None}}).encode()


def test_yahoo_is_default_without_key_and_adjusts_for_dividends(tmp_path, monkeypatch):
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    monkeypatch.delenv("PRICE_SOURCE", raising=False)
    seen = []
    def opener(req):
        seen.append(req.full_url)
        # 2024-01-02 och 2024-01-03 kl 14:30 UTC (börsöppning i New York); andra dagen saknar data
        return _yahoo([1704205800, 1704292200, 1704378600], [10.0, 20.0, None], [10.0, 20.0, None], [5.0, 20.0, None])
    df = stocks.load_prices("BRK.B", tmp_path, opener)
    assert "chart/BRK-B?" in seen[0]
    assert list(df.index.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"] and str(df.index.tz) == "UTC"
    assert df.iloc[0]["open"] == 5.0 and df.iloc[0]["close"] == 5.0 and df.iloc[1]["open"] == 20.0
    stocks.load_prices("BRK.B", tmp_path, opener)
    assert len(seen) == 1   # cachad


def test_yahoo_unknown_ticker_is_none_but_errors_are_not_cached(tmp_path, monkeypatch):
    import urllib.error
    import pytest
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    monkeypatch.delenv("PRICE_SOURCE", raising=False)
    def missing(req):
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
    assert stocks.load_prices("GONE", tmp_path, missing) is None
    def limited(req):
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
    with pytest.raises(stocks.PriceSourceUnavailable):
        stocks.load_prices("AAPL", tmp_path, limited)
    def html(req):
        return b"<html>blocked</html>"
    with pytest.raises(stocks.PriceSourceUnavailable):
        stocks.load_prices("AAPL", tmp_path, html)
    assert not (tmp_path / "raw" / "yahoo" / "AAPL.json").exists()
