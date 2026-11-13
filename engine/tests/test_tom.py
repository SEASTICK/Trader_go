"""H-0024 (månadsskiftet): beräkningskoden på rent syntetiska prisserier. Ingen Yahoo/SPY-data, ingen fil, ingen avkastningssiffra från riktiga kurser."""
import sys

import numpy as np
import pandas as pd
import pytest

from traderlab import nyse_sessions, stats, tom


def calendar(start="2005-01-03", end="2025-03-31") -> pd.DatetimeIndex:
    """Handelsdagar med samma helgdagsregler och extra stängningar som den fasta NYSE-kalendern (identisk med den inom 2006–2024)."""
    closed = set(nyse_sessions.SPECIAL_CLOSURES)
    for y in range(pd.Timestamp(start).year, pd.Timestamp(end).year + 1):
        closed |= nyse_sessions.holidays(y)
    return pd.DatetimeIndex([d for d in pd.bdate_range(start, end) if d.date() not in closed])


def prices(index, window_boost=0.0, shift=0, noise=0.01, drift=0.0004, seed=1) -> pd.DataFrame:
    """Syntetisk serie: slumpbrus plus en planterad extra avkastning `window_boost` på fönsterdagarna (T0..T3), förskjutna `shift` handelsdagar."""
    rng = np.random.default_rng(seed)
    g = rng.normal(drift, noise, len(index))
    if window_boost:
        for i0 in tom.month_end_positions(index):
            for k in range(4):
                t = i0 + shift + k + 1                    # g[t+1] är avkastningen open(t)→open(t+1), alltså etiketten t
                if 0 <= t < len(index):
                    g[t] += window_boost
    op = 100.0 * np.cumprod(1 + g)
    return pd.DataFrame({"open": op, "close": op * 1.0003}, index=index)


def tiny():
    """Jan–mars 2007 med riktiga börshelger (15 jan och 19 feb stängt): hand-kontrollerad kalender."""
    idx = calendar("2007-01-02", "2007-03-30")
    op = pd.Series(np.arange(100.0, 100.0 + len(idx)), index=idx)
    return pd.DataFrame({"open": op, "close": op + 0.5}, index=idx)


def test_t0_till_t4_ur_kalendern_med_helger():
    df = tiny()
    i0s = tom.month_end_positions(df.index)
    t0 = [df.index[i].strftime("%Y-%m-%d") for i in i0s]
    assert t0 == ["2007-01-31", "2007-02-28"]                                  # mars saknar en efterföljande månad i serien: sista raden räknas inte
    i = int(i0s[0])
    window = [df.index[i + k].strftime("%Y-%m-%d") for k in range(5)]
    assert window == ["2007-01-31", "2007-02-01", "2007-02-02", "2007-02-05", "2007-02-06"]      # T0, T1, T2, T3, T4
    assert pd.Timestamp("2007-02-19") not in df.index and pd.Timestamp("2007-01-15") not in df.index
    cyc = tom.window_cycles(df.index, (pd.Timestamp("2007-01-01"), pd.Timestamp("2007-03-31")))
    assert [df.index[c].strftime("%Y-%m-%d") for c in cyc] == ["2007-01-31", "2007-02-28"]


def test_fyra_oppning_till_oppning_avkastningar_och_noll_utanfor_fonstret():
    df = tiny()
    r = tom.open_to_open(df)
    cyc = tom.window_cycles(df.index, (pd.Timestamp("2007-01-01"), pd.Timestamp("2007-03-31")))
    s = tom.strategy_returns(df, cyc, 0, side_cost=0.0)
    i = cyc[0]
    for k in range(4):
        assert s.iloc[i + k] == pytest.approx(df["open"].iloc[i + k + 1] / df["open"].iloc[i + k] - 1)       # open(t+1)/open(t)−1
        assert s.iloc[i + k] == pytest.approx(r.iloc[i + k])
    win_pos = {c + k for c in cyc for k in range(4)}
    assert all(s.iloc[j] == 0.0 for j in range(len(s)) if j not in win_pos)                                  # kontanter 0 % utanför fönstret
    assert np.isnan(r.iloc[-1]) and s.iloc[-1] == 0.0                                                          # sista raden saknar nästa öppning
    assert np.prod(1 + s.iloc[i:i + 4]) == pytest.approx(df["open"].iloc[i + 4] / df["open"].iloc[i])       # fönstrets produkt = open(T4)/open(T0)


