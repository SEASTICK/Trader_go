"""Tester för kontrollen av COIN-M-luckan 2023-08-28 till 2023-08-31 (syntetiska filer, inget nätverk)."""
import hashlib
import io
import urllib.error
import zipfile

import pandas as pd
import pytest

from traderlab.data import gapcheck as g


def _zip(day: str, o=100.0, h=110.0, l=90.0, c=105.0, v=10.0, ts=None) -> bytes:
    t = ts if ts is not None else int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", f"{t},{o},{h},{l},{c},{v},{t + 86399999},0,0,0,0,0\n")
    return buf.getvalue()


def _opener(files: dict, bad_checksum=()):
    def opener(url):
        base = url[:-9] if url.endswith(".CHECKSUM") else url
        if base not in files:
            raise urllib.error.HTTPError(url, 404, "nf", {}, None)
        raw = files[base]
        if url.endswith(".CHECKSUM"):
            return (("0" * 64) if base in bad_checksum else hashlib.sha256(raw).hexdigest()).encode() + b"  x.zip"
        return raw
    return opener



def _df(day, o=100.0, h=110.0, l=90.0, c=105.0, v=10.0):
    return pd.DataFrame({"open": [o], "high": [h], "low": [l], "close": [c], "volume": [v]}, index=pd.DatetimeIndex([pd.Timestamp(day, tz="UTC")], name="open_time"))


def test_fetch_verified_saves_ok_files_and_reports_missing_and_bad_checksums(tmp_path):
    url_ok, url_bad, url_missing = (g.daily_url("cm", "BTCUSD_230929", d) for d in ("2023-08-28", "2023-08-29", "2023-08-30"))
    files = {url_ok: _zip("2023-08-28"), url_bad: _zip("2023-08-29")}
    op = _opener(files, bad_checksum=[url_bad])
    ok = g.fetch_verified(url_ok, tmp_path / "ok.zip", op)
    assert ok["status"] == "ok" and ok["sha256"] == hashlib.sha256(files[url_ok]).hexdigest() and (tmp_path / "ok.zip").exists()
    assert (tmp_path / "ok.zip.CHECKSUM").exists()
    bad = g.fetch_verified(url_bad, tmp_path / "bad.zip", op)
    assert bad["status"] == "checksumma ogiltig" and not (tmp_path / "bad.zip").exists()   # en fil utan giltig checksumma används aldrig
    assert g.fetch_verified(url_missing, tmp_path / "m.zip", op)["status"] == "saknas"


def test_sanity_flags_wrong_timestamp_inconsistent_ohlc_and_negative_volume():
    assert g.sanity("2023-08-28", _df("2023-08-28"))["ok"]
    assert not g.sanity("2023-08-28", _df("2023-08-29"))["ok"]                       # fel dag
    assert "OHLC" in g.sanity("2023-08-28", _df("2023-08-28", h=100.0, c=105.0))["problem"]   # high under close
    assert "volym" in g.sanity("2023-08-28", _df("2023-08-28", v=-1.0))["problem"]
    assert g.sanity("2023-08-28", pd.concat([_df("2023-08-28"), _df("2023-08-29")]))["rows"] == 2


def test_compare_with_monthly_is_exact_and_none_for_gap_days():
    m = pd.concat([_df("2023-08-27")])
    same = g.compare_with_monthly(_df("2023-08-27"), m, "2023-08-27")
    assert same == {"equal": True, "differences": {}}
    diff = g.compare_with_monthly(_df("2023-08-27", v=11.0), m, "2023-08-27")
    assert diff["equal"] is False and diff["differences"] == {"volume": [11.0, 10.0]}
    assert g.compare_with_monthly(_df("2023-08-28"), m, "2023-08-28") is None   # gapdag: månadsfilen saknar dagen


