import datetime as dt
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from traderlab import h0022_coverage as hc

REPO = Path(__file__).resolve().parents[2]


def _frame(days, vol=5.0):
    idx = pd.DatetimeIndex([pd.Timestamp(d, tz="UTC") for d in days])
    return pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": vol}, index=idx)


def _cycle(fill="2022-03-18", exit_="2022-06-17", decision="2022-03-17"):
    return {"cycle": 5, "expiry": "2022-06-24", "decision": decision, "fill": fill, "exit": exit_, "valid_coins": ["ADA"], "flat": False}


def _alldays(a, b):
    return hc._days(a, b)


def _complete(cycle=None, vol=5000.0):
    c = cycle or _cycle()
    fut = _frame(_alldays("2022-01-01", c["exit"]), vol)
    mark = _frame(_alldays(c["fill"], c["exit"]))
    spot = _frame(_alldays("2022-01-01", c["exit"]), 1.0)
    return c, fut, mark, spot


def test_kalendern_reproducerar_protokollets_14_cykler_exakt():
    rows = json.loads((REPO / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
    cycles = hc.cycle_calendar(rows)
    proto = (REPO / "research" / "h0022-protokoll.md").read_text(encoding="utf-8")
    table = []
    for line in proto.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) == 7 and re.fullmatch(r"\d+", c[0]) and re.fullmatch(r"20\d\d-\d\d-\d\d", c[1]):
            table.append(c)
    assert len(cycles) == len(table) == 14
    for cy, row in zip(cycles, table):
        assert (str(cy["cycle"]), cy["expiry"], cy["decision"], cy["fill"], cy["exit"]) == (row[0], row[1], row[2], row[3], row[4])
    assert [c["cycle"] for c in cycles if c["flat"]] == [2]


def test_komplett_data_ger_data_complete_och_ingen_ogiltighet():
    c, fut, mark, spot = _complete()
    a = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=10.0)
    assert a["decision_possible"] and a["data_complete"] and not a["ogiltig_if_traded"] and a["missing"] == {}
    assert a["open_time_aligned_fill_exit"] and a["median20_usd"] == pytest.approx(5000.0 * 10.0)


def test_saknad_markprisdag_inne_i_innehavet_ger_ogiltig_om_handlad():
    c, fut, mark, spot = _complete()
    mark = mark.drop(pd.Timestamp("2022-04-20", tz="UTC"))
    a = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=10.0)
    assert a["missing"]["mark_held_days"] == ["2022-04-20"] and a["ogiltig_if_traded"] and not a["data_complete"]


def test_nollvolym_pa_fyllnings_eller_utträdesdag_räknas_som_saknad_stapel():
    c, fut, mark, spot = _complete()
    fut.loc[pd.Timestamp(c["exit"], tz="UTC"), "volume"] = 0.0
    spot.loc[pd.Timestamp(c["fill"], tz="UTC"), "volume"] = 0.0
    a = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=10.0)
    assert a["missing"]["fut_exit_bar"] == [c["exit"]] and a["missing"]["spot_fill_bar"] == [c["fill"]]
    assert a["ogiltig_if_traded"]


def test_saknad_nasta_oppning_efter_hallen_dag_flaggas_for_riskstopp():
    c, fut, mark, spot = _complete()
    fut = fut.drop(pd.Timestamp("2022-05-10", tz="UTC"))
    a = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=10.0)
    assert a["missing"]["fut_next_open_days"] == ["2022-05-10"] and not a["data_complete"]


def test_färre_än_20_handelsdagar_eller_fel_kontraktsstorlek_stoppar_beslutet_men_är_inte_ogiltigt():
    c, fut, mark, spot = _complete()
    few = fut[fut.index >= pd.Timestamp("2022-03-01", tz="UTC")]          # bara 17 dagar före beslutsdagen
    a = hc.audit_coin_cycle(cycle=c, fut=few, mark=mark, spot=spot, implied_size_median=10.0)
    assert a["traded_days_before_decision"] == 17 and not a["decision_possible"] and not a["ogiltig_if_traded"]
    b = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=12.0)
    assert not b["contract_size_ok"] and not b["decision_possible"]


def test_likviditetströsklarna_500k_och_1m_och_medianen_använder_bara_dagar_till_beslutsdagen():
    c, fut, mark, spot = _complete(vol=5000.0)                                       # 50 000 USD/dag (kontrakt × 10)
    a = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=10.0)
    assert not a["liquidity_min_ok"]
    c2, fut2, mark2, spot2 = _complete(vol=60000.0)                                  # 600 000 USD/dag
    fut2.loc[fut2.index > pd.Timestamp(c2["decision"], tz="UTC"), "volume"] = 1e9      # senare dagar ska ignoreras
    b = hc.audit_coin_cycle(cycle=c2, fut=fut2, mark=mark2, spot=spot2, implied_size_median=10.0)
    assert b["median20_usd"] == pytest.approx(600000.0) and b["liquidity_min_ok"] and not b["liquidity_start_ok"]
    assert hc.MIN_MEDIAN20_USD == 500_000.0 and hc.START_SIZE_MEDIAN20_USD == pytest.approx(1_000_000.0)