def test_kostnad_10_bp_per_sida_och_stress_2_5x():
    df = tiny()
    df["open"] = 100.0                                                           # platt pris: bara kostnaden syns
    cyc = tom.window_cycles(df.index, (pd.Timestamp("2007-01-01"), pd.Timestamp("2007-03-31")))[:1]
    s1 = tom.strategy_returns(df, cyc, 0, side_cost=tom.SIDE_COST)
    s25 = tom.strategy_returns(df, cyc, 0, side_cost=tom.SIDE_COST * tom.STRESS)
    i = cyc[0]
    assert s1.iloc[i] == pytest.approx(-0.0010) and s1.iloc[i + 3] == pytest.approx(-0.0010)                  # köp på T0, sälj i slutet av T3
    assert s1.iloc[i + 1] == 0.0 and s1.iloc[i + 2] == 0.0
    assert np.prod(1 + s1.iloc[i:i + 4]) == pytest.approx((1 - 0.0010) ** 2)
    assert s25.iloc[i] == pytest.approx(-0.0025) and np.prod(1 + s25.iloc[i:i + 4]) == pytest.approx((1 - 0.0025) ** 2)
    assert tom.SIDE_COST == 0.0010 and tom.STRESS == 2.5


def test_utforande_b_stangning_till_stangning():
    df = tiny()
    cyc = tom.window_cycles(df.index, (pd.Timestamp("2007-01-01"), pd.Timestamp("2007-03-31")))
    s = tom.strategy_returns(df, cyc, 0, side_cost=0.0, execution="B")
    i = cyc[0]
    assert s.iloc[i] == pytest.approx(df["close"].iloc[i] / df["close"].iloc[i - 1] - 1)


def test_placebo_tjugo_forskjutningar_gemensam_c_och_ratt_rang():
    idx = calendar("2004-01-02", "2025-02-28")
    good = prices(idx, window_boost=0.004, noise=0.006)
    df, _ = tom.clean_prices(good)
    m = tom.window_metrics(df, tom.PRIMARY, "A", 1.0)
    assert sorted(int(u) for u in m["placebo_mean_d"]) == list(range(-10, 11)) and len(m["placebo_mean_d"]) == 21 and len(tom.SHIFTS) == 21
    assert m["window_is_best_of_21"] and m["placebo_rank"] == 1                                                 # planterad effekt på verkligt fönster
    assert m["window_share_c"] == pytest.approx(4 * m["cycles"] / m["days"])                                      # c = fönsterdagar / handelsdagar i perioden
    assert 0.17 < m["window_share_c"] < 0.20
    shifted = prices(idx, window_boost=0.004, shift=3, noise=0.006)
    ms = tom.window_metrics(tom.clean_prices(shifted)[0], tom.PRIMARY, "A", 1.0)
    assert not ms["window_is_best_of_21"] and ms["placebo_mean_d"]["3"] == max(ms["placebo_mean_d"].values())     # effekt på +3 vinner placebo, inte fönstret
    assert tom.evaluate(shifted)["criteria"]["window_best_of_21_placebo"] is False


