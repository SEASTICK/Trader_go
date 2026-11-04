import json

from traderlab.data import stocks


def test_prices_parse_and_cache(tmp_path):
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
