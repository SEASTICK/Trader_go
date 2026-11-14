"""Datapreflighten för H-0024: täckning enligt protokollets datakrav, kapning vid 2025-01-01 före första kontroll, inga kurser i resultatet. Ingen nätverkskontakt, bara syntetiska svar."""
import ast
import json
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from traderlab import nyse_sessions, tom, tom_preflight as pf


def yahoo_json(days: pd.DatetimeIndex, open_=None, close=None, adj=None, poison_after=True) -> bytes:
    """Ett syntetiskt Yahoo-svar. Timestamps är 14:30 UTC på handelsdagen. Värdena efter 2025-01-01 kan vara giftiga strängar som kraschar om de läses."""
    ts = [int((d + pd.Timedelta(hours=14, minutes=30)).replace(tzinfo=None).timestamp()) for d in pd.DatetimeIndex(days).tz_localize(None)]
    n = len(ts)
    o = list(np.linspace(100, 200, n)) if open_ is None else list(open_)
    c = list(np.linspace(100.5, 200.5, n)) if close is None else list(close)
    a = list(np.linspace(90, 190, n)) if adj is None else list(adj)
    if poison_after:
        for i, d in enumerate(pd.DatetimeIndex(days).tz_localize(None)):
            if d >= pd.Timestamp("2025-01-01"):
                o[i], c[i], a[i] = "GIFTIG", "GIFTIG", "GIFTIG"
    return json.dumps({"chart": {"result": [{"meta": {"exchangeTimezoneName": "America/New_York"}, "timestamp": ts,
                                              "indicators": {"quote": [{"open": o, "high": o, "low": o, "close": c, "volume": [1] * n}], "adjclose": [{"adjclose": a}]}}], "error": None}}).encode()


def good_frame() -> pd.DataFrame:
    cal = nyse_sessions.load()
    return pd.DataFrame({"open": np.linspace(100, 200, len(cal)), "close": np.linspace(101, 201, len(cal))}, index=cal)


def test_forfragan_slutar_vid_2025_01_01_och_borjar_2006():
    url = pf.request_url()
    assert "period1=1136073600" in url and "period2=1735689600" in url and "SPY" in url          # 2006-01-01 och 2025-01-01 (exklusivt) UTC
    assert pd.Timestamp(1735689600, unit="s") == pd.Timestamp("2025-01-01")


def test_parse_cut_laser_aldrig_varden_fran_2025_och_raknar_bara_antalet():
    days = pd.bdate_range("2024-12-20", "2025-01-10")
    raw = yahoo_json(days)                                                                       # värdena efter 2025-01-01 är strängen "GIFTIG": float() på dem kraschar
    df, n_cut = pf.parse_cut(raw)
    assert n_cut == int((days >= pd.Timestamp("2025-01-01")).sum()) and df.index.max() < pd.Timestamp("2025-01-01")
    assert not df.isna().any().any() and len(df) == len(days) - n_cut                           # ingen rad från 2025 finns kvar och inget giftigt värde har rörts


def test_parse_cut_behaller_saknade_falt_som_nan_i_stallet_for_att_tappa_raden():
    days = pd.bdate_range("2024-03-01", "2024-03-08")
    o = [None] + [1.0] * (len(days) - 1)
    df, n_cut = pf.parse_cut(yahoo_json(days, open_=o, adj=[2.0] * len(days), close=[2.0] * len(days)))
    assert n_cut == 0 and len(df) == len(days) and int(df["open"].isna().sum()) == 1


def test_preflight_uppfylld_pa_komplett_serie_och_resultatet_har_inga_kurser():
    r = pf.preflight(good_frame(), n_cut=3)
    assert r["status"] == "UPPFYLLT" and all(r["requirements"].values()) and r["rows_cut_holdout"] == 3
    assert r["cycles_expected"] == r["cycles_complete"] == 227 and r["rows_with_missing_fields"] == 0 and r["incomplete_cycles"] == []
    pf.assert_no_prices(r)
    flat = json.dumps(r)
    assert not any(isinstance(v, float) for v in r.values())                                    # inga flyttal på toppnivå: bara antal, sant/falskt, datum och hashar
    assert "open" not in r and "close" not in r and "return" not in flat.lower().replace("returns", "")