def test_manadsvis_D_t_graensen_och_alla_fem_kriterier():
    idx = calendar("2004-01-02", "2025-02-28")
    out = tom.evaluate(prices(idx, window_boost=0.004, noise=0.006))
    assert out["valid"] and out["t_required"] == 2.87 and round(stats.t_krav(tom.ATTEMPTS), 2) == 2.87 and tom.ATTEMPTS == 24
    assert set(out["criteria"]) == {"t_at_least_required", "stressed_costs_positive", "sharpe_above_buy_and_hold", "window_best_of_21_placebo", "stable_in_both_halves"}
    assert all(out["criteria"].values()) and out["decision"] == "MORE_RESEARCH"
    m = out["metrics"]
    assert m["months"] == 228 and m["cycles"] == 227                                                            # jan 2006–dec 2024; sista cykeln kräver data efter kapningen
    df, _ = tom.clean_prices(prices(idx, window_boost=0.004, noise=0.006))
    r = tom.open_to_open(df)
    mask = tom._period_mask(df.index, r, tom.PRIMARY)
    d = (tom.strategy_returns(df, tom.window_cycles(df.index, tom.PRIMARY)) - m["window_share_c"] * r)[mask]
    d_m = d.groupby(d.index.to_period("M")).sum()
    assert m["t_D"] == pytest.approx(stats.t_stat(d_m)) and m["mean_D_m"] == pytest.approx(d_m.mean())
    assert out["stressed"]["cost_mult"] == 2.5 and out["stressed"]["mean_D_m"] < m["mean_D_m"]


def test_brus_ger_reject_och_ett_kriterium_raeknar():
    idx = calendar("2004-01-02", "2025-02-28")
    out = tom.evaluate(prices(idx, seed=7))
    assert out["valid"] and out["decision"] == "REJECT" and not all(out["criteria"].values())
    assert tom.decide(True, {"a": True, "b": True}) == "MORE_RESEARCH" and tom.decide(True, {"a": True, "b": False}) == "REJECT"
    assert tom.decide(False, {"a": True}) == "OGILTIG" and tom.decide(False, None) == "OGILTIG"


def test_stabilitet_kraver_positivt_i_bada_halvorna():
    idx = calendar("2004-01-02", "2025-02-28")
    df = prices(idx, window_boost=0.004, noise=0.006)
    out = tom.evaluate(df)
    assert out["metrics"]["halves_mean_D_m"]["first"] > 0 and out["metrics"]["halves_mean_D_m"]["second"] > 0 and out["criteria"]["stable_in_both_halves"]
    neg = df.copy()                                           # från 2015 är fönsterdagarna negativa (varje fönsterdag sänker alla senare öppningar 1,2 %)
    for i0 in tom.month_end_positions(idx):
        if idx[i0] >= pd.Timestamp("2015-01-01"):
            for k in range(4):
                if i0 + k + 1 < len(idx):
                    neg.iloc[i0 + k + 1:, 0] *= (1 - 0.012)
    o2 = tom.evaluate(neg)
    assert o2["metrics"]["halves_mean_D_m"]["second"] < 0 and o2["criteria"]["stable_in_both_halves"] is False and o2["decision"] == "REJECT"


def test_data_fran_2025_kapas_innan_beraekning_och_paverkar_inget():
    idx = calendar("2004-01-02", "2025-06-30")
    good = prices(idx, window_boost=0.004, noise=0.006)
    clean = good[good.index < "2025-01-01"].copy()
    poisoned = good.copy()
    poisoned.loc[poisoned.index >= "2025-01-01", ["open", "close"]] = [1e9, np.nan]                  # giftiga värden efter gränsen
    a, b = tom.evaluate(clean), tom.evaluate(poisoned)
    assert b["rows_cut_holdout"] == int((good.index >= "2025-01-01").sum()) > 0 and a["rows_cut_holdout"] == 0
    assert a["decision"] == b["decision"] and a["metrics"] == b["metrics"] and a["stressed"] == b["stressed"]       # identiska: kapade rader används inte
    df, n = tom.clean_prices(poisoned)
    assert n > 0 and df.index.max() < tom.HOLDOUT and df.notna().all().all()
    with pytest.raises(tom.HoldoutError):
        tom.clean_prices(poisoned, strict=True)
    with pytest.raises(tom.HoldoutError):
        tom.evaluate(poisoned, strict=True)
    tz = poisoned.copy()
    tz.index = tz.index.tz_localize("UTC")                                                           # tidszon påverkar inte gränsen
    assert tom.clean_prices(tz)[1] == n
    assert tom.clean_prices(clean, strict=True)[1] == 0


