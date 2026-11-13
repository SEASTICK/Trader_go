"""python -m traderlab.agentlab run [--ideas 60 --top 14 --controls 4 --workers 4 --seed 1]"""
import argparse
import json
from pathlib import Path

from .data import load_um_panel
from .orchestrator import Orchestrator

REPO = Path(__file__).resolve().parents[3]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "status", "rejudge", "audit", "universe-audit", "sensitivity"])
    ap.add_argument("--ideas", type=int, default=60)
    ap.add_argument("--top", type=int, default=14)
    ap.add_argument("--controls", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-iter", type=int, default=2)
    a = ap.parse_args()
    root = REPO / "research" / "agentlab"
    if a.cmd == "status":
        from .state import Blackboard
        print(json.dumps(Blackboard(root).view(), ensure_ascii=False, indent=1))
        return
    if a.cmd == "audit":
        from .audit import run_audit
        print(json.dumps(run_audit(REPO, root), ensure_ascii=False, indent=1)[:3000])
        return
    if a.cmd == "sensitivity":
        from .sensitivity import run_sensitivity
        rep = run_sensitivity(REPO, root, REPO / "research" / "agentlab" / "sensitivity")
        print(json.dumps(rep["summary"], ensure_ascii=False, indent=1))
        return
    if a.cmd == "universe-audit":
        from .universe_audit import run_universe_audit
        rep = run_universe_audit(REPO, root)
        print(json.dumps({k: rep[k] for k in ("universe_gap", "compare_old_vs_pointintime")}, ensure_ascii=False, indent=1, default=float)[:3500])
        return
    if a.cmd == "rejudge":
        from .orchestrator import Orchestrator as O
        print(json.dumps(O(root, None, workers=1).rejudge(), ensure_ascii=False, indent=1))
        return
    panel = load_um_panel(REPO / "data", cache=REPO / "data" / "clean" / "agentlab-panel-v3.pkl", listing=REPO)
    s = Orchestrator(root, panel, workers=a.workers, seed=a.seed, max_iter=a.max_iter, cache=REPO / "data" / "clean" / "agentlab-cache").run(n_ideas=a.ideas, top_k=a.top, controls=a.controls)
    print(json.dumps({k: s[k] for k in ("run", "ideas_generated", "ideas_selected", "evaluated_versions", "verdicts", "trials", "experiments_registered", "agents_spawned", "seconds", "promising", "learnings")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
