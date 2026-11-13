"""ML-agentens modeller: tvärsnittsprognos av framtida avkastning med walk-forward (omträning i takt, bara historia, städade etiketter).

Modeller: ridge, random forest, LightGBM (regression och sannolikhet), MLP och ensemble. Saknas ett bibliotek hoppas modellen över.
Neurala nät utöver sklearns MLP (LSTM/GRU/TCN) kräver torch och är inte installerat; ML-agenten redovisar det som en känd begränsning.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import Panel
from .strategies import ModelUnavailable, _hold, _ls

FEATURES = ["r1", "r3", "r7", "r14", "r30", "r60", "v10", "v30", "rv30", "dv", "f3", "f7", "f30", "rb7", "rb30", "hi60"]


def _rank(df: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    return df.where(mask).rank(axis=1, pct=True) - 0.5


def feature_cube(panel: Panel, uni: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """(dagar × symboler × features), alla tvärsnittsrankade per dag och bara med data till och med dag t."""
    btc = panel.ret(7)["BTCUSDT"] if "BTCUSDT" in panel.close else panel.ret(7).mean(axis=1)
    btc30 = panel.ret(30)["BTCUSDT"] if "BTCUSDT" in panel.close else panel.ret(30).mean(axis=1)
    ldv = np.log(panel.dvol.replace(0, np.nan))
    f = {
        "r1": panel.ret(1), "r3": panel.ret(3), "r7": panel.ret(7), "r14": panel.ret(14), "r30": panel.ret(30), "r60": panel.ret(60),
        "v10": panel.vol(10), "v30": panel.vol(30), "rv30": panel.ret(30) / panel.vol(30), "dv": ldv - ldv.rolling(60, min_periods=30).mean(),
        "f3": panel.fund(3), "f7": panel.fund(7), "f30": panel.fund(30),
        "rb7": panel.ret(7).sub(btc, axis=0), "rb30": panel.ret(30).sub(btc30, axis=0),
        "hi60": panel.close / panel.close.rolling(60, min_periods=30).max(),
    }
    cube = np.stack([_rank(f[n], uni).values for n in FEATURES], axis=2)
    return cube, FEATURES


def _model(name: str, seed: int = 0):
    try:
        if name == "ridge":
            from sklearn.linear_model import Ridge
            return Ridge(alpha=50.0)
        if name == "rf":
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(n_estimators=60, max_depth=5, min_samples_leaf=300, max_features=0.6, n_jobs=1, random_state=seed)
        if name == "mlp":
            from sklearn.neural_network import MLPRegressor
            return MLPRegressor(hidden_layer_sizes=(32, 16), alpha=1e-2, early_stopping=True, max_iter=60, random_state=seed)
        if name in ("lgbm", "lgbm_prob"):
            import lightgbm as lgb
            kw = dict(n_estimators=150, learning_rate=0.03, num_leaves=15, min_child_samples=300, subsample=0.8, subsample_freq=1,
                      colsample_bytree=0.8, reg_lambda=5.0, n_jobs=1, verbose=-1, random_state=seed)
            return lgb.LGBMClassifier(**kw) if name == "lgbm_prob" else lgb.LGBMRegressor(**kw)
    except ImportError as exc:
        raise ModelUnavailable(f"{name}: {exc}") from exc
    raise ValueError(name)


def _fit_predict(name: str, Xtr, ytr, Xte, seed=0):
    if name == "ens":
        preds = [pd.Series(_fit_predict(m, Xtr, ytr, Xte, seed)).rank(pct=True).values for m in ("ridge", "lgbm", "mlp")]
        return np.mean(preds, axis=0)
    m = _model(name, seed)
    if name == "lgbm_prob":
        thr = np.quantile(ytr, 2 / 3)
        m.fit(Xtr, (ytr >= thr).astype(int))
        return m.predict_proba(Xte)[:, 1]
    m.fit(Xtr, ytr)
    return m.predict(Xte)


def build_ml(p: dict, panel: Panel) -> pd.DataFrame:
    """Walk-forward: modellen tränas om var `retrain`:e dag på rader vars etikett är känd före omträningen (städning h+2 dagar)."""
    h, model, q, retrain = int(p["h"]), p["model"], p["q"], int(p["retrain"])
    uni = panel.universe(p["uni"])
    cube, _ = feature_cube(panel, uni)
    T, N, _F = cube.shape
    open_ = panel.open
    fwdh = open_.shift(-(1 + h)) / open_.shift(-1) - 1.0                      # etikett för beslut på dag t
    y = (fwdh.where(uni).rank(axis=1, pct=True) - 0.5).values
    ok = uni.values & np.isfinite(cube).all(axis=2)
    score = np.full((T, N), np.nan)
    first = int(np.argmax(ok.sum(axis=1) >= 8)) + 220                          # minst ~220 dagar historia
    for start in range(first, T, retrain):
        last_label = start - (h + 2)                                           # etiketten för dag t är känd först vid öppning t+1+h
        lo = max(0, last_label - 730)
        rows = [(t, np.where(ok[t] & np.isfinite(y[t]))[0]) for t in range(lo, last_label + 1)]
        tr_t = np.concatenate([[t] * len(js) for t, js in rows if len(js)]) if rows else np.array([])
        if tr_t.size < 2000:
            continue
        tr_j = np.concatenate([js for _t, js in rows if len(js)])
        Xtr, ytr = cube[tr_t.astype(int), tr_j], y[tr_t.astype(int), tr_j]
        if len(ytr) > 60000:
            sel = np.random.default_rng(0).choice(len(ytr), 60000, replace=False)
            Xtr, ytr = Xtr[sel], ytr[sel]
        end = min(T, start + retrain)
        te_t, te_j = np.where(ok[start:end])
        if not len(te_t):
            continue
        pred = _fit_predict(model, Xtr, ytr, cube[start + te_t, te_j])
        score[start + te_t, te_j] = pred
    sc = pd.DataFrame(score, index=panel.close.index, columns=panel.close.columns)
    return _hold(_ls(sc, uni & sc.notna(), q), h)
