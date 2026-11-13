"""Agenterna. Varje agent är en uppsättning uppgiftsfunktioner som körs parallellt (en process per uppgift) mot samma delade panel.

Roller: Idé, Data, Quant (Builder), ML, Kostnad/Utförande, Risk, Skeptiker (adversarial), Portfölj. Domaren och Orchestratorn finns i judge.py och orchestrator.py.
En agent kan skapa tillfälliga sub-agenter: den lägger en `spawn`-begäran i sitt resultat, och Orchestratorn startar sub-agenten som en ny uppgift med ett eget mål.
Alla invändningar är dicts {code, severity 0..1, agent, text, mutable}. `mutable` = Builder har en bestämd ändring som kan adressera den.
"""
from __future__ import annotations

import hashlib
import os
import pickle
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from . import backtest as bt
from .data import PERIODS, SOURCES, Panel, period_slice
from .strategies import (ModelUnavailable, build, make_spec, neighbors, sample_ideas)

_PANEL: Panel | None = None
_CACHE: Path | None = None
XS_FAMILIES = {"xs_mom", "xs_rev", "lowvol", "bab", "funding_carry", "ensemble_rank", "ml_xs", "placebo"}

AGENT_DEFS = {
    "orchestrator": "Delar upp mål i uppgifter, startar agenter och sub-agenter parallellt, samlar resultat och avgör vilka idéer som behöver en ny runda.",
    "idea": "Genererar många rimliga idéer brett över familjer, tidsramar och datakällor.",
    "data": "Kontrollerar vilken data som finns, bygger features och föreslår nya källor. Kan skapa FundingSpecialist, OrderbookSpecialist, OISpecialist.",
    "quant": "BUILDER: försöker hitta edge. Implementerar, backtestar, jämför parametrar och baslinjer. Kan skapa CrossSectionSpecialist, PairsSpecialist.",
    "ml": "Testar ML-modeller (ridge, rf, LightGBM, MLP, ensemble) med walk-forward och jämför mot enkla baslinjer.",
    "cost": "COST/EXECUTION: försöker göra strategin olönsam med realistiska kostnader, fördröjning och finansiering.",
    "risk": "RISK: letar situationen där den går sönder. Drawdown, svansrisk, koncentration, regimkänslighet. Kan skapa LiquidationStressSpecialist.",
    "skeptic": "SKEPTIC/ADVERSARIAL: försöker visa att edgen inte finns. Slumptest, deflated Sharpe, instabilitet. Kan skapa LeakageSpecialist, AssetSplitSpecialist.",
    "portfolio": "Frågar om strategin tillför något jämfört med de andra och baslinjerna. Kombinerar okorrelerade edges.",
    "judge": "Väger all evidens med ett gemensamt poängsystem och dömer REJECT / MORE_RESEARCH / PROMISING / READY_FOR_PAPER.",
}


_FULL: Panel | None = None
_VIEWS: dict[str, Panel] = {}
_ACTIVE = "disc"


def set_panel(p: Panel | None, cache: Path | None = None) -> None:
    """Sparar hela panelen bara som källa för begränsade vyer. Uppgifter får aldrig den hela: se `panel()`."""
    global _FULL, _CACHE, _VIEWS, _ACTIVE
    _FULL, _CACHE, _VIEWS, _ACTIVE = p, cache, {}, "disc"


def _view(upto: str) -> Panel:
    """Panelen avskuren efter periodens slutdatum: `disc` slutar 2022-12-31, `valid` 2023-12-31, `final` är hela. Det som ligger efter finns inte i processen."""
    assert _FULL is not None, "ingen panel inladdad"
    if upto not in _VIEWS:
        end = pd.Timestamp(PERIODS[upto][1], tz="UTC")
        cut = lambda df: df.loc[:end]
        f = _FULL
        _VIEWS[upto] = Panel(cut(f.open), cut(f.high), cut(f.low), cut(f.close), cut(f.dvol), cut(f.funding), meta={**f.meta, "upto": upto},
                             funding_known=cut(f.funding_known), funding_rule=f.funding_rule)
    return _VIEWS[upto]


