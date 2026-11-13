"""Syntetiska tester för H-0023:s strategimotor (traderlab/h0023.py). Inga marknadsdata läses och ingen resultatfil skrivs."""
import copy
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from traderlab import h0023 as h
from traderlab.basis_costs import position_size
from traderlab.h0022_coverage import _series_name, cycle_calendar, cycle_windows, paired_observations
from traderlab.pit_universe import SEVEN

REPO = Path(__file__).resolve().parents[2]
ROWS = json.loads((REPO / "research" / "universe" / "coinm-pit-series.json").read_text(encoding="utf-8"))["series"]

START, END = "2021-12-01", "2022-12-31"
ALL_COINS = list(SEVEN)
CYCLES = [
    {"cycle": 1, "expiry": "2022-03-25", "decision": "2022-01-14", "fill": "2022-01-15", "exit": "2022-03-18", "valid_coins": ALL_COINS, "flat": False},
    {"cycle": 2, "expiry": "2022-06-24", "decision": "2022-03-25", "fill": "2022-03-26", "exit": "2022-06-17", "valid_coins": [], "flat": True},
    {"cycle": 3, "expiry": "2022-09-30", "decision": "2022-06-24", "fill": "2022-06-25", "exit": "2022-09-23", "valid_coins": ALL_COINS, "flat": False},
]
SIZES = {_series_name(c, e): {"median": 10.0} for c in ALL_COINS for e in ("2022-03-25", "2022-06-24", "2022-09-30")}


def _spot(day: pd.Timestamp) -> float:
    return 100.0 * (1 + 0.0005 * (day - pd.Timestamp(START, tz="UTC")).days)


def _frame(days, price, vol, hi=1.01, lo=0.99):
    idx = pd.DatetimeIndex(list(days))
    open_ = np.array([price(d) for d in idx])
    return pd.DataFrame({"open": open_, "high": open_ * hi, "low": open_ * lo, "close": open_, "volume": [vol] * len(idx)}, index=idx)


def mkpanel(cycles=CYCLES, basis=0.03, vol=2e5):
    """Terminen = spot · (1 + basis · dagar kvar / 90), alltså en basis som konvergerar linjärt mot förfall."""
    days = pd.date_range(START, END, freq="D", tz="UTC")
    fut, mark, spot = {}, {}, {}
    for coin in ALL_COINS:
        spot[coin] = _frame(days, _spot, 1e4)
        for e in {c["expiry"] for c in cycles}:
            sym = _series_name(coin, e)
            exp = pd.Timestamp(e, tz="UTC")
            price = lambda d, exp=exp: _spot(d) * (1 + basis * max(0, (exp - d).days) / 90)
            fut[sym] = _frame(days, price, vol)
            mark[sym] = _frame(days, price, 0.0)
    return h.Panel(fut, mark, spot, _frame(days, lambda d: 20000.0 * (1 + 0.001 * (d - pd.Timestamp(START, tz="UTC")).days), 5e3))


def _run(panel=None, cycles=CYCLES, **kw):
    return h.simulate(panel or mkpanel(cycles), cycles, SIZES, **kw)


# ------------------------------------------------------------------ kalender: 14 cykler, platt cykel 2, sista X_14
def test_kalendern_har_14_cykler_inklusive_platt_cykel_2_och_sista_utträdet_x14():
    cal = cycle_calendar(ROWS, "rullning_b")
    assert len(cal) == 14 and [c["cycle"] for c in cal if c["flat"]] == [2]
    win = cycle_windows(cal)
    assert win[-1] == (cal[-1]["fill"], "2024-09-20") and all(b <= "2024-09-20" for _, b in win)
    for c in cal:
        h._check_cycle(c)                                                      # beslut + 1 dag = fyllning för alla 14
    with pytest.raises(ValueError):
        h._check_cycle({**cal[0], "fill": "2021-03-28"})


# ------------------------------------------------------------------ beslut med bara redan avslutad beslutsdags data
def test_beslutet_ändras_inte_av_något_efter_beslutsdagen_utom_fyllningsstaplarna():
    base = _run()
    p2 = mkpanel()
    for sym, df in list(p2.fut.items()) + list(p2.spot.items()):
        df.loc[df.index > pd.Timestamp("2022-01-14", tz="UTC"), "volume"] *= 1000          # volymen efter beslutsdagen ändras kraftigt
    flipped = _run(p2)
    assert [(r["cycle"], sorted(p["coin"] for p in r["positions"])) for r in base.cycles] == [(r["cycle"], sorted(p["coin"] for p in r["positions"])) for r in flipped.cycles]
    assert base.cycles[0]["positions"][0]["size"] == flipped.cycles[0]["positions"][0]["size"]     # taket använder bara dagar till och med beslutsdagen


