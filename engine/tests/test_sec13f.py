import json

import pytest

from traderlab.data import sec13f

XML = b"""<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
<infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip><value>600</value>
<shrsOrPrnAmt><sshPrnamt>10</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip><value>400</value>
<shrsOrPrnAmt><sshPrnamt>5</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>APPLE INC</nameOfIssuer><cusip>037833100</cusip><value>9999</value><putCall>Call</putCall>
<shrsOrPrnAmt><sshPrnamt>1</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>BANK AMER CORP</nameOfIssuer><cusip>060505104</cusip><value>500</value>
<shrsOrPrnAmt><sshPrnamt>50</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>SOME BOND</nameOfIssuer><cusip>000000AA0</cusip><value>8000</value>
<shrsOrPrnAmt><sshPrnamt>8000</sshPrnamt><sshPrnamtType>PRN</sshPrnamtType></shrsOrPrnAmt></infoTable>
</informationTable>"""


def test_parse_sums_rows_and_skips_options_and_bonds():
    rows = sec13f.parse_infotable(XML)
    assert set(rows) == {"037833100", "060505104"}
    assert rows["037833100"]["value"] == 1000 and rows["037833100"]["shares"] == 15


def test_top_weights_are_value_weighted():
    w = sec13f.top_weights(sec13f.parse_infotable(XML), n=1)
    assert w == {"037833100": 1.0}
    w2 = sec13f.top_weights(sec13f.parse_infotable(XML), n=10)
    assert w2["037833100"] == pytest.approx(1000 / 1500)


def test_list_filings_and_holdings_use_cache(tmp_path):
    calls = []
    sub = {"filings": {"recent": {"accessionNumber": ["0000000001-24-000002", "0000000001-24-000001", "0000000001-24-000003"],
                                  "form": ["13F-HR", "13F-HR", "13F-HR/A"], "filingDate": ["2024-05-15", "2024-02-14", "2024-05-20"],
                                  "reportDate": ["2024-03-31", "2023-12-31", "2024-03-31"]}, "files": []}}
    idx = {"directory": {"item": [{"name": "primary_doc.xml"}, {"name": "infotable.xml"}]}}

    def opener(url):
        calls.append(url)
        if url.endswith(".json") and "submissions" in url:
            return json.dumps(sub).encode()
        if url.endswith("index.json"):
            return json.dumps(idx).encode()
        if url.endswith("infotable.xml"):
            return XML
        raise AssertionError(url)

    fs = sec13f.list_filings(1, tmp_path, opener)
    assert [f.filed for f in fs] == ["2024-02-14", "2024-05-15"]   # rättelsen 13F-HR/A räknas inte
    h = sec13f.holdings(fs[0], tmp_path, opener)
    assert "037833100" in h
    n = len(calls)
    sec13f.list_filings(1, tmp_path, opener); sec13f.holdings(fs[0], tmp_path, opener)
    assert len(calls) == n   # allt från cachen andra gången


def test_user_agent_requires_contact(monkeypatch):
    monkeypatch.delenv("SEC_CONTACT", raising=False)
    with pytest.raises(RuntimeError):
        sec13f.user_agent()
