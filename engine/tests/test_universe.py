"""Punkt-i-tid-universum: listning, avnotering, arkivhål, leveranskontrakt, ingen framtidsblick, spärr mot ofullständigt universum. Allt på syntetisk data."""
import numpy as np
import pandas as pd

from traderlab.agentlab import judge, universe, universe_listing
from traderlab.agentlab.data import Panel

IDX = pd.date_range("2021-01-01", periods=400, freq="D", tz="UTC")


def mk(cols: dict) -> Panel:
    """cols: symbol -> (första dagsindex, sista dagsindex inklusive, [dagsindex med hål])."""
    close = pd.DataFrame(np.nan, index=IDX, columns=list(cols))
    for s, (a, b, holes) in cols.items():
        close.iloc[a:b + 1, close.columns.get_loc(s)] = 100.0
        for h in holes:
            close.iloc[h, close.columns.get_loc(s)] = np.nan
    dvol = close * 0 + 1e8
    dvol = dvol.where(close.notna())
    fund = close * 0 + 0.0001
    fund = fund.fillna(0.0)
    return Panel(close.copy(), close.copy(), close.copy(), close, dvol, fund)


def on(p, day):
    return universe.universe_at(p, IDX[day], top_n=30, min_age=90)


def test_klassning_perp_leverans_avvecklad_och_övriga():
    assert universe.classify("BTCUSDT") == {"kind": "perp_usdt", "quote": "USDT", "expiry": None, "in_scope": True}
    d = universe.classify("BTCUSDT_230331")
    assert d["kind"] == "delivery" and d["expiry"] == "2023-03-31" and not d["in_scope"]
    assert universe.classify("BTCBUSD_210129")["kind"] == "delivery"                  # leverans även i BUSD
    assert universe.classify("BTCUSDC")["kind"] == "perp_usdc" and not universe.in_scope("BTCUSDC")
    assert universe.classify("ETHBUSD")["kind"] == "perp_busd" and not universe.in_scope("ETHBUSD")
    assert universe.classify("AERGOUSDTSETTLED")["kind"] == "settled" and not universe.in_scope("AERGOUSDTSETTLED")
    assert universe.classify("ICPUSDT_SETTLED")["kind"] == "settled"
    assert universe.classify("ETHBTC")["kind"] == "other" and not universe.in_scope("ETHBTC")
    assert universe.in_scope("币安人生USDT")                                           # icke-ASCII-namn på riktig perp
    assert universe.classify("BTCUSDT_991399")["expiry"] is None                       # ogiltigt datum kraschar inte


def test_listning_ett_kontrakt_finns_inte_före_sin_första_stapel_och_måste_bli_moget():
    p = mk({"AUSDT": (0, 399, []), "BUSDT": (150, 399, [])})
    assert on(p, 100) == ["AUSDT"]                      # B finns inte än
    assert on(p, 150 + 50) == ["AUSDT"]                 # B finns men är yngre än 90 dagar
    assert set(on(p, 150 + 95)) == {"AUSDT", "BUSDT"}
    assert universe.explain_at(p, IDX[100])["BUSDT"] == "inte noterad än"
    assert universe.explain_at(p, IDX[200])["BUSDT"] == "för ung"


def test_avnotering_kvarstår_fram_till_sista_stapeln_och_försvinner_sedan():
    p = mk({"AUSDT": (0, 399, []), "CUSDT": (0, 200, [])})
    assert "CUSDT" in on(p, 200)                         # sista stapeln: fortfarande handlingsbar (beslut på stängning, fyllning vid nästa öppning bedöms av motorn)
    assert "CUSDT" not in on(p, 201)
    assert "CUSDT" not in on(p, 399)
    assert "ingen stapel idag" in universe.explain_at(p, IDX[250])["CUSDT"]
    assert "CUSDT" in on(p, 150)                         # historiskt fanns den: inget döljs för att den är avnoterad idag


def test_arkivhål_gör_kontraktet_ohandlingsbart_just_den_dagen_och_fylls_aldrig_i():
    p = mk({"AUSDT": (0, 399, []), "DUSDT": (0, 399, [200, 201, 202])})
    assert "DUSDT" in on(p, 199)
    assert all("DUSDT" not in on(p, d) for d in (200, 201, 202))
    assert "DUSDT" in on(p, 203)
    assert np.isnan(p.close["DUSDT"].iloc[201])         # hålet är kvar


