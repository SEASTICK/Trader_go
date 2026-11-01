"""Pappershandel framåt (skillen papper-framat). Inga riktiga order, inga börskonton, inga nycklar.

- freeze(): fryser en strategi som har beslutet READY_FOR_PAPER. Specifikationen sparas med kontrollsumma
  och commit. En ändring därefter är en ny strategi (regel 3 i CLAUDE.md), och step() vägrar fortsätta.
- step(): bearbetar nya stängda staplar. Beslut vid stängning, fyllning vid nästa öppning, samma kostnader
  som i backtestet. Händelser läggs till sist i log.jsonl och ändras aldrig.
- status(): sammanfattning från loggen.

Pappersresultatet på samma staplar ska bli exakt samma som backtest.run (testas).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ..costs import CostModel
from ..registry import require_decision
from ..strategies.registry import build

PAPER = Path("paper")


class TamperedError(RuntimeError):
    pass


def _canonical(spec: dict) -> str:
    return json.dumps(spec, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _sha(spec: dict) -> str:
    return hashlib.sha256(_canonical(spec).encode()).hexdigest()


def folder(repo: Path, paper_id: str) -> Path:
    return repo / PAPER / paper_id


def freeze(repo: Path, paper_id: str, hypothesis_id: str, spec: dict, planned_trades: int, stop_rule: str) -> Path:
    """spec: {"market", "symbol", "interval", "strategy": {"name", "params"}, "costs": {...}, "leverage"}.

    planned_trades och stop_rule bestäms i förväg (papper-framat, punkt 3 och 4).
    """
    commit = require_decision(hypothesis_id, repo, "READY_FOR_PAPER")
    d = folder(repo, paper_id)
    if d.exists():
        raise FileExistsError(f"{d} finns redan. En ny frysning kräver ett nytt id.")
    d.mkdir(parents=True)
    frozen = {"paper_id": paper_id, "hypothesis_id": hypothesis_id, "registry_commit": commit,
              "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "planned_trades": planned_trades, "stop_rule": stop_rule, "spec": spec}
    frozen["sha256"] = _sha(spec)
    (d / "strategy.json").write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (d / "log.jsonl").touch()
    return d


def _load(repo: Path, paper_id: str) -> dict:
    d = folder(repo, paper_id)
    frozen = json.loads((d / "strategy.json").read_text(encoding="utf-8"))
    if _sha(frozen["spec"]) != frozen["sha256"]:
        raise TamperedError("Den frysta strategin har ändrats. En ändring är en ny strategi: frys med nytt id.")
    return frozen


def _events(repo: Path, paper_id: str) -> list[dict]:
    p = folder(repo, paper_id) / "log.jsonl"
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _append(repo: Path, paper_id: str, events: list[dict]) -> None:
    with (folder(repo, paper_id) / "log.jsonl").open("a", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


@dataclass
class State:
    equity: float = 1.0
    pos: float = 0.0
    qty: float = 0.0
    last_bar: str | None = None
    pending: float | None = None  # målposition beslutad vid senaste stängning, fylls vid nästa öppning


def _replay(events: list[dict]) -> State:
    s = State()
    for e in events:
        if e["type"] == "bar":
            s.equity, s.pos, s.qty, s.last_bar, s.pending = e["equity"], e["pos"], e["qty"], e["time"], e["decision"]
    return s


def step(repo: Path, paper_id: str, bars: pd.DataFrame) -> int:
    """Bearbetar alla stängda staplar efter den senast loggade. Returnerar antal nya staplar.

    `bars` ska bara innehålla stängda staplar. Körs flera gånger utan dubbletter.
    """
    frozen = _load(repo, paper_id)
    spec = frozen["spec"]
    if spec.get("leverage", 1.0) != 1.0:
        raise NotImplementedError("Hävstång i papper är inte stödd än. Kräver riskgranser-genomgång.")
    rate = CostModel(**spec.get("costs", {})).per_side
    strategy = build(spec["strategy"]["name"], spec["strategy"].get("params"), spec.get("risk"))
    s = _replay(_events(repo, paper_id))
    times = [t.isoformat() for t in bars.index]
    start = times.index(s.last_bar) + 1 if s.last_bar in times else 0
    if s.last_bar is not None and s.last_bar not in times:
        raise ValueError("Den senast loggade stapeln finns inte i datan. Skicka med hela historiken.")
    new = []
    for i in range(start, len(bars)):
        o = float(bars["open"].iloc[i])
        events = []
        # 1) Fyll beslutet från förra stängningen vid den här öppningen.
        if s.pending is not None and s.pending != s.pos:
            if s.qty != 0:
                c = abs(s.qty) * o * rate
                s.equity -= c
                events.append({"type": "fill", "time": times[i], "action": "close", "price": o, "qty": s.qty, "cost": c})
                s.qty = 0.0
            s.pos = s.pending
            if s.pos != 0:
                notional = abs(s.pos) * s.equity
                c = notional * rate
                s.equity -= c
                s.qty = (1 if s.pos > 0 else -1) * notional / o
                events.append({"type": "fill", "time": times[i], "action": "open", "price": o, "qty": s.qty, "cost": c})
        # 2) Värdera till nästa öppning (eller stängningen om det är sista stapeln vi har).
        if i + 1 < len(bars):
            nxt = float(bars["open"].iloc[i + 1])
            s.equity += s.qty * (nxt - o)
        else:
            # Sista stängda stapeln: värdera inte framåt än; nästa step() fortsätter härifrån.
            pass
        # 3) Beslut vid stängningen av stapel i, med data till och med i.
        decision = float(strategy(bars.iloc[: i + 1]).iloc[-1])
        decision = max(-1.0, min(1.0, decision))
        events.append({"type": "bar", "time": times[i], "open": o, "close": float(bars["close"].iloc[i]),
                       "equity": s.equity, "pos": s.pos, "qty": s.qty, "decision": decision,
                       "valued_to_next_open": i + 1 < len(bars)})
        if i + 1 >= len(bars):
            # Sista stapeln: spara utan framåtvärdering, och ta bort den igen nästa gång (se nedan).
            events[-1]["provisional"] = True
        new.extend(events)
        s.last_bar = times[i]
        s.pending = decision
    if new and new[-1].get("provisional"):
        # Den sista stapeln värderas framåt när nästa stapel finns. För att loggen ska vara oföränderlig
        # loggas den först då: vi skriver alla händelser utom den sista stapelns.
        last_time = new[-1]["time"]
        new = [e for e in new if e["time"] != last_time]
    _append(repo, paper_id, new)
    return sum(1 for e in new if e["type"] == "bar")


def closed_only(bars: pd.DataFrame, interval: str, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Tar bort staplar som inte har stängt än. Beslut får bara tas på stängda staplar."""
    from ..bars import interval_delta
    now = now or pd.Timestamp.now(tz="UTC")
    return bars[bars.index + interval_delta(interval) <= now]


def status(repo: Path, paper_id: str) -> dict:
    frozen = _load(repo, paper_id)
    ev = _events(repo, paper_id)
    bars = [e for e in ev if e["type"] == "bar"]
    opens = [e for e in ev if e["type"] == "fill" and e["action"] == "open"]
    return {"paper_id": paper_id, "hypothesis_id": frozen["hypothesis_id"], "bars": len(bars),
            "trades": len(opens), "planned_trades": frozen["planned_trades"],
            "equity": bars[-1]["equity"] if bars else 1.0, "position": bars[-1]["pos"] if bars else 0.0,
            "last_bar": bars[-1]["time"] if bars else None, "stop_rule": frozen["stop_rule"]}
