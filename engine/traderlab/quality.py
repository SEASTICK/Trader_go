"""Kvalitetskontroller enligt skillen hamta-data.

Rapporterar siffror. Lagar ingenting och fyller aldrig luckor: det är ett beslut för människan.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .bars import COLUMNS, interval_delta


@dataclass
class QualityReport:
    rows: int
    first: str | None
    last: str | None
    expected_rows: int
    missing_bars: int
    largest_gaps: list[tuple[str, str, int]] = field(default_factory=list)  # (från, till, antal saknade)
    duplicates: int = 0
    not_increasing: int = 0
    misaligned: int = 0
    bad_ohlc: int = 0
    non_positive_price: int = 0
    negative_volume: int = 0
    outliers: list[tuple[str, float]] = field(default_factory=list)  # (tid, logavkastning)
    stale_runs: list[tuple[str, int]] = field(default_factory=list)  # (start, längd)
    timezone_ok: bool = True
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_markdown(self, title: str = "Kvalitetskontroll") -> str:
        lines = [f"### {title}", "", f"- Rader: {self.rows} (förväntat {self.expected_rows})",
                 f"- Period: {self.first} till {self.last}", f"- Saknade staplar: {self.missing_bars}",
                 f"- Dubbletter: {self.duplicates}", f"- Ej stigande tid: {self.not_increasing}",
                 f"- Fel tidsjustering: {self.misaligned}", f"- Felaktiga OHLC: {self.bad_ohlc}",
                 f"- Pris noll eller negativt: {self.non_positive_price}", f"- Negativ volym: {self.negative_volume}",
                 f"- Utstickare: {len(self.outliers)}", f"- Stillastående pris: {len(self.stale_runs)} serier",
                 f"- Tidszon UTC: {'ja' if self.timezone_ok else 'NEJ'}", ""]
        if self.largest_gaps:
            lines.append("Största luckor:")
            lines += [f"- {a} → {b}: {n} staplar" for a, b, n in self.largest_gaps]
            lines.append("")
        lines.append("Resultat: **OK**" if self.ok else "Resultat: **PROBLEM**: " + "; ".join(self.problems))
        return "\n".join(lines)


def check(bars: pd.DataFrame, interval: str, outlier_k: float = 12.0, stale_min: int = 6,
          max_gap_list: int = 5) -> QualityReport:
    """Kör alla kontroller. outlier_k: antal robusta standardavvikelser (MAD) för en utstickare."""
    step = interval_delta(interval)
    idx = bars.index
    missing_cols = [c for c in COLUMNS if c not in bars.columns]
    if missing_cols:
        raise ValueError(f"Kolumner saknas: {missing_cols}")

    tz_ok = isinstance(idx, pd.DatetimeIndex) and idx.tz is not None and str(idx.tz) == "UTC"
    rep = QualityReport(rows=len(bars), first=str(idx[0]) if len(idx) else None,
                        last=str(idx[-1]) if len(idx) else None, expected_rows=0, missing_bars=0,
                        timezone_ok=tz_ok)
    if not tz_ok:
        rep.problems.append("tidsstämplar är inte UTC")
    if len(bars) == 0:
        rep.problems.append("ingen data")
        return rep

    rep.duplicates = int(idx.duplicated().sum())
    diffs = pd.Series(idx[1:] - idx[:-1])
    rep.not_increasing = int((diffs <= pd.Timedelta(0)).sum())

    uniq = idx[~idx.duplicated()].sort_values()
    rep.expected_rows = int((uniq[-1] - uniq[0]) / step) + 1
    rep.missing_bars = max(0, rep.expected_rows - len(uniq))
    gaps = []
    for a, b in zip(uniq[:-1], uniq[1:]):
        n_missing = int((b - a) / step) - 1
        if n_missing > 0:
            gaps.append((str(a), str(b), n_missing))
    rep.largest_gaps = sorted(gaps, key=lambda g: -g[2])[:max_gap_list]

    if tz_ok:
        epoch = pd.Timestamp("1970-01-01", tz="UTC")
        rep.misaligned = int(sum(((t - epoch) % step) != pd.Timedelta(0) for t in uniq))

    o, h, l, c, v = (bars[k].to_numpy(dtype=float) for k in COLUMNS)
    rep.bad_ohlc = int(np.sum((l > np.minimum(o, c)) | (h < np.maximum(o, c)) | (l > h)))
    rep.non_positive_price = int(np.sum((o <= 0) | (h <= 0) | (l <= 0) | (c <= 0)))
    rep.negative_volume = int(np.sum(v < 0))

    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.diff(np.log(np.where(c > 0, c, np.nan)))
    finite = lr[np.isfinite(lr)]
    if finite.size > 10:
        med = np.median(finite)
        mad = np.median(np.abs(finite - med)) * 1.4826
        if mad > 0:
            hits = np.where(np.abs(lr - med) > outlier_k * mad)[0]
            rep.outliers = [(str(idx[i + 1]), float(lr[i])) for i in hits]

    run_start, run_len = 0, 1
    for i in range(1, len(c) + 1):
        same = i < len(c) and c[i] == c[i - 1] and v[i] == 0
        if same:
            run_len += 1
        else:
            if run_len >= stale_min:
                rep.stale_runs.append((str(idx[run_start]), run_len))
            run_start, run_len = i, 1

    if rep.duplicates: rep.problems.append(f"{rep.duplicates} dubbletter")
    if rep.not_increasing: rep.problems.append(f"{rep.not_increasing} tider som inte stiger")
    if rep.missing_bars: rep.problems.append(f"{rep.missing_bars} saknade staplar")
    if rep.misaligned: rep.problems.append(f"{rep.misaligned} staplar på fel tid")
    if rep.bad_ohlc: rep.problems.append(f"{rep.bad_ohlc} felaktiga OHLC")
    if rep.non_positive_price: rep.problems.append(f"{rep.non_positive_price} priser noll eller negativa")
    if rep.negative_volume: rep.problems.append(f"{rep.negative_volume} negativa volymer")
    if rep.outliers: rep.problems.append(f"{len(rep.outliers)} utstickare att kontrollera mot annan källa")
    if rep.stale_runs: rep.problems.append(f"{len(rep.stale_runs)} serier med stillastående pris")
    return rep
