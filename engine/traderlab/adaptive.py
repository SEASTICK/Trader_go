"""Strategiväljaren för Fas 2 (H-0013), enligt research/fas2-protokoll.md. Ändras inte efter registreringen.

En spelbok tilldelar varje marknadsläge en kandidat: ema_adx_trend 1.0.0, bb_rsi_reversion 1.0.0 eller platt, alltid
med strategiernas standardparametrar (strategies.rules.SPECS, oförändrade). Väljaren gör om kandidatens signal till
en målposition med protokollets handelsregler:

- Bara med trenden: long bara i upp-lägen, short bara i ned-lägen. En signal mot trenden blir platt.
- `okänt` är alltid platt.
- Byts läget, eller får läget en annan kandidat (till exempel en ny spelbok vid en fönstergräns), stängs positionen
  vid nästa stapels öppning. En gammal affär tas aldrig upp igen: kandidaten får bara öppna en **ny** affär, när
  dess signal går från platt eller motsatt riktning till den tillåtna riktningen, tidigast på stapeln efter bytet.
- Beslut på stängd stapel, fyllning vid nästa öppning (backtest.run). Kandidatens ATR-stop sätts vid inträdet.

Tidsregeln: beslutet vid stapel i:s stängning gäller stapel i+1. Därför används läget och spelboken för stapel i+1,
alltså läget för kalenderdagen före stapel i+1:s dag (regime.per_bar). Det är känt vid stapel i:s stängning: den
sista stapeln på en dag stänger samtidigt som dagen.

Här finns ingen träning eller urvalsregel (walk-forward); spelböckerna ges in färdiga.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import regime
from .strategies.rules import SPECS

CONTRACT_VERSION = "h0013-adaptive/1.0.0"
FLAT = "platt"
# Kandidaterna och deras låsta versioner. Platt har ingen strategi.
CANDIDATES: dict[str, str | None] = {"ema_adx_trend": "1.0.0", "bb_rsi_reversion": "1.0.0", FLAT: None}
NO_PLAYBOOK = "ingen spelbok"


def _direction(label: str) -> int:
    """Tillåten riktning i ett läge: +1 i upp-lägen, -1 i ned-lägen, 0 för `okänt`."""
    return 1 if label.startswith("upp/") else -1 if label.startswith("ned/") else 0


@dataclass(frozen=True)
class Playbook:
    """Ett val per marknadsläge. `okänt` ingår inte; det är alltid platt."""
    choices: tuple[tuple[str, str], ...]

    @classmethod
    def of(cls, choices: Mapping[str, str]) -> Playbook:
        if set(choices) != set(regime.LABELS):
            raise ValueError(f"En spelbok behöver exakt ett val för var och ett av {', '.join(regime.LABELS)}")
        bad = {k: v for k, v in choices.items() if v not in CANDIDATES}
        if bad:
            raise ValueError(f"Okända kandidater {bad}. Tillåtna: {', '.join(CANDIDATES)}")
        return cls(tuple((label, choices[label]) for label in regime.LABELS))

    def candidate(self, label: str) -> str:
        return dict(self.choices).get(label, FLAT)

    def to_dict(self) -> dict:
        return {"contract": CONTRACT_VERSION, "choices": dict(self.choices),
                "candidates": {k: CANDIDATES[k] for k in sorted(set(dict(self.choices).values()))}}

    @classmethod
    def from_dict(cls, data: Mapping) -> Playbook:
        if data.get("contract") != CONTRACT_VERSION:
            raise ValueError(f"Fel kontraktsversion {data.get('contract')!r}, väntade {CONTRACT_VERSION}")
        for name, version in data.get("candidates", {}).items():
            if CANDIDATES.get(name, "saknas") != version:
                raise ValueError(f"Kandidaten {name} har version {version}, låst version är {CANDIDATES.get(name)}")
        return cls.of(data["choices"])

    @property
    def id(self) -> str:
        """Stabilt id för spelboken, till exempel för att räkna försök och spara resultat."""
        h = hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:8]
        return f"spelbok#{h}"


def all_playbooks() -> list[Playbook]:
    """Alla 3⁴ = 81 möjliga spelböcker, i fast ordning."""
    out = [{}]
    for label in regime.LABELS:
        out = [{**p, label: c} for p in out for c in CANDIDATES]
    return [Playbook.of(p) for p in out]


Schedule = Playbook | Sequence[tuple[str | pd.Timestamp, Playbook]]


def _schedule(schedule: Schedule) -> list[tuple[pd.Timestamp | None, Playbook]]:
    """En spelbok (gäller alla staplar), eller spelböcker med starttid (fönstergränser). En spelbok med starttid
    gäller staplar från och med den tiden; staplar före första starttiden är platta."""
    if isinstance(schedule, Playbook):
        return [(None, schedule)]
    items = [(pd.Timestamp(t), p) for t, p in schedule]
    for t, p in items:
        if t.tz is None or t.utcoffset() != pd.Timedelta(0):
            raise ValueError("Spelbokens starttid måste vara i UTC")
        if not isinstance(p, Playbook):
            raise ValueError("Varje fönster behöver en Playbook")
    if not items or any(a[0] >= b[0] for a, b in zip(items, items[1:])):
        raise ValueError("Spelböckerna måste ha stigande starttider")
    return items


@dataclass(frozen=True)
class AdaptiveSignals:
    """Väljarens utdata per stapel. Allt avser beslutet vid stapelns stängning, som gäller nästa stapel."""
    target: pd.Series          # målposition -1, 0 eller 1 (backtest.run fyller vid nästa öppning)
    stop_distance: pd.Series   # vald kandidats ATR-stop som prisavstånd, används vid inträdet
    regime: pd.Series          # läget för nästa stapel
    candidate: pd.Series       # vald kandidat i det läget
    playbook: pd.Series        # spelbokens id, eller "ingen spelbok"
    switch: pd.Series          # True när läge eller kandidat byts: positionen stängs vid nästa öppning
    contract: str = CONTRACT_VERSION
    candidate_runs: tuple[tuple[str, str], ...] = ()


def candidate_signals(bars: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Kandidaternas egna målpositioner och stop-avstånd med standardparametrar (oförändrade strategier)."""
    out = {}
    for name in CANDIDATES:
        if name == FLAT:
            continue
        spec = SPECS[name]
        if spec.version != CANDIDATES[name]:
            raise ValueError(f"{name} är version {spec.version}, H-0013 kräver {CANDIDATES[name]}")
        sig = spec.signals(bars)
        stop = sig.stop_distance if sig.stop_distance is not None else pd.Series(np.nan, index=bars.index)
        out[name] = (sig.target.reindex(bars.index).fillna(0.0).to_numpy(float),
                     stop.reindex(bars.index).to_numpy(float))
    return out