def test_saknad_beslutsdagsstapel_färre_än_20_dagar_eller_fel_kontraktsstorlek_gör_myntet_platt_inte_ogiltigt():
    p = mkpanel()
    sym = _series_name("ADA", "2022-03-25")
    p.fut[sym] = p.fut[sym].drop(pd.Timestamp("2022-01-14", tz="UTC"))                    # ingen terminsstapel beslutsdagen
    p.spot["BCH"] = p.spot["BCH"].drop(pd.Timestamp("2022-01-14", tz="UTC"))                # ingen spotstapel beslutsdagen
    p.fut[_series_name("BNB", "2022-03-25")] = p.fut[_series_name("BNB", "2022-03-25")].loc["2022-01-05":]       # färre än 20 handelsdagar före beslutet
    sizes = {**SIZES, _series_name("DOT", "2022-03-25"): {"median": 12.0}}
    res = h.simulate(p, CYCLES, sizes)
    traded = {x["coin"] for x in res.cycles[0]["positions"]}
    assert traded == {"LINK", "LTC", "XRP"}
    assert res.cycles[0]["not_traded"]["ADA"].startswith("ingen verifierad terminsstapel")
    assert "spotstapel" in res.cycles[0]["not_traded"]["BCH"] and "20 handelsdagar" in res.cycles[0]["not_traded"]["BNB"]
    assert "kontraktsstorlek" in res.cycles[0]["not_traded"]["DOT"]


@pytest.mark.parametrize("mutate", [
    lambda p, f, x: p.fut.__setitem__(_series_name("ADA", "2022-03-25"), p.fut[_series_name("ADA", "2022-03-25")].drop(pd.Timestamp(f, tz="UTC"))),
    lambda p, f, x: p.fut[_series_name("ADA", "2022-03-25")].loc.__setitem__((pd.Timestamp(f, tz="UTC"), "volume"), 0.0),      # nollvolym på fyllningsdagen
    lambda p, f, x: p.spot["ADA"].loc.__setitem__((pd.Timestamp(x, tz="UTC"), "volume"), 0.0),                                 # nollvolym på utträdesdagen (spot)
    lambda p, f, x: p.spot.__setitem__("ADA", p.spot["ADA"].drop(pd.Timestamp("2022-02-10", tz="UTC"))),                      # saknad nästa öppning (spot)
    lambda p, f, x: p.fut.__setitem__(_series_name("ADA", "2022-03-25"), p.fut[_series_name("ADA", "2022-03-25")].drop(pd.Timestamp("2022-02-10", tz="UTC"))),
    lambda p, f, x: p.mark.__setitem__(_series_name("ADA", "2022-03-25"), p.mark[_series_name("ADA", "2022-03-25")].drop(pd.Timestamp("2022-02-10", tz="UTC"))),
])
def test_saknad_fyllnings_eller_hållen_dagsstapel_för_en_beslutad_position_är_ogiltig_aldrig_platt(mutate):
    p = mkpanel()
    mutate(p, "2022-01-15", "2022-03-18")
    with pytest.raises(h.InvalidRun):
        h.simulate(p, CYCLES, SIZES)


def test_open_time_0100_på_fyllningsdagen_är_ogiltig_eftersom_dagsstapeln_måste_vara_00_00():
    p = mkpanel()
    sym = _series_name("ADA", "2022-03-25")
    df = p.fut[sym].copy()
    idx = list(df.index)
    i = idx.index(pd.Timestamp("2022-01-15", tz="UTC"))
    idx[i] = idx[i] + pd.Timedelta(hours=1)
    df.index = pd.DatetimeIndex(idx)
    p.fut[sym] = df
    with pytest.raises(h.InvalidRun):
        h.simulate(p, CYCLES, SIZES)