def test_data_fran_2025_paverkar_inte_utfallet_och_kapas_forst(monkeypatch):
    base = good_frame()
    extra = pd.DataFrame({"open": [1e9, np.nan, 5.0], "close": [np.nan, 1e9, 6.0]}, index=pd.DatetimeIndex(["2025-01-02", "2025-01-03", "2026-05-04"]))
    poisoned = pd.concat([base, extra])
    a, b = pf.preflight(base), pf.preflight(poisoned)
    drop = {"fetched_at_utc", "rows_cut_holdout"}
    assert {k: v for k, v in a.items() if k not in drop} == {k: v for k, v in b.items() if k not in drop}
    assert b["rows_cut_holdout"] == 3 and a["series_sha256"] == b["series_sha256"]


@pytest.mark.parametrize("mutate, key, needle", [
    (lambda d: d.drop(pd.Timestamp("2013-06-12")), "1_alla_sessioner_och_inga_saknade_varden", "2013-06-12"),
    (lambda d: pd.concat([d, pd.DataFrame({"open": [1.0], "close": [1.0]}, index=pd.DatetimeIndex(["2013-07-04"]))]).sort_index(), "1_alla_sessioner_och_inga_saknade_varden", "2013-07-04"),
])
def test_saknade_och_extra_dagar_ger_ejuppfylld_med_exakt_datum(mutate, key, needle):
    r = pf.preflight(mutate(good_frame()))
    assert r["status"] == "EJ UPPFYLLT" and r["requirements"][key] is False and needle in (r["missing_sessions"] + r["unexpected_days"])


def test_saknat_varde_arar_inte_tyst():
    d = good_frame()
    mid = pd.Timestamp("2010-03-15")
    d.loc[mid, "open"] = np.nan                                                                  # en vanlig dag mitt i månaden: räknas som saknat värde men ingår inte i någon T0–T4-cykel
    r = pf.preflight(d)
    assert r["rows_with_missing_fields"] == 1 and r["requirements"]["1_alla_sessioner_och_inga_saknade_varden"] is False and r["status"] == "EJ UPPFYLLT" and r["incomplete_cycles"] == []
    t0 = d.index[(d.index.year == 2010) & (d.index.month == 3)][-1]                              # månadens sista handelsdag = T0 för cykeln 2010-03
    d2 = good_frame()
    d2.loc[t0, "close"] = np.nan
    r2 = pf.preflight(d2)
    assert r2["incomplete_cycles"] == ["2010-03"] and r2["requirements"]["2b_varje_cykel_har_T0_T4"] is False


def test_ar_utanfor_249_253_och_manad_under_15_fangas():
    d = good_frame()
    mar = d.index[(d.index.year == 2015) & (d.index.month == 3)]
    r = pf.preflight(d.drop(mar[:10]))                                                           # 10 dagar bort i mars 2015: månaden har < 15 dagar och året < 249
    assert r["requirements"]["2_minst_15_dagar_per_manad"] is False and "2015-03" in r["months_below_minimum"]
    assert r["requirements"]["1b_249_253_dagar_per_ar"] is False and r["per_year_days"]["2015"] < 249


def test_blockerad_kalla_ger_blockerad_utan_att_byta_kalla_eller_skriva_kurser(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "CACHE_DIR", tmp_path / "raw")
    def refuse(req):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)
    r = pf.run(opener=refuse, write=False)
    assert r["status"] == "BLOCKERAD" and "403" in r["blocker"] and "requirements" not in r
    assert not (tmp_path / "raw").exists()                                                       # inget sparat
    assert "ingen annan källa" in r["note"]
    md = pf.markdown(r)
    assert "BLOCKERAD" in md and "okörd" in md and "kringgås" in md


def test_hela_flodet_med_syntetiskt_svar_sparar_bara_den_kapade_serien(tmp_path, monkeypatch):
    monkeypatch.setattr(pf, "CACHE_DIR", tmp_path / "raw")
    cal = nyse_sessions.load()
    days = cal.append(pd.bdate_range("2025-01-02", "2025-02-14"))
    raw = yahoo_json(days)
    r = pf.run(opener=lambda req: raw, write=False)
    assert r["status"] == "UPPFYLLT" and r["rows_cut_holdout"] == len(pd.bdate_range("2025-01-02", "2025-02-14"))
    saved = (tmp_path / "raw").glob("*.csv")
    text = next(saved).read_text()
    assert "2025" not in text.split("\n", 1)[1].split(",")[0] and max(l.split(",")[0] for l in text.splitlines()[1:]) < "2025-01-01"   # inga rader från 2025 på disk
    assert not list((tmp_path / "raw").glob("*.json"))                                           # det råa svaret sparas aldrig