def panel() -> Panel:
    """Den panel den aktuella uppgiften får se. Standard är discovery; bara `validate_task` och `final_task` byter vy, och bara i sin egen uppgift."""
    return _view(_ACTIVE)


class use:
    """Byter vy tillfälligt (bara för valideringssteget och slutsteget). Återställs alltid till discovery."""
    def __init__(self, upto: str):
        self.upto = upto

    def __enter__(self):
        global _ACTIVE
        _ACTIVE = self.upto

    def __exit__(self, *exc):
        global _ACTIVE
        _ACTIVE = "disc"


def weights(spec: dict) -> pd.DataFrame:
    """Vikter för en spec, med diskcache så att flera agenter inte bygger samma modell om (skrivs atomärt)."""
    pan = panel()
    sig = hashlib.sha1(f"{pan.close.shape}{pan.close.index[-1]}{float(pan.close.iloc[-1].sum()):.4f}".encode()).hexdigest()[:8]
    f = _CACHE / f"{spec['key']}-{sig}.pkl" if _CACHE else None
    if f is not None and f.exists():
        try:
            return pickle.loads(f.read_bytes())
        except Exception:
            pass
    W = build(spec, pan)
    if f is not None:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_bytes(pickle.dumps(W))
        tmp.replace(f)
    return W


def obj(code: str, severity: float, agent: str, text: str, mutable: bool = False) -> dict:
    return {"code": code, "severity": round(float(severity), 2), "agent": agent, "text": text, "mutable": mutable}


def _disc(r: pd.Series) -> pd.Series:
    return r[period_slice(r.index, "disc")]


def _btc(pan: Panel) -> pd.Series:
    return pan.close["BTCUSDT"].pct_change(fill_method=None) if "BTCUSDT" in pan.close else pan.close.mean(axis=1).pct_change(fill_method=None)


def _beta(r: pd.Series, pan: Panel) -> float:
    b = _btc(pan).reindex(r.index)
    x = pd.concat([_disc(r), _disc(b)], axis=1).dropna()
    return float(x.cov().iloc[0, 1] / x.iloc[:, 1].var()) if len(x) > 30 and x.iloc[:, 1].var() > 0 else 0.0


