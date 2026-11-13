"""Orchestratorn: genererar idéer, rankar dem, kör specialistagenter parallellt mot varje kandidat, samlar invändningarna, låter Builder iterera,
slänger det som dör och låter Domaren avgöra. All kommunikation går via blackboarden (och en GitHub-outbox)."""
from __future__ import annotations

import json
import math
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import numpy as np

from . import agents, judge
from .data import SOURCES, Panel
from .state import Blackboard, ExperimentRegistry, TaskQueue
from .strategies import DATA_NEEDS, FAMILY_TAGS, GRID, make_spec, mutate

def effective_trials(R: np.ndarray) -> float:
    """Effektivt antal oberoende försök: deltagandekvoten (Σλ)²/Σλ² för korrelationsmatrisen av alla försöks avkastningsserier.
    Många varianter av samma idé är starkt korrelerade och räknas därför inte som många oberoende försök."""
    if R.ndim != 2 or R.shape[1] < 2:
        return float(max(1, R.shape[1] if R.ndim == 2 else 1))
    C = np.corrcoef(R, rowvar=False)
    C = np.nan_to_num(C, nan=0.0)
    lam = np.clip(np.linalg.eigvalsh(C), 0, None)
    return float(lam.sum() ** 2 / (lam ** 2).sum())


PRIOR = {"xs_mom": .55, "xs_rev": .45, "ts_mom": .5, "trend_ma": .5, "donchian": .45, "lowvol": .45, "bab": .4, "funding_carry": .55, "funding_fade": .4, "pairs": .4,
         "vol_regime": .4, "vol_shock": .35, "mtf_trend": .45, "ensemble_rank": .5, "ml_xs": .5}


def rank_ideas(ideas: list[dict], bb: Blackboard) -> list[tuple[float, dict]]:
    """Ranka idéer billigt, utan backtest: familjeprior, vad systemet redan lärt sig, nyhetsbonus, omsättnings- och komplexitetsstraff, datatillgång."""
    out = []
    for s in ideas:
        fam, p = s["family"], s["params"]
        st = bb.family(fam)
        sc = PRIOR.get(fam, 0.4)
        if st["tested"] >= 3 and st["rejected"] / st["tested"] >= 0.9:
            sc -= 0.15                                           # familjen har bara dött hittills: mindre budget
        if st["tested"] == 0:
            sc += 0.10                                           # outforskat
        if st["promising"]:
            sc += 0.15
        if p.get("rebal") == 1 or p.get("hold") == 1:
            sc -= 0.08                                           # kostnadskänsligt
        if fam == "ml_xs":
            sc -= 0.05                                           # komplexitet måste förtjäna sin plats
        for need in DATA_NEEDS.get(fam, []):
            if SOURCES.get(need, {}).get("status") != "available":
                sc -= 1.0
        out.append((round(sc, 3), s))
    return sorted(out, key=lambda x: -x[0])


def select(ranked: list[tuple[float, dict]], k: int) -> list[dict]:
    """Bredd först: bäst rankade idén i varje familj först, sedan fylls resten på efter poäng med högst `cap` per familj."""
    cap = max(2, math.ceil(k / 5))
    out, per, used = [], {}, set()
    for sc, s in ranked:                                       # pass 1: en per familj
        if sc >= 0 and s["family"] not in per:
            per[s["family"]] = 1; out.append(s); used.add(s["key"])
            if len(out) >= k:
                return out
    for sc, s in ranked:                                       # pass 2: fyll på
        if sc < 0 or s["key"] in used or per.get(s["family"], 0) >= cap:
            continue
        per[s["family"]] = per.get(s["family"], 0) + 1
        out.append(s)
        if len(out) >= k:
            break
    return out


