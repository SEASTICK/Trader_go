import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from traderlab import copypelosi
from traderlab.data import house

TEXT = """Owner Asset Transaction Type Date Notification Date Amount
SP Alphabet Inc. - Class A
(GOOGL) [ST]
P 12/30/2020 01/05/2021 $500,001 - $1,000,000
SP Apple Inc. (AAPL) [OP] P 03/17/2023 03/17/2023 $1,000,001 - $5,000,000
DESCRIPTION: Purchased 50 call options with a strike price of $80.
SP Tesla, Inc. (TSLA) [OP] P 03/17/2023 03/17/2023 $15,001 - $50,000
DESCRIPTION: Purchased 10 put options.
SP Walt Disney Company (DIS) [ST] S 01/10/2021 01/12/2021 $1,000,001 - $5,000,000
SP Microsoft Corporation (MSFT) [ST] S (partial) 02/02/2021 02/03/2021 $250,001 - $500,000
SP Some Fund (XYZ) [MF] P 01/01/2021 01/02/2021 $1,001 - $15,000
"""


def test_parse_follows_protocol():
    tr = house.parse(TEXT)
    assert [(t.ticker, t.kind, t.asset) for t in tr] == [("GOOGL", "buy", "ST"), ("AAPL", "buy", "OP"), ("DIS", "sell", "ST")]
    assert tr[0].traded == "2020-12-30"


OLD = ("TrANSAcTIONSIDOwnerAssetTransaction TypeDate Notification DateAmount sPalcoa Inc. (aa)s 10/23/2014 10/23/2014 "
       "$15,001 - $50,000 FIlINg sTaTus: NewsPsunEdison, Inc. (suNE)P 10/24/2014 10/24/2014 $100,001 - $250,000 "
       "FIlINg sTaTus: New Hertz global Holdings, Inc (HTZ)P 11/5/2014 11/5/2014 $15,001 - $50,000 FIlINg sTaTus: "
       "NewDEsCRIPTION: Purchase of 50 OptionsWalt Disney Company (DIs)P 12/10/2014 12/10/2014 $50,001 - $100,000 "
       "FIlINg sTaTus: NewDEsCRIPTION: Purchase of 92 Puts options")


def test_parse_old_format_without_tags_and_broken_case():
    tr = house.parse(OLD)
    assert [(t.ticker, t.kind, t.asset, t.traded) for t in tr] == [
        ("AA", "sell", "ST", "2014-10-23"), ("SUNE", "buy", "ST", "2014-10-24"), ("HTZ", "buy", "OP", "2014-11-05")]


def test_reports_filters_pelosi_ptr(tmp_path):
    xml = b"""<FinancialDisclosure>
<Member><Last>Pelosi</Last><First>Nancy</First><FilingType>P</FilingType><FilingDate>1/5/2021</FilingDate><DocID>20017744</DocID></Member>
<Member><Last>Pelosi</Last><First>Nancy</First><FilingType>O</FilingType><FilingDate>5/15/2021</FilingDate><DocID>1</DocID></Member>
<Member><Last>Smith</Last><First>Adam</First><FilingType>P</FilingType><FilingDate>1/6/2021</FilingDate><DocID>2</DocID></Member>
</FinancialDisclosure>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("2021FD.xml", xml)
    reps = house.reports(2021, tmp_path, opener=lambda url: buf.getvalue())
    assert [(r.doc_id, r.filed) for r in reps] == [("20017744", "2021-01-05")]


def T(t, k):
    return house.Trade(t, k, "ST", "2020-01-01")


def test_holdings_respect_disclosure_date_and_expiry():
    ts = lambda s: pd.Timestamp(s, tz="UTC")
    ev = [(ts("2021-01-05"), [T("GOOGL", "buy")]), (ts("2021-03-01"), [T("DIS", "buy")]), (ts("2021-06-01"), [T("DIS", "sell")])]
    assert copypelosi.holdings_after(ev, ts("2021-01-05")) == set()            # inte före offentliggörandet
    assert copypelosi.holdings_after(ev, ts("2021-01-06")) == {"GOOGL"}
    assert copypelosi.holdings_after(ev, ts("2021-04-01")) == {"GOOGL", "DIS"}
    assert copypelosi.holdings_after(ev, ts("2021-06-02")) == {"GOOGL"}
    assert copypelosi.holdings_after(ev, ts("2022-01-10")) == set()           # 365 dagar har gått


def test_weights_equal_and_spy_when_empty():
    idx = pd.bdate_range("2021-01-04", "2022-03-01", tz="UTC")
    opens = pd.DataFrame({"GOOGL": 100.0, "SPY": 300.0}, index=idx)
    ev = [(pd.Timestamp("2021-01-05", tz="UTC"), [T("GOOGL", "buy")])]
    w = copypelosi.build_weights(ev, opens)
    assert w.loc[pd.Timestamp("2021-01-05", tz="UTC"), "GOOGL"] == 1.0
    assert w.iloc[-1]["SPY"] == 1.0 and w.iloc[-1]["GOOGL"] == 0.0


def test_no_space_before_date_and_real_estate_only():
    t = "sPAmazon.com, Inc. (AMZN) [sT] P07/27/2018 07/27/2018 $500,001 - $1,000,000"
    assert [(x.ticker, x.kind, x.traded) for x in house.parse(t)] == [("AMZN", "buy", "2018-07-27")]
    estate = "JT1600 Atlas Peak Road - Real EstateInvestmentS 12/30/2016 12/30/2016 $500,001 - $1,000,000 Napa/Napa, CA"
    assert house.parse(estate) == [] and not house.has_securities(estate)
    assert house.has_securities(t)