def signals(bars: pd.DataFrame, schedule: Schedule, interval: str = "4h",
            effective: pd.Series | None = None) -> AdaptiveSignals:
    """Målposition per stapel för en spelbok eller en följd av spelböcker (fönstergränser).

    `effective` är det gällande dagsläget (regime.daily). Utan det räknas läget från `bars`.
    """
    step = regime.validate(bars, interval)
    effective = regime.daily(bars, interval) if effective is None else effective
    nxt = bars.index + step
    labels = regime.per_bar(pd.DataFrame(index=nxt), effective, interval).to_numpy(dtype=object)
    plan = _schedule(schedule)
    if plan[0][0] is None:
        which = np.zeros(len(bars), dtype=int)
    else:
        which = pd.DatetimeIndex([t for t, _ in plan]).searchsorted(nxt, side="right") - 1
    cand = candidate_signals(bars)

    n = len(bars)
    target = np.zeros(n)
    stop = np.full(n, np.nan)
    chosen = np.empty(n, dtype=object)
    book = np.empty(n, dtype=object)
    switch = np.zeros(n, dtype=bool)
    context = None
    pos = 0.0
    for i in range(n):
        label = labels[i]
        if which[i] < 0:
            name, book[i] = FLAT, NO_PLAYBOOK
        else:
            playbook = plan[which[i]][1]
            name, book[i] = playbook.candidate(label), playbook.id  # `okänt` finns inte i spelboken: platt
        chosen[i] = name
        here = (label, name)
        if here != context:
            switch[i] = context is not None
            context, pos = here, 0.0
            continue  # stäng vid nästa öppning; ett nytt inträde tidigast på nästa stapel
        side = _direction(label)
        if name == FLAT or side == 0:
            continue
        sig, sd = cand[name]
        if pos == 0.0:
            if sig[i] == side and sig[i - 1] != side:  # ny inträdessignal i tillåten riktning
                pos = float(side)
        elif sig[i] != side:  # kandidaten går ur eller vänder: ut
            pos = 0.0
        target[i] = pos
        stop[i] = sd[i]
    runs = tuple((k, SPECS[k].run_id({})) for k in CANDIDATES if k != FLAT)
    idx = bars.index
    return AdaptiveSignals(
        target=pd.Series(target, index=idx, name="target"),
        stop_distance=pd.Series(stop, index=idx, name="stop_distance"),
        regime=pd.Series(labels, index=idx, name="regime"),
        candidate=pd.Series(chosen, index=idx, name="candidate"),
        playbook=pd.Series(book, index=idx, name="playbook"),
        switch=pd.Series(switch, index=idx, name="switch"),
        candidate_runs=runs,
    )
