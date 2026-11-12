import datetime as dt

from traderlab.pit_observed import expiry_of, is_last_friday_of_quarter_month
from traderlab.pit_universe import (SEVEN, build_series, hindsight_free_window, hindsight_selection, parse_event, resolve_expiry,
                                    universe_at, universe_report)


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


def _obs(u, expiry, first, last, bars=50):
    return {"contract": f"{u}USD_{expiry[2:4]}{expiry[5:7]}{expiry[8:]}", "underlying": u, "expiry": expiry, "ordinary_expiry_rule": True,
            "first_bar": first, "last_bar": last, "first_traded_bar": first, "last_traded_bar": last, "bars": bars,
            "missing_days_between": 0, "zero_volume_bars": 0, "left_censored": False, "right_censored": False,
            "ended_before_expiry": False, "bars_after_expiry": 0, "traded_runs": [[first, last]], "missing_days": [],
            "zero_volume_days": [], "daily_filled_days": [], "gap_fill_unverified": False}


def _events():
    return [{"code": "a", "released": "2020-11-30", "title": "t", "underlyings": ["BCH", "EOS"], "series": [{"mmdd": "1225", "expiry": "2020-12-25"}, {"mmdd": "0326", "expiry": "2021-03-26"}], "not_listed": []},
            {"code": "b", "released": "2020-12-25", "title": "t", "underlyings": ["BCH"], "series": [{"mmdd": "0625", "expiry": "2021-06-25"}], "not_listed": ["EOS"]}]


def test_annonserad_men_ännu_ohandlad_serie_är_inte_valbar():
    rows = build_series(_events(), [_obs("BCH", "2020-12-25", "2020-12-03", "2020-12-25"), _obs("BCH", "2021-03-26", "2020-12-03", "2021-03-26")])
    assert universe_at(rows, "2020-12-01", SEVEN) == []                       # annonserad 2020-11-30, första handel 2020-12-03
    assert {r["expiry"] for r in universe_at(rows, "2020-12-03", SEVEN)} == {"2020-12-25", "2021-03-26"}
    rep = universe_report(rows, "2020-12-01")
    assert len(rep["announced_not_yet_traded"]) == 2 and rep["tradable"] == []


def test_serie_utan_granskad_data_eller_not_listed_returneras_aldrig():
    rows = build_series(_events(), [])                    # ingen observerad data alls
    assert universe_at(rows, "2020-12-10", ("BCH", "EOS", "ETC")) == []
    assert any(r["underlying"] == "EOS" and r["status"] == "not_listed" for r in rows)
    rows = build_series(_events(), [_obs("BCH", "2021-06-25", "2020-12-26", "2021-06-25")])
    assert [r["underlying"] for r in universe_at(rows, "2021-01-05", ("BCH", "EOS"))] == ["BCH"]


def test_utgången_serie_och_dag_efter_sista_handlade_stapel_är_inte_valbara():
    rows = build_series(_events(), [_obs("BCH", "2020-12-25", "2020-12-03", "2020-12-25")])
    assert universe_at(rows, "2020-12-25", SEVEN) == []                       # förfallodagen: serien är slut
    assert universe_at(rows, "2020-12-24", SEVEN) != []


def test_överlevnadsbias_sju_ensamma_är_efterhandsurval_till_sista_förfallet_hos_de_fyra():
    rows = build_series(_events(), [_obs("BCH", "2021-06-25", "2020-12-26", "2021-06-25")])
    assert hindsight_selection(rows, "2020-12-10", SEVEN)                     # EOS har 1225/0326-serier aktiva
    assert hindsight_selection(rows, "2021-03-25", SEVEN)
    assert not hindsight_selection(rows, "2021-03-26", SEVEN)                 # EOS 0326 har löpt ut
    assert hindsight_free_window(rows) == ("2021-03-26", "2024-08-14")
    assert hindsight_selection(rows, "2024-08-14", SEVEN)                     # SOL har lanserats och saknas i urvalet
    assert not hindsight_selection(rows, "2024-08-14", SEVEN + ("SOL",))


