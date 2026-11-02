#!/usr/bin/env bash
# Bygger ett versionsmärkt workerpaket från en commit. Driftsätter, laddar upp och migrerar ingenting.
# Paketet är reproducerbart: samma commit ger samma SHA-256 (sorterade poster, commitens tid, ägare 0, gzip utan
# tidsstämpel), så granskaren kan bygga om och jämföra. Se docs/fas2-driftsattning.md.
#
#   scripts/build-research-release.sh [commit] [utkatalog]
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
commit=$(git -C "$repo" rev-parse --verify "${1:-HEAD}^{commit}")
out=${2:-$repo/dist/research-release}
name="tradergo-research-${commit:0:12}"
# Det workern läser när den kör: motor, tjänstefiler, migrationer, register, protokoll, frysta auditfiler och
# Fas 1-underlag. Ingen app-kod, inga hemligheter (.env finns aldrig i Git).
paths=(engine services supabase research data/MANIFEST.md data/audits app/data scripts/verify-research-release.py)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git -C "$repo" archive --format=tar --prefix="$name/" "$commit" "${paths[@]}" | tar -x -C "$work"
mkdir -p "$out"
python3 - "$work/$name" "$commit" "$(git -C "$repo" show -s --format=%ct "$commit")" "$out" <<'PY'
import gzip, hashlib, io, json, sys, tarfile
from pathlib import Path
root, commit, stamp, out = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
(root / "REVISION.env").write_text(f"TRADERGO_REVISION={commit}\n")
files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(root.rglob("*")) if p.is_file() and p.name != "release.json"}
manifest = {"package": root.name, "commit": commit, "revision_env": "REVISION.env",
            "migrations": sorted(p for p in files if p.startswith("supabase/migrations/")),
            "requires_migration": "supabase/migrations/0005_h0013_queue.sql",
            "service": "services/research-worker/tradergo-research-worker.service", "files": files}
(root / "release.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
    for p in [root, *sorted(root.rglob("*"))]:
        info = tar.gettarinfo(p, arcname=(Path(root.name) / p.relative_to(root)).as_posix())
        info.mtime, info.uid, info.gid, info.uname, info.gname = stamp, 0, 0, "root", "root"
        info.mode = 0o755 if p.is_dir() or (p.stat().st_mode & 0o111) else 0o644
        with (open(p, "rb") if p.is_file() else io.BytesIO()) as fh:
            tar.addfile(info, fh if p.is_file() else None)
target = out / f"{root.name}.tar.gz"
with open(target, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
    gz.write(buf.getvalue())
digest = hashlib.sha256(target.read_bytes()).hexdigest()
(out / f"{root.name}.tar.gz.sha256").write_text(f"{digest}  {target.name}\n")
print(target)
print(digest)
PY