# ------------------------------------------------------------------ självfinansierande kapital, 8 dagars kontanter, platt cykel
def test_kassaboken_kedjar_v_återinvesterar_och_ligger_8_dagar_i_kontanter_mellan_cyklerna():
    res = _run()
    c1, c2, c3 = res.cycles
    assert c1["v_start"] == 140000.0 and [p["size"] for p in c1["positions"]] == [20000.0] * 7          # V/7
    assert c2["positions"] == [] and c2["r"] == 0.0 and c2["v_start"] == c1["v_end"] and c2["v_end"] == c1["v_end"]     # platt cykel
    assert c3["v_start"] == c2["v_end"]
    assert all(abs(p["size"] - c3["v_start"] / 7) < 1e-9 for p in c3["positions"])                      # vinster återinvesteras
    assert res.v_final == c3["v_end"] and c1["invested"] + c1["cash_idle"] == pytest.approx(c1["v_start"])
    # 8 dagar kontanter utan ränta: värdet är konstant från utträdet till nästa inträde
    idle = res.daily.loc["2022-03-18":"2022-03-25"]
    assert len(idle) == 8 and idle.nunique() == 1 and idle.iloc[0] == pytest.approx(c1["v_end"])
    # kontanterna ger ingen ränta under den platta cykeln (c2): värdet står stilla hela vägen till nästa inträde
    assert res.daily.loc["2022-03-26":"2022-06-24"].nunique() == 1
    assert res.windows == [("2022-01-15", "2022-03-26"), ("2022-03-26", "2022-06-25"), ("2022-06-25", "2022-09-23")]


def test_storleken_är_densamma_som_kassabokens_enda_storleksregel_och_taket_begränsar():
    assert position_size(140000.0, slots=7, valid=True, cap=15000.0, min_size=10000.0) == 15000.0
    assert position_size(140000.0, slots=7, valid=True, cap=9000.0, min_size=10000.0) == 0.0
    assert position_size(60000.0, slots=7, valid=True, cap=1e9, min_size=10000.0) == 0.0               # V/7 under minsta storlek
    capped = _run(mkpanel(vol=7.5e4))                                                                      # 750 000 USD/dag -> tak 15 000
    assert all(p["size"] == pytest.approx(15000.0) for p in capped.cycles[0]["positions"])
    assert capped.cycles[0]["cash_idle"] == pytest.approx(140000.0 - 7 * 15000.0)


# ------------------------------------------------------------------ separata priser, 50 bp och 2,5× stress
def test_nollbasis_kostar_50_bp_och_stress_125_bp_per_position_oberoende_av_prisriktningen():
    p = mkpanel(basis=0.0)                                                                                  # termin = spot vid inträde och utträde
    res, stressed = _run(p), _run(p, costs=h.Costs().stressed())
    for rec, rec_s in zip(res.cycles[:1], stressed.cycles[:1]):
        for q, q_s in zip(rec["positions"], rec_s["positions"]):
            assert -q["ret"] * 1e4 == pytest.approx(50.0, abs=8.0)                                         # heltalsavrundning av ett kontrakt (10 USD av 20 000)
            assert -q_s["ret"] * 1e4 == pytest.approx(125.0, abs=8.0)
    assert stressed.v_final < res.v_final


def test_spot_och_termin_har_separata_priser_vid_in_och_utträde():
    res = _run(mkpanel(basis=0.04))
    q = res.cycles[0]["positions"][0]
    assert q["entry_basis"] > q["exit_basis"] >= 0                                                         # basis 4 % -> ~0 vid utträdet sju dagar före förfall
    assert q["entry_basis"] != q["exit_basis"]
    # utan kostnader är avkastningen exakt fut0/spot0 · spot_exit/fut_exit − 1 (inte avräkning mot en enda kurs)
    free = _run(mkpanel(basis=0.04), costs=h.Costs(0.0, 0.0, 0.0))
    qf = free.cycles[0]["positions"][0]
    assert qf["ret"] == pytest.approx((1 + qf["entry_basis"]) / (1 + qf["exit_basis"]) - 1, abs=1e-3)


# ------------------------------------------------------------------ riskstopp vid markpris
def test_riskstopp_stänger_vid_nästa_öppning_med_full_kostnad_och_standardgränsen_0_8_utlöses_aldrig_vid_full_täckning():
    assert _run().stops == []                                                                              # kvoten är ~0,5 oberoende av priset
    res = _run(stop_ratio=0.4)                                                                            # under den strukturella 0,5: stoppet utlöses
    assert len(res.stops) >= 7 and all(s["exit_day"] > s["day"] for s in res.stops)
    first = res.stops[0]
    assert first["day"] == "2022-01-15" and first["exit_day"] == "2022-01-16" and first["ratio"] >= 0.4
    pos = res.cycles[0]["positions"][0]
    assert pos["stopped"] and pos["exit_day"] == "2022-01-16"
    assert res.daily.loc["2022-01-16":"2022-03-18"].nunique() == 1                                         # platt resten av cykeln: kontanter


