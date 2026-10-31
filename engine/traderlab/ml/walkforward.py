"""Walk-forward: modellen tränas om med jämna mellanrum och förutsäger bara framåt.

Vid förutsägelse för stapel t används bara exempel vars etikett var känd vid stängningen av t.
Omträningspunkterna räknas från historikens början, så samma tidpunkt får samma modell oavsett hur
mycket framtida data som finns. Därför klarar ML-strategin check_no_lookahead.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from .features import build_features
from .labels import direction, label_end
from .models import make_model


def walk_forward_proba(bars: pd.DataFrame, horizon: int = 1, model: str = "logistic", min_train: int = 500,
                       step: int = 100, max_train: int | None = None, seed: int = 0,
                       features: Callable[[pd.DataFrame], pd.DataFrame] = build_features) -> pd.Series:
    """Sannolikhet att nästa affär går upp, utanför träningsdatan. NaN innan första modellen finns."""
    X = features(bars)
    y = direction(bars, horizon)
    known_at = label_end(bars, horizon)
    n = len(bars)
    proba = pd.Series(np.nan, index=bars.index, name="proba_up")
    pos_index = {t: i for i, t in enumerate(bars.index)}
    known_pos = known_at.map(lambda t: pos_index.get(t, np.nan) if pd.notna(t) else np.nan).to_numpy()
    usable = X.notna().all(axis=1).to_numpy() | (model == "gbm")
    for start in range(min_train, n, step):
        decision = start - 1  # modellen byggs vid stängningen av stapel start-1
        # Etiketten för i är känd när stapel known_pos[i] har stängt, alltså om known_pos[i] <= decision.
        train = np.where((known_pos <= decision) & usable & y.notna().to_numpy())[0]
        if max_train is not None:
            train = train[-max_train:]
        if len(train) < 50 or len(np.unique(y.iloc[train])) < 2:
            continue
        m = make_model(model, seed)
        m.fit(X.iloc[train], y.iloc[train])
        stop = min(n, start + step)
        rows = np.arange(start, stop)
        ok = rows[usable[rows]]
        if len(ok):
            proba.iloc[ok] = m.predict_proba(X.iloc[ok])[:, 1]
    return proba


def ml_strategy(horizon: int = 1, model: str = "logistic", band: float = 0.02, allow_short: bool = True,
                **kwargs) -> Callable[[pd.DataFrame], pd.Series]:
    """Strategi: long om sannolikheten > 0,5 + band, short om < 0,5 − band, annars platt."""
    def strategy(bars: pd.DataFrame) -> pd.Series:
        p = walk_forward_proba(bars, horizon=horizon, model=model, **kwargs)
        pos = np.where(p > 0.5 + band, 1.0, np.where(p < 0.5 - band, -1.0 if allow_short else 0.0, 0.0))
        return pd.Series(pos, index=bars.index).where(p.notna(), 0.0)
    return strategy