def test_lucka_i_serien_gör_inte_dagen_valbar_fast_den_ligger_mellan_första_och_sista():
    o = _obs("ADA", "2023-09-29", "2023-03-31", "2023-09-29")
    o.update({"traded_runs": [["2023-03-31", "2023-08-27"], ["2023-09-01", "2023-09-29"]],
              "missing_days": ["2023-08-28", "2023-08-29", "2023-08-30", "2023-08-31"], "gap_fill_unverified": True})
    ev = [{"code": "x", "released": "2023-03-29", "title": "t", "underlyings": ["ADA"], "series": [{"mmdd": "0929", "expiry": "2023-09-29"}], "not_listed": []}]
    rows = build_series(ev, [o])
    assert universe_at(rows, "2023-08-29", SEVEN) == []
    assert universe_at(rows, "2023-08-27", SEVEN) != [] and universe_at(rows, "2023-09-01", SEVEN) != []
    rep = universe_report(rows, "2023-08-29")
    assert rep["active_without_verified_bar"] == [{"underlying": "ADA", "expiry": "2023-09-29", "reason": "data_gap_unverified"}]


def test_nollvolymdag_inne_i_serien_är_inte_en_observerad_handel():
    o = _obs("ADA", "2021-03-26", "2020-09-25", "2021-03-26")
    o.update({"traded_runs": [["2020-09-25", "2020-10-09"], ["2020-10-11", "2021-03-26"]], "zero_volume_days": ["2020-10-10"]})
    ev = [{"code": "x", "released": "2020-09-24", "title": "t", "underlyings": ["ADA"], "series": [{"mmdd": "0326", "expiry": "2021-03-26"}], "not_listed": []}]
    rows = build_series(ev, [o])
    assert universe_at(rows, "2020-10-10", SEVEN) == []
    assert universe_report(rows, "2020-10-10")["active_without_verified_bar"][0]["reason"] == "zero_volume"


def _frame(days, vols):
    import pandas as pd
    idx = pd.DatetimeIndex([pd.Timestamp(d, tz="UTC") for d in days])
    return pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": vols}, index=idx)


def test_observed_markerar_saknad_dag_och_nollvolym_och_fyller_bara_med_verifierad_dagsstapel(monkeypatch, tmp_path):
    from traderlab import pit_observed as po
    base = _frame(["2023-08-26", "2023-08-27", "2023-09-01", "2023-09-02", "2023-09-03"], [5, 5, 0, 5, 5])
    monkeypatch.setattr(po.binance, "load", lambda *a, **k: base.copy())
    monkeypatch.setattr(po.gapcheck, "load_manifest", lambda repo: {})

    def refuse(monthly, *a, **k):
        raise po.gapcheck.UnverifiedGapFill("test")
    monkeypatch.setattr(po.gapcheck, "combined", refuse)
    o = po.observed("ADAUSD_230929", tmp_path / "data")
    assert o["gap_fill_unverified"] and o["daily_filled_days"] == []
    assert o["missing_days"] == ["2023-08-28", "2023-08-29", "2023-08-30", "2023-08-31"]
    assert o["zero_volume_days"] == ["2023-09-01"]
    assert o["traded_runs"] == [["2023-08-26", "2023-08-27"], ["2023-09-02", "2023-09-03"]]

    def fill(monthly, *a, **k):
        out = monthly.copy()
        out["source"] = "monthly"
        add = _frame(["2023-08-28", "2023-08-29", "2023-08-30", "2023-08-31"], [7, 7, 7, 7])
        add["source"] = "daily"
        import pandas as pd
        return pd.concat([out, add]).sort_index()
    monkeypatch.setattr(po.gapcheck, "combined", fill)
    o = po.observed("ADAUSD_230929", tmp_path / "data")
    assert not o["gap_fill_unverified"] and o["missing_days"] == []
    assert o["daily_filled_days"] == ["2023-08-28", "2023-08-29", "2023-08-30", "2023-08-31"]
    assert o["traded_runs"] == [["2023-08-26", "2023-08-31"], ["2023-09-02", "2023-09-03"]]      # 09-01 har nollvolym: aldrig handlad