class Orchestrator:
    def _universe_gap(self) -> list[str]:
        """Täckningsgrinden till Domaren. Kontrollerad panel: lucklistan (tom = godkänd). Panel inläst utan arkivlista: okontrollerad = blockerad. Syntetisk panel (ingen nyckel): ingen grind."""
        m = self.panel.meta
        if m.get("universe_gap_checked") is False:
            return ["okontrollerad täckning (panelen lästes utan arkivlista)"]
        return list(m.get("universe_gap") or [])

    def __init__(self, root: Path, panel: Panel, *, workers: int = 4, seed: int = 1, max_iter: int = 2, cache: Path | None = None):
        self.root, self.panel, self.workers, self.seed, self.max_iter = root, panel, workers, seed, max_iter
        self.bb = Blackboard(root)
        self.registry = ExperimentRegistry(root / "experiments.jsonl")
        self.cache = cache or (root / "cache")
        self.log: list[str] = []
        f = root / "trial_returns.npz"
        self.trials_store: dict = {k: v.astype(float) for k, v in np.load(f).items()} if f.exists() else {}
        agents.set_panel(panel, self.cache)

    # ---------------------------------------------------------------- parallell körning
    def drain(self, q: TaskQueue, ex) -> None:
        """Kör alla uppgifter som har sina beroenden klara, parallellt, tills kön är tom. Sub-agenter som en agent begär läggs som nya uppgifter."""
        while True:
            ready = q.ready()
            if not ready:
                return
            for t in ready:
                t.status = "running"
            if ex is None:
                done = [(t, agents.run_task(t.fn, t.payload)) for t in ready]
            else:
                futs = {ex.submit(agents.run_task, t.fn, t.payload): t for t in ready}
                done = [(futs[f], f.result()) for f in as_completed(futs)]
            for t, res in done:
                t.result, t.status = res, "failed" if res.get("error") and not res.get("skipped") else "done"
                if res.get("error"):
                    self.bb.issue(f"{t.agent}/{t.fn}: {res['error']}")
                for sp in res.get("spawn", []):
                    st = q.add(sp["name"], sp["fn"], sp["payload"], parent=t.id, priority=3, tid=f"{t.id}>{sp['name']}")
                    self.bb.s["agents"][st.id] = {"name": sp["name"], "goal": sp["goal"], "parent": t.agent, "ephemeral": True, "run": self.run_id}
                    self.bb.say(t.agent, sp["name"], "info", f"skapar sub-agent {sp['name']}", sp["goal"])

    # ---------------------------------------------------------------- en utvärderingsvåg för en uppsättning kandidater
    def evaluate(self, cands: list[dict], ex) -> None:
        q = TaskQueue()
        n_trials = self.bb.s["trials"] + 7 * len(cands) + len(cands)     # konservativt: ~1 + 6 grannar per kandidat räknas som försök innan DSR
        for c in cands:
            spec, k = c["spec"], c["spec"]["key"]
            pl = {"spec": spec}
            tq = q.add("ml" if spec["family"] == "ml_xs" else "quant", "quant_task", pl, priority=1, tid=f"{k}:quant")
            deps = [tq.id] if spec["family"] == "ml_xs" else []             # ML bygger vikterna först (delad cache), övriga kör direkt parallellt
            q.add("cost", "cost_task", pl, deps=deps, tid=f"{k}:cost")
            q.add("risk", "risk_task", pl, deps=deps, tid=f"{k}:risk")
            q.add("skeptic", "skeptic_task", {**pl, "n_trials": n_trials, "disc_sharpes": self.bb.s["disc_sharpes"][-200:]}, deps=deps, tid=f"{k}:skeptic")
        self.drain(q, ex)
        for c in cands:
            k = c["spec"]["key"]
            ev = {"spec": c["spec"], "specialists": {}}
            for kind in ("quant", "cost", "risk", "skeptic"):
                t = q.get(f"{k}:{kind}")
                ev[kind] = t.result or {}
            for t in q.all():
                if t.id.startswith(f"{k}:") and ">" in t.id:
                    ev["specialists"][t.agent] = t.result or {}
            sk = ev["skeptic"]
            lk = ev["specialists"].get("LeakageSpecialist", {})
            sk["leakage"] = bool(lk.get("leakage"))
            if "asset_pos" in ev["specialists"].get("AssetSplitSpecialist", {}):
                sk["asset_pos"] = ev["specialists"]["AssetSplitSpecialist"]["asset_pos"]
            ev["objections"] = sorted([o for part in [ev["quant"], ev["cost"], ev["risk"], ev["skeptic"], *ev["specialists"].values()] for o in part.get("objections", [])],
                                      key=lambda o: -o["severity"])
            c["evidence"] = ev
            c["errors"] = [t.result["error"] for t in q.all() if t.id.startswith(f"{k}:") and (t.result or {}).get("error") and not (t.result or {}).get("skipped")]
            inv = [t.result["reason"] for t in q.all() if t.id.startswith(f"{k}:") and ">" not in t.id and (t.result or {}).get("invalid")]
            c["invalid_reason"] = inv[0] if inv else None
            c["skipped"] = [t.result["error"] for t in q.all() if t.id.startswith(f"{k}:") and (t.result or {}).get("skipped")]
            if ev["quant"].get("disc"):
                self.bb.s["trials"] += ev["quant"].get("trials", 1)
                self.bb.s["disc_sharpes"].append(ev["quant"]["disc"]["sharpe"])
        self.deflate(cands)
        for c in cands:
            ev = c["evidence"]
            ev["objections"] = sorted(ev["objections"], key=lambda o: -o["severity"])
            for o in ev["objections"][:5]:                              # intern debatt: varje agent säger sitt till Builder
                self.bb.say(o["agent"], "builder", "objection", f"{c['spec']['key']}: {o['code']}", o["text"])

    def deflate(self, cands: list[dict]) -> None:
        """Deflated Sharpe med effektivt antal oberoende försök (korrelationsbaserat) över ALLA utvärderade serier hittills, inklusive denna våg."""
        from ..stats import deflated_sharpe
        store = self.trials_store
        for c in cands:
            r = c["evidence"].get("quant", {}).get("disc_returns")
            if r:
                store[c["spec"]["key"]] = np.array(r)
        n = min(len(v) for v in store.values()) if store else 0
        for c in cands:
            ev = c["evidence"]
            r = ev.get("quant", {}).get("disc_returns")
            if not r or n < 20:
                continue
            R = np.column_stack([v[:n] for v in store.values()])
            n_eff = effective_trials(R)
            sd = R.std(axis=0)
            sr = np.where(sd > 0, R.mean(axis=0) / np.where(sd > 0, sd, 1), 0.0)
            dsr = deflated_sharpe(np.array(r), max(2, int(round(n_eff))), float(np.var(sr)) if len(sr) > 5 else None)
            dsr = float(dsr) if dsr == dsr else 0.0
            ev["skeptic"].update({"dsr": dsr, "n_trials": int(self.bb.s["trials"]), "n_eff": round(n_eff, 1)})
            if dsr < 0.5:
                ev["objections"].append({"code": "selection_bias", "severity": 0.7, "agent": "skeptic", "mutable": False,
                                         "text": f"Deflated Sharpe {dsr:.2f} med {n_eff:.0f} effektiva oberoende försök (av {int(self.bb.s['trials'])} räknade): kan vara bästa av många."})
        if store:
            np.savez_compressed(self.root / "trial_returns.npz", **{k: v.astype(np.float32) for k, v in store.items()})

    # ---------------------------------------------------------------- registerpost
    def record(self, c: dict, stage: str, verdict: str, extra: dict | None = None) -> str:
        ev, spec = c["evidence"], c["spec"]
        q, co, ri, sk = ev.get("quant", {}), ev.get("cost", {}), ev.get("risk", {}), ev.get("skeptic", {})
        rec = {"run": self.run_id, "stage": stage, "key": spec["key"], "parent": spec.get("parent"), "iteration": c["iter"], "control": c.get("control", False),
               "hypothesis": spec["hypothesis"], "family": spec["family"], "tags": FAMILY_TAGS.get(spec["family"], ""), "parameters": spec["params"],
               "model": spec["params"].get("model", "rule-based"), "features": "se strategies.py / ml.py",
               "data": ["um_ohlcv", "um_funding"], "timeframe": "1d", "market": "Binance USDⓈ-M perpar (lokala arkiv)",
               "results": {"discovery": q.get("disc"), "neighbors": q.get("neighbors"), "baselines": q.get("baselines"), "turnover_ann": q.get("turnover_ann"), "beta_btc": q.get("beta_btc")},
               "costs": {"sharpe_grid": co.get("sharpe_grid"), "breakeven_bp_per_side": co.get("breakeven_bp_per_side"), "delay1_sharpe": co.get("delay1_sharpe"),
                         "funding_ann": co.get("funding_ann")},
               "risk": {k: ri.get(k) for k in ("max_dd", "cvar5", "worst_day", "top5_day_share", "asset_hhi", "regime", "beta_btc")},
               "adversarial": {k: sk.get(k) for k in ("perm_p", "dsr", "half_pos", "asset_pos", "leakage", "n_trials", "n_eff")},
               "comments": [f"[{o['agent']}] {o['code']}: {o['text']}" for o in ev.get("objections", [])[:8]],
               "verdict": verdict, "judge_version": judge.JUDGE_VERSION, "note": c.get("note", ""), **(extra or {})}
        return self.registry.append(rec)

    def read_inbox(self, skip: set[str]) -> list[dict]:
        """Idéer utifrån (till exempel från Codex eller en människa via en GitHub-kommentar som Claude lagt in här): `inbox/ideas.jsonl` med {"family", "params"} per rad.
        De rankas och prövas på samma sätt som egna idéer, med samma kontroller och samma domare."""
        f = self.root / "inbox" / "ideas.jsonl"
        out = []
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    d = json.loads(line)
                    if d["family"] not in GRID or d["family"] == "placebo":
                        raise ValueError(f"okänd familj {d['family']}")
                    sp = make_spec(d["family"], d.get("params", {}), note=f"inbox: {d.get('source', 'okänd')}")
                except Exception as exc:                          # noqa: BLE001
                    self.bb.issue(f"inbox: ogiltig rad ({exc}): {line[:80]}")
                    continue
                if sp["key"] not in skip:
                    out.append(sp); skip.add(sp["key"])
        return out

    def refresh_state(self) -> None:
        """Bygger om listan över lovande och bästa kandidater ur registret: senaste dom per nyckel gäller (omdömningar ersätter äldre domar)."""
        latest: dict[str, dict] = {}
        for r in self.registry.read():
            if r["stage"] in ("final", "rejudge") and not r.get("control"):
                latest[r["key"]] = r
        self.bb.s["promising"] = [{"key": k, "desc": f"{r['family']}({r['parameters']})", "verdict": r["verdict"], "score": r.get("score"), "run": r.get("run")}
                                  for k, r in latest.items() if r["verdict"] in ("PROMISING", "READY_FOR_PAPER")]
        self.bb.s["best"] = [{"key": k, "desc": f"{r['family']}({r['parameters']})", "verdict": r["verdict"], "score": r.get("score")}
                             for k, r in sorted(latest.items(), key=lambda kv: -(kv[1].get("score") or 0))[:10]]
        self.bb.s["experiments"] = self.registry.count()
        self.bb.save()

    def rejudge(self) -> list[dict]:
        """Dömer om äldre slutdomar med nuvarande domarversion utan att öppna någon ny förseglad data. Lägger till nya rader (stage "rejudge"), ändrar aldrig gamla."""
        done = {(r["key"]) for r in self.registry.read() if r["stage"] == "rejudge" and r.get("judge_version") == judge.JUDGE_VERSION}
        out = []
        for r in self.registry.read():
            if r["stage"] != "final" or r.get("judge_version") == judge.JUDGE_VERSION or r["key"] in done:
                continue
            ev = {"quant": {"disc": r["results"]["discovery"], "neighbors": r["results"]["neighbors"] or [], "turnover_ann": r["results"]["turnover_ann"] or 0.0,
                            "beta_btc": r["results"]["beta_btc"] or 0.0, "baselines": r["results"]["baselines"] or {}},
                  "cost": {"sharpe_grid": r["costs"]["sharpe_grid"] or {}}, "risk": {}, "skeptic": r["adversarial"], "portfolio": r.get("portfolio") or {}}
            res = judge.final(ev, r["sealed"], universe_gap=self._universe_gap())
            if res["verdict"] != r["verdict"]:
                self.registry.append({**{k: r[k] for k in ("run", "key", "parent", "iteration", "control", "hypothesis", "family", "tags", "parameters", "model", "data", "timeframe", "market")},
                                      "stage": "rejudge", "judge_version": judge.JUDGE_VERSION, "verdict": res["verdict"], "previous_verdict": r["verdict"], "score": res["score"],
                                      "notes": res["notes"], "rejudged_from": r["id"]})
                out.append({"id": r["id"], "key": r["key"], "from": r["verdict"], "to": res["verdict"], "notes": res["notes"]})
        self.refresh_state()
        return out

    # ---------------------------------------------------------------- huvudloop
    def run(self, *, n_ideas: int = 60, top_k: int = 14, controls: int = 4, families: list[str] | None = None) -> dict:
        t0 = time.time()
        bb = self.bb
        bb.s["runs"] += 1
        self.run_id = f"R{bb.s['runs']:03d}"
        rdir = self.root / "runs" / self.run_id
        rdir.mkdir(parents=True, exist_ok=True)
        ctx = get_context("fork")
        ex = ProcessPoolExecutor(max_workers=self.workers, mp_context=ctx) if self.workers > 1 else None
        try:
            # --- våg 0: Data och Idé parallellt
            q = TaskQueue()
            q.add("data", "data_task", {}, priority=1, tid="data")
            q.add("idea", "idea_task", {"n": n_ideas, "seed": self.seed + bb.s["runs"], "families": families, "skip": sorted(bb.tested())}, priority=1, tid="ideas")
            self.drain(q, ex)
            d = q.get("data").result
            bb.s["data"] = d["availability"]
            bb.s["data_panel"] = d["panel"]
            specialists = {t.agent: t.result for t in q.all() if ">" in t.id}
            bb.s["data_findings"] = specialists
            ideas = q.get("ideas").result["ideas"]
            ideas += self.read_inbox(set(bb.tested()) | {i["key"] for i in ideas})
            bb.say("idea", "orchestrator", "finding", f"{len(ideas)} idéer genererade", "Familjer: " + ", ".join(sorted({i['family'] for i in ideas})))
            # --- rankning och urval + negativa kontroller
            ranked = rank_ideas(ideas, bb)
            chosen = select(ranked, top_k)
            ctrl = [make_spec("placebo", {"seed": self.seed * 100 + i, "q": 0.2, "rebal": 3 + 4 * (i % 2), "uni": 30}) for i in range(controls)]
            cands = [{"spec": s, "iter": 0, "status": "active", "control": False} for s in chosen] + [{"spec": s, "iter": 0, "status": "active", "control": True} for s in ctrl]
            bb.say("orchestrator", "all", "info", f"urval: {len(chosen)} idéer + {len(ctrl)} negativa kontroller", "")
            all_c, done, survivors, killed = list(cands), [], [], []
            todo = list(cands)
            rnd = 0
            while todo:
                rnd += 1
                bb.say("orchestrator", "all", "info", f"runda {rnd}: {len(todo)} kandidater, parallella agenter", "")
                self.evaluate(todo, ex)
                nxt = []
                for c in todo:
                    spec, ev = c["spec"], c["evidence"]
                    bb.s["tested_keys"].append(spec["key"])
                    fam = bb.family(spec["family"])
                    if not c["control"]:
                        fam["tested"] += 1
                    if c.get("invalid_reason"):
                        # datatäckning: en exponerad position saknar nödvändig data. OGILTIG, aldrig REJECT och aldrig ett resultat.
                        c["decision"], c["reasons"] = "invalid", [c["invalid_reason"]]
                    elif c["errors"] or not ev["quant"].get("disc"):
                        c["decision"], c["reasons"] = "kill", c["errors"] or c["skipped"] or ["inget resultat"]
                    else:
                        c["decision"], c["reasons"] = judge.preliminary(ev, c["iter"], self.max_iter)
                    if c["decision"] == "iterate":
                        child = None
                        for o in ev["objections"]:
                            if o["mutable"] and o["code"] not in c.get("tried", []):
                                m = mutate(spec, o["code"])
                                if m and m["key"] not in set(bb.tested()) | {x["spec"]["key"] for x in all_c}:
                                    child = (o, m); break
                        if child is None:
                            c["decision"], c["reasons"] = "kill", ["ingen rimlig ändring finns"]
                        else:
                            o, m = child
                            nc = {"spec": m, "iter": c["iter"] + 1, "status": "active", "control": c["control"], "tried": c.get("tried", []) + [o["code"]], "note": m["note"]}
                            bb.say("builder", o["agent"], "revision", f"{spec['key']} → {m['key']}", f"svarar på {o['code']}: {m['note']}")
                            nxt.append(nc); all_c.append(nc)
                            self.record(c, "discovery", "ITERATED", {"child": m["key"]})
                            continue
                    if c["decision"] == "invalid":
                        c["status"] = "invalid"
                        c["final"] = {"verdict": "OGILTIG", "score": None, "notes": c["reasons"]}
                        if not c["control"]:
                            fam["invalid"] = fam.get("invalid", 0) + 1
                        self.record(c, "discovery", "OGILTIG", {"reasons": c["reasons"]})
                        bb.say("judge", "all", "verdict", f"{spec['key']} {spec['desc']}: OGILTIG (datatäckning)", c["reasons"][0])
                        continue
                    if c["decision"] == "kill":
                        c["status"] = "rejected"
                        c["final"] = {"verdict": "REJECT", "score": None, "notes": c["reasons"]}
                        if not c["control"]:
                            fam["rejected"] += 1
                            bb.s["rejected"].append({"key": spec["key"], "family": spec["family"], "desc": spec["desc"], "reason": "; ".join(c["reasons"])[:160], "run": self.run_id})
                        self.record(c, "discovery", "REJECT", {"reasons": c["reasons"]})
                        bb.say("judge", "all", "verdict", f"{spec['key']} {spec['desc']}: REJECT", "; ".join(c["reasons"]))
                        killed.append(c)
                    else:
                        c["status"] = "advanced"
                        survivors.append(c)
                        bb.say("judge", "all", "verdict", f"{spec['key']} {spec['desc']}: går vidare till förseglad data", "")
                todo = nxt
            # --- portfölj (bara överlevare) och slutdom med förseglad validering
            if survivors:
                q = TaskQueue()
                q.add("portfolio", "portfolio_task", {"specs": [c["spec"] for c in survivors]}, tid="portfolio")
                self.drain(q, ex)
                pf = q.get("portfolio").result
                bb.s["portfolio"] = {k: v for k, v in pf.items() if k in ("combos", "max_corr", "div_value")}
                for c in survivors:
                    c["evidence"]["portfolio"] = {"div_value": pf.get("div_value", {}).get(c["spec"]["key"], 0.0), "max_corr": pf.get("max_corr", {}).get(c["spec"]["key"], 0.0)}
            # --- STEG 1: valideringsåret 2023, bara för discovery-överlevare, i en egen uppgift med en panel som slutar 2023-12-31 (2024 finns inte där)
            sealed_all = {id(c): {"valid": None, "final": None} for c in survivors}
            if survivors:
                vq = TaskQueue()
                for c in survivors:
                    vq.add("judge", "validate_task", {"spec": c["spec"]}, tid=f"{c['spec']['key']}:valid")
                self.drain(vq, ex)
                for c in survivors:
                    r = vq.get(f"{c['spec']['key']}:valid").result or {}
                    sealed_all[id(c)]["valid"] = r.get("valid") or {"sharpe": 0.0, "ann_ret": 0.0, "max_dd": 0.0, "invalid": r.get("reason", "inget resultat")}
                    bb.s["spent"]["valid"].append({"run": self.run_id, "key": c["spec"]["key"]})
            verdict1 = {id(c): judge.final(c["evidence"], {"valid": sealed_all[id(c)]["valid"], "final": None}, universe_gap=self._universe_gap()) for c in survivors}
            # --- STEG 2: slutåret 2024, bara för dem som klarade valideringsgrinden (PROMISING), i en egen uppgift
            passers = [c for c in survivors if verdict1[id(c)]["verdict"] == "PROMISING"]
            if passers:
                fq = TaskQueue()
                for c in passers:
                    fq.add("judge", "final_task", {"spec": c["spec"]}, tid=f"{c['spec']['key']}:final")
                self.drain(fq, ex)
                for c in passers:
                    sealed_all[id(c)]["final"] = (fq.get(f"{c['spec']['key']}:final").result or {}).get("final")
                    bb.s["spent"]["final"].append({"run": self.run_id, "key": c["spec"]["key"]})
            bb.s["sealed_looks"] = bb.s.get("sealed_looks", 0) + len(survivors) + len(passers)
            for c in survivors:
                ev, sealed = c["evidence"], sealed_all[id(c)]
                res = judge.final(ev, sealed, universe_gap=self._universe_gap())
                c["final"], c["sealed"] = res, sealed
                fam = bb.family(c["spec"]["family"])
                if not c["control"]:
                    if res["verdict"] == "REJECT":
                        fam["rejected"] += 1
                        bb.s["rejected"].append({"key": c["spec"]["key"], "family": c["spec"]["family"], "desc": c["spec"]["desc"], "reason": "; ".join(res["notes"])[:160] or f"poäng {res['score']}", "run": self.run_id})
                    if res["verdict"] in ("PROMISING", "READY_FOR_PAPER"):
                        fam["promising"] += 1
                        bb.s["promising"].append({"key": c["spec"]["key"], "desc": c["spec"]["desc"], "verdict": res["verdict"], "score": res["score"], "run": self.run_id})
                fam["best_score"] = max(fam["best_score"], res["score"] or 0)
                c["status"] = res["verdict"]
                self.record(c, "final", res["verdict"], {"score": res["score"], "components": res["components"], "sealed": sealed, "notes": res["notes"],
                                                         "portfolio": ev.get("portfolio")})
                bb.say("judge", "all", "verdict", f"{c['spec']['key']} {c['spec']['desc']}: {res['verdict']} (poäng {res['score']})", "; ".join(res["notes"]))
            # --- sammanfattning
            summary = self.summarize(all_c, ranked, ideas, time.time() - t0)
        finally:
            if ex is not None:
                ex.shutdown(wait=True, cancel_futures=True)
        bb.s["learnings"] = summary["learnings"]
        self.refresh_state()
        (rdir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
        (rdir / "report.md").write_text(self.report(summary, all_c), encoding="utf-8")
        (self.root / "outbox").mkdir(exist_ok=True)
        (self.root / "outbox" / f"github-{self.run_id}.md").write_text(self.outbox(summary), encoding="utf-8")
        return summary

    # ---------------------------------------------------------------- sammanfattning, rapport, GitHub-outbox
    def summarize(self, all_c, ranked, ideas, secs) -> dict:
        real = [c for c in all_c if not c["control"]]
        ctrl = [c for c in all_c if c["control"]]
        verdicts = {}
        for c in real:
            v = (c.get("final") or {}).get("verdict", "ITERATED")
            verdicts[v] = verdicts.get(v, 0) + 1
        fam = {}
        for c in real:
            f = fam.setdefault(c["spec"]["family"], {"tested": 0, "rejected": 0, "advanced": 0, "best_disc_sharpe": -9.0})
            f["tested"] += 1
            f["rejected"] += int(c.get("status") == "rejected" or (c.get("final") or {}).get("verdict") == "REJECT")
            f["advanced"] += int(c.get("status") not in ("rejected", "active"))
            d = c["evidence"].get("quant", {}).get("disc")
            if d:
                f["best_disc_sharpe"] = max(f["best_disc_sharpe"], d["sharpe"])
        kill_reasons = {}
        for c in all_c:
            for r in (c.get("reasons") or (c.get("final") or {}).get("notes") or []):
                key = r.split("(")[0].split(":")[0].strip()[:60]
                kill_reasons[key] = kill_reasons.get(key, 0) + 1
        ml = [c for c in real if c["spec"]["family"] == "ml_xs" and c["evidence"].get("quant", {}).get("disc")]
        learn = []
        if ml:
            wins = sum(1 for c in ml if c["evidence"]["quant"]["disc"]["sharpe"] > c["evidence"]["quant"].get("simple_baseline_sharpe", 9))
            learn.append(f"ML slog den enkla tumregeln xs_mom i {wins} av {len(ml)} körningar (discovery).")
        fp = [c for c in ctrl if c.get("status") not in ("rejected",)]
        learn.append(f"Negativa kontroller: {len(ctrl)} slumpstrategier, {len(fp)} gick vidare förbi discovery (falsklarmsfrekvens {len(fp)}/{len(ctrl)}).")
        top = sorted(kill_reasons.items(), key=lambda x: -x[1])[:5]
        learn.append("Vanligaste dödsorsaker: " + "; ".join(f"{k} ({v})" for k, v in top))
        return {"run": self.run_id, "seconds": round(secs, 1), "ideas_generated": len(ideas), "ideas_selected": len(real) - sum(1 for c in real if c["iter"] > 0),
                "evaluated_versions": len(real), "controls": len(ctrl), "controls_advanced": len(fp), "verdicts": verdicts, "families": fam,
                "trials": self.bb.s["trials"], "experiments_registered": self.registry.count(), "learnings": learn, "known_issues": self.bb.s["known_issues"][-12:],
                "sealed_looks": self.bb.s.get("sealed_looks", 0),
                "promising": [c["spec"]["desc"] + f" [{c['final']['verdict']}, poäng {c['final']['score']}]" for c in real if (c.get("final") or {}).get("verdict") in ("PROMISING", "READY_FOR_PAPER")],
                "workers": self.workers, "agents_spawned": sum(1 for a in self.bb.s["agents"].values() if a.get("run") == self.run_id)}

    def report(self, s: dict, all_c: list) -> str:
        L = [f"# Agentlab {s['run']}: första autonoma forskningskörningen", "",
             "Utforskande. Allt här är upprepade försök på samma data och inget är ett bekräftande test. Slutprovet 2025+ är aldrig läst.", "",
             f"* Idéer genererade: **{s['ideas_generated']}**, utvalda: **{s['ideas_selected']}** (+ {s['controls']} negativa kontroller), utvärderade versioner inklusive iterationer: **{s['evaluated_versions']}**",
             f"* Domslut: {s['verdicts']}", f"* Försök som räknas (inklusive grannparametrar): **{s['trials']}**, registrerade experiment: **{s['experiments_registered']}**",
             f"* Sub-agenter som skapades: **{s['agents_spawned']}**, parallella arbetsprocesser: **{s['workers']}**, tid: {s['seconds']} s",
             f"* Förbrukad data denna körning: validerings- och slutårsmått beräknades bara efter sina grindar ({s['sealed_looks']} beräkningar). Hela historiken: se `data_status` och `spent` i state.json.", ""]
        L += ["## Vad systemet lärde sig", ""] + [f"* {x}" for x in s["learnings"]] + [""]
        L += ["## Familjer", "", "| Familj | Testade | REJECT | Gick vidare | Bästa discovery-Sharpe |", "|---|---|---|---|---|"]
        for f, v in sorted(s["families"].items()):
            L.append(f"| {f} | {v['tested']} | {v['rejected']} | {v['advanced']} | {v['best_disc_sharpe']:.2f} |")
        L += ["", "## Kandidater (efter debatt)", "", "| Nyckel | Idé | Iter | Disc-Sharpe | Slutdom | Poäng | Huvudinvändning |", "|---|---|---|---|---|---|---|"]
        for c in sorted(all_c, key=lambda c: -((c.get("final") or {}).get("score") or -1)):
            d = c["evidence"].get("quant", {}).get("disc", {})
            obj = c["evidence"].get("objections", [])
            fin = c.get("final") or {}
            L.append(f"| `{c['spec']['key']}` | {'(kontroll) ' if c['control'] else ''}{c['spec']['desc'][:70]} | {c['iter']} | {d.get('sharpe', float('nan')):.2f} | {fin.get('verdict', 'ITERATED')} | {fin.get('score', '')} | {(obj[0]['code'] + ': ' + obj[0]['text'][:60]) if obj else ''} |")
        if s["promising"]:
            L += ["", "## Lovande kandidater", ""] + [f"* {p}" for p in s["promising"]]
        else:
            L += ["", "## Lovande kandidater", "", "Inga. Allt blev REJECT eller dog på vägen. Det är ett helt acceptabelt utfall."]
        L += ["", "## Kända problem", ""] + ([f"* {i}" for i in s["known_issues"]] or ["* Inga fel från agenterna."])
        return "\n".join(L) + "\n"

    def outbox(self, s: dict) -> str:
        return (f"**Agentlab {s['run']}** (utforskande sidoprojekt, inte ett bekräftande test)\n\n"
                f"* {s['ideas_generated']} idéer, {s['ideas_selected']} utvalda, {s['evaluated_versions']} versioner utvärderade (inklusive iterationer), {s['controls']} negativa kontroller.\n"
                f"* Domslut: {s['verdicts']}. Lovande: {len(s['promising'])}.\n* Försök som räknas: {s['trials']}. Sub-agenter: {s['agents_spawned']}.\n"
                + "".join(f"* {x}\n" for x in s["learnings"]) + "\n---\n_Generated by [Claude Code](https://claude.ai/code)_\n")
