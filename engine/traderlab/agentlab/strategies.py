"""Strategifamiljer: idé-specar och viktbyggare. Alla vikter för dag t använder bara data till och med stängningen av dag t.

En spec är en vanlig dict: {id, family, params, desc, hypothesis}. `build(spec, panel)` ger vikter (dag × symbol) med bruttoexponering 1 (före vol-målsättning).
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
import warnings

import numpy as np
import pandas as pd

from .data import Panel

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------- parametergrid (används för idéer, grannar och mutationer)
GRID: dict[str, dict] = {
    "xs_mom": {"k": [7, 14, 30, 60, 90, 120], "skip": [0, 1, 3], "q": [0.2, 0.3], "rebal": [1, 3, 7, 14], "uni": [20, 30, 50], "vt": [0, 0.2]},
    "xs_rev": {"k": [1, 2, 3, 5, 7], "q": [0.2, 0.3], "rebal": [1, 2, 3, 5], "uni": [20, 30], "vt": [0, 0.2]},
    "ts_mom": {"k": [10, 20, 40, 80, 160], "long_only": [True, False], "vt": [0, 0.15], "uni": [5, 10]},
    "trend_ma": {"n": [20, 50, 100, 200], "basket": [2, 5, 10], "vt": [0, 0.15]},
    "donchian": {"n": [20, 40, 80], "basket": [5, 10], "vt": [0, 0.15]},
    "lowvol": {"k": [20, 40, 90], "q": [0.2, 0.3], "rebal": [7, 14], "uni": [30, 50], "vt": [0, 0.2]},
    "bab": {"k": [60, 90, 180], "q": [0.2, 0.3], "rebal": [7, 14], "uni": [30, 50], "vt": [0, 0.2]},
    "funding_carry": {"k": [3, 7, 14, 30], "q": [0.2, 0.3], "rebal": [1, 3, 7], "uni": [30, 50], "vt": [0, 0.2]},
    "funding_fade": {"k": [3, 7], "z": [1.5, 2.0], "hold": [3, 7], "uni": [30, 50]},
    "pairs": {"lb": [20, 40, 60], "z_in": [1.5, 2.0, 2.5], "z_out": [0.0, 0.5], "npairs": [3, 6]},
    "vol_regime": {"base": ["xs_mom", "ts_mom"], "k_vol": [20, 60], "mode": ["low", "high"], "k": [30, 60], "uni": [30]},
    "vol_shock": {"z": [2.0, 3.0], "mode": ["fade", "follow"], "hold": [1, 3], "uni": [30, 50]},
    "mtf_trend": {"ks": [[10, 30, 90], [20, 60, 180]], "basket": [5, 10], "vt": [0, 0.15]},
    "ensemble_rank": {"members": [["xs_mom", "funding_carry", "lowvol"], ["xs_mom", "xs_rev", "bab"], ["funding_carry", "lowvol", "bab"]], "q": [0.2, 0.3], "rebal": [3, 7]},
    "ml_xs": {"model": ["ridge", "lgbm", "rf", "mlp", "ens", "lgbm_prob"], "h": [1, 3, 5], "q": [0.2, 0.3], "retrain": [60, 90], "uni": [30]},
    "placebo": {"seed": list(range(50)), "q": [0.2], "rebal": [3, 7], "uni": [30]},
}
DEFAULTS: dict[str, dict] = {
    "xs_mom": {"skip": 0, "q": 0.2, "rebal": 7, "uni": 30, "vt": 0}, "xs_rev": {"q": 0.2, "rebal": 2, "uni": 30, "vt": 0},
    "ts_mom": {"long_only": True, "vt": 0, "uni": 10}, "trend_ma": {"vt": 0}, "donchian": {"vt": 0}, "lowvol": {"vt": 0},
    "bab": {"vt": 0}, "funding_carry": {"vt": 0}, "funding_fade": {}, "pairs": {}, "vol_regime": {}, "vol_shock": {}, "mtf_trend": {"vt": 0},
    "ensemble_rank": {}, "ml_xs": {}, "placebo": {},
}
FAMILY_TAGS = {
    "xs_mom": "momentum, cross-sectional, market neutral, long/short", "xs_rev": "mean reversion, cross-sectional, market neutral",
    "ts_mom": "momentum, trend, time-series", "trend_ma": "trend, simple rule system", "donchian": "trend, breakout, simple rule system",
    "lowvol": "volatility, low-vol anomaly, market neutral", "bab": "relative value, beta, market neutral",
    "funding_carry": "carry, funding, market neutral", "funding_fade": "funding, contrarian, crowding", "pairs": "statistical arbitrage, relative value",
    "vol_regime": "regime model, volatility", "vol_shock": "anomaly detection, order flow proxy (volume)", "mtf_trend": "multi-timeframe, trend",
    "ensemble_rank": "ensemble, multi-factor", "ml_xs": "probabilistic ML, cross-sectional", "placebo": "negativ kontroll",
}
DATA_NEEDS = {"funding_carry": ["um_funding"], "funding_fade": ["um_funding"], "ml_xs": ["um_ohlcv", "um_funding"], "ensemble_rank": ["um_funding"]}


def spec_key(spec: dict) -> str:
    """Stabil nyckel för en spec (samma familj och parametrar = samma nyckel)."""
    return hashlib.sha1(json.dumps([spec["family"], spec["params"]], sort_keys=True, default=str).encode()).hexdigest()[:12]


def make_spec(family: str, params: dict, parent: str | None = None, note: str = "") -> dict:
    p = {**DEFAULTS.get(family, {}), **params}
    s = {"family": family, "params": p, "parent": parent, "note": note}
    s["key"] = spec_key(s)
    s["desc"] = describe(family, p)
    s["hypothesis"] = hypothesis(family, p)
    return s


def describe(family: str, p: dict) -> str:
    return f"{family}(" + ", ".join(f"{k}={v}" for k, v in p.items()) + ")"


def hypothesis(family: str, p: dict) -> str:
    k = p.get("k", p.get("n", p.get("lb", "")))
    t = {
        "xs_mom": f"Perpar med starkast {k}-dagars avkastning (hoppa över {p.get('skip', 0)} dagar) slår de svagaste de närmaste {p.get('rebal')} dagarna (momentum i tvärsnittet).",
        "xs_rev": f"Perpar som stigit mest på {k} dagar faller tillbaka mot de som fallit mest inom {p.get('rebal')} dagar (kortsiktig reversion i tvärsnittet).",
        "ts_mom": f"Varje pars egen {k}-dagarstrend fortsätter ({'bara long' if p.get('long_only') else 'long och short'}).",
        "trend_ma": f"En korg av de {p.get('basket')} största perparna som ligger över sitt {p.get('n')}-dagarssnitt ger bättre risk än att alltid vara inne.",
        "donchian": f"Utbrott över {p.get('n')}-dagars högsta i de {p.get('basket')} största perparna fortsätter.",
        "lowvol": f"Perpar med låg {k}-dagars volatilitet ger bättre riskjusterad avkastning än de med hög (low-vol-anomalin).",
        "bab": f"Perpar med låg beta mot BTC ({k} dagar) ger mer per riskenhet än de med hög beta (betting against beta).",
        "funding_carry": f"Perpar med lägst {k}-dagars finansieringsränta slår de med högst (carry/ trängsel i longpositioner).",
        "funding_fade": f"När {k}-dagars finansieringsränta är extrem ({p.get('z')} standardavvikelser) vänder priset (kontrarian mot trängsel).",
        "pairs": f"Utvalda korrelerade par återgår mot sitt {p.get('lb')}-dagars snittförhållande efter |z|>{p.get('z_in')} (statistisk arbitrage).",
        "vol_regime": f"Basstrategin {p.get('base')} fungerar bara i {'låg' if p.get('mode') == 'low' else 'hög'}-volatilitetsregimen för BTC.",
        "vol_shock": f"Volymchocker (z>{p.get('z')}) följs av {'reversion' if p.get('mode') == 'fade' else 'fortsättning'} i dagens riktning.",
        "mtf_trend": f"Trend som är överens över flera tidsramar {p.get('ks')} är starkare än en enskild.",
        "ensemble_rank": f"Ett medelrank av flera svaga faktorer {p.get('members')} slår dem var för sig.",
        "ml_xs": f"En {p.get('model')}-modell på enkla pris-, volym- och finansieringsfeatures förutsäger tvärsnittet {p.get('h')} dagar framåt bättre än tumregler.",
        "placebo": "Slumpmässig tvärsnittssignal (negativ kontroll): ska aldrig se bra ut.",
    }
    return t.get(family, family)


# ---------------------------------------------------------------- byggstenar
def _ls(score: pd.DataFrame, mask: pd.DataFrame, q: float, long_only: bool = False) -> pd.DataFrame:
    s = score.where(mask)
    r = s.rank(axis=1, pct=True)
    long = (r > 1 - q).astype(float)
    short = (r <= q).astype(float)
    wl = long.div(long.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    ws = short.div(short.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    return wl if long_only else 0.5 * wl - 0.5 * ws


def _hold(W: pd.DataFrame, every: int) -> pd.DataFrame:
    if every <= 1:
        return W
    keep = np.arange(len(W)) % every == 0
    return W.where(pd.Series(keep, index=W.index), np.nan).ffill().fillna(0.0)


def _hold_events(ev: pd.DataFrame, hold: int) -> pd.DataFrame:
    """Håll en händelsesignal i `hold` dagar (hold=1 = bara händelsedagen)."""
    return ev if hold <= 1 else ev.where(ev != 0).ffill(limit=hold - 1).fillna(0.0)


def _vt(W: pd.DataFrame, panel: Panel, target: float, lb: int = 30) -> pd.DataFrame:
    """Vol-målsättning med bara historia: portföljens egen avkastning blir känd först två dagar efter beslutet (shift 2)."""
    if not target:
        return W
    p = (W * panel.fwd().fillna(0.0)).sum(axis=1)
    est = p.shift(2).rolling(lb, min_periods=15).std() * np.sqrt(365)
    scale = (target / est).clip(0.25, 3.0).fillna(1.0)
    return W.mul(scale, axis=0)


def _rank_mix(scores: list[pd.DataFrame], mask: pd.DataFrame) -> pd.DataFrame:
    return sum(s.where(mask).rank(axis=1, pct=True) for s in scores) / len(scores)


def _basket_signal(panel: Panel, sig: pd.DataFrame, basket: int, long_only: bool = True) -> pd.DataFrame:
    """Lika risk i de `basket` största perparna med signalen (+1/−1/0), skalad så bruttoexponeringen är högst 1."""
    uni = panel.universe(basket, 90)
    s = sig.where(uni).fillna(0.0)
    if long_only:
        s = s.clip(lower=0.0)
    inv = (1.0 / panel.vol(30).where(uni)).fillna(0.0)
    w = s * inv
    return w.div(w.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


# ---------------------------------------------------------------- familjer
def _xs_mom(p, panel):
    uni = panel.universe(p["uni"])
    score = panel.ret(p["k"]).shift(p.get("skip", 0)) if p.get("skip") else panel.ret(p["k"])
    return _vt(_hold(_ls(score, uni, p["q"]), p["rebal"]), panel, p.get("vt", 0))


def _xs_rev(p, panel):
    uni = panel.universe(p["uni"])
    return _vt(_hold(_ls(-panel.ret(p["k"]), uni, p["q"]), p["rebal"]), panel, p.get("vt", 0))


def _ts_mom(p, panel):
    sig = np.sign(panel.ret(p["k"]))
    return _vt(_basket_signal(panel, sig, p["uni"], p.get("long_only", True)), panel, p.get("vt", 0))


def _trend_ma(p, panel):
    sig = (panel.close > panel.close.rolling(p["n"], min_periods=p["n"] // 2).mean()).astype(float)
    return _vt(_basket_signal(panel, sig, p["basket"], True), panel, p.get("vt", 0))


def _donchian(p, panel):
    n = p["n"]
    hi = panel.close.rolling(n, min_periods=n // 2).max().shift(1)
    lo = panel.close.rolling(n, min_periods=n // 2).min().shift(1)
    state = pd.DataFrame(np.nan, index=panel.close.index, columns=panel.close.columns)
    state[panel.close > hi] = 1.0
    state[panel.close < lo] = 0.0
    sig = state.ffill().fillna(0.0)
    return _vt(_basket_signal(panel, sig, p["basket"], True), panel, p.get("vt", 0))


def _lowvol(p, panel):
    return _vt(_hold(_ls(-panel.vol(p["k"]), panel.universe(p["uni"]), p["q"]), p["rebal"]), panel, p.get("vt", 0))


def _bab(p, panel):
    k = p["k"]
    btc = panel.close["BTCUSDT"].pct_change(fill_method=None) if "BTCUSDT" in panel.close else panel.close.mean(axis=1).pct_change(fill_method=None)
    r = panel.close.pct_change(fill_method=None)
    beta = r.rolling(k, min_periods=k // 2).cov(btc).div(btc.rolling(k, min_periods=k // 2).var(), axis=0)
    return _vt(_hold(_ls(-beta, panel.universe(p["uni"]), p["q"]), p["rebal"]), panel, p.get("vt", 0))


def _funding_carry(p, panel):
    return _vt(_hold(_ls(-panel.fund(p["k"]), panel.universe(p["uni"]), p["q"]), p["rebal"]), panel, p.get("vt", 0))


def _funding_fade(p, panel):
    f = panel.fund(p["k"])
    z = (f - f.rolling(90, min_periods=30).mean()) / f.rolling(90, min_periods=30).std()
    uni = panel.universe(p["uni"])
    ev = pd.DataFrame(0.0, index=z.index, columns=z.columns)
    ev[(z > p["z"]) & uni] = -1.0              # trängsel i long: short
    ev[(z < -p["z"]) & uni] = 1.0
    held = _hold_events(ev, p["hold"])
    return held.div(held.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


def _pairs(p, panel):
    uni = panel.universe(30)
    liquid = list(panel.dvol.where(uni).median().sort_values(ascending=False).dropna().index[:14])
    lc = np.log(panel.close[liquid])
    ret = lc.diff()
    corr = ret.loc[ret.index < ret.index[min(len(ret) - 1, 250)]].corr()
    pairs, used = [], set()
    for _c, a, b in sorted(((corr.loc[a, b], a, b) for i, a in enumerate(liquid) for b in liquid[i + 1:]), reverse=True):
        if a in used or b in used:
            continue
        pairs.append((a, b)); used |= {a, b}
        if len(pairs) >= p["npairs"]:
            break
    W = pd.DataFrame(0.0, index=panel.close.index, columns=panel.close.columns)
    lb = p["lb"]
    for a, b in pairs:
        spread = lc[a] - lc[b]
        z = (spread - spread.rolling(lb, min_periods=lb // 2).mean()) / spread.rolling(lb, min_periods=lb // 2).std()
        pos = pd.Series(np.nan, index=z.index)
        pos[z > p["z_in"]] = -1.0
        pos[z < -p["z_in"]] = 1.0
        pos[z.abs() <= p["z_out"]] = 0.0
        pos = pos.ffill().fillna(0.0)
        W[a] += pos / (2 * len(pairs))
        W[b] -= pos / (2 * len(pairs))
    return W


def _vol_regime(p, panel):
    base = {"xs_mom": lambda: _xs_mom({"k": p["k"], "skip": 0, "q": 0.2, "rebal": 7, "uni": p["uni"], "vt": 0}, panel),
            "ts_mom": lambda: _ts_mom({"k": p["k"], "long_only": True, "vt": 0, "uni": 10}, panel)}[p["base"]]()
    btc = panel.close["BTCUSDT"] if "BTCUSDT" in panel.close else panel.close.mean(axis=1)
    v = btc.pct_change(fill_method=None).rolling(p["k_vol"], min_periods=p["k_vol"] // 2).std()
    thr = v.expanding(min_periods=60).median()
    on = (v < thr) if p["mode"] == "low" else (v >= thr)
    return base.mul(on.astype(float), axis=0)


def _vol_shock(p, panel):
    uni = panel.universe(p["uni"])
    dv = np.log(panel.dvol.where(uni))
    z = (dv - dv.rolling(30, min_periods=15).mean()) / dv.rolling(30, min_periods=15).std()
    day = panel.ret(1)
    direction = np.sign(day) * (1.0 if p["mode"] == "follow" else -1.0)
    ev = direction.where(z > p["z"], 0.0).where(uni, 0.0).fillna(0.0)
    held = _hold_events(ev, p["hold"])
    return held.div(held.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)


def _mtf_trend(p, panel):
    agree = sum(np.sign(panel.ret(k)) for k in p["ks"]) / len(p["ks"])
    sig = (agree >= 0.99).astype(float)
    return _vt(_basket_signal(panel, sig, p["basket"], True), panel, p.get("vt", 0))


def _ensemble(p, panel):
    uni = panel.universe(30)
    parts = []
    for m in p["members"]:
        if m == "xs_mom": parts.append(panel.ret(30))
        elif m == "xs_rev": parts.append(-panel.ret(3))
        elif m == "funding_carry": parts.append(-panel.fund(7))
        elif m == "lowvol": parts.append(-panel.vol(40))
        elif m == "bab":
            btc = panel.close["BTCUSDT"].pct_change(fill_method=None) if "BTCUSDT" in panel.close else panel.close.mean(axis=1).pct_change(fill_method=None)
            parts.append(-panel.close.pct_change(fill_method=None).rolling(90, min_periods=45).cov(btc).div(btc.rolling(90, min_periods=45).var(), axis=0))
    return _hold(_ls(_rank_mix(parts, uni), uni, p["q"]), p["rebal"])


def _placebo(p, panel):
    rng = np.random.default_rng(p["seed"])
    score = pd.DataFrame(rng.random(panel.close.shape), index=panel.close.index, columns=panel.close.columns)
    return _hold(_ls(score, panel.universe(p["uni"]), p["q"]), p["rebal"])


BUILDERS = {"xs_mom": _xs_mom, "xs_rev": _xs_rev, "ts_mom": _ts_mom, "trend_ma": _trend_ma, "donchian": _donchian, "lowvol": _lowvol, "bab": _bab,
            "funding_carry": _funding_carry, "funding_fade": _funding_fade, "pairs": _pairs, "vol_regime": _vol_regime, "vol_shock": _vol_shock,
            "mtf_trend": _mtf_trend, "ensemble_rank": _ensemble, "placebo": _placebo}


class ModelUnavailable(RuntimeError):
    pass


def build(spec: dict, panel: Panel) -> pd.DataFrame:
    fam = spec["family"]
    if fam == "ml_xs":
        from .ml import build_ml
        return build_ml(spec["params"], panel)
    return BUILDERS[fam](spec["params"], panel)


# ---------------------------------------------------------------- grannar och mutationer (Builder)
def neighbors(spec: dict, limit: int = 6) -> list[dict]:
    """Närliggande parametrar (ett steg i gridet, ett i taget). Används för parameterkänslighet och räknas som försök."""
    grid = GRID.get(spec["family"], {})
    out = []
    for name, vals in grid.items():
        cur = spec["params"].get(name)
        if cur not in vals or len(vals) < 2 or name in ("seed", "model", "base", "mode", "members", "long_only"):
            continue
        i = vals.index(cur)
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                out.append(make_spec(spec["family"], {**spec["params"], name: vals[j]}, parent=spec["key"], note=f"granne {name}={vals[j]}"))
    return out[:limit] if len(out) <= limit else [out[i] for i in np.linspace(0, len(out) - 1, limit).astype(int)]


def _step(spec, name, direction):
    vals = GRID[spec["family"]].get(name, [])
    cur = spec["params"].get(name)
    if cur not in vals:
        return None
    j = vals.index(cur) + direction
    return vals[j] if 0 <= j < len(vals) else None


def mutate(spec: dict, objection: str) -> dict | None:
    """Builders svar på en invändning: en bestämd, billig ändring som adresserar just den. None = ingen rimlig ändring finns."""
    fam, p = spec["family"], dict(spec["params"])
    changed = {}
    if objection in ("cost_fragile", "high_turnover"):
        if "rebal" in p and (v := _step(spec, "rebal", +1)): changed["rebal"] = v
        elif "k" in p and (v := _step(spec, "k", +1)): changed["k"] = v
        elif "hold" in p and (v := _step(spec, "hold", +1)): changed["hold"] = v
        elif "h" in p and (v := _step(spec, "h", +1)): changed["h"] = v
    elif objection in ("tail_risk", "drawdown"):
        if "vt" in GRID.get(fam, {}) and not p.get("vt"): changed["vt"] = 0.15 if fam in ("ts_mom", "trend_ma", "donchian", "mtf_trend") else 0.2
        elif "q" in p and (v := _step(spec, "q", +1)): changed["q"] = v
    elif objection == "param_unstable":
        if "k" in p and (v := _step(spec, "k", +1)): changed["k"] = v
        elif "q" in p and (v := _step(spec, "q", +1)): changed["q"] = v
    elif objection == "concentration":
        if "uni" in p and (v := _step(spec, "uni", +1)): changed["uni"] = v
        elif "q" in p and (v := _step(spec, "q", +1)): changed["q"] = v
    elif objection == "ml_overfit":
        if fam == "ml_xs" and p.get("model") != "ridge": changed["model"] = "ridge"
    elif objection == "regime_fragile":
        if fam in ("xs_mom", "ts_mom"):
            return make_spec("vol_regime", {"base": fam, "k_vol": 20, "mode": "low", "k": p.get("k", 30) if p.get("k", 30) in (30, 60) else 30, "uni": 30}, parent=spec["key"], note=f"mutation: {objection}")
    if not changed:
        return None
    return make_spec(fam, {**p, **changed}, parent=spec["key"], note=f"mutation: {objection} {changed}")


# ---------------------------------------------------------------- idéer
def sample_ideas(n: int, seed: int, families: list[str] | None = None, skip_keys: set[str] | None = None) -> list[dict]:
    """Många rimliga idéer brett över familjer. Slumpar parametrar ur gridet och undviker dubbletter."""
    rng = np.random.default_rng(seed)
    fams = [f for f in (families or list(GRID)) if f != "placebo"]
    out, seen = [], set(skip_keys or ())
    tries = 0
    while len(out) < n and tries < n * 40:
        tries += 1
        fam = fams[len(out) % len(fams)] if tries % 3 else str(rng.choice(fams))
        params = {k: (v[int(rng.integers(len(v)))] if not isinstance(v[0], list) else v[int(rng.integers(len(v)))]) for k, v in GRID[fam].items()}
        spec = make_spec(fam, params)
        if spec["key"] in seen:
            continue
        seen.add(spec["key"])
        out.append(spec)
    return out
