"""H-0013 (Fas 2) som registrerat jobb i samma kö och samma worker. Se docs/fas2-ko-tolkningar.md (K1–K12).

Körs i workerns beräkningsprocess, utan servernyckel. Läser bara de 120 verifierade frysta arkiven för
2020–2024; arkiv från slutprovet öppnas aldrig. Ändrar inga strategier och skriver inget beslut i registret.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path

import pandas as pd

from .. import fas2, fas2_eval
from ..data import binance
from ..registry import count_attempts
from .runner import clean

HYPOTHESIS = "H-0013"
STRATEGY = "h0013_adaptive_playbook"
DATASET = "6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c"
REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "data/audits/fas1-20261102" / f"frozen-{DATASET}.json"
EXPECTED = {
    "kind": "registered", "hypothesis_id": HYPOTHESIS, "strategy": STRATEGY,
    "version": fas2_eval.EVALUATION_VERSION, "market": "um", "symbol": "BTCUSDT", "interval": "4h",
    "params": {"protocol": "research/fas2-protokoll.md", "n_permutations": fas2_eval.N_PERMUTATIONS,
               "playbooks": fas2_eval.N_PLAYBOOKS},
    "capital": 100000, "costs": {"fee_bps": 10, "spread_bps": 2, "slippage_bps": 5},
}
TIMEOUT = 2 * 3600   # sekunder (K9); utforskning har 30 min


def validate(job: dict) -> None:
    """Hela jobbet måste vara det förregistrerade H-0013-kontraktet (K3). Ingenting väljs av användaren."""
    for key, value in EXPECTED.items():
        if job.get(key) != value:
            raise ValueError(f"H-0013-jobbet avviker från kontraktet i fältet {key}")
    start, end = (pd.Timestamp(job.get(k)) for k in ("period_start", "period_end"))
    if (start.tz is None or end.tz is None or start != fas2._ts(fas2.DEV_START) or end != fas2._ts(fas2.HOLDOUT_START)):
        raise ValueError("H-0013 körs bara på 2020-01-01 till 2025-01-01, exklusivt slut")


def _folders(data_dir: Path) -> dict[str, Path]:
    base = data_dir / "raw/binance/um/BTCUSDT"
    return {"4h": base / "4h", "fundingRate": base / "fundingRate"}


def verify_frozen_archives(data_dir: Path, manifest: dict) -> list[Path]:
    """Jämför först namnen på de arkiv som skulle läsas med manifestet, och verifierar sedan varje fil (K10).
    Endast manifestets filer öppnas; arkiv från 2025 och senare väljs aldrig ut."""
    lo, hi = fas2._ts(fas2.DEV_START), fas2._ts(fas2.HOLDOUT_START)
    wanted = {item["name"]: item["sha256"] for item in manifest["files"]}
    selected: list[Path] = []
    for kind, folder in _folders(data_dir).items():
        pattern = f"BTCUSDT-{kind}-*.zip"
        selected += binance._bounded_files(sorted(folder.glob(pattern)), lo, hi)
    names = sorted(p.name for p in selected)
    if names != sorted(wanted):
        missing = sorted(set(wanted) - set(names))
        extra = sorted(set(names) - set(wanted))
        raise ValueError(f"Arkiven matchar inte det frysta manifestet: saknas {missing[:3]}, extra {extra[:3]}")
    for path in selected:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != wanted[path.name]:
            raise ValueError(f"Fryst arkiv har ändrats: {path.name}")
        checksum = path.with_suffix(".zip.CHECKSUM")
        if not checksum.exists():
            raise ValueError(f"CHECKSUM saknas för {path.name}")
        binance.verify_checksum(raw, checksum.read_bytes())
    return selected


def load_frozen(data_dir: Path, manifest: dict | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Verifierade arkiv först, sedan inläsning, sedan jämförelse av värdena med manifestet."""
    manifest = json.loads(MANIFEST.read_text()) if manifest is None else manifest
    verify_frozen_archives(data_dir, manifest)
    bars, funding = fas2.load_development(data_dir)
    if hashlib.sha256(bars.to_csv(float_format="%.17g").encode()).hexdigest() != manifest["bars_sha256"]:
        raise ValueError("Staplarna matchar inte det frysta datasetet")
    if hashlib.sha256(funding.to_csv(float_format="%.17g").encode()).hexdigest() != manifest["funding_sha256"]:
        raise ValueError("Finansieringsräntan matchar inte det frysta datasetet")
    return bars, funding