def test_stopp_ger_reject_via_kriteriet_och_aldrig_morgonbeslut():
    ordinary, stressed = _run(stop_ratio=0.4), _run(stop_ratio=0.4, costs=h.Costs().stressed())
    out = h.evaluate(ordinary, stressed, mkpanel(), CYCLES, n_boot=50, min_coin_cycles=10, min_cycles_four=1)
    assert out["valid"] and out["criteria"]["no_risk_stop"] is False and out["decision"] == "REJECT"


# ------------------------------------------------------------------ datakrav som fail-closed, ogiltig utan siffror
def test_datakrav_4_ger_ogiltig_utan_prestandasiffror_och_aldrig_more_research():
    ordinary, stressed = _run(), _run(costs=h.Costs().stressed())
    out = h.evaluate(ordinary, stressed, mkpanel(), CYCLES, n_boot=50)                          # standardkrav 46 av 91 och 10 av 13
    assert out["valid"] is False and out["decision"] == "OGILTIG" and any("Datakrav 4" in r for r in out["invalid_reasons"])
    for forbidden in ("t_over_cycles", "cagr", "beta_btc", "total_return", "stressed_total_return", "cycle_returns", "criteria", "positions"):
        assert forbidden not in out
    assert out["coverage_diagnostic"]["traded_coin_cycles"] == 14 and out["coverage_diagnostic"]["cycles_with_four"] == 2


def test_saknad_btc_stapel_för_beta_ger_ogiltig():
    p = mkpanel()
    p.btc = p.btc.drop(pd.Timestamp("2022-06-25", tz="UTC"))                                                 # T_2 = F_3
    ordinary, stressed = _run(mkpanel()), _run(mkpanel(), costs=h.Costs().stressed())
    out = h.evaluate(ordinary, stressed, p, CYCLES, n_boot=50, min_coin_cycles=10, min_cycles_four=2)
    assert out["decision"] == "OGILTIG" and any("Datakrav 8" in r and "2022-06-25" in r for r in out["invalid_reasons"])
    assert "beta_btc" not in out


def test_giltig_syntetisk_körning_ger_siffror_och_beslut_enligt_kriterierna():
    ordinary, stressed = _run(), _run(costs=h.Costs().stressed())
    out = h.evaluate(ordinary, stressed, mkpanel(), CYCLES, n_boot=200, min_coin_cycles=10, min_cycles_four=2)
    assert out["valid"] and out["n_cycles"] == 3 and len(out["cycle_returns"]) == 3 and out["cycle_returns"][1] == 0.0
    assert out["t_required"] == h.LOCKED_T_REQUIRED == 3.45 and out["decision"] == h.decide(out["criteria"])
    assert out["span_days"] == (pd.Timestamp("2022-09-23") - pd.Timestamp("2022-01-15")).days
    assert out["cagr"] == pytest.approx((ordinary.v_final / 140000.0) ** (365 / out["span_days"]) - 1)


# ------------------------------------------------------------------ statistik och beslut på 14 cykler
def _fake(rs):
    """En SimResult med 14 cykler ur den riktiga kalendern och givna cykelavkastningar (statistiken testas utan simulering)."""
    cal = cycle_calendar(ROWS, "rullning_b")
    v, recs = 140000.0, []
    for c, r in zip(cal, rs):
        recs.append({"cycle": c["cycle"], "fill": c["fill"], "exit": c["exit"], "v_start": v, "v_end": v * (1 + r), "r": r,
                     "positions": [] if c["flat"] else [{"coin": k} for k in range(5)]})
        v *= 1 + r
    return h.SimResult(140000.0, v, recs, [], pd.Series(dtype=float), sum(len(r["positions"]) for r in recs), cycle_windows(cal)), cal


def _btc_panel(cal):
    days = pd.date_range("2021-03-01", "2024-09-30", freq="D", tz="UTC")
    return h.Panel({}, {}, {}, _frame(days, lambda d: 20000.0 + 10.0 * (d - days[0]).days, 1e3))


