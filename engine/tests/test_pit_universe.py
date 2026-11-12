import datetime as dt

from traderlab.pit_observed import expiry_of, is_last_friday_of_quarter_month
from traderlab.pit_universe import SEVEN, build_series, parse_event, resolve_expiry, universe_at


def test_titel_med_flera_underliggande_och_två_serier():
    ev = parse_event("Binance Futures Will Launch BNBUSD and DOTUSD Quarterly 1225 & 0326 Coin-Margined Contracts With Up to 75x Leverage",
                     "Fellow Binancians, ...", "2020-11-03", "c1")
    assert ev["underlyings"] == ["BNB", "DOT"]
    assert [s["expiry"] for s in ev["series"]] == ["2020-12-25", "2021-03-26"]


def test_text_med_not_listed_och_undantagna_underliggande():
    text = ("Fellow Binancians, Binance Futures will list BTC, ETH, BNB, ADA, LINK, BCH, XRP, DOT and LTC Coin-margined Quarterly 0625 Contracts "
            "within the next few hours. Notes: ETC, TRX, EOS and FIL quarterly 0625 contracts will not be listed. Users are only")
    ev = parse_event("Binance Futures Will List Coin-Margined Quarterly 0625 Futures Contracts", text, "2020-12-25", "c2")
    assert "BNB" in ev["underlyings"] and "ETC" not in ev["underlyings"]
    assert ev["not_listed"] == ["EOS", "ETC", "FIL", "TRX"]
    assert ev["series"] == [{"mmdd": "0625", "expiry": "2021-06-25"}]


def test_nyare_format_med_and_före_sista_namnet():
    text = ("will list the following USDⓈ-M and COIN-M Quarterly 0627 Delivery Contracts ... COIN-M BTC, ETH, BNB, ADA, LINK, BCH, XRP, DOT, LTC, and SOL "
            "Quarterly 0627 Delivery Contracts COIN-M Delivery Contracts")
    ev = parse_event("Binance Futures Will List USDⓈ-M & COIN-M Quarterly 0627 Delivery Contracts", text, "2024-12-20", "c3")
    assert {"LTC", "SOL", "ADA"} <= set(ev["underlyings"])


def test_inget_listningsmeddelande_ger_none():
    assert parse_event("Updates on Leverage & Margin Tiers of Multiple COIN-M Perpetual", "Fellow Binancians, tiers", "2023-05-31", "c4") is None


def test_förfall_sista_fredagen_och_uppslag():
    assert is_last_friday_of_quarter_month(expiry_of("ADAUSD_200925"))
    assert not is_last_friday_of_quarter_month(dt.date(2020, 9, 18))
    assert resolve_expiry("0326", "2020-09-24") == dt.date(2021, 3, 26)


def test_universum_vid_tidpunkt_använder_bara_redan_meddelade_serier():
    ev = [{"code": "a", "released": "2020-11-03", "title": "t", "underlyings": ["BNB"], "series": [{"mmdd": "1225", "expiry": "2020-12-25"}], "not_listed": []},
          {"code": "b", "released": "2020-12-25", "title": "t", "underlyings": ["BNB"], "series": [{"mmdd": "0625", "expiry": "2021-06-25"}], "not_listed": ["EOS"]}]
    rows = build_series(ev, [])
    assert [r["expiry"] for r in universe_at(rows, "2020-12-01", SEVEN)] == ["2020-12-25"]    # 0625 var inte meddelad ännu
    assert [r["expiry"] for r in universe_at(rows, "2020-12-26", SEVEN)] == ["2021-06-25"]    # 1225 hade löpt ut
    assert any(r["underlying"] == "EOS" and r["status"] == "not_listed" for r in build_series(ev, []))