def test_täckningen_visar_att_krav_4b_inte_kan_uppfyllas_när_högst_9_cykler_har_fyra_mynt():
    cycles = [{"cycle": k, "flat": k == 2} for k in range(1, 15)]
    audits = []
    for k in range(1, 15):
        if k == 2:
            continue
        n = 7 if k <= 9 else 2                                                       # cykel 10 till 14: bara två mynt
        for i in range(7):
            ok = i < n
            audits.append({"coin": f"C{i}", "cycle": k, "decision_possible": True, "data_complete": True, "ogiltig_if_traded": False,
                           "liquidity_min_ok": ok, "liquidity_start_ok": ok})
    cov = hc.possible_coverage(audits, cycles)
    r = cov["minsta_storlek_10000"]
    assert r["mynt_cykler_mojliga"] >= 46 and r["cykler_med_minst_4_mynt"] == 8 and r["av_cykler"] == 13 and not r["krav_uppfyllda"]


def test_dataperioden_stänger_2025_och_checksummekontroll_upptäcker_fel(tmp_path):
    assert hc.DATA_END == pd.Timestamp("2024-10-01", tz="UTC") and hc.DATA_END < pd.Timestamp("2025-01-01", tz="UTC")
    z = tmp_path / "X-1d-2021-03.zip"
    z.write_bytes(b"innehall")
    assert hc.verify_file(z)["ok"] is False                                          # ingen .CHECKSUM sparad
    import hashlib
    z.with_suffix(".zip.CHECKSUM").write_text(hashlib.sha256(b"innehall").hexdigest() + "  X-1d-2021-03.zip")
    assert hc.verify_file(z)["ok"] is True
    z.write_bytes(b"manipulerat")
    assert hc.verify_file(z)["ok"] is False


def test_incheckad_rapport_har_inga_checksummefel_och_inga_hål_för_beslutade_mynt():
    rep = json.loads((REPO / "research" / "coverage" / "h0022-datatackning.json").read_text(encoding="utf-8"))
    assert rep["checksum_failures"] == {} and rep["coverage"]["ogiltig_om_handlad"] == []
    assert len(rep["audits"]) == 91 and all(a["open_time_aligned_fill_exit"] and a["data_complete"] for a in rep["audits"])
    assert all(a["off_midnight_bars"] == {} for a in rep["audits"]) and all("spot_next_open_days" not in a["missing"] for a in rep["audits"])
    assert not any(k.startswith("data/raw/binance") and re.search(r"2025-\d\d|2026-\d\d", k) for k in rep["files"])


# ------------------------------------------------------------------ fail-closed: exakt gemensam open_time och nästa öppning för båda benen
def _shift_day(df, day, hours):
    """Flyttar en stapels open_time `hours` timmar (t.ex. 01:00 i stället för 00:00)."""
    idx = list(df.index)
    i = idx.index(pd.Timestamp(day, tz="UTC"))
    idx[i] = idx[i] + pd.Timedelta(hours=hours)
    out = df.copy()
    out.index = pd.DatetimeIndex(idx)
    return out


def test_ena_benet_med_open_time_0100_i_stallet_for_0000_ar_ofullstandigt_och_ogiltigt_om_handlat():
    c, fut, mark, spot = _complete()
    fut2 = _shift_day(fut, c["fill"], 1)                              # terminen 01:00, spot 00:00 samma kalenderdag
    a = hc.audit_coin_cycle(cycle=c, fut=fut2, mark=mark, spot=spot, implied_size_median=10.0)
    assert not a["open_time_aligned_fill_exit"] and not a["data_complete"] and a["ogiltig_if_traded"]
    assert a["off_midnight_bars"]["fut"] == [c["fill"]] and c["fill"] in a["missing"]["fut_fill_bar"]
    spot2 = _shift_day(spot, c["exit"], 1)                            # och utträdesdagen på spoten
    b = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot2, implied_size_median=10.0)
    assert not b["data_complete"] and b["ogiltig_if_traded"] and c["exit"] in b["missing"]["spot_exit_bar"]


def test_bada_benen_0100_samma_dag_godkänns_inte_eftersom_protokollet_kräver_öppningen_0000():
    c, fut, mark, spot = _complete()
    a = hc.audit_coin_cycle(cycle=c, fut=_shift_day(fut, c["fill"], 1), mark=mark, spot=_shift_day(spot, c["fill"], 1), implied_size_median=10.0)
    assert not a["data_complete"] and a["ogiltig_if_traded"]          # lika tid, men inte öppningen: fortfarande ofullständigt


def test_spot_som_saknar_en_mellandag_ger_ofullständigt_även_om_terminen_är_komplett():
    c, fut, mark, spot = _complete()
    spot = spot.drop(pd.Timestamp("2022-05-10", tz="UTC"))
    a = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=10.0)
    assert a["missing"]["spot_next_open_days"] == ["2022-05-10"] and "fut_next_open_days" not in a["missing"]
    assert not a["data_complete"] and not a["held_days_complete"] and a["ogiltig_if_traded"]


def test_en_off_midnight_stapel_på_en_oväsentlig_dag_ändrar_inte_fullständigheten_men_redovisas_inte_som_gemensam_tid():
    c, fut, mark, spot = _complete()
    fut = _shift_day(fut, "2022-01-05", 1)                            # långt före beslutsdagen: ingen krävd dag
    a = hc.audit_coin_cycle(cycle=c, fut=fut, mark=mark, spot=spot, implied_size_median=10.0)
    assert a["data_complete"] and a["open_time_aligned_fill_exit"] and a["off_midnight_bars"] == {}