# ================================================================ QUANT / ML (Builder)
def quant_task(pl: dict) -> dict:
    spec = pl["spec"]
    pan = panel()
    W = weights(spec)
    res = bt.run(pan, W)
    disc = bt.metrics(_disc(res.ret))                       # bara discovery: panelen slutar 2022-12-31
    d_idx = period_slice(res.ret.index, "disc")
    turnover = float(res.turnover[d_idx].mean() * 365)
    beta = _beta(res.ret, pan)
    out = {"agent": "quant" if spec["family"] != "ml_xs" else "ml", "key": spec["key"], "disc": disc,
           "disc_returns": [round(float(x), 6) for x in res.ret[d_idx].fillna(0.0).values],
           "turnover_ann": turnover, "beta_btc": beta, "trials": 1, "neighbors": [], "objections": [], "spawn": []}
    base = bt.baselines(pan)
    out["baselines"] = {k: bt.sharpe(_disc(v)) for k, v in base.items()}
    if spec["family"] != "ml_xs":                                   # grannar: parameterkänslighet (räknas som försök)
        for ns in neighbors(spec, 6):
            try:
                out["neighbors"].append([ns["key"], bt.sharpe(_disc(bt.run(pan, weights(ns)).ret))])
            except (bt.CoverageInvalid, ModelUnavailable):
                pass                                                  # en granne med okänd data räknas inte som ett resultat
        out["trials"] += len(out["neighbors"])
    else:                                                           # ML mot enkla baslinjer med samma uppdrag
        simple = make_spec("xs_mom", {"k": 30, "q": spec["params"].get("q", 0.2), "rebal": spec["params"].get("h", 3), "uni": spec["params"].get("uni", 30)})
        ridge = make_spec("ml_xs", {**spec["params"], "model": "ridge"}) if spec["params"]["model"] != "ridge" else None
        out["simple_baseline_sharpe"] = bt.sharpe(_disc(bt.run(pan, weights(simple)).ret))
        out["trials"] += 1
        if ridge is not None:
            try:
                out["ridge_sharpe"] = bt.sharpe(_disc(bt.run(pan, weights(ridge)).ret))
                out["trials"] += 1
            except ModelUnavailable:
                pass
    s = disc["sharpe"]
    if s < 0.3:
        out["objections"].append(obj("weak_disc", 0.9, out["agent"], f"Discovery-Sharpe {s:.2f} är för låg."))
    if turnover > 100:
        out["objections"].append(obj("high_turnover", min(1, turnover / 300), out["agent"], f"Omsättning {turnover:.0f}x per år äter kostnader.", True))
    nb = out["neighbors"]
    if nb and np.mean([x[1] > 0.5 * max(s, 0.1) for x in nb]) < 0.5 and s > 0:
        out["objections"].append(obj("param_unstable", 0.7, out["agent"], "Grannparametrar är klart sämre: kanten sitter i en parameterpunkt.", True))
    if spec["family"] == "ml_xs":
        sb = out.get("simple_baseline_sharpe", 0.0)
        if s < max(sb * 1.15, 0.3):
            out["objections"].append(obj("ml_no_better_than_simple", 0.8, "ml", f"ML ({s:.2f}) slår inte tumregeln xs_mom ({sb:.2f}). Behåll det enkla.", False))
        if "ridge_sharpe" in out and s < out["ridge_sharpe"]:
            out["objections"].append(obj("ml_overfit", 0.6, "ml", f"Ickelinjär modell ({s:.2f}) sämre än ridge ({out['ridge_sharpe']:.2f}).", True))
    if beta > 0.5 and s <= out["baselines"].get("bh_btc", 9):
        out["objections"].append(obj("no_edge_vs_baseline", 0.8, out["agent"], f"Beta {beta:.2f} mot BTC och Sharpe ≤ köp-och-behåll ({out['baselines']['bh_btc']:.2f}).", False))
    if spec["family"] in XS_FAMILIES and spec["family"] != "placebo":
        out["spawn"].append({"name": "CrossSectionSpecialist", "goal": "Visa om edgen ligger i long- eller short-benet", "fn": "crosssection_specialist", "payload": {"spec": spec}})
    if spec["family"] == "pairs":
        out["spawn"].append({"name": "PairsSpecialist", "goal": "Kontrollera att spreadarna verkligen är mean-reverting (halveringstid)", "fn": "pairs_specialist", "payload": {"spec": spec}})
    return out


# ================================================================ COST / EXECUTION
def cost_task(pl: dict) -> dict:
    spec, pan = pl["spec"], panel()
    W = weights(spec)
    grid = {}
    for mult in (0.0, 1.0, 2.5, 5.0):
        grid[f"{mult}"] = bt.sharpe(_disc(bt.run(pan, W, cost=bt.COST_PER_SIDE * mult).ret))
    base = bt.run(pan, W)
    d = period_slice(base.ret.index, "disc")
    gross = float(base.gross[d].mean() * 365)
    fund = float(base.funding[d].mean() * 365)
    cost_ann = float(base.cost[d].mean() * 365)
    be = None                                                       # break-even-kostnad per sida (bp)
    mean_ex_cost = float((base.gross - base.funding)[d].mean())
    to = float(base.turnover[d].mean())
    if to > 0 and mean_ex_cost > 0:
        be = mean_ex_cost / to * 1e4
    delayed = bt.sharpe(_disc(bt.run(pan, W, delay=1).ret))
    nofund = bt.sharpe(_disc(bt.run(pan, W, funding=False).ret))
    out = {"agent": "cost", "key": spec["key"], "sharpe_grid": grid, "breakeven_bp_per_side": be, "delay1_sharpe": delayed, "nofunding_sharpe": nofund,
           "gross_ann": gross, "cost_ann": cost_ann, "funding_ann": fund, "objections": [], "spawn": []}
    b = grid["1.0"]
    if b > 0 and grid["2.5"] < 0.5 * b:
        out["objections"].append(obj("cost_fragile", 0.8 if grid["2.5"] <= 0 else 0.5, "cost", f"Sharpe {b:.2f} faller till {grid['2.5']:.2f} med 2,5x kostnader.", True))
    elif b <= 0 < grid["0.0"]:
        out["objections"].append(obj("cost_fragile", 0.9, "cost", f"Lönsam före kostnader (Sharpe {grid['0.0']:.2f}) men inte efter ({b:.2f}).", True))
    if b > 0 and delayed < 0.5 * b:
        out["objections"].append(obj("alpha_decay", 0.6, "cost", f"Edgen försvinner med en dags fördröjning ({delayed:.2f} mot {b:.2f}): kräver snabbt, billigt utförande.", False))
    if gross > 0 and fund > 0.3 * gross:
        out["objections"].append(obj("funding_drag", 0.5, "cost", f"Finansieringsränta tar {fund / gross:.0%} av bruttoavkastningen.", False))
    return out


