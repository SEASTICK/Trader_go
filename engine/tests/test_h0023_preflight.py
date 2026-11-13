"""Syntetiska tester för H-0023:s datapreflight. Inga marknadsdata hämtas, inga priser jämförs och inga 2025+-arkiv öppnas."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from test_h0023 import CYCLES, SIZES, _run, mkpanel
from traderlab import h0023 as h
from traderlab import h0023_preflight as pf
from traderlab.data import binance as bn
from traderlab.data import gapcheck
from traderlab.h0022_coverage import _series_name, cycle_calendar, cycle_windows

REPO = Path(__file__).resolve().parents[2]
ROWS = json.loads((REPO / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]
CAL = cycle_calendar(ROWS, "rullning_b")


def test_krävda_filer_slutar_senast_2024_09_och_btc_täcker_varje_fönstergräns():
    need = pf.required_files(CAL)
    assert all(m <= "2024-09" for months in need.values() for m in months)
    assert min(m for months in need.values() for m in months) >= "2021-03"
    btc = set(need[("spot", "BTCUSDT")])
    wins = cycle_windows([c for c in CAL if not c["flat"]])
    assert {d[:7] for w in wins for d in w} <= btc
    assert ("cm-mark", _series_name("ADA", "2021-06-25")) in need and not any(k[1] == "ETHUSDT" or k[1] == "BTCUSD_210625" for k in need)


def test_en_kalender_som_kräver_2025_stoppar_innan_något_hämtas_eller_öppnas():
    late = [{**CAL[-1], "exit": "2025-01-10", "fill": "2024-12-20", "decision": "2024-12-19"}]
    with pytest.raises(ValueError, match="slutprovet"):
        pf.required_files(late)


def _zip(name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, "0,1,1,1,1,1,1,1,1,1,1,0\n")
    return buf.getvalue()


def test_fetch_missing_hämtar_bara_saknade_krävda_månader_och_aldrig_2025(tmp_path):
    need = {("spot", "BTCUSDT"): ["2021-03", "2021-04"]}
    existing = pf._path(tmp_path, "spot", "BTCUSDT", "2021-03")
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"befintlig")                                    # rörs inte
    asked = []

    def opener(url):
        asked.append(url)
        if url.endswith(".CHECKSUM"):
            return (hashlib.sha256(_zip("x.csv")).hexdigest() + "  x.zip\n").encode()
        return _zip("x.csv")
    pf.fetch_missing(tmp_path, need, opener)
    assert existing.read_bytes() == b"befintlig"
    assert len(asked) == 2 and all("2021-04" in u for u in asked) and not any("2025" in u for u in asked)


def test_inventering_hittar_saknad_fil_saknad_checksumma_och_fel_checksumma(tmp_path):
    need = {("spot", "ADAUSDT"): ["2021-03", "2021-04", "2021-05"]}
    for m in ("2021-04", "2021-05"):
        p = pf._path(tmp_path, "spot", "ADAUSDT", m)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_zip("x.csv"))
    pf._path(tmp_path, "spot", "ADAUSDT", "2021-05").with_suffix(".zip.CHECKSUM").write_bytes(b"0" * 64 + b"  x.zip\n")        # fel checksumma
    inv = pf.inventory(tmp_path, need)
    kinds = sorted(p["problem"].split(":")[0] for p in inv["problems"])
    assert kinds == ["checksumman stämmer inte", "filen saknas", "sparad checksumma saknas"] and inv["verified"] == 0


# ---------------------------------------------------------------- oprövad luckfyllnad får aldrig passera som verifierad data
def test_riktig_oprövad_luckfyllnad_ger_anmärkning_från_h0022_load(tmp_path, monkeypatch):
    """Dagsfil för en gapdag utan manifest/grannfiler: `gapcheck.combined` kastar `UnverifiedGapFill` och `_load` returnerar en anmärkning."""
    from traderlab import h0022_coverage as hc
    idx = pd.DatetimeIndex([d for d in pd.date_range("2023-08-01", "2023-09-05", freq="D", tz="UTC") if d.strftime("%Y-%m-%d") not in gapcheck.GAP_DAYS])
    frame = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 5.0}, index=idx)
    monkeypatch.setattr(bn, "load", lambda *a, **k: frame)
    folder = tmp_path / "raw" / "binance" / "spot-daily" / "ADAUSDT" / "1d"
    folder.mkdir(parents=True)
    (folder / "ADAUSDT-1d-2023-08-28.zip").write_bytes(_zip("x.csv"))
    df, note = hc._load("spot", "ADAUSDT", tmp_path, {}, gap_fill=True)
    assert note and note.startswith("oprövad luckfyllnad") and "source" not in df.columns


def _panel_with_note(monkeypatch, notes: dict):
    """`load_panel` med syntetiska staplar där utpekade källor får en anmärkning om oprövad luckfyllnad."""
    from traderlab import h0022_coverage as hc
    base = mkpanel()

    def fake_load(market, sym, data_dir, manifest, gap_fill):
        frames = {"cm": base.fut, "cm-mark": base.mark}
        if market == "spot":
            df = base.btc if sym == "BTCUSDT" else base.spot[sym[:-4]]
        else:
            df = next(iter(frames[market].values()))                  # kalendern är den riktiga, staplarna syntetiska
        return df, notes.get((market, sym))
    monkeypatch.setattr(hc, "_load", fake_load)
    return h.load_panel(REPO, [c for c in CAL if c["cycle"] in (1,)])[0]


def test_load_panel_sparar_oprövade_källor_i_panelen(monkeypatch):
    note = "oprövad luckfyllnad: x.zip: sparad checksumma saknas"
    panel = _panel_with_note(monkeypatch, {("cm-mark", _series_name("ADA", "2021-06-25")): note, ("spot", "BTCUSDT"): note})
    assert panel.unverified == {f"mark:{_series_name('ADA', '2021-06-25')}": note, "btc": note}


def test_oprövad_markprisskälla_för_en_beslutad_position_är_ogiltig(monkeypatch):
    p = mkpanel()
    sym = _series_name("ADA", "2022-03-25")
    p.unverified[f"mark:{sym}"] = "oprövad luckfyllnad: test"
    with pytest.raises(h.InvalidRun, match="oprövad luckfyllnad"):
        h.simulate(p, CYCLES, SIZES)


@pytest.mark.parametrize("kind, key", [("fut", _series_name("ADA", "2022-03-25")), ("spot", "ADA")])
def test_oprövad_termins_eller_spotkälla_gör_att_myntet_inte_beslutas_med_tydlig_orsak(kind, key):
    p = mkpanel()
    p.unverified[f"{kind}:{key}"] = "oprövad luckfyllnad: test"
    res = h.simulate(p, CYCLES, SIZES)
    assert "ADA" not in {x["coin"] for x in res.cycles[0]["positions"]}
    assert "oprövad luckfyllnad" in res.cycles[0]["not_traded"]["ADA"]


def test_oprövad_btc_källa_ger_ogiltig_utan_prestandasiffror():
    ordinary, stressed = _run(), _run()
    p = mkpanel()
    p.unverified["btc"] = "oprövad luckfyllnad: test"
    out = h.evaluate(ordinary, stressed, p, CYCLES, n_boot=20, min_coin_cycles=10, min_cycles_four=2)
    assert out["valid"] is False and out["decision"] == "OGILTIG" and any("oprövad luckfyllnad" in r for r in out["invalid_reasons"])
    assert "beta_btc" not in out and "t_over_cycles" not in out


def test_oprövad_källa_gör_att_preflighten_inte_är_ok(monkeypatch):
    rep = {"inventory": {"problems": [], "required": 1, "verified": 1}, "fetch_missing_from_source": {},
           "probe": {"unverified_sources": {"btc": "x"}, "btc_boundaries": {"days": 1, "problems": []}, "daily_fill_files": {}, "coin_cycles_checked": 0,
                     "complete_coin_cycles": 0, "latent_invalid_if_decided": []}, "preflight_ok": False}
    assert "EJ OK" in pf.render(rep) and "Oprövad luckfyllnad" in pf.render(rep)


def test_saknad_sparad_checksumma_kompletteras_bara_om_filen_stämmer_mot_den_publicerade(tmp_path):
    need = {("spot", "ADAUSDT"): ["2021-03", "2021-04"]}
    good, bad = _zip("a.csv"), _zip("b.csv")
    for m, raw in (("2021-03", good), ("2021-04", bad)):
        p = pf._path(tmp_path, "spot", "ADAUSDT", m)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    publ = {"2021-03": hashlib.sha256(good).hexdigest(), "2021-04": "0" * 64}
    res = pf.backfill_checksums(tmp_path, need, lambda url: (publ[url.split("-1d-")[1][:7]] + "  x.zip\n").encode())
    assert res[str(pf._path(tmp_path, "spot", "ADAUSDT", "2021-03").relative_to(tmp_path))].startswith("verifierad")
    assert res[str(pf._path(tmp_path, "spot", "ADAUSDT", "2021-04").relative_to(tmp_path))].startswith("ej verifierad")
    assert pf._path(tmp_path, "spot", "ADAUSDT", "2021-03").read_bytes() == good                 # filen oförändrad
    inv = pf.inventory(tmp_path, need)
    assert inv["verified"] == 1 and [p["file"].endswith("2021-04.zip") for p in inv["problems"]] == [True]