def test_leveranskontrakt_ingår_aldrig_i_universumet_men_kan_ses_med_gamla_regeln():
    p = mk({"BTCUSDT": (0, 399, []), "BTCUSDT_210625": (0, 170, [])})
    assert on(p, 150) == ["BTCUSDT"]
    assert "ut" in universe.explain_at(p, IDX[150])["BTCUSDT_210625"] or "omfång" in universe.explain_at(p, IDX[150])["BTCUSDT_210625"]
    p.scope_rule = False
    p._cache.clear()
    assert set(on(p, 150)) == {"BTCUSDT", "BTCUSDT_210625"}   # så såg R001-R004 ut


def test_ingen_framtidsblick_universum_dag_t_är_oförändrat_om_all_data_efter_t_tas_bort():
    cols = {"AUSDT": (0, 399, []), "BUSDT": (100, 399, [250]), "CUSDT": (0, 300, [])}
    p = mk(cols)
    for t in (50, 130, 199, 250, 300, 301, 380):
        cut = Panel(*(df.iloc[:t + 1] for df in (p.open, p.high, p.low, p.close, p.dvol, p.funding)))
        assert on(p, t) == universe.universe_at(cut, IDX[t], top_n=30, min_age=90), t


def test_finansieringsregeln_kräver_känd_finansiering_före_beslutet():
    p = mk({"AUSDT": (0, 399, []), "BUSDT": (0, 399, [])})
    fk = pd.DataFrame(True, index=IDX, columns=p.close.columns)
    fk.loc[IDX[200]:, "BUSDT"] = False                    # finansieringsarkivet slutar dag 200
    p.funding_known = fk
    assert "BUSDT" in on(p, 202)                          # dagarna 195-201 före beslutet: 5 av 7 kända (195-199)
    assert "BUSDT" not in on(p, 203)                      # 4 av 7: inte längre handlingsbar
    assert "BUSDT" not in on(p, 215)
    assert universe.explain_at(p, IDX[215])["BUSDT"] == "finansiering okänd"


def _listing(**syms):
    return {"symbols": {k: {"klines_1d": v, "funding": []} for k, v in syms.items()}}


def test_universe_gap_hela_symboler_och_saknade_månader_över_alla_år():
    p = mk({"AUSDT": (0, 399, [])})                       # 2021-01-01 .. 2022-02-04
    L = _listing(AUSDT=["2021-01", "2021-02"], ZUSDT=["2021-05"], **{"AUSDT_210625": ["2021-03"]}, NEWUSDT=["2023-04"])
    assert universe.universe_gap(p, L) == ["NEWUSDT", "ZUSDT"]                  # 2023-symbol räknas nu (hela 2020-2024), leverans ignoreras
    assert universe.universe_gap(p, L, until="2022-12") == ["ZUSDT"]
    p2 = mk({"AUSDT": (0, 399, []), "ZUSDT": (0, 399, []), "NEWUSDT": (0, 399, [])})
    assert universe.universe_gap(p2, L) == ["NEWUSDT@2023-04"]                   # symbolen finns, men panelen (slutar 2022) har ingen stapel i den listade månaden 2023-04


def test_universe_gap_saknad_månad_för_symbol_som_annars_finns():
    p = mk({"AUSDT": (0, 399, list(range(31, 59)))})       # februari 2021 helt utan staplar
    L = _listing(AUSDT=["2021-01", "2021-02", "2021-03"])
    assert universe.universe_gap(p, L) == ["AUSDT@2021-02"]
    p3 = mk({"AUSDT": (0, 399, [40])})                     # ett enstaka dagshål är inte en saknad månadsfil
    assert universe.universe_gap(p3, L) == []


def test_cacheträff_hoppar_inte_över_täckningskontrollen_och_gammal_cache_blir_inte_godkänd(tmp_path):
    import json
    import pickle
    from traderlab.agentlab import data
    full = mk({"AUSDT": (0, 399, []), "BUSDT": (0, 399, [])})
    cache = tmp_path / "panel.pkl"
    repo = tmp_path / "repo"
    (repo / "research/agentlab/universe").mkdir(parents=True)
    (repo / "research/agentlab/universe/um-listing.json").write_text(json.dumps({"symbols": {"AUSDT": {"klines_1d": ["2021-01"], "funding": []}, "BUSDT": {"klines_1d": ["2021-01"], "funding": []},
                                                                                    "CUSDT": {"klines_1d": ["2023-06"], "funding": []}}}))
    cache.write_bytes(pickle.dumps(full))
    cached = data.load_um_panel(tmp_path, cache=cache, listing=repo)               # cache innehåller inte CUSDT (listad först 2023)
    assert cached.meta["universe_gap"] == ["CUSDT"] and cached.meta["universe_gap_checked"] is True
    old = mk({"AUSDT": (0, 399, [])})                                               # gammal cache utan BUSDT
    cache.write_bytes(pickle.dumps(old))
    assert data.load_um_panel(tmp_path, cache=cache, listing=repo).meta["universe_gap"] == ["BUSDT", "CUSDT"]
    nolist = data.load_um_panel(tmp_path, cache=cache)                              # utan arkivlista: okontrollerat
    assert nolist.meta["universe_gap_checked"] is False and nolist.meta["universe_gap"] is None