# ================================================================ RISK
def risk_task(pl: dict) -> dict:
    spec, pan = pl["spec"], panel()
    W = weights(spec)
    res = bt.run(pan, W)
    r = _disc(res.ret).dropna()
    m = bt.metrics(r)
    worst_day = float(r.min()) if len(r) else 0.0
    wk = r.rolling(7).sum()
    top5 = float(r.nlargest(5).clip(lower=0).sum() / max(r.clip(lower=0).sum(), 1e-9)) if len(r) else 0.0
    Wd = W[period_slice(W.index, "disc")]
    gross = Wd.abs().sum(axis=1)
    hhi = float(((Wd.pow(2).sum(axis=1)) / gross.pow(2).replace(0, np.nan)).mean())
    btc = _btc(pan).reindex(r.index)
    up = btc.rolling(30).sum() > 0
    vol = btc.rolling(30).std()
    hi = vol > vol.median()
    reg = {"btc_up": bt.sharpe(r[up.reindex(r.index).fillna(False)]), "btc_down": bt.sharpe(r[~up.reindex(r.index).fillna(True)]),
           "vol_high": bt.sharpe(r[hi.reindex(r.index).fillna(False)]), "vol_low": bt.sharpe(r[~hi.reindex(r.index).fillna(True)])}
    out = {"agent": "risk", "key": spec["key"], "max_dd": m["max_dd"], "cvar5": m["cvar5"], "worst_day": worst_day, "worst_week": float(wk.min()) if wk.notna().any() else 0.0,
           "top5_day_share": top5, "asset_hhi": hhi, "gross_p99": float(gross.quantile(0.99)), "regime": reg, "beta_btc": _beta(res.ret, pan), "objections": [], "spawn": []}
    if m["max_dd"] < -0.35:
        out["objections"].append(obj("drawdown", min(1, abs(m["max_dd"])), "risk", f"Största nedgång {m['max_dd']:.0%} på discovery.", True))
    if m["cvar5"] < -0.05 or worst_day < -0.12:
        out["objections"].append(obj("tail_risk", 0.7, "risk", f"Svansen är tung: CVaR5 {m['cvar5']:.1%}, sämsta dag {worst_day:.1%}.", True))
    if top5 > 0.5:
        out["objections"].append(obj("concentration", 0.6, "risk", f"{top5:.0%} av vinsten kommer från de fem bästa dagarna.", True))
    if hhi > 0.25:
        out["objections"].append(obj("concentration", 0.5, "risk", f"Få tillgångar bär portföljen (HHI {hhi:.2f}).", True))
    worst_reg = min(reg.values())
    if m["sharpe"] > 0 and worst_reg < -0.5:
        out["objections"].append(obj("regime_fragile", 0.6, "risk", f"Går sönder i en regim (Sharpe {worst_reg:.2f}): {reg}", True))
    if out["gross_p99"] > 1.2 or abs(out["beta_btc"]) > 0.3:
        out["spawn"].append({"name": "LiquidationStressSpecialist", "goal": "Stressa hävstång och likvidationsrisk", "fn": "liquidation_specialist", "payload": {"spec": spec}})
    return out


