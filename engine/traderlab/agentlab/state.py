"""Delat tillstånd: blackboard, uppgiftskö, meddelanden och experimentregister (JSON/JSONL, bara filer, ingen server).

Orchestratorn är den enda som skriver. Agenterna läser en kompakt `view()` i stället för hela historiken.
"""
from __future__ import annotations

import heapq
import itertools
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

NOW = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------- uppgifter
@dataclass(order=True)
class Task:
    priority: int
    seq: int
    id: str = field(compare=False)
    agent: str = field(compare=False)         # vilken agent (eller sub-agent) som äger uppgiften
    fn: str = field(compare=False)            # funktion i agents.TASKS
    payload: dict = field(compare=False, default_factory=dict)
    deps: list = field(compare=False, default_factory=list)
    parent: str | None = field(compare=False, default=None)     # sub-agentens skapare
    status: str = field(compare=False, default="open")          # open | running | done | failed
    result: dict | None = field(compare=False, default=None)


class TaskQueue:
    """Prioritetskö med beroenden. `ready()` ger alla uppgifter vars beroenden är klara, så att de kan köras parallellt."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._seq = itertools.count()

    def add(self, agent: str, fn: str, payload: dict, *, priority: int = 5, deps: list | None = None, parent: str | None = None, tid: str | None = None) -> Task:
        seq = next(self._seq)
        t = Task(priority, seq, tid or f"T{seq:04d}", agent, fn, payload, deps or [], parent)
        self._tasks[t.id] = t
        return t

    def ready(self) -> list[Task]:
        done = {i for i, t in self._tasks.items() if t.status == "done"}
        out = [t for t in self._tasks.values() if t.status == "open" and all(d in done or self._tasks[d].status == "failed" for d in t.deps)]
        return sorted(out)

    def open(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.status in ("open", "running")]

    def get(self, tid: str) -> Task:
        return self._tasks[tid]

    def all(self) -> list[Task]:
        return sorted(self._tasks.values())


# ---------------------------------------------------------------- meddelanden
@dataclass
class Message:
    ts: str
    sender: str
    to: str
    kind: str          # finding | objection | revision | verdict | question | info
    subject: str
    body: str
    channel: str = "blackboard"     # blackboard | github (hamnar i outbox som kan postas som PR-kommentar)


# ---------------------------------------------------------------- experimentregister (append-only)
class ExperimentRegistry:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def count(self) -> int:
        return len(self.read())

    def append(self, rec: dict) -> str:
        eid = f"X-{self.count() + 1:04d}"
        rec = {"id": eid, "ts": NOW(), **rec}
        with open(self.path, "a", encoding="utf-8") as f:       # bara tillägg, rader ändras eller tas aldrig bort
            f.write(json.dumps(rec, ensure_ascii=False, default=float) + "\n")
        return eid


# ---------------------------------------------------------------- blackboard
class Blackboard:
    """Litet gemensamt tillstånd: aktuella kandidater, bästa, avvisade idéer, öppna uppgifter, datatillgång, kända problem, antal försök."""

    FILE = "state.json"

    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.s: dict = {"runs": 0, "trials": 0, "experiments": 0, "tested_keys": [], "family_stats": {}, "best": [], "rejected": [], "promising": [],
                        "data": {}, "known_issues": [], "agents": {}, "disc_sharpes": [], "learnings": []}
        self.messages: list[Message] = []
        p = root / self.FILE
        if p.exists():
            self.s.update(json.loads(p.read_text(encoding="utf-8")))
        self.s.setdefault("spent", {"valid": [], "final": []})
        self.s.setdefault("data_status", {
            "disc": "utforskande: flera körningar och många försök har använt den",
            "valid": "FÖRBRUKAD: sedd av tidigare körningar (se spent.valid och legacy_unsealed)",
            "final": "FÖRBRUKAD: sedd av tidigare körningar (se spent.final och legacy_unsealed)"})
        if self.s["runs"] and "legacy_unsealed" not in self.s:
            # R001-R004 byggdes innan informationsbarriären fanns i koden: alla arbetsprocesser hade hela panelen och 2023/2024 beräknades för
            # ALLA kandidater, och bara visningen begränsades. Valideringsåret och slutåret är därför förbrukade (utforskande), för alla deras kandidater.
            self.s["legacy_unsealed"] = {"runs": [f"R{i:03d}" for i in range(1, self.s["runs"] + 1)],
                                         "note": "Barriären var bara en visningsregel i dessa körningar. 2023 och 2024 är förbrukade för alla deras kandidater. "
                                                 "Deflated Sharpe med effektivt antal försök och domare v2 valdes efter att utfall setts och kan inte retroaktivt bekräfta en kandidat."}

    # ---- skriv
    def say(self, sender: str, to: str, kind: str, subject: str, body: str = "", channel: str = "blackboard") -> None:
        m = Message(NOW(), sender, to, kind, subject, body, channel)
        self.messages.append(m)
        with open(self.root / "messages.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")

    def issue(self, text: str) -> None:
        if text not in self.s["known_issues"]:
            self.s["known_issues"].append(text)

    def family(self, fam: str) -> dict:
        return self.s["family_stats"].setdefault(fam, {"tested": 0, "rejected": 0, "promising": 0, "best_score": 0.0, "trials": 0})

    def save(self) -> None:
        (self.root / self.FILE).write_text(json.dumps(self.s, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")

    # ---- läs (kompakt vy, inte hela historiken)
    def view(self, open_tasks: int = 0) -> dict:
        s = self.s
        return {"research_count": s["experiments"], "trials": s["trials"], "runs": s["runs"], "open_tasks": open_tasks,
                "best_candidates": s["best"][:5], "rejected_recent": s["rejected"][-8:], "promising": s["promising"][:5],
                "family_stats": s["family_stats"], "data": {k: v["status"] for k, v in s["data"].items()},
                "known_issues": s["known_issues"][-8:]}

    def tested(self) -> set[str]:
        return set(self.s["tested_keys"])