def test_cykelstatistik_t_beta_cagr_och_beslut_på_de_14_cyklerna_med_x14_som_slutpunkt():
    rs = [0.01, 0.0, 0.012, 0.011, 0.009, 0.013, 0.01, 0.012, 0.008, 0.011, 0.01, 0.012, 0.009, 0.011]
    sim, cal = _fake(rs)
    out = h.evaluate(sim, sim, _btc_panel(cal), cal, n_boot=500)
    assert out["valid"] and out["n_cycles"] == 14
    assert out["t_over_cycles"] == pytest.approx(h.cycle_t(rs)) and out["t_required"] == 3.45 and out["t_quantile_unrounded"] == pytest.approx(3.4452, abs=1e-3) and out["attempts"] == 23
    assert h.t_required(23, 14) == pytest.approx(max(2.8518, 3.4452), abs=1e-3)
    win = cycle_windows(cal)
    port = {r["fill"]: r["v_start"] for r in sim.cycles}
    port[win[-1][1]] = sim.cycles[-1]["v_end"]
    days = pd.date_range("2021-03-01", "2024-09-30", freq="D", tz="UTC")
    btc = {d: 20000.0 + 10.0 * (pd.Timestamp(d, tz="UTC") - days[0]).days for w in win for d in w}
    pairs = paired_observations(win, port, btc)
    pr, br = np.array([a for a, _ in pairs]), np.array([b for _, b in pairs])
    assert out["beta_btc"] == pytest.approx(np.cov(pr, br, ddof=1)[0, 1] / np.var(br, ddof=1))
    assert out["span_days"] == 1273 == (pd.Timestamp("2024-09-20") - pd.Timestamp("2021-03-27")).days
    assert out["cagr"] == pytest.approx((sim.v_final / 140000.0) ** (365 / 1273) - 1)
    assert out["decision"] == h.decide(out["criteria"]) and set(out["criteria"]) == {"t_over_cycles_at_least_required", "stressed_costs_positive",
                                                                                      "abs_beta_btc_at_most_limit", "cagr_above_cash", "no_risk_stop"}


def test_beslutsmatrisen_more_research_bara_om_alla_fem_kriterier_gäller():
    ok = {"t_over_cycles_at_least_required": True, "stressed_costs_positive": True, "abs_beta_btc_at_most_limit": True, "cagr_above_cash": True, "no_risk_stop": True}
    assert h.decide(ok) == "MORE_RESEARCH"
    for k in ok:
        assert h.decide({**ok, k: False}) == "REJECT"
    assert h.cycle_t([0.01] * 5) == math.inf and h.cycle_t([0.0] * 5) == 0.0 and h.cycle_t([-0.01] * 5) == -math.inf
    assert h.t_required(23, 14) > h.t_required(22, 14)                                                      # N = 23 ger högre krav än N = 22


# ------------------------------------------------------------------ slutprovet (2025+) läses aldrig
def test_staplar_från_slutprovet_i_panelen_ger_ogiltig_och_läsarna_stänger_2024_10():
    p = mkpanel()
    sym = _series_name("ADA", "2022-03-25")
    extra = _frame([pd.Timestamp("2025-01-02", tz="UTC")], lambda d: 1.0, 1.0)
    p.fut[sym] = pd.concat([p.fut[sym], extra])
    with pytest.raises(h.InvalidRun, match="slutprovet"):
        h.simulate(p, CYCLES, SIZES)
    from traderlab import h0022_coverage as hc
    assert hc.DATA_END == pd.Timestamp("2024-10-01", tz="UTC") < pd.Timestamp(h.HOLDOUT, tz="UTC")


def test_läsaren_öppnar_inte_filer_från_2025(tmp_path):
    from traderlab import h0022_coverage as hc
    import io
    import zipfile
    folder = tmp_path / "raw" / "binance" / "spot" / "BTCUSDT" / "1d"
    folder.mkdir(parents=True)

    def zipped(name, text):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(name, text)
        return buf.getvalue()
    (folder / "BTCUSDT-1d-2024-09.zip").write_bytes(zipped("a.csv", "1725148800000,1,2,0.5,1.5,10,1725235199999,0,0,0,0,0\n"))
    (folder / "BTCUSDT-1d-2025-01.zip").write_bytes(b"inte en zip: far aldrig oppnas")
    df, note = hc._load("spot", "BTCUSDT", tmp_path, {}, gap_fill=False)
    assert df is not None and len(df) == 1 and df.index.max() < pd.Timestamp("2025-01-01", tz="UTC")