# ================================================================ SKEPTIC / ADVERSARIAL
def skeptic_task(pl: dict) -> dict:
    spec, pan = pl["spec"], panel()
    W = weights(spec)
    res = bt.run(pan, W)
    r = _disc(res.ret).dropna()
    rng = np.random.default_rng(int(spec["key"][:6], 16))
    # permutationstest: cirkulär tidsförskjutning av vikterna (bevarar vikternas struktur och omsättning, bryter timingen mot priserna)
    fwd = pan.fwd().fillna(0.0).values
    fwdf = pan.fwd_funding().fillna(0.0).values
    Wv = W.reindex(index=pan.close.index, columns=pan.close.columns).fillna(0.0).values
    g = np.abs(Wv).sum(axis=1)
    Wv = Wv * np.where(g > bt.LEV_CAP, bt.LEV_CAP / np.where(g > 0, g, 1), 1.0)[:, None]
    turn = np.abs(np.diff(Wv, axis=0, prepend=Wv[:1])).sum(axis=1)
    d_mask = period_slice(pan.close.index, "disc")
    real = bt.sharpe(r)
    null = []
    n = len(Wv)
    for _ in range(300):
        sft = int(rng.integers(40, n - 40))
        Wr = np.roll(Wv, sft, axis=0)
        net = (Wr * fwd).sum(axis=1) - (Wr * fwdf).sum(axis=1) - np.roll(turn, sft) * bt.COST_PER_SIDE
        null.append(bt.sharpe(pd.Series(net, index=pan.close.index).shift(1)[d_mask]))
    null = np.array(null)
    perm_p = float((np.sum(null >= real) + 1) / (len(null) + 1))
    halves = [g for _, g in r.groupby([r.index.year, (r.index.month > 6)])]
    half_pos = float(np.mean([g.sum() > 0 for g in halves])) if halves else 0.0
    out = {"agent": "skeptic", "key": spec["key"], "perm_p": perm_p, "perm_null_mean": float(null.mean()), "dsr": None, "n_trials": None,
           "half_pos": half_pos, "leakage": False, "asset_pos": 0.5, "objections": [], "spawn": []}
    if perm_p > 0.10:
        out["objections"].append(obj("indistinguishable_from_luck", 0.9, "skeptic", f"Slumpmässig timing ger lika bra resultat i {perm_p:.0%} av fallen (p={perm_p:.2f})."))
    if half_pos < 0.6:
        out["objections"].append(obj("unstable_periods", 0.6, "skeptic", f"Bara {half_pos:.0%} av halvåren är positiva.", True))
    out["spawn"] += [{"name": "LeakageSpecialist", "goal": "Bevisa eller motbevisa läckage med en trunkeringstest", "fn": "leakage_specialist", "payload": {"spec": spec}},
                     {"name": "AssetSplitSpecialist", "goal": "Testa om edgen bärs av ett fåtal tillgångar", "fn": "asset_split_specialist", "payload": {"spec": spec}}]
    return out