def revision() -> dict:
    """Paketets revision (TRADERGO_REVISION på servern), annars Git-commit i arbetskopian (K12)."""
    packaged = os.environ.get("TRADERGO_REVISION")
    if packaged:
        return {"commit": packaged, "source": "TRADERGO_REVISION"}
    rev = fas2_eval.code_revision(REPO)
    return {**rev, "source": "git"}


def _watch_progress(progress: dict, path: Path, stop: threading.Event) -> None:
    """Skriver andelen färdiga steg till .progress, som föräldern skickar i heartbeat."""
    while not stop.wait(5):
        steps = progress.get("steps") or {}
        done = sum(v == "done" for v in steps.values())
        path.write_text(str(round(0.3 + 0.6 * done / max(len(steps), 1), 3)))


def result_payload(job: dict, result: dict, data: dict, manifest_sha: str) -> dict:
    """Det Supabase tar emot (K6): fullständigt resultat, affärer och spårbarhet. Inget beslut i registret."""
    main = result["h0013"]
    eq = result["curves"]["h0013"]
    trades = result.get("trades_out", [])
    return clean({
        "mode": "registered", "hypothesis_id": HYPOTHESIS, "evaluation_version": fas2_eval.EVALUATION_VERSION,
        "status": "completed", "decision": result["decision"], "criteria": result["criteria"],
        "stats": main, "curves": {"t": result["curves"]["t"], "equity": eq},
        "dataset_sha256": DATASET, "manifest_sha256": manifest_sha, "data": data, "holdout_loaded": False,
        "attempt": job.get("attempts"), "run_id": job.get("id"), "revision": revision(),
        "result": {k: v for k, v in result.items() if k not in ("curves", "trades_out")},
        "trades": trades,
        "warnings": ["Historisk forskning på utvecklingsperioden 2020–2024; slutprovet har inte lästs",
                     "Beslutet förs in i research/registry.md först efter granskning",
                     "Kandidaterna är REJECT ensamma; inget godkänns för papper eller live"],
    })


def run_job(job: dict, data_dir: Path, output: Path) -> None:
    """Workerns ingång för H-0013. Varje försök sparas i data_dir/h0013-attempts, även avbrutna (K11)."""
    validate(job)
    attempts_dir = data_dir / "h0013-attempts"
    meta = {"hypothesis_id": HYPOTHESIS, "run_id": job.get("id"), "attempt": job.get("attempts"),
            "evaluation_version": fas2_eval.EVALUATION_VERSION, "revision": revision(), "dataset_sha256": DATASET}
    progress: dict = {}
    stop = threading.Event()
    watcher = threading.Thread(target=_watch_progress, args=(progress, output.with_suffix(".progress"), stop),
                               daemon=True)
    try:
        manifest_text = MANIFEST.read_text()
        manifest = json.loads(manifest_text)
        output.with_suffix(".progress").write_text("0.1")
        bars, funding = load_frozen(data_dir, manifest)
        data = fas2_eval.data_fingerprint(bars, funding)
        meta["data"] = data
        output.with_suffix(".progress").write_text("0.3")
        watcher.start()
        attempts = count_attempts((REPO / "research/registry.md").read_text(encoding="utf-8"))
        result = fas2_eval.evaluate(bars, funding, attempts_now=attempts, progress=progress)
        result["trades_out"] = _trades(bars, funding, result)
    except BaseException as exc:
        stop.set()
        fas2_eval.record(attempts_dir, {**meta, **progress, "error": f"{type(exc).__name__}: {exc}"}, "aborted")
        raise
    stop.set()
    payload = result_payload(job, result, data, hashlib.sha256(manifest_text.encode()).hexdigest())
    fas2_eval.record(attempts_dir, {**meta, **payload}, "completed")
    output.write_text(json.dumps(payload, allow_nan=False))
    output.with_suffix(".progress").write_text("0.95")


def _trades(bars, funding, result) -> list[dict]:
    """H-0013:s affärer utanför urvalet, på den ihopsatta kurvans kapitalbas, i run_trades-format."""
    wf = fas2.walk_forward(bars, funding)
    return [{"side": t.side, "entry_time": t.entry_time.isoformat(),
             "exit_time": t.exit_time.isoformat() if t.exit_time is not None else None,
             "entry_price": t.entry_price, "exit_price": t.exit_price, "net_return": t.net_return,
             "exit_reason": t.exit_reason} for t in wf.trades]