# ------------------------------------------------------------------ körningen: bekräftelse och registrering, ingen resultatfil
def test_körningen_kräver_bekräftelse_och_skriver_ingen_fil_utan_den(monkeypatch, tmp_path):
    saved = []
    monkeypatch.setattr(h, "_save", lambda *a, **k: saved.append(a))
    with pytest.raises(RuntimeError, match="confirm-registered-run"):
        h.run(tmp_path)
    from traderlab.registry import NotRegisteredError
    with pytest.raises(NotRegisteredError):
        h.run(tmp_path, confirm_registered_run=True)                                                       # ingen committad registerfil i tmp_path
    assert saved == []
    assert not any("H-0023" in p.name for p in (REPO / "research" / "results").glob("*"))                   # ingen resultatfil finns


def test_reglertabellen_pekar_på_kod_och_tester_som_finns():
    doc = (REPO / "research" / "h0023-motor-regler.md").read_text(encoding="utf-8")
    code = (REPO / "engine" / "traderlab" / "h0023.py").read_text(encoding="utf-8") + (REPO / "engine" / "traderlab" / "basis_costs.py").read_text(encoding="utf-8")
    tests = "".join(f.read_text(encoding="utf-8") for f in (REPO / "engine" / "tests").glob("test_*.py"))
    syms = set(re.findall(r"`((?:h0023\.)?[a-z_]+(?:\(\))?)`", doc))
    names = {m for m in re.findall(r"`(test_[a-zåäö_0-9]+)`", doc)}
    assert names, "tabellen ska nämna tester"
    for n in names:
        assert f"def {n}" in tests, n
    for fn in ("simulate", "evaluate", "decide", "t_required", "cycle_t", "assert_before_holdout", "run", "position_size", "ledger_run", "margin_ratio"):
        assert f"def {fn}" in code and fn in doc, fn


# ------------------------------------------------------------------ låst beslutsgräns (granskningsfynd P1)
def _rs_with_t(t_target):
    """14 cykelavkastningar med exakt det önskade t (t är skalinvariant: medelvärdet sätts efter standardavvikelsen)."""
    d = np.array([1, -1, 2, -2, 0.5, -0.5, 1.5, -1.5, 1, -1, 0.2, -0.2, 0.7, -0.7])
    sd = float(np.std(d, ddof=1))
    return list(0.001 * (d + t_target * sd / math.sqrt(14)))


@pytest.mark.parametrize("t_target, expected", [(3.4452, False), (3.4499, False), (3.4501, True), (3.60, True)])
def test_beslutsgränsen_är_det_frysta_3_45_inte_den_oavrundade_kvantilen(t_target, expected):
    rs = _rs_with_t(t_target)
    assert h.cycle_t(rs) == pytest.approx(t_target, abs=1e-9)
    sim, cal = _fake(rs)
    out = h.evaluate(sim, sim, _btc_panel(cal), cal, n_boot=20)
    assert out["t_required"] == h.LOCKED_T_REQUIRED == 3.45 and out["attempts"] == h.LOCKED_ATTEMPTS == 23
    assert out["criteria"]["t_over_cycles_at_least_required"] is expected


def test_senare_registerrader_ändrar_inte_h0023_gränsen(monkeypatch):
    """Ett senare registrerat id (N = 24) får varken ändra kravet eller beslutet; registerantalet redovisas bara som information."""
    from types import SimpleNamespace
    seen = {}
    sim, cal = _fake(_rs_with_t(3.4499))
    monkeypatch.setattr(h, "require_registered", lambda hyp, repo=None: SimpleNamespace(attempts=24, registry_commit="x"))
    monkeypatch.setattr(h, "load_panel", lambda repo, cycles: (_btc_panel(cal), {}))
    monkeypatch.setattr(h, "simulate", lambda *a, **k: sim)
    monkeypatch.setattr(h, "_save", lambda repo, out: seen.setdefault("out", out) and Path("x"))
    real = h.evaluate
    monkeypatch.setattr(h, "evaluate", lambda *a, **k: real(*a, **{**k, "n_boot": 20}))
    assert "attempts" not in real.__code__.co_varnames[:real.__code__.co_argcount + real.__code__.co_kwonlyargcount]
    h.run(Path(__file__).resolve().parents[2], confirm_registered_run=True)
    out = seen["out"]
    assert out["registry_attempts_now"] == 24 and out["attempts"] == 23 and out["t_required"] == 3.45
    assert out["criteria"]["t_over_cycles_at_least_required"] is False and out["decision"] == "REJECT"