def test_combined_fills_only_verified_gap_days_and_keeps_provenance(tmp_path):
    sym = "BTCUSD_230929"
    monthly = pd.concat([_df(d) for d in ("2023-08-27", "2023-09-01")])
    for day in ("2023-08-28", "2023-08-29"):   # bara två av fyra gapdagar finns som originalfil
        p = tmp_path / "raw/binance/cm-daily" / sym / "1d" / f"{sym}-1d-{day}.zip"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_zip(day))
    c = g.combined(monthly, tmp_path, "cm", sym)
    assert list(c.index.strftime("%Y-%m-%d")) == ["2023-08-27", "2023-08-28", "2023-08-29", "2023-09-01"]
    assert list(c["source"]) == ["monthly", "daily", "daily", "monthly"]
    assert "2023-08-30" not in c.index.strftime("%Y-%m-%d")   # utan originalfil förblir dagen en lucka: inget fylls


def test_combined_never_overwrites_a_monthly_bar_or_accepts_a_wrong_timestamp(tmp_path):
    sym = "BTCUSD_230929"
    monthly = _df("2023-08-28", c=111.0)
    p = tmp_path / "raw/binance/cm-daily" / sym / "1d" / f"{sym}-1d-2023-08-28.zip"
    p.parent.mkdir(parents=True)
    p.write_bytes(_zip("2023-08-28", c=100.0))
    assert g.combined(monthly, tmp_path, "cm", sym)["close"].iloc[0] == 111.0   # månadsfilen vinner
    p2 = tmp_path / "raw/binance/cm-daily" / sym / "1d" / f"{sym}-1d-2023-08-29.zip"
    p2.write_bytes(_zip("2023-08-29", ts=int(pd.Timestamp("2023-08-30", tz="UTC").timestamp() * 1000)))   # fel tidsstämpel
    assert "2023-08-29" not in g.combined(monthly, tmp_path, "cm", sym).index.strftime("%Y-%m-%d")


def test_summary_counts_verified_missing_and_mismatching_days():
    def cell(status="ok", ok=True, eq=None, in_monthly=False):
        r = {"daily": {"status": status}, "in_monthly": in_monthly}
        if status == "ok":
            r["sanity"] = {"ok": ok}
            r["vs_monthly"] = None if eq is None else {"equal": eq}
        return r
    cm = {"A": {"2023-08-28": cell(), "2023-08-29": cell(status="saknas"), "2023-08-26": cell(eq=True), "2023-08-27": cell(eq=False)}}
    sp = {"S": {"2023-08-28": cell(in_monthly=True, eq=True), "2023-08-26": cell(eq=True)}}
    s = g.summarize(cm, sp)
    assert s["cm_gap_contract_days"] == 2 and s["cm_gap_days_with_verified_original"] == 1
    assert s["cm_gap_days_missing_or_failed"] == [("A", "2023-08-29")] and s["cm_neighbor_mismatches"] == [("A", "2023-08-27")]
    assert s["spot_gap_days_in_monthly"] == 1 and s["spot_gap_days_with_verified_daily"] == 1 and s["spot_gap_days_equal_to_monthly"] == 1


def test_markdown_tables_are_generated_from_the_report():
    def cell(in_monthly=False, eq=None):
        r = {"daily": {"status": "ok"}, "sanity": {"ok": True}, "in_monthly": in_monthly}
        if eq is not None:
            r["vs_monthly"] = {"equal": eq}
        return r
    days = {d: cell() for d in g.GAP_DAYS} | {"2023-08-26": cell(eq=True), "2023-08-27": cell(eq=True), "_after_fill": {"missing_days_to_expiry": 0}}
    sp = {d: cell(in_monthly=True) for d in g.GAP_DAYS} | {"2023-08-26": cell(eq=True)}
    t = g.markdown_tables({"cm": {"BTCUSD_230929": days}, "spot": {"BTCUSDT": sp}})
    assert "| BTCUSD_230929 | 4/4 | 4/4 | 4/4 | 2/2 | 0 |" in t and "| BTCUSDT | 4/4 | 4/4 | 1/1 |" in t