def test_resultat_med_otillatna_nycklar_avvisas():
    with pytest.raises(AssertionError):
        pf.assert_no_prices({"status": "X", "mean_return": 0.1})


def test_modulen_importerar_ingen_annan_kalla_eller_beraeknar_ingen_avkastning():
    src = Path(pf.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not {i for i in imports if i and ("stooq" in i or "tiingo" in i or "binance" in i)}
    for forbidden in ("window_metrics", "strategy_returns", "open_to_open", "close_to_close", "t_stat", "_evaluate", "evaluate(", "decide("):
        assert forbidden not in src, forbidden                                                  # inga avkastnings-/beslutsfunktioner anropas


def test_committade_utfallet_ar_i_synk_och_utan_kurser():
    f = pf.OUT_JSON
    if not f.exists():
        pytest.skip("inget preflight-utfall committat än")
    r = json.loads(f.read_text(encoding="utf-8"))
    pf.assert_no_prices(r)
    assert r["status"] in ("UPPFYLLT", "EJ UPPFYLLT", "BLOCKERAD")
    assert pf.OUT_MD.read_text(encoding="utf-8") == pf.markdown(r)
    assert not any(isinstance(v, float) for v in r.values())


def test_sparat_utfall_beror_inte_pa_nagot_fran_2025_aven_om_servern_skickar_det(tmp_path, monkeypatch):
    """Två annars identiska Yahoo-svar med olika innehåll efter gränsen (värden, antal rader, extra fält) ger identiskt utfall på allt som sparas, bortsett från tidsstämpeln
    och radantalsdiagnostiken `rows_cut_holdout`. Fångar bland annat en hash över det råa svaret, som annars skulle bero på värdena efter gränsen."""
    monkeypatch.setattr(pf, "CACHE_DIR", tmp_path / "raw")
    cal = nyse_sessions.load()
    pre_o, pre_c, pre_a = np.linspace(100, 200, len(cal)), np.linspace(100.5, 200.5, len(cal)), np.linspace(90, 190, len(cal))   # identiska värden före gränsen i alla svar

    def response(post_days, post_value):
        days = cal.append(post_days)
        k = len(post_days)
        return yahoo_json(days, open_=[*pre_o, *[post_value] * k], close=[*pre_c, *[post_value] * k], adj=[*pre_a, *[post_value] * k], poison_after=False)
    a = response(pd.bdate_range("2025-01-02", "2025-03-14"), 123.456)
    b = response(pd.bdate_range("2025-01-02", "2025-02-07"), 999999.0)                                   # annat antal rader och andra värden efter gränsen
    c = json.loads(a)
    c["chart"]["result"][0]["meta"]["detaljer_efter_gransen"] = "annat innehåll"                         # även metadata i svaret får vara olika utan att något sparat ändras
    ra = pf.run(opener=lambda req: a, write=False)
    rb = pf.run(opener=lambda req: b, write=False)
    rc = pf.run(opener=lambda req: json.dumps(c).encode(), write=False)
    allowed_diff = {"fetched_at_utc", "rows_cut_holdout"}
    strip = lambda r: {k: v for k, v in r.items() if k not in allowed_diff}
    assert ra["rows_cut_holdout"] != rb["rows_cut_holdout"]                                              # radantalsdiagnostiken får skilja
    assert strip(ra) == strip(rb) == strip(rc)
    md = lambda r: pf.markdown(r)
    assert md(ra).replace(str(ra["rows_cut_holdout"]) + " rader kapades", "X") == md(rb).replace(str(rb["rows_cut_holdout"]) + " rader kapades", "X")
    assert "response_sha256" not in ra and "response" not in json.dumps(ra).lower().replace("responsible", "")
    saved = sorted(p.name for p in (tmp_path / "raw").iterdir())
    assert all(n.endswith("-cut.csv") for n in saved)                                                    # bara den kapade serien sparas
