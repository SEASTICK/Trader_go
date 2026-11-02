"""Speglar research/registry.md, strategierna och de registrerade resultaten till Supabase.

Registret i Git är källan. Supabase är en kopia för appen och raderar aldrig något.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..strategies.rules import SPECS
from .supa import Supabase

DECISIONS = {"REJECT", "MORE_RESEARCH", "READY_FOR_PAPER", "OGILTIG"}


def parse_registry(md: str) -> list[dict]:
    header, rows = None, {}
    for line in md.splitlines():
        t = line.strip()
        if not t.startswith("|"):
            continue
        cells = [c.strip() for c in t.strip("|").split("|")]
        if header is None and any(c.lower() == "id" for c in cells):
            header = [c.lower() for c in cells]
            continue
        if header is None or not re.match(r"H-\d{4}$", cells[0]):
            continue
        rec = dict(zip(header, cells))
        hid = cells[0]
        first = hid not in rows
        if first:
            track = re.search(r"Spår ([ABC])", rec.get("hypotes", "")) or re.search(r"spår ([ABC])", rec.get("hypotes", ""))
            rows[hid] = {"id": hid, "registered_at": rec.get("datum"), "registry_commit": rec.get("commit", ""),
                         "statement": rec.get("hypotes", ""), "track": track.group(1) if track else "A", "decision": None}
        d = rec.get("beslut", "")
        if d in DECISIONS:
            rows[hid]["decision"] = d
    return list(rows.values())


def sync(db: Supabase, repo: Path) -> dict:
    hyps = parse_registry((repo / "research/registry.md").read_text(encoding="utf-8"))
    db.upsert("hypotheses", hyps, "id")
    strategies = [{"name": s.name, "version": s.version, "description": s.description, "defaults": s.defaults,
                   "space": {k: vars(v) for k, v in s.space.items()}} for s in SPECS.values()]
    db.upsert("strategies", strategies, "name,version")
    return {"hypotheses": len(hyps), "strategies": len(strategies)}
