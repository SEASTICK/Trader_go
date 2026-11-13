"""Fryst känslighetskontroll av de fyra R001-R004-kandidater som överlevde discovery, på den rättade grunden (396 USDT-perpar, `universe_at`, nuvarande täcknings- och kostnadsregler).

**Efterhandsdiagnostik, utforskande.** Inte en bekräftelse och ingen ny hypotes. Ingen parameter ändras: specifikationerna läses ur `experiments.jsonl` och kontrolleras mot sin nyckel.
Bara discoveryperioden 2020-10-01..2022-12-31 utvärderas, och panelen läses med `load_um_panel(end=2023-01-01)`, så arkiv från 2023 och senare öppnas aldrig. Gamla registerposter, state.json och
registret ändras inte; rapporten skrivs till `research/agentlab/sensitivity/`.

Tre steg gör avvikelsen mot R001-R004 förklarbar utan att några regler justeras:
  A. registrets gamla discovery-siffror (119 kontrakt inkl. 34 leveranskontrakt, gamla regler, tyst noll för okänd data);
  B. samma 85 perpar som då fanns, men med nuvarande regler (omfång, datatäckning, debitering av okänd data) = effekten av reglerna;
  C. hela 396-panelen (alla arkivlistade USDT-perpar som fanns före 2023) med nuvarande regler = effekten av de saknade kontrakten.
"överlever" nedan är en deskriptiv sammanfattning med trösklar som skrevs innan körningen (se `SURVIVE`), inte ett beslutskriterium för någon hypotes.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from .. import stats
from . import agents, backtest as bt
from .data import Panel, period_slice
from .strategies import ModelUnavailable, make_spec

DISC_END = pd.Timestamp("2022-12-31", tz="UTC")
LOAD_END = pd.Timestamp("2023-01-01", tz="UTC")           # exklusiv: arkiv från 2023 öppnas aldrig
FROZEN_RUNS = ("R001", "R002", "R003", "R004")
SURVIVE = {"sharpe": 1.0, "t": 2.0, "sharpe_cost_2_5x": 0.0}   # skrivna före körningen: giltig täckning, netto-Sharpe ≥ 1,0, t ≥ 2,0 och Sharpe > 0 med 2,5x kostnader


def frozen_candidates(root: Path) -> list[dict]:
    """De registrerade kandidaterna som nådde slutsteget i R001-R004 (inga kontroller), en per nyckel, med sina gamla discovery-siffror. Verifierar att parametrarna ger samma nyckel."""
    seen: dict[str, dict] = {}
    for line in (root / "experiments.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("stage") != "final" or r.get("control") or r["run"] not in FROZEN_RUNS or r["key"] in seen:
            continue
        spec = make_spec(r["family"], r["parameters"])
        if spec["key"] != r["key"]:
            raise ValueError(f"parametrarna för {r['id']} ger inte registrets nyckel ({spec['key']} != {r['key']}): specifikationen är inte oförändrad")
        d, c = r["results"]["discovery"], r["costs"]
        seen[r["key"]] = {"id": r["id"], "run": r["run"], "key": r["key"], "family": r["family"], "parameters": r["parameters"], "verdict_at_the_time": r["verdict"],
                          "old": {"n": d["n"], "sharpe": d["sharpe"], "t": d["sharpe"] * np.sqrt(d["n"] / 365), "ann_ret": d["ann_ret"], "max_dd": d["max_dd"],
                                  "turnover_ann": r["results"]["turnover_ann"], "funding_ann": c["funding_ann"], "sharpe_cost_2_5x": c["sharpe_grid"]["2.5"], "sharpe_cost_1x": c["sharpe_grid"]["1.0"]}}
    return list(seen.values())


def restrict(panel: Panel, cols: list[str]) -> Panel:
    cols = [c for c in cols if c in panel.close.columns]
    f = lambda df: df[cols]
    return Panel(f(panel.open), f(panel.high), f(panel.low), f(panel.close), f(panel.dvol), f(panel.funding), meta={**panel.meta, "restricted": len(cols)},
                 funding_known=f(panel.funding_known), funding_rule=panel.funding_rule, scope_rule=panel.scope_rule)


def _disc(r: pd.Series) -> pd.Series:
    return r[period_slice(r.index, "disc")]


def evaluate(panel: Panel, spec: dict, cache: Path | None) -> dict:
    """Ett steg för en specifikation: universum, täckning/giltighet, nettomått, kostnadsstress. Bara discovery (panelen slutar 2022-12-31)."""
    if len(panel.close) and panel.close.index.max() > DISC_END:
        raise ValueError("panelen innehåller data efter discoveryperioden (2022-12-31): känslighetskontrollen läser bara 2020-2022")
    agents.set_panel(panel, cache)
    out: dict = {"symbols_in_panel": len(panel.close.columns)}
    try:
        with agents.use("disc"):
            pan = agents.panel()
            W = agents.weights(spec)
            uni = pan.universe(int(spec["params"].get("uni", 30)), 90)
            d_mask = period_slice(uni.index, "disc")
            Wd = W.reindex(index=pan.close.index, columns=pan.close.columns).fillna(0.0)[period_slice(pan.close.index, "disc")]
            out["universe"] = {"mean_eligible_per_day": float(uni[d_mask].sum(axis=1).mean()), "min_eligible_per_day": int(uni[d_mask].sum(axis=1).min()),
                               "symbols_ever_eligible": int(uni[d_mask].any().sum()), "symbols_ever_held": int((Wd.abs().sum() > 0).sum())}
            try:
                res = bt.run(pan, W)
                out["status"], out["status_reason"] = "GILTIG", ""
            except bt.CoverageInvalid as e:
                out["status"], out["status_reason"] = "OGILTIG", str(e)
                res = bt.run(pan, W, strict=False)                    # siffrorna nedan är då bara diagnostik
            r = _disc(res.ret).dropna()
            m = bt.metrics(r)
            d = period_slice(res.ret.index, "disc")
            stress = bt.run(pan, W, cost=bt.COST_PER_SIDE * 2.5, strict=False)
            ms = bt.metrics(_disc(stress.ret).dropna())
            cov = res.coverage or {}
            out.update({"n": m["n"], "net_ann_ret": m["ann_ret"], "net_total": m["total"], "sharpe": m["sharpe"], "t": stats.t_stat(r), "max_dd": m["max_dd"],
                        "turnover_ann": float(res.turnover[d].mean() * 365), "funding_ann": float(res.funding[d].mean() * 365), "cost_ann": float(res.cost[d].mean() * 365),
                        "sharpe_cost_2_5x": ms["sharpe"], "net_ann_ret_cost_2_5x": ms["ann_ret"],
                        "coverage": {k: cov.get(k) for k in ("gross_exposure", "blocked_share", "gap_filled_share", "unknown_exit_share", "missing_price_share", "unknown_funding_share", "any_unknown_share")}})
    except ModelUnavailable as e:
        out.update({"status": "EJ KÖRBAR", "status_reason": str(e)})
    return out


def survives(step: dict) -> bool:
    return (step.get("status") == "GILTIG" and step.get("sharpe", -9) >= SURVIVE["sharpe"] and step.get("t", -9) >= SURVIVE["t"]
            and step.get("sharpe_cost_2_5x", -9) > SURVIVE["sharpe_cost_2_5x"])


def run_sensitivity(repo: Path, root: Path, out_dir: Path, panel: Panel | None = None, old_symbols: list[str] | None = None, candidates: list[dict] | None = None) -> dict:
    """Kör kontrollen. `panel` = discovery-panel (None: läs 396-panelen med end=2023-01-01). Skriver bara till `out_dir`."""
    from .data import load_um_panel
    cands = candidates if candidates is not None else frozen_candidates(root)
    if panel is None:
        panel = load_um_panel(repo / "data", cache=repo / "data" / "clean" / "agentlab-panel-v3-disc.pkl", listing=repo, end=LOAD_END)
    if old_symbols is None:
        old_symbols = json.loads((out_dir / "r001-r004-panel-symbols.json").read_text(encoding="utf-8"))["perp_usdt"]
    gap = panel.meta.get("universe_gap")
    cache = repo / "data" / "clean" / "agentlab-cache"
    old_panel = restrict(panel, old_symbols)
    rows = []
    for c in cands:
        spec = make_spec(c["family"], c["parameters"])
        b = evaluate(old_panel, spec, cache)
        cfull = evaluate(panel, spec, cache)
        rows.append({**c, "step_B_old_perps_new_rules": b, "step_C_full_panel_new_rules": cfull, "survives_B": survives(b), "survives_C": survives(cfull)})
    rep = {"label": "EFTERHANDSDIAGNOSTIK / UTFORSKANDE. Inte en bekräftelse och ingen ny hypotes. R001-R004 och registret är oförändrade.",
           "period": "2020-10-01..2022-12-31 (discovery). Panelen läses med end=2023-01-01; arkiv från 2023 och senare öppnas inte.",
           "panel": {"symbols": len(panel.close.columns), "first": str(panel.close.index.min().date()), "last": str(panel.close.index.max().date()), "universe_gap_discovery": gap,
                     "universe_gap_checked": panel.meta.get("universe_gap_checked"), "old_panel_perps": len(old_panel.close.columns)},
           "survive_thresholds": SURVIVE, "unchanged_parameters_checked": True, "candidates": rows,
           "summary": {"candidates": len(rows), "survive_B": sum(r["survives_B"] for r in rows), "survive_C": sum(r["survives_C"] for r in rows),
                       "valid_C": sum(r["step_C_full_panel_new_rules"].get("status") == "GILTIG" for r in rows)}}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "frozen-r001-r004.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    (out_dir / "frozen-r001-r004.md").write_text(render_md(json.loads(json.dumps(rep, default=float))), encoding="utf-8")
    return rep


def render_md(rep: dict) -> str:
    pct = lambda x: "–" if x is None else f"{100 * x:.1f} %"
    f2 = lambda x: "–" if x is None else f"{x:.2f}"
    L = ["# Fryst känslighetskontroll: R001–R004-kandidaterna på den rättade grunden", "", f"**{rep['label']}**", "",
         f"Period: {rep['period']}", f"Panel: {rep['panel']['symbols']} USDT-perpar ({rep['panel']['first']} till {rep['panel']['last']}); gamla panelens perpar: {rep['panel']['old_panel_perps']}; täckningsluckor mot arkivlistan under discovery: "
         f"{len(rep['panel']['universe_gap_discovery'] or [])} (kontrollerad: {rep['panel']['universe_gap_checked']}).", "",
         "Reproducera: `python -m traderlab.agentlab sensitivity` (kräver lokala rådata). Parametrarna läses ur `experiments.jsonl` och kontrolleras mot registrets nyckel; inget skrivs till registret eller `state.json`.", "",
         f"**Steg:** A = registrets gamla discovery-siffror (119 kontrakt inkl. 34 leveranskontrakt, gamla regler). B = samma 85 perpar med nuvarande regler (effekten av reglerna). C = hela panelen med nuvarande regler (effekten av de saknade kontrakten). "
         f"t = medelvärde/(std/√n) för dagliga nettoavkastningar (`stats.t_stat`, samma metod som övriga projektet; för A härlett ur registrets Sharpe och n, vilket är identiskt). Funding > 0 betyder kostnad, < 0 intäkt. "
         f"\"Överlever\" (endast beskrivning, trösklar satta före körningen): giltig täckning, Sharpe ≥ {rep['survive_thresholds']['sharpe']}, t ≥ {rep['survive_thresholds']['t']} och Sharpe > 0 med 2,5× kostnader.", ""]
    s = rep["summary"]
    L += [f"**Sammanfattning:** {s['survive_C']} av {s['candidates']} kandidater överlever på hela panelen (C); {s['survive_B']} av {s['candidates']} med bara de gamla perparna och nuvarande regler (B); {s['valid_C']} har giltig täckning i C.", ""]
    for c in rep["candidates"]:
        o, B, C = c["old"], c["step_B_old_perps_new_rules"], c["step_C_full_panel_new_rules"]
        L += [f"## {c['id']} · {c['family']} · `{c['key']}` ({c['run']}, dåvarande utfall {c['verdict_at_the_time']})", "", f"Parametrar: `{json.dumps(c['parameters'], ensure_ascii=False)}`", "",
              "| Mått (discovery) | A: registret (gammalt) | B: gamla perpar, nya regler | C: hela panelen, nya regler |", "|---|---|---|---|",
              f"| Universum (symboler i panelen / aldrig valbara / någonsin hållna) | 119 / – / – | {B.get('symbols_in_panel')} / {B.get('universe', {}).get('symbols_ever_eligible', '–')} / {B.get('universe', {}).get('symbols_ever_held', '–')} | {C.get('symbols_in_panel')} / {C.get('universe', {}).get('symbols_ever_eligible', '–')} / {C.get('universe', {}).get('symbols_ever_held', '–')} |",
              f"| Valbara per dag (medel / min) | – | {f2(B.get('universe', {}).get('mean_eligible_per_day'))} / {B.get('universe', {}).get('min_eligible_per_day', '–')} | {f2(C.get('universe', {}).get('mean_eligible_per_day'))} / {C.get('universe', {}).get('min_eligible_per_day', '–')} |",
              f"| Täckning / status | ej mätt (tyst noll) | {B.get('status')} {B.get('status_reason', '')} | {C.get('status')} {C.get('status_reason', '')} |",
              f"| Okänd data (andel av bruttoexponering: saknad kurs / okänd finansiering) | ej mätt | {pct((B.get('coverage') or {}).get('missing_price_share'))} / {pct((B.get('coverage') or {}).get('unknown_funding_share'))} | {pct((C.get('coverage') or {}).get('missing_price_share'))} / {pct((C.get('coverage') or {}).get('unknown_funding_share'))} |",
              f"| Nettoavkastning per år | {pct(o['ann_ret'])} | {pct(B.get('net_ann_ret'))} | {pct(C.get('net_ann_ret'))} |",
              f"| Sharpe | {f2(o['sharpe'])} | {f2(B.get('sharpe'))} | {f2(C.get('sharpe'))} |",
              f"| t | {f2(o['t'])} | {f2(B.get('t'))} | {f2(C.get('t'))} |",
              f"| Största nedgång | {pct(o['max_dd'])} | {pct(B.get('max_dd'))} | {pct(C.get('max_dd'))} |",
              f"| Omsättning (gånger/år) | {o['turnover_ann']:.1f} | {B.get('turnover_ann', 0):.1f} | {C.get('turnover_ann', 0):.1f} |",
              f"| Finansiering per år | {pct(o['funding_ann'])} | {pct(B.get('funding_ann'))} | {pct(C.get('funding_ann'))} |",
              f"| Sharpe med 2,5× kostnader | {f2(o['sharpe_cost_2_5x'])} | {f2(B.get('sharpe_cost_2_5x'))} | {f2(C.get('sharpe_cost_2_5x'))} |",
              f"| Överlever (beskrivning) | – | {'ja' if c['survives_B'] else 'nej'} | {'ja' if c['survives_C'] else 'nej'} |", ""]
    L += ["## Avvikelser mot R001–R004 (förklaring utan regeljusteringar)", "",
          "| Kandidat | ΔSharpe A→B (regler, 85 perpar) | ΔSharpe B→C (saknade kontrakt) | ΔSharpe A→C (totalt) | Δnetto/år A→C |", "|---|---|---|---|---|"]
    for c in rep["candidates"]:
        o, B, C = c["old"], c["step_B_old_perps_new_rules"], c["step_C_full_panel_new_rules"]
        L.append(f"| {c['id']} {c['family']} | {B.get('sharpe', 0) - o['sharpe']:+.2f} | {C.get('sharpe', 0) - B.get('sharpe', 0):+.2f} | {C.get('sharpe', 0) - o['sharpe']:+.2f} | {100 * (C.get('net_ann_ret', 0) - o['ann_ret']):+.1f} procentenheter |")
    L += ["", "- **A→B** isolerar reglerna: leveranskontrakten (34 av 119 kolumner) är borta, universum och rankning bygger bara på USDT-perpar, kontrakt utan känd finansiering blir inte valbara och okänd data debiteras i stället för att bli noll. "
          "Skillnaden ska läsas som \"vad de gamla siffrorna hade varit med dagens motor\", inte som en förbättring.",
          "- **B→C** isolerar de 81 perpar som saknades i R001–R004 (de fanns bara inte lokalt). De ändrar topp-30/50-urvalet och därmed vikterna; i discovery låg 7 % (2020–2021) och 19,7 % (2022) av de gamla platserna utanför ett korrekt universum.",
          "- Registrets siffror (A) är återskapade med den gamla motorn och stämde mot auditen (`audits/coverage-R001-R004.json`); inga regler eller parametrar har justerats för att rädda eller fälla någon kandidat.",
          "- **Urvalsfel kvarstår.** De fyra är de som överlevde R001–R004:s cirka 170 discovery-utvärderingar och är därför utvalda på just den här perioden. Trösklarna ovan är inte justerade för antalet försök (ingen DSR räknades om här), så \"överlever\" betyder bara \"försvinner inte av universumskorrigeringen\", inte att kanten är bekräftad. "
          "De två ensemblerna (X-0081, X-0122) har samma medlemmar och är starkt korrelerade, alltså i praktiken en och samma upptäckt.",
          "- Valid (2023), final (2024) och 2025+ är inte öppnade. Inget i den här rapporten är en ny hypotes eller ett skäl att köra något av dem.", ""]
    return "\n".join(L) + "\n"
