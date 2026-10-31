"""Läser research/registry.md och upprätthåller regel 2 i CLAUDE.md:
hypotesen skrivs ned och committas **innan** resultatet finns.

Registret är en Markdown-tabell. Första kolumnen är id (H-0001, H-0002 ...).
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REGISTRY = Path("research/registry.md")
ID_RE = re.compile(r"^\s*\|\s*(H-\d{4})\s*\|")


class NotRegisteredError(RuntimeError):
    pass


@dataclass
class Registration:
    hypothesis_id: str
    registry_commit: str
    attempts: int


def ids_in(text: str) -> list[str]:
    """Alla id i tabellen, i ordning, med upprepningar (en hypotes kan ha flera rader)."""
    return [m.group(1) for line in text.splitlines() if (m := ID_RE.match(line))]


def count_attempts(text: str) -> int:
    """Antal försök = antal olika hypotes-id.

    OBS: skillen ny-hypotes säger "alla rader i registret". Resultatrader skulle då räknas
    dubbelt, så här räknas olika id. Bekräfta med människan om regeln ska tolkas så.
    """
    return len(set(ids_in(text)))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def require_registered(hypothesis_id: str, repo: Path) -> Registration:
    """Kastar NotRegisteredError om hypotesen inte finns i den **committade** versionen av registret.

    Kräver också att registret inte har ocommittade ändringar, så att regeln och commiten hör ihop.
    """
    path = repo / REGISTRY
    if not path.exists():
        raise NotRegisteredError(f"{REGISTRY} finns inte. Registrera hypotesen först (skillen ny-hypotes).")
    try:
        committed = _git(repo, "show", f"HEAD:{REGISTRY.as_posix()}")
    except subprocess.CalledProcessError as exc:
        raise NotRegisteredError(f"{REGISTRY} är inte committad. Committa raden före körningen.") from exc
    if hypothesis_id not in ids_in(committed):
        raise NotRegisteredError(f"{hypothesis_id} finns inte i den committade versionen av {REGISTRY}.")
    dirty = _git(repo, "status", "--porcelain", "--", REGISTRY.as_posix()).strip()
    if dirty:
        raise NotRegisteredError(f"{REGISTRY} har ocommittade ändringar. Committa dem innan testet körs.")
    commit = _git(repo, "log", "-1", "--format=%H", "--", REGISTRY.as_posix()).strip()
    return Registration(hypothesis_id, commit, count_attempts(committed))