def test_orchestratorn_blockerar_okontrollerad_och_ofullständig_täckning_men_inte_syntetisk():
    from traderlab.agentlab.orchestrator import Orchestrator
    o = Orchestrator.__new__(Orchestrator)
    o.panel = mk({"AUSDT": (0, 399, [])})
    assert o._universe_gap() == []                                                  # syntetisk panel: ingen grind
    o.panel.meta.update({"universe_gap": ["ZUSDT", "AUSDT@2021-02"], "universe_gap_checked": True})
    assert o._universe_gap() == ["ZUSDT", "AUSDT@2021-02"]
    o.panel.meta.update({"universe_gap": None, "universe_gap_checked": False})
    assert len(o._universe_gap()) == 1 and "okontrollerad" in o._universe_gap()[0]


def test_domaren_nekar_promising_när_universumet_är_ofullständigt():
    ev = {"quant": {"disc": {"sharpe": 2.0, "ann_ret": 0.8, "max_dd": -0.1, "n": 800}, "baselines": {"bh_btc": 0.5}, "beta_btc": 0.0, "turnover_ann": 20.0, "neighbors": [[None, 1.9]] * 4},
          "cost": {"sharpe_grid": {"1.0": 2.0, "2.5": 1.8}}, "skeptic": {"perm_p": 0.0, "dsr": 1.0, "half_pos": 1.0, "asset_pos": 1.0}, "portfolio": {"div_value": 0.5}}
    sealed = {"valid": {"sharpe": 1.5, "ann_ret": 0.8, "max_dd": -0.1}, "final": None}
    assert judge.final(ev, sealed)["verdict"] == "PROMISING"
    gated = judge.final(ev, sealed, universe_gap=["ZUSDT"])
    assert gated["verdict"] == "MORE_RESEARCH" and any("universum" in n for n in gated["notes"])
    assert judge.final(ev, sealed, universe_gap=[])["verdict"] == "PROMISING"


def test_arkivlistan_sparar_aldrig_månader_efter_2024_12(monkeypatch):
    def fake(prefix, delimiter=None):
        if delimiter:
            return [], ["data/futures/um/monthly/klines/AUSDT/", "data/futures/um/monthly/klines/BUSDT_240628/"]
        months = ["2024-11", "2024-12", "2025-01", "2026-03"]
        if "fundingRate" in prefix:
            return [(f"{prefix}AUSDT-fundingRate-{m}.zip", 1) for m in months] + [(f"{prefix}AUSDT-fundingRate-{months[0]}.zip.CHECKSUM", 1)], []
        return [(f"{prefix}AUSDT-1d-{m}.zip", 1) for m in months], []
    monkeypatch.setattr(universe_listing, "list_prefix", fake)
    out = universe_listing.build(workers=1)
    assert out["symbols"]["AUSDT"]["klines_1d"] == ["2024-11", "2024-12"]
    assert out["symbols"]["AUSDT"]["funding"] == ["2024-11", "2024-12"]


def test_census_skiljer_perp_och_leverans_med_finansieringsarkiv_och_hittar_månadshål():
    from traderlab.agentlab import universe_audit as ua
    L = {"symbols": {"AUSDT": {"klines_1d": ["2021-01", "2021-02", "2021-04"], "funding": ["2021-01", "2021-02"]},
                     "AUSDT_210625": {"klines_1d": ["2021-03"], "funding": []}, "ABUSD": {"klines_1d": ["2021-01"], "funding": ["2021-01"]},
                     "QBUSD": {"klines_1d": ["2021-01"], "funding": ["2021-01"]}, "ZUSDT": {"klines_1d": ["2021-02"], "funding": ["2021-02"]}}}
    c = ua.census(L)
    assert c["by_kind"]["delivery"]["with_funding_archive"] == 0 and c["by_kind"]["perp_usdt"]["without_funding_archive"] == 0
    assert c["listing_month_holes"] == {"AUSDT": ["2021-03"]}
    assert c["anomalies"]["usdt_perp_funding_shorter_than_klines"] == ["AUSDT"]
    assert c["anomalies"]["busd_usdc_perps_listed_by_2022_12_without_usdt_perp_on_same_underlying"] == ["QBUSD"]