def test_datakrav_brott_ger_ogiltig_utan_kriterier():
    idx = calendar("2004-01-02", "2025-02-28")
    base = prices(idx, window_boost=0.004, noise=0.006)
    assert tom.evaluate(base)["valid"]
    gap_year = base[~((base.index >= "2010-03-01") & (base.index <= "2010-12-31"))]                  # nästan ett helt år saknas
    out = tom.evaluate(gap_year)
    assert out["valid"] is False and out["decision"] == "OGILTIG" and "criteria" not in out and "metrics" not in out
    assert any("2010" in r for r in out["invalid_reasons"])
    nan = base.copy()
    nan.iloc[2000, 0] = np.nan
    assert tom.evaluate(nan)["decision"] == "OGILTIG" and any("saknade" in r for r in tom.evaluate(nan)["invalid_reasons"])
    thin = base[~((base.index >= "2012-05-08") & (base.index <= "2012-05-31"))]                      # en månad med färre än 15 dagar, året ändå inom 249–253
    out3 = tom.evaluate(thin)
    assert out3["decision"] == "OGILTIG" and any("2012-05" in r for r in out3["invalid_reasons"])
    short = base[base.index >= "2008-01-01"]
    assert tom.evaluate(short)["decision"] == "OGILTIG"                                              # 2006–2007 saknas
    dup = pd.concat([base, base.iloc[[5]]])
    with pytest.raises(tom.InvalidRun):
        tom.clean_prices(dup)


def test_den_syntetiska_kalendern_ger_249_till_253_dagar_per_ar():
    idx = calendar("2006-01-02", "2024-12-31")
    per_year = pd.Series(1, index=idx).groupby(idx.year).sum()
    assert per_year.min() >= 249 and per_year.max() <= 253


def test_modulen_hamtar_ingen_data_och_skriver_ingenting():
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(tom))
    imported = {n.module if isinstance(n, ast.ImportFrom) else a.name for n in ast.walk(tree) for a in (getattr(n, "names", []) or [None]) if isinstance(n, (ast.Import, ast.ImportFrom)) and (n.module if isinstance(n, ast.ImportFrom) else a.name)}
    assert imported <= {"__future__", "numpy", "pandas", None, ""}, imported                                   # bara numpy/pandas och `from . import stats`
    calls = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "") for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not calls & {"open", "to_csv", "write_text", "write_bytes", "urlopen", "load_prices", "dump", "to_json", "read_csv"}, calls


# ------------------------------------------------------------------ fast NYSE-sessionskalender (datakrav: varje förväntad session ska finnas)
def test_sessionskalendern_ar_fast_versionshanterad_och_stammer_med_kanda_antal():
    cal = nyse_sessions.load()                                                       # kastar om filen ändrats (SHA-256)
    assert (cal == nyse_sessions.generate()).all() and cal.min() == pd.Timestamp("2006-01-03") and cal.max() == pd.Timestamp("2024-12-31")
    per_year = pd.Series(1, index=cal).groupby(cal.year).sum().to_dict()
    assert per_year == nyse_sessions.EXPECTED_PER_YEAR and sum(per_year.values()) == len(cal) == 4781
    absent = ["2007-01-02", "2012-10-29", "2012-10-30", "2018-12-05", "2022-06-20", "2009-07-03", "2010-07-05", "2010-12-24", "2011-12-26", "2012-01-02", "2017-01-02", "2015-04-03"]
    assert not any(pd.Timestamp(d) in cal for d in absent)
    assert all(pd.Timestamp(d) in cal for d in ["2010-12-31", "2021-12-31", "2006-12-29", "2008-12-31"])         # nyårsdagen på lördag stänger inte 31 dec
    assert nyse_sessions.SESSIONS_FILE.read_bytes().count(b"\r") == 0


