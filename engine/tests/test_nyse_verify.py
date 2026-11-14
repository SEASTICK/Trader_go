"""Avstämningen av NYSE-ledgern mot officiella dokument: rena delar testas alltid; körning mot de nedladdade dokumenten testas bara om NYSE_EVIDENCE_DIR är satt."""
import os
import shutil
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from traderlab import nyse_sessions, nyse_verify as nv


def test_memo_regex_laser_stangda_datum_med_veckodag():
    text = ("The NYSE and other U.S. securities exchanges will be closed on Monday, January 16, 2006, in observance of Martin Luther King, Jr., Day.\n"
            "The NYSE and the securities exchanges will be closed on Friday, March 25, 2005, in observance of Good Friday.\n"
            "will be closed\n   on Tuesday, July 4, 2006, in observance of Independence Day.")
    got = nv.memo_closures(text, {2006, 2007})
    assert set(got) == {date(2006, 1, 16), date(2006, 7, 4)}                                                          # 2005 filtreras bort, radbrytning mellan 'closed' och 'on' hanteras


def test_evidence_har_hash_for_varje_dokument_och_ratt_ar_pa_kalendrarna():
    assert set(nv.CALENDAR_YEARS.values()) <= set(nv.EVIDENCE) and all(len(e["sha256"]) == 64 for e in nv.EVIDENCE.values())
    assert set(nv.CALENDAR_YEARS) == {2020, 2022, 2023, 2024}


def test_apply_fyller_bara_styrkta_rader_och_skriver_inte_over(tmp_path, monkeypatch):
    f = tmp_path / "ledger.csv"
    led = nyse_sessions.closure_ledger()
    led.loc[1, "verified_source"] = "tidigare källa"
    f.write_text(nyse_sessions.ledger_to_csv_text(led), encoding="utf-8")
    monkeypatch.setattr(nyse_sessions, "LEDGER_FILE", f)
    monkeypatch.setattr(nyse_sessions, "read_ledger", lambda path=f: pd.read_csv(f, dtype=str, keep_default_na=False))
    d0, d1 = pd.Timestamp(led.loc[0, "date"]).date(), pd.Timestamp(led.loc[1, "date"]).date()
    n = nv.apply({d0: ("K", "ref0"), d1: ("K", "ref1")}, "testare", "2026-11-14")
    out = pd.read_csv(f, dtype=str, keep_default_na=False)
    assert n == 2 and out.loc[0, "verified_source"] == "K: ref0"                                                         # raden som styrks + den människoverifierade 2018-12-05 and out.loc[0, "verified_by"] == "testare" and out.loc[0, "verified_date"] == "2026-11-14"
    assert out.loc[1, "verified_source"] == "tidigare källa" and out.loc[1, "verified_by"] == ""                       # rörs inte
    others = out[~out["date"].isin(["2006-01-02", "2006-01-16", "2018-12-05"])]
    assert (others["verified_source"] == "").all()                                                                     # allt annat förblir overifierat


def test_repots_ledger_har_bara_kallor_som_finns_i_evidence_och_fail_closed_gar_kvar():
    led = nyse_sessions.read_ledger()
    ver = led[led["verified_source"].str.strip() != ""]
    assert len(ver) >= 58
    human = {h["source"] for h in nv.HUMAN_VERIFIED.values()}
    assert all(r["verified_source"].split(":")[0] in nv.EVIDENCE or r["verified_source"] in human or r["verified_source"].strip().lower() == "saknas" for _, r in ver.iterrows())
    assert (ver["verified_by"].str.strip() != "").all() and (ver["verified_date"].str.strip() != "").all()
    r = nyse_sessions.reconcile()
    assert r["ok"] and (r["fully_verified"] is False or r["verified_rows"] == r["ledger_rows"])


@pytest.mark.skipif(not os.environ.get("NYSE_EVIDENCE_DIR") or not shutil.which("pdftoppm"), reason="kräver NYSE_EVIDENCE_DIR med dokumenten och poppler")
def test_avstamning_mot_de_nedladdade_dokumenten(tmp_path):
    pytest.importorskip("PIL")
    r = nv.verify(Path(os.environ["NYSE_EVIDENCE_DIR"]), tmp_path)
    assert r["problems"] == [] and r["rule_7_2_text_found"] and r["supported_rows"] == 57
    years = sorted({d.year for d in r["supported"]})
    assert years == [2006, 2007, 2012, 2020, 2022, 2023, 2024]
    assert date(2012, 10, 30) in r["supported"] and date(2007, 1, 2) in r["supported"] and date(2020, 7, 3) in r["supported"] and date(2018, 12, 5) not in r["supported"]   # 2018-12-05 styrks av en människa, inte av maskinavstämningen


def test_manniskoverifierad_rad_markeras_som_det_och_fylls_av_apply(tmp_path, monkeypatch):
    f = tmp_path / "ledger.csv"
    led = nyse_sessions.closure_ledger()
    f.write_text(nyse_sessions.ledger_to_csv_text(led), encoding="utf-8")
    monkeypatch.setattr(nyse_sessions, "LEDGER_FILE", f)
    monkeypatch.setattr(nyse_sessions, "read_ledger", lambda path=f: pd.read_csv(f, dtype=str, keep_default_na=False))
    assert nv.apply({}, "maskin", "2026-11-14") == len(nv.HUMAN_VERIFIED) == 1
    out = pd.read_csv(f, dtype=str, keep_default_na=False)
    row = out[out["date"] == "2018-12-05"].iloc[0]
    assert 'Exchanges will be closed on Wednesday, December 5, 2018 in observance of a National Day of Mourning for President George H. W. Bush.' in row["verified_source"]
    assert "RB-18-06" in row["verified_source"] and "s. 1" in row["verified_source"] and "2018-12-03" in row["verified_source"]
    assert row["verified_by"].startswith("Codex") and "Claude har inte kunnat öppna dokumentet" in row["verified_by"] and "ingen maskinavstämning" in row["verified_by"]
    assert "SEASTICK" in row["verified_by"] and not row["verified_by"].startswith("SEASTICK")                           # SEASTICK återgav citatet, Codex läste dokumentet
    assert (out["verified_source"] != "").sum() == 1


def test_luckorna_listas_datum_for_datum_och_filen_ar_i_synk_med_ledgern():
    led = nyse_sessions.read_ledger()
    text = nv.gaps_markdown(led)
    src = led["verified_source"].astype(str).str.strip()
    open_dates = sorted(led.loc[(src == "") | (src.str.lower() == "saknas"), "date"])
    assert all(f"- {d} " in text for d in open_dates) and text.count("\n- ") == len(open_dates)
    assert nv.GAPS_FILE.read_text(encoding="utf-8") == text                                                          # den committade listan är genererad ur den committade ledgern


def test_2018_12_05_ar_den_enda_manniskoverifierade_raden_och_resten_ar_overifierat():
    assert list(nv.HUMAN_VERIFIED) == [date(2018, 12, 5)]
    led = nyse_sessions.read_ledger()
    ver = led[led["verified_source"].str.strip() != ""]
    machine = ver[ver["verified_by"].str.startswith("Claude")]
    human = ver[~ver["verified_by"].str.startswith("Claude")]
    assert list(human["date"]) == ["2018-12-05"] and len(machine) == len(ver) - 1                                      # övriga verifierade rader är maskinavstämda
    r = nyse_sessions.reconcile()
    assert (r["verified_rows"], r["unverified_rows"], r["fully_verified"]) == (58, 118, False)                         # 58/176, resten fail-closed
