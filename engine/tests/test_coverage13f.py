import json
import urllib.error

from traderlab import coverage13f
from traderlab.data import ftd, sec13f, stocks


def _chart(close):
    return json.dumps({"chart": {"result": [{"meta": {}, "timestamp": [1704205800, 1704292200],
                                             "indicators": {"quote": [{"open": close, "high": close, "low": close, "close": close,
                                                                       "volume": [1, 1]}], "adjclose": [{"adjclose": close}]}}]}}).encode()


def test_classifies_gaps_without_filling_them(tmp_path, monkeypatch):
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    monkeypatch.delenv("PRICE_SOURCE", raising=False)
    monkeypatch.setattr(coverage13f, "MANAGERS", {1: "M"})
    monkeypatch.setattr(ftd, "load_map", lambda d: {"c_ok": "OK", "c_bk": "BK", "c_gone": "GONE", "c_lim": "LIM"})
    monkeypatch.setattr(sec13f, "list_filings", lambda cik, d, opener=None, refresh=False: [sec13f.Filing(1, "a", "2020-02-14", "2019-12-31")])
    rows = {k: {"name": k.upper(), "value": v, "shares": 1} for k, v in
            {"c_ok": 40.0, "c_bk": 30.0, "c_gone": 20.0, "c_lim": 10.0, "c_none": 5.0}.items()}
    monkeypatch.setattr(sec13f, "holdings", lambda f, d, opener=None: rows)
    # Tidigare kod sparade ett tomt svar för BK; OK har riktiga data i cachen.
    yahoo = tmp_path / "raw" / "yahoo"
    yahoo.mkdir(parents=True)
    (yahoo / "OK.json").write_bytes(_chart(10.0))
    (yahoo / "BK.json").write_bytes(b'{"chart": {"result": null, "error": {"code": "Too Many Requests"}}}')

    def opener(req):
        if "/BK?" in req.full_url:
            return _chart(50.0)
        if "/GONE?" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)
        raise urllib.error.HTTPError(req.full_url, 429, "limit", {}, None)

    d = coverage13f.diagnose(tmp_path, tmp_path, opener=opener)
    by = {r["ticker"]: r["klass"] for r in d["rows"]}
    assert by == {"OK": "hade_kurs", "BK": "fixad", "GONE": "finns_inte", "LIM": "otillgänglig", None: "ingen_ticker"}
    bk = next(r for r in d["rows"] if r["ticker"] == "BK")
    assert bk["cache_before"].startswith("tomt")
    assert d["summary"]["finns_inte"]["tickers"] == 1 and d["summary"]["ingen_ticker"]["avg_weight"] > 0