def test_andrad_sessionskalender_vagras(tmp_path):
    bad = tmp_path / "nyse.csv"
    text = nyse_sessions.SESSIONS_FILE.read_text(encoding="utf-8").replace("2013-06-12\n", "")
    bad.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="har ändrats"):
        nyse_sessions.load(bad)
    crlf = tmp_path / "crlf.csv"
    crlf.write_bytes(nyse_sessions.SESSIONS_FILE.read_bytes().replace(b"\n", b"\r\n"))
    assert (nyse_sessions.load(crlf) == nyse_sessions.load()).all()                   # radslut (Windows) ändrar inte hashen


def test_saknad_vanlig_session_i_ar_med_252_ger_ogiltig_trots_att_arsgransen_passeras():
    idx = calendar("2004-01-02", "2025-02-28")
    base = prices(idx, window_boost=0.004, noise=0.006)
    assert nyse_sessions.EXPECTED_PER_YEAR[2013] == 252
    gone = pd.Timestamp("2013-06-12")
    dropped = base[base.index != gone]
    assert int((dropped.index.year == 2013).sum()) == 251 and tom.YEAR_DAYS[0] <= 251 <= tom.YEAR_DAYS[1]          # inom 249–253: årsgränsen ser inget
    out = tom.evaluate(dropped)
    assert out["valid"] is False and out["decision"] == "OGILTIG" and "criteria" not in out and "metrics" not in out and "stressed" not in out
    assert any("2013-06-12" in r and "saknas" in r for r in out["invalid_reasons"])
    assert not any("2013:" in r for r in out["invalid_reasons"])                                                     # det var just kalenderkontrollen som fångade det


def test_saknad_manadsslutssession_flyttar_t0_men_ger_ogiltig():
    idx = calendar("2004-01-02", "2025-02-28")
    base = prices(idx, window_boost=0.004, noise=0.006)
    assert tom.evaluate(base)["valid"]
    gone = pd.Timestamp("2013-05-31")                                                                                # månadens sista handelsdag
    dropped = base[base.index != gone]
    df, _ = tom.clean_prices(dropped)
    t0 = [df.index[i] for i in tom.month_end_positions(df.index)]
    assert pd.Timestamp("2013-05-30") in t0 and gone not in t0                                                       # utan kalenderkontroll skulle T0 flyttats en dag
    out = tom.evaluate(dropped)
    assert out["valid"] is False and out["decision"] == "OGILTIG" and "criteria" not in out and "metrics" not in out
    assert any("2013-05-31" in r for r in out["invalid_reasons"])
    assert tom.check_data(df, tom.PRIMARY, nyse_sessions.load()) == out["invalid_reasons"]


def test_extra_dag_som_inte_ar_session_ger_ogiltig():
    idx = calendar("2004-01-02", "2025-02-28")
    base = prices(idx, window_boost=0.004, noise=0.006)
    row = base.iloc[[0]].copy()
    row.index = pd.DatetimeIndex([pd.Timestamp("2013-07-04")])                                                       # helgdag
    extra = pd.concat([base, row]).sort_index()
    out = tom.evaluate(extra)
    assert out["valid"] is False and out["decision"] == "OGILTIG" and any("2013-07-04" in r and "inga NYSE-sessioner" in r for r in out["invalid_reasons"])
    assert tom.evaluate(base)["valid"] is True                                                                       # och en komplett serie är fortfarande giltig


def test_kalenderkontrollen_ar_bara_for_perioden_och_ger_ingen_ny_ogiltighet_for_fullstandig_serie():
    idx = calendar("2004-01-02", "2025-02-28")
    base = prices(idx, window_boost=0.004, noise=0.006)
    out = tom.evaluate(base)
    assert out["valid"] and out["decision"] == "MORE_RESEARCH"
    before = base[base.index < "2006-01-01"].iloc[10:]                                                              # luckor före perioden spelar ingen roll
    holey = pd.concat([before.iloc[::2], base[base.index >= "2006-01-01"]])
    assert tom.evaluate(holey)["valid"]
