#!/usr/bin/env python3
"""Verifierar ett uppackat workerpaket innan det installeras: varje fil mot release.json, inga extra eller
saknade filer, och att REVISION.env anger samma commit som manifestet. Ändrar ingenting.

    python3 scripts/verify-research-release.py /opt/tradergo/releases/tradergo-research-<commit>
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def verify(root: Path) -> dict:
    manifest = json.loads((root / "release.json").read_text())
    actual = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob("*")) if p.is_file() and p.name != "release.json"
              and "__pycache__" not in p.parts}
    expected = manifest["files"]
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    changed = sorted(k for k in set(expected) & set(actual) if expected[k] != actual[k])
    if missing or extra or changed:
        raise SystemExit(f"Paketet stämmer inte med release.json: saknas {missing[:5]}, extra {extra[:5]}, "
                         f"ändrade {changed[:5]}")
    revision = dict(line.split("=", 1) for line in (root / "REVISION.env").read_text().split())
    if revision.get("TRADERGO_REVISION") != manifest["commit"] or len(manifest["commit"]) != 40:
        raise SystemExit("REVISION.env anger inte paketets commit")
    if root.name != manifest["package"] or not manifest["package"].endswith(manifest["commit"][:12]):
        raise SystemExit("Katalognamnet stämmer inte med paketets commit")
    if manifest["requires_migration"] not in expected:
        raise SystemExit("Paketet saknar migrationen det kräver")
    return {"package": manifest["package"], "commit": manifest["commit"], "files": len(expected)}


if __name__ == "__main__":
    print(json.dumps(verify(Path(sys.argv[1]).resolve())))