# ================================================================ PORTFOLIO
def portfolio_task(pl: dict) -> dict:
    """Korrelation och diversifieringsvärde mellan kandidaterna, plus okorrelerade kombinationer. Kandidater = lista av specs."""
    pan = panel()
    specs = pl["specs"]
    rets = {s["key"]: bt.run(pan, weights(s)).ret for s in specs}
    base = bt.baselines(pan)
    R = pd.DataFrame({**rets, "bh_btc": base["bh_btc"]})
    Rd = R[period_slice(R.index, "disc")].dropna()
    corr = Rd.corr()
    vol = Rd.std().replace(0, np.nan)

    def port_sharpe(keys, frame):
        sub = frame[keys].dropna()
        w = (1 / sub.std())
        w = w / w.sum()
        return bt.sharpe((sub * w).sum(axis=1))
    out = {"agent": "portfolio", "corr": {k: {j: round(float(v), 2) for j, v in row.items()} for k, row in corr.iterrows()}, "div_value": {}, "max_corr": {}, "combos": {}}
    keys = [s["key"] for s in specs]
    for k in keys:
        others = [x for x in keys if x != k] + ["bh_btc"]
        out["div_value"][k] = float(port_sharpe(others + [k], Rd) - port_sharpe(others, Rd))
        out["max_corr"][k] = float(corr.loc[k, [x for x in keys if x != k]].abs().max()) if len(keys) > 1 else 0.0
    # kombinationer: inverse-vol på alla, och girig framåtval av okorrelerade (disc)
    if keys:
        chosen, best = [], -9.0
        for _ in range(len(keys)):
            cand = [(port_sharpe(chosen + [k], Rd), k) for k in keys if k not in chosen]
            if not cand:
                break
            sc, k = max(cand)
            if sc <= best + 0.02:
                break
            chosen.append(k); best = sc
        allw = (1 / Rd[keys].std()); allw = allw / allw.sum()
        for name, ks in (("all_invvol", keys), ("greedy", chosen)):
            sub = R[ks].dropna()
            w = (1 / sub[period_slice(sub.index, "disc")].std()); w = w / w.sum()
            pr = (sub * w).sum(axis=1)
            out["combos"][name] = {"members": ks, "disc": bt.metrics(pr[period_slice(pr.index, "disc")])}
    return out


# ================================================================ DATA
def data_task(pl: dict) -> dict:
    pan = panel()
    avail = {}
    for name, s in SOURCES.items():
        avail[name] = {"status": s["status"], "description": s["description"], "needs": s["needs"]}
    info = {"symbols": len(pan.symbols), "first": str(pan.close.index[0].date()), "last": str(pan.close.index[-1].date()),
            "funding_symbols": int((pan.funding.abs().sum() > 0).sum()), "caveat": pan.meta.get("caveat", "")}
    return {"agent": "data", "availability": avail, "panel": info, "objections": [], "spawn": [
        {"name": "FundingSpecialist", "goal": "Mät om finansieringsränta förutsäger framtida avkastning (informationskoefficient)", "fn": "funding_specialist", "payload": {}},
        {"name": "OrderbookSpecialist", "goal": "Kontrollera om orderboksdata finns och föreslå hur den skaffas", "fn": "orderbook_specialist", "payload": {}},
        {"name": "OISpecialist", "goal": "Kontrollera om open interest finns och föreslå hur den skaffas", "fn": "oi_specialist", "payload": {}}]}


def idea_task(pl: dict) -> dict:
    ideas = sample_ideas(pl["n"], pl["seed"], pl.get("families"), set(pl.get("skip", [])))
    return {"agent": "idea", "ideas": ideas, "objections": [], "spawn": []}


# ================================================================ SUB-AGENTER (tillfälliga)
def crosssection_specialist(pl: dict) -> dict:
    spec, pan = pl["spec"], panel()
    W = weights(spec).reindex(index=pan.close.index, columns=pan.close.columns).fillna(0.0)
    f = pan.fwd().fillna(0.0)
    d = period_slice(W.index, "disc")
    lg = (W.clip(lower=0) * f)[d].sum(axis=1)
    sh = (W.clip(upper=0) * f)[d].sum(axis=1)
    out = {"agent": "CrossSectionSpecialist", "long_leg_ann": float(lg.mean() * 365), "short_leg_ann": float(sh.mean() * 365), "objections": []}
    if lg.mean() <= 0 < sh.mean():
        out["objections"].append(obj("edge_only_short_leg", 0.5, "CrossSectionSpecialist", "All avkastning kommer från short-benet: dyrare, lånebegränsat och riskablare att utföra."))
    return out


