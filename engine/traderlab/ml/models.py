"""Modeller. Fast frö överallt, så samma data ger samma svar."""
from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def make_model(kind: str = "logistic", seed: int = 0):
    if kind == "logistic":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(C=0.1, max_iter=500))
    if kind == "gbm":
        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=150,
                                              l2_regularization=1.0, early_stopping=False, random_state=seed)
    raise ValueError(f"Okänd modell: {kind}")
