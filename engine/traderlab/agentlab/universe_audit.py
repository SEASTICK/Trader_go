"""Universums- och datatäckningsaudit för Binance USDⓈ-M (discoveryperioden 2020-2022, förbrukade år 2023-2024 redovisas bara på filnivå och som utfall av R001-R004).

Svarar på: vilka kontrakt fanns (arkivlistan), vilka är perpar och vilka leveranskontrakt (verifierbart), vilka historiska filer saknas lokalt, vilka symboler
kan Agentlab välja, och hur stor del av R001-R004:s exponering som låg utanför ett korrekt universum. Läser aldrig 2025 eller senare. Ändrar inga experimentposter.

Körning: `python -m traderlab.agentlab universe-audit`  (skriver research/agentlab/universe/coverage-discovery.json och .md)
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import agents
from .data import HOLDOUT, PERIODS, load_um_panel, period_slice
from .state import ExperimentRegistry
from .strategies import make_spec
from .universe import classify, in_scope, load_listing

YEARS = [2020, 2021, 2022, 2023, 2024]
DISC_END = "2022-12"


def _local_months(data: Path, sym: str, kind: str) -> list[str]:
    d = data / "raw" / "binance" / "um" / sym / ("1d" if kind == "klines" else "fundingRate")
    return sorted(p.name.rsplit("-", 2)[-2] + "-" + p.name.rsplit("-", 1)[-1][:2] for p in d.glob("*.zip")) if d.exists() else []


def _yr(months: list[str]) -> dict[int, int]:
    out = {y: 0 for y in YEARS}
    for m in months:
        if int(m[:4]) in out:
            out[int(m[:4])] += 1
    return out


def census(listing: dict) -> dict:
    """Arter i arkivlistan och verifiering av perp/leverans mot finansieringsarkiv (bara perpar har finansiering)."""
    rows = {}
    for s, v in listing["symbols"].items():
        c = classify(s)
        rows[s] = {"kind": c["kind"], "first_month": v["klines_1d"][0], "last_month": v["klines_1d"][-1], "kline_months": len(v["klines_1d"]), "funding_months": len(v["funding"]), "expiry": c["expiry"]}
    kinds = sorted({r["kind"] for r in rows.values()})
    tab = {}
    for k in kinds:
        sub = {s: r for s, r in rows.items() if r["kind"] == k}
        disc = {s: r for s, r in sub.items() if r["first_month"] <= DISC_END}
        tab[k] = {"symbols_with_archive_before_2025": len(sub), "listed_by_2022_12": len(disc), "with_funding_archive": sum(1 for r in sub.values() if r["funding_months"] > 0),
                  "without_funding_archive": sum(1 for r in sub.values() if r["funding_months"] == 0)}
    anomalies = {"delivery_with_funding": sorted(s for s, r in rows.items() if r["kind"] == "delivery" and r["funding_months"] > 0),
                 "usdt_perp_without_funding": sorted(s for s, r in rows.items() if r["kind"] == "perp_usdt" and r["funding_months"] == 0),
                 "usdt_perp_funding_shorter_than_klines": sorted(s for s, r in rows.items() if r["kind"] == "perp_usdt" and 0 < r["funding_months"] < r["kline_months"])}
    usdt_bases = {s[:-4] for s, r in rows.items() if r["kind"] == "perp_usdt"}
    only_other_quote = sorted(s for s, r in rows.items() if r["kind"] in ("perp_busd", "perp_usdc") and s[:-4] not in usdt_bases and r["first_month"] <= DISC_END)
    anomalies["busd_usdc_perps_listed_by_2022_12_without_usdt_perp_on_same_underlying"] = only_other_quote
    holes = {s: [m for m in pd.period_range(v["klines_1d"][0], v["klines_1d"][-1], freq="M").strftime("%Y-%m") if m not in set(v["klines_1d"])] for s, v in listing["symbols"].items()}
    return {"by_kind": tab, "anomalies": anomalies, "listing_month_holes": {s: h for s, h in holes.items() if h}, "rows": rows}


def delivery_check(data: Path) -> dict:
    """Leveranskontrakt: sista stapeln ska ligga på utgångsdatumet i namnet (verifierar att namnregeln stämmer). Bara kontrakt som gått ut före 2025."""
    from ..data import binance
    out = []
    for p in sorted((data / "raw" / "binance" / "um").iterdir()):
        c = classify(p.name)
        if c["kind"] != "delivery" or c["expiry"] is None or pd.Timestamp(c["expiry"]) >= pd.Timestamp("2025-01-01"):
            continue
        try:
            df = binance.load("um", p.name, "1d", data, start=pd.Timestamp("2019-01-01", tz="UTC"), end=HOLDOUT)
        except FileNotFoundError:
            continue
        out.append({"symbol": p.name, "expiry_in_name": c["expiry"], "last_bar": str(df.index.max().date()), "days_after_expiry": int((df.index.max() - pd.Timestamp(c["expiry"], tz="UTC")).days)})
    d = [o["days_after_expiry"] for o in out]
    return {"checked": len(out), "last_bar_on_expiry_date": sum(x == 0 for x in d), "last_bar_within_2_days_after": sum(0 <= x <= 2 for x in d), "outside_0_to_2_days": [o for o in out if not 0 <= o["days_after_expiry"] <= 2],
            "note": "Namnets datum är nominellt utgångsdatum (fredag); sista dagsstapeln kan ligga 1-2 dagar senare (avvecklingshelg). Regeln 'namn SYMBOL_YYMMDD = leveranskontrakt' stöds också av att inget leveranskontrakt har finansieringsarkiv."}


def file_coverage(listing: dict, data: Path) -> dict:
    """Månadsfiler som arkivlistan visar jämfört med lokalt, per år. I omfånget (USDT-perpar) och utanför (andra arter, redovisas som avgränsning)."""
    res = {}
    for scope in ("in_scope", "out_of_scope"):
        listed, local, missing, fmissing, flisted = ({y: 0 for y in YEARS} for _ in range(5))
        miss_syms = set()
        for s, v in listing["symbols"].items():
            if in_scope(s) != (scope == "in_scope"):
                continue
            lm, lo = set(v["klines_1d"]), set(_local_months(data, s, "klines"))
            for m in lm:
                y = int(m[:4])
                if y in listed:
                    listed[y] += 1
                    if m in lo:
                        local[y] += 1
                    else:
                        missing[y] += 1
                        miss_syms.add(s)
            fl, flo = set(v["funding"]), set(_local_months(data, s, "funding"))
            for m in lm:                                      # finansieringsfil förväntas för varje stapelmånad hos perpar
                y = int(m[:4])
                if y in flisted and scope == "in_scope":
                    flisted[y] += 1
                    fmissing[y] += int(m not in fl)             # saknas redan i bucketen (arkivhål hos Binance)
        res[scope] = {"listed_symbol_months": listed, "local_symbol_months": local, "missing_symbol_months": missing,
                      "missing_share": {y: (missing[y] / listed[y] if listed[y] else 0.0) for y in YEARS}, "symbols_with_missing_months": len(miss_syms)}
        if scope == "in_scope":
            res[scope]["kline_months_without_funding_file_in_bucket"] = fmissing
            res[scope]["funding_missing_share"] = {y: (fmissing[y] / flisted[y] if flisted[y] else 0.0) for y in YEARS}
            res[scope]["symbols_missing_locally"] = sorted(miss_syms)
    return res


def symbol_days(panel) -> dict:
    """Per år: dagar mellan en perps första och sista stapel (tills panelens slut) och hur många av dem saknar stapel (arkivhål). Efterhandsmått, bara för rapporten."""
    c = panel.close
    first = c.apply(lambda x: x.first_valid_index())
    last = c.apply(lambda x: x.last_valid_index())
    idx = c.index
    span = pd.DataFrame({s: (idx >= first[s]) & (idx <= last[s]) for s in c.columns}, index=idx)
    holes = span & c.isna()
    out, per_sym = {}, {}
    for y in YEARS:
        m = idx.year == y
        out[y] = {"listed_symbol_days": int(span[m].values.sum()), "hole_symbol_days": int(holes[m].values.sum())}
        out[y]["hole_share"] = out[y]["hole_symbol_days"] / max(out[y]["listed_symbol_days"], 1)
    for s in c.columns:
        h = int(holes[s].sum())
        if h:
            per_sym[s] = {"holes": h, "first": str(first[s].date()), "last": str(last[s].date())}
    return {"per_year": out, "symbols_with_holes": per_sym}


def exposure_outside(repo: Path, root: Path, old, new, new_uni: pd.DataFrame) -> dict:
    """R001-R004: hur stor del av bruttoexponeringen låg på kontrakt/dagar utanför ett korrekt universum? Vikterna återskapas på den gamla panelen (som körningarna)."""
    v1 = replace(old, funding_rule=False, scope_rule=False, _cache={})
    agents.set_panel(v1, repo / "data" / "clean" / "agentlab-cache")
    seen = {}
    for r in ExperimentRegistry(root / "experiments.jsonl").read():
        if r["stage"] in ("discovery", "final") and r["key"] not in seen and r["results"].get("discovery"):
            seen[r["key"]] = r
    new_cols = set(new_uni.columns)
    inside = new_uni.reindex(index=v1.close.index, columns=v1.close.columns).fillna(False).astype(bool)      # delivery- och andra kolumner utan motsvarighet = utanför
    deliv_cols = [c for c in v1.close.columns if classify(c)["kind"] != "perp_usdt"]
    # skäl för "utanför", i ordning: (1) inte USDT-perp (leverans m.m.), (2) funding okänd enligt datatäckningsregeln, (3) kontraktet fanns och var känt men rankades bort av kontrakt som den gamla panelen saknade
    fund_ok = new.funding_known.shift(1, fill_value=False).rolling(7, min_periods=1).sum().ge(5).reindex(index=v1.close.index, columns=v1.close.columns).fillna(False).astype(bool)
    has_bar = v1.close.notna()
    reason = {"non_perp": 0.0, "funding_unknown": 0.0, "displaced_by_missing_contracts": 0.0}
    per, tot = [], {y: [0.0, 0.0, 0.0, 0, 0] for y in YEARS}          # brutto, utanför, varav icke-perp, positioner, positioner utanför
    for key, r in seen.items():
        spec = make_spec(r["family"], r["parameters"])
        if spec["key"] != key:
            continue
        with agents.use("final"):
            W = agents.weights(spec)
        Wa = W.reindex(index=v1.close.index, columns=v1.close.columns).fillna(0.0).abs()
        out_m = ~inside
        g = float(Wa.values.sum())
        o = float(Wa.values[out_m.values].sum())
        d = float(Wa[deliv_cols].values.sum()) if deliv_cols else 0.0
        is_np = pd.DataFrame(False, index=Wa.index, columns=Wa.columns)
        is_np[deliv_cols] = True
        r1 = out_m & is_np
        r2 = out_m & ~is_np & ~fund_ok
        r3 = out_m & ~is_np & fund_ok
        reason["non_perp"] += float(Wa.values[r1.values].sum()); reason["funding_unknown"] += float(Wa.values[r2.values].sum()); reason["displaced_by_missing_contracts"] += float(Wa.values[r3.values].sum())
        pos = Wa.values > 0
        per.append({"key": key, "family": r["family"], "control": r["control"], "gross": g, "outside_share": o / g if g else 0.0, "non_perp_share": d / g if g else 0.0,
                    "positions": int(pos.sum()), "positions_outside": int((pos & out_m.values).sum())})
        for y in YEARS:
            m = (Wa.index.year == y)
            tot[y][0] += float(Wa.values[m].sum()); tot[y][1] += float((Wa.values * out_m.values)[m].sum())
            tot[y][2] += float(Wa[deliv_cols].values[m].sum()) if deliv_cols else 0.0
            tot[y][3] += int(pos[m].sum()); tot[y][4] += int((pos & out_m.values)[m].sum())
    real = [p for p in per if not p["control"]]
    gtot = sum(t[0] for t in tot.values())
    return {"candidates": len(per), "outside_reasons_share_of_gross": {k: v / gtot for k, v in reason.items()}, "real_candidates": len(real),
            "per_year": {y: {"gross_exposure": t[0], "outside_share": t[1] / t[0] if t[0] else 0.0, "non_perp_share": t[2] / t[0] if t[0] else 0.0,
                            "positions": t[3], "positions_outside": t[4], "positions_outside_share": t[4] / t[3] if t[3] else 0.0} for y, t in tot.items()},
            "candidates_with_outside_share_over_1pct": sum(p["outside_share"] > 0.01 for p in per), "candidates_with_outside_share_over_5pct": sum(p["outside_share"] > 0.05 for p in per),
            "candidates_with_any_non_perp_exposure": sum(p["non_perp_share"] > 0 for p in per), "max_outside_share": max(p["outside_share"] for p in per), "mean_outside_share": float(np.mean([p["outside_share"] for p in per])),
            "per_candidate": per}


def universe_compare(old, new) -> dict:
    """Det universum R001-R004 kunde välja (gamla panelen, gamla regeln) mot punkt-i-tid-universumet (ny panel, ny regel), per år. Efterhandsjämförelse."""
    v1 = replace(old, funding_rule=False, scope_rule=False, _cache={})
    uo, un = v1.universe(30, 90), new.universe(30, 90)
    idx, cols = uo.index.union(un.index), uo.columns.union(un.columns)
    uo, un = uo.reindex(index=idx, columns=cols).fillna(False).astype(bool), un.reindex(index=idx, columns=cols).fillna(False).astype(bool)
    absent = [c for c in cols if c not in v1.close.columns]
    nonperp = [c for c in uo.columns if classify(c)["kind"] != "perp_usdt"]
    out = {}
    for y in YEARS:
        m = idx.year == y
        o, n = uo.values[m], un.values[m]
        row = {"slots_old": int(o.sum()), "slots_new": int(n.sum()), "old_slots_outside_new": int((o & ~n).sum()), "new_slots_old_could_not_select": int((n & ~o).sum()),
               "old_slots_on_non_perp": int(uo[nonperp].values[m].sum()) if nonperp else 0, "new_slots_on_symbols_absent_in_old_panel": int(un[absent].values[m].sum()) if absent else 0}
        row["old_slots_outside_new_share"] = row["old_slots_outside_new"] / max(row["slots_old"], 1)
        row["new_slots_old_missing_share"] = row["new_slots_old_could_not_select"] / max(row["slots_new"], 1)
        row["new_slots_on_absent_share"] = row["new_slots_on_symbols_absent_in_old_panel"] / max(row["slots_new"], 1)
        out[y] = row
    return {"per_year": out, "symbols_old_panel": len(old.close.columns), "symbols_old_panel_non_perp": len([c for c in old.close.columns if classify(c)["kind"] != "perp_usdt"]), "symbols_new_panel": len(new.close.columns),
            "symbols_new_not_in_old": len(absent), "universe_new_never_selected_symbols": int((~un.any()).sum())}, un


def run_universe_audit(repo: Path, root: Path) -> dict:
    data = repo / "data"
    listing = load_listing(repo)
    old = load_um_panel(data, cache=data / "clean" / "agentlab-panel-v2.pkl")               # panelen R001-R004 använde (119 symboler inkl. leveranskontrakt)
    new = load_um_panel(data, cache=data / "clean" / "agentlab-panel-v3.pkl", listing=repo)
    cen = census(listing)
    cmp_, un = universe_compare(old, new)
    rep = {"note": "Universums- och täckningsaudit, Binance USDⓈ-M, daglig. Filnamnslistan sträcker sig bara till 2024-12; 2025+ är aldrig öppnat. Ändrar inga experimentposter.",
           "listing": {"fetched_utc": listing["fetched_utc"], "source": listing["source"], "symbols_in_bucket": listing["symbols_in_bucket"], "symbols_with_archive_before_2025": len(listing["symbols"])},
           "census": {k: v for k, v in cen.items() if k != "rows"}, "delivery_expiry_check": delivery_check(data), "file_coverage": file_coverage(listing, data),
           "symbol_days": symbol_days(new), "universe_gap": new.meta.get("universe_gap"), "compare_old_vs_pointintime": cmp_, "r001_r004_exposure": exposure_outside(repo, root, old, new, un)}
    out = repo / "research" / "agentlab" / "universe"
    out.mkdir(parents=True, exist_ok=True)
    (out / "coverage-discovery.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    (out / "coverage-discovery.md").write_text(render_md(json.loads(json.dumps(rep, default=float))), encoding="utf-8")
    return rep


def render_md(rep: dict) -> str:
    """Läsbar sammanfattning av coverage-discovery.json."""
    pct = lambda x: f"{100 * x:.1f} %"
    c, fc, sd, cmp_, ex = rep["census"], rep["file_coverage"], rep["symbol_days"], rep["compare_old_vs_pointintime"], rep["r001_r004_exposure"]
    L = ["# Universums- och datatäckningsaudit (Binance USDⓈ-M, daglig)", "",
         f"Genererad av `python -m traderlab.agentlab universe-audit`. Arkivlista hämtad {rep['listing']['fetched_utc']} från {rep['listing']['source']}. {rep['note']}", "",
         "## 1. Vad arkivet visar (arter)", "", "| Art | Symboler med arkiv före 2025 | Varav listade senast 2022-12 | Med finansieringsarkiv | Utan |", "|---|---|---|---|---|"]
    for k, v in c["by_kind"].items():
        L.append(f"| {k} | {v['symbols_with_archive_before_2025']} | {v['listed_by_2022_12']} | {v['with_funding_archive']} | {v['without_funding_archive']} |")
    a = c["anomalies"]
    dv = rep["delivery_expiry_check"]
    L += ["", f"**Perp eller leverans.** Leveranskontrakt ({c['by_kind']['delivery']['symbols_with_archive_before_2025']} st) har inga finansieringsarkiv ({len(a['delivery_with_funding'])} undantag); alla USDT-perpar ({c['by_kind']['perp_usdt']['symbols_with_archive_before_2025']} st) har det "
          f"({len(a['usdt_perp_without_funding'])} undantag). Av {dv['checked']} utgångna leveranskontrakt med lokala data ligger sista stapeln på utgångsdatumet i namnet för {dv['last_bar_on_expiry_date']} och högst 2 dagar efter för {dv['last_bar_within_2_days_after']}.",
          f"{len(a['usdt_perp_funding_shorter_than_klines'])} USDT-perpar har färre finansieringsmånader än stapelmånader (arkivhål i finansieringen): {', '.join(a['usdt_perp_funding_shorter_than_klines'])}.", "",
          "**Omfång.** Agentlab handlar bara USDT-perpar (`universe.in_scope`). BUSD- och USDC-perpar, `*SETTLED` (efterhandsnamn på avnoterade kontrakt) och övriga produkter (`ETHBTC`, `BTCUSD1` ...) ligger utanför och redovisas nedan som avgränsning, inte som täckning.", "",
          "## 2. Månadsfiler: listade i arkivet mot lokalt (USDT-perpar, 1d-staplar)", "", "| År | Listade symbolmånader | Lokalt | Saknas | Andel saknas | Stapelmånad utan finansieringsfil i arkivet |", "|---|---|---|---|---|---|"]
    i = fc["in_scope"]
    for y in YEARS:
        y = str(y)
        L.append(f"| {y} | {i['listed_symbol_months'][y]} | {i['local_symbol_months'][y]} | {i['missing_symbol_months'][y]} | {pct(i['missing_share'][y])} | {i['kline_months_without_funding_file_in_bucket'][y]} ({pct(i['funding_missing_share'][y])}) |")
    o = fc["out_of_scope"]
    ob = a["busd_usdc_perps_listed_by_2022_12_without_usdt_perp_on_same_underlying"]
    L += ["", f"Utanför omfånget (andra arter) saknas medvetet {sum(o['missing_symbol_months'].values())} av {sum(o['listed_symbol_months'].values())} symbolmånader ({o['symbols_with_missing_months']} symboler). BUSD/USDC-perpar listade senast 2022-12 vars underliggande saknar USDT-perp: {len(ob)} st" + (f" ({', '.join(ob)})" if ob else "") + ".", ""]
    L += ["## 3. Arkivhål på dagsnivå (inne i ett kontrakts liv)", "", "| År | Symboldagar mellan första och sista stapel | Hål | Andel |", "|---|---|---|---|"]
    for y in YEARS:
        r = sd["per_year"][str(y)]
        L.append(f"| {y} | {r['listed_symbol_days']} | {r['hole_symbol_days']} | {pct(r['hole_share'])} |")
    L += ["", f"{len(sd['symbols_with_holes'])} symboler har minst ett hål. Hål fylls aldrig i: kontraktet är ohandlingsbart den dagen.", "",
          "## 4. Universum R001-R004 kunde välja mot punkt-i-tid-universumet (top 30, ålder ≥ 90 dagar)", "",
          f"Gamla panelen: {cmp_['symbols_old_panel']} symboler varav {cmp_['symbols_old_panel_non_perp']} leveranskontrakt. Nya panelen: {cmp_['symbols_new_panel']} symboler ({cmp_['symbols_new_not_in_old']} fler än den gamla).", "",
          "| År | Platser (ny) | Gamla platser utanför korrekt universum | Andel | Platser den gamla panelen inte kunde välja | Andel | Gamla platser på leveranskontrakt |", "|---|---|---|---|---|---|---|"]
    for y in YEARS:
        r = cmp_["per_year"][str(y)]
        L.append(f"| {y} | {r['slots_new']} | {r['old_slots_outside_new']} | {pct(r['old_slots_outside_new_share'])} | {r['new_slots_old_could_not_select']} | {pct(r['new_slots_old_missing_share'])} | {r['old_slots_on_non_perp']} |")
    L += ["", "## 5. R001-R004: bruttoexponering utanför ett korrekt universum (exploratoriskt, oförändrat)", "",
          f"{ex['candidates']} kandidater ({ex['real_candidates']} riktiga). Över 1 % utanför: {ex['candidates_with_outside_share_over_1pct']}; över 5 %: {ex['candidates_with_outside_share_over_5pct']}; med någon exponering mot leveranskontrakt: {ex['candidates_with_any_non_perp_exposure']}. Högsta andel {pct(ex['max_outside_share'])}, medel {pct(ex['mean_outside_share'])}.", "",
          "Skäl (andel av total bruttoexponering): " + ", ".join(f"{ {'non_perp': 'inte USDT-perp', 'funding_unknown': 'finansiering okänd', 'displaced_by_missing_contracts': 'bortrankad av kontrakt som panelen saknade'}[k] } {pct(v)}" for k, v in ex["outside_reasons_share_of_gross"].items()) + ".", "",
          "| År | Bruttoexponering | Andel utanför | Varav leveranskontrakt | Positionsdagar | Utanför |", "|---|---|---|---|---|---|"]
    for y in YEARS:
        r = ex["per_year"][str(y)]
        L.append(f"| {y} | {r['gross_exposure']:.0f} | {pct(r['outside_share'])} | {pct(r['non_perp_share'])} | {r['positions']} | {pct(r['positions_outside_share'])} |")
    L += ["", f"## 6. Kvarstående luckor som blockerar bekräftande påståenden", "",
          f"Perpar i arkivlistan (USDT, listade senast 2022-12) som saknas i panelen: **{len(rep['universe_gap'] or [])}**." + (" " + ", ".join(rep["universe_gap"]) if rep["universe_gap"] else ""), ""]
    return "\n".join(L) + "\n"