def pairs_specialist(pl: dict) -> dict:
    spec, pan = pl["spec"], panel()
    lb = spec["params"]["lb"]
    uni = pan.universe(30)
    liquid = list(pan.dvol.where(uni).median().sort_values(ascending=False).dropna().index[:14])
    lc = np.log(pan.close[liquid])
    hl = []
    for i, a in enumerate(liquid):
        for b in liquid[i + 1:]:
            s = (lc[a] - lc[b]).dropna()
            if len(s) < 200:
                continue
            x, y = s.values[:-1] - s.values[:-1].mean(), s.values[1:] - s.values[:-1].mean()
            phi = float((x * y).sum() / (x * x).sum())
            if 0 < phi < 1:
                hl.append(-np.log(2) / np.log(phi))
    med = float(np.median(hl)) if hl else float("inf")
    out = {"agent": "PairsSpecialist", "median_halflife_days": med, "objections": []}
    if med > 3 * lb:
        out["objections"].append(obj("spread_not_mean_reverting", 0.7, "PairsSpecialist", f"Spreadarnas halveringstid {med:.0f} dagar är mycket längre än fönstret {lb}."))
    return out


def liquidation_specialist(pl: dict) -> dict:
    spec, pan = pl["spec"], panel()
    r = _disc(bt.run(pan, weights(spec)).ret).dropna()
    res = {}
    for L in (1, 2, 3, 5):
        eq = (1 + L * r).cumprod()
        dd = float((eq / eq.cummax() - 1).min())
        res[str(L)] = {"max_dd": dd, "liquidated": bool(dd <= -(0.9 if L > 1 else 1.0))}
    safe = max([L for L in (1, 2, 3, 5) if not res[str(L)]["liquidated"]] or [0])
    out = {"agent": "LiquidationStressSpecialist", "by_leverage": res, "max_safe_leverage": safe, "objections": []}
    if safe < 2:
        out["objections"].append(obj("liquidation_risk", 0.6, "LiquidationStressSpecialist", f"Högsta hävstång utan likvidation på discovery är {safe}x."))
    return out


def leakage_specialist(pl: dict) -> dict:
    """Trunkeringstest: vikter byggda på data till och med T ska vara identiska med vikterna för samma dagar när hela serien finns."""
    spec, pan = pl["spec"], panel()
    if spec["family"] == "ml_xs":
        return {"agent": "LeakageSpecialist", "leakage": False, "tested": False, "note": "ML hoppas över (för långsamt); walk-forward städar etiketter med h+2 dagar.", "objections": []}
    W = weights(spec)
    n = len(pan.close)
    worst = 0.0
    for frac in (0.55, 0.7, 0.85):
        cut = int(n * frac)
        sub = Panel(pan.open.iloc[:cut], pan.high.iloc[:cut], pan.low.iloc[:cut], pan.close.iloc[:cut], pan.dvol.iloc[:cut], pan.funding.iloc[:cut], meta=pan.meta,
                    funding_known=pan.funding_known.iloc[:cut], funding_rule=pan.funding_rule)
        Ws = build(spec, sub).reindex(columns=W.columns).fillna(0.0)
        a, b = Ws.values, W.iloc[:cut].fillna(0.0).values            # alla rader inklusive den sista: en dags framtidsblick syns bara där
        worst = max(worst, float(np.nanmax(np.abs(a - b))))
    leak = worst > 1e-8
    out = {"agent": "LeakageSpecialist", "leakage": leak, "tested": True, "max_abs_diff": worst, "objections": []}
    if leak:
        out["objections"].append(obj("leakage", 1.0, "LeakageSpecialist", f"Vikterna ändras av framtida data (maxskillnad {worst:.3g}): läckage."))
    return out


