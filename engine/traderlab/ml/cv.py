"""Gallrad korsvalidering med embargo (López de Prado, Advances in Financial Machine Learning, kap. 7).

Vanlig k-fold läcker information i tidsserier: ett träningsexempel vars etikett sträcker sig in i
testperioden har sett testdata. Gallringen tar bort sådana exempel, och embargot tar också bort
exempel strax efter testperioden.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd


class PurgedKFold:
    def __init__(self, n_splits: int = 5, embargo: float = 0.01):
        if n_splits < 2:
            raise ValueError("Minst två delar.")
        self.n_splits = n_splits
        self.embargo = embargo

    def split(self, label_end: pd.Series) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        """label_end: när varje exempels etikett blir känd (samma index som exemplen, i tidsordning)."""
        t0 = label_end.index
        t1 = label_end.fillna(t0[-1]).to_numpy()
        n = len(t0)
        emb = int(np.ceil(n * self.embargo))
        bounds = np.array_split(np.arange(n), self.n_splits)
        t0v = t0.to_numpy()
        for test in bounds:
            start, stop = test[0], test[-1]
            test_t0, test_t1 = t0v[start], t1[test].max()
            # Gallra: träningsexempel vars intervall [t0, t1] överlappar testets [test_t0, test_t1].
            overlap = (t0v <= test_t1) & (t1 >= test_t0)
            keep = ~overlap
            # Embargo efter testperioden.
            keep[stop + 1: min(n, stop + 1 + emb)] = False
            keep[test] = False
            yield np.where(keep)[0], test