def asset_split_specialist(pl: dict) -> dict:
    spec, pan = pl["spec"], panel()
    W = weights(spec).reindex(index=pan.close.index, columns=pan.close.columns).fillna(0.0)
    rng = np.random.default_rng(1)
    cols = list(W.columns)
    sh = []
    for _ in range(12):
        keep = rng.random(len(cols)) < 0.5
        Wk = W.copy()
        Wk.loc[:, [c for c, k in zip(cols, keep) if not k]] = 0.0
        sh.append(bt.sharpe(_disc(bt.run(pan, Wk).ret)))
    pos = float(np.mean(np.array(sh) > 0))
    out = {"agent": "AssetSplitSpecialist", "asset_pos": pos, "split_sharpes": [round(x, 2) for x in sh], "objections": []}
    if pos < 0.6:
        out["objections"].append(obj("asset_fragile", 0.6, "AssetSplitSpecialist", f"Bara {pos:.0%} av slumpmässiga halvuniversum är lönsamma: edgen bärs av få tillgångar.", True))
    return out


def funding_specialist(pl: dict) -> dict:
    pan = panel()
    f, fw = pan.fund(7).where(pan.universe(30)), pan.fwd()
    ic = f.rank(axis=1).corrwith(fw.rank(axis=1), axis=1)
    d = ic[period_slice(ic.index, "disc")]
    return {"agent": "FundingSpecialist", "ic_funding7_vs_fwd1d_disc": float(d.mean()), "ic_t": float(d.mean() / (d.std() / np.sqrt(d.count()))) if d.count() > 30 else 0.0,
            "note": "Negativ IC = hög finansieringsränta följs av sämre avkastning (carry/trängsel).", "objections": []}


def _source_check(name: str, needs: str) -> dict:
    return {"agent": name, "available": False, "proposal": needs, "objections": []}


def orderbook_specialist(pl: dict) -> dict:
    return _source_check("OrderbookSpecialist", "Ingen orderbok finns lokalt. Förslag: data.binance.vision futures/um/daily/bookDepth (stort; börja med BTC/ETH) och bygg spread/obalans-features. Binance API är blockerat (451).")


def oi_specialist(pl: dict) -> dict:
    return _source_check("OISpecialist", "Ingen open interest lokalt. Förslag: data.binance.vision futures/um/daily/metrics (OI, long/short-kvot) som dagsfiler per symbol.")


# ================================================================ FÖRSEGLADE STEG (körs separat efter sina grindar)
def _reveal(spec: dict, period: str) -> dict:
    """Beräknar bara en periods mått. Panelen är avskuren efter periodens slut, och resultatet innehåller inget annat än den perioden."""
    with use(period):
        pan = panel()
        res = bt.run(pan, weights(spec))
        return {"agent": "judge", "key": spec["key"], period: bt.metrics(res.ret[period_slice(res.ret.index, period)]), "objections": [], "spawn": []}


def validate_task(pl: dict) -> dict:
    """Valideringsåret 2023. Körs bara för kandidater som passerat discovery-grinden. Panelen slutar 2023-12-31, så 2024 finns inte här."""
    return _reveal(pl["spec"], "valid")


def final_task(pl: dict) -> dict:
    """Slutåret 2024. Körs bara för kandidater som klarat valideringsgrinden."""
    return _reveal(pl["spec"], "final")


TASKS = {f.__name__: f for f in (validate_task, final_task, quant_task, cost_task, risk_task, skeptic_task, portfolio_task, data_task, idea_task, crosssection_specialist, pairs_specialist,
                                liquidation_specialist, leakage_specialist, asset_split_specialist, funding_specialist, orderbook_specialist, oi_specialist)}


def run_task(fn: str, payload: dict) -> dict:
    """Körs i en arbetsprocess. Fel blir ett resultat (ingen krasch): Orchestratorn loggar dem som kända problem och går vidare."""
    try:
        return TASKS[fn](payload)
    except ModelUnavailable as exc:
        return {"error": f"modell saknas: {exc}", "skipped": True, "objections": [], "spawn": []}
    except bt.CoverageInvalid as exc:                  # okänd data under exponerad position: utvärderingen är ogiltig, aldrig ett resultat
        return {"invalid": True, "reason": str(exc), "objections": [], "spawn": []}
    except Exception as exc:                          # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-600:], "objections": [], "spawn": []}
