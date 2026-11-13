"""Domaren: gemensamt poängsystem och domslut. Poängen belönar stabilitet och kostnadstålighet, inte hög historisk avkastning.

Domslut: REJECT, MORE_RESEARCH, PROMISING, READY_FOR_PAPER. READY_FOR_PAPER betyder bara "kandidat": en formell registrering (research/registry.md)
och ett färskt test framåt krävs före papper. Inget här är ett bekräftande test (allt är utforskande, upprepade försök på samma data).
"""
from __future__ import annotations

import numpy as np

JUDGE_VERSION = 2          # v1: PROMISING räckte med poäng ≥ 55. v2: kräver även valideringsårets Sharpe ≥ 0,5 efter kostnad (satt efter att första körningen visade discovery→validering 1,7→0,3)
WEIGHTS = {"after_cost_return": 0.12, "sharpe": 0.15, "max_drawdown": 0.08, "stability_periods": 0.10, "stability_assets": 0.08, "turnover": 0.05,
           "cost_sensitivity": 0.12, "parameter_sensitivity": 0.08, "diversification": 0.07, "evidence_quality": 0.15}
clip01 = lambda x: float(min(1.0, max(0.0, x)))


def components(ev: dict, sealed: dict | None = None) -> dict:
    """Poängkomponenter 0..1. `sealed` = öppnade valideringsmått (annars bara discovery)."""
    q, c, r, s, p = ev.get("quant", {}), ev.get("cost", {}), ev.get("risk", {}), ev.get("skeptic", {}), ev.get("portfolio", {})
    d = q.get("disc", {})
    ann, sh, dd = d.get("ann_ret", 0.0), d.get("sharpe", 0.0), d.get("max_dd", 0.0)
    if sealed and sealed.get("valid"):                       # belöna bara det som håller i valideringsåret också (sämsta av de två)
        ann, sh = min(ann, sealed["valid"].get("ann_ret", ann)), min(sh, sealed["valid"].get("sharpe", sh))
        dd = min(dd, sealed["valid"].get("max_dd", dd))
    grid = c.get("sharpe_grid", {})
    base = grid.get("1.0", sh)
    nb = q.get("neighbors", [])
    perm = s.get("perm_p", 1.0)
    dsr = s.get("dsr") or 0.0
    n = d.get("n", 0)
    ev_quality = (0.0 if s.get("leakage") else 1.0) * (0.4 * clip01(1 - perm / 0.10) + 0.3 * (dsr if dsr == dsr else 0.0) + 0.3 * clip01(n / 600))
    return {
        "after_cost_return": clip01(ann / 0.5), "sharpe": clip01(sh / 2.0), "max_drawdown": 1 - clip01(abs(dd) / 0.5),
        "stability_periods": clip01(s.get("half_pos", 0.0)), "stability_assets": clip01(s.get("asset_pos", 0.0)),
        "turnover": 1 - clip01(q.get("turnover_ann", 0.0) / 150.0),
        "cost_sensitivity": clip01(grid.get("2.5", 0.0) / base) if base > 0.1 else 0.0,
        "parameter_sensitivity": (float(np.mean([x[1] > 0.5 * max(sh, 0.1) for x in nb])) if nb else 0.4) if sh > 0 else 0.0,
        "diversification": clip01(p.get("div_value", 0.1) / 0.3) if p else 0.3,
        "evidence_quality": clip01(ev_quality),
    }


def score(comp: dict) -> float:
    return round(100 * sum(WEIGHTS[k] * comp[k] for k in WEIGHTS), 1)


def hard_fails(ev: dict, sealed: dict | None = None) -> list[str]:
    q, c, s = ev.get("quant", {}), ev.get("cost", {}), ev.get("skeptic", {})
    d = q.get("disc", {})
    out = []
    if s.get("leakage"):
        out.append("läckage: vikter för dag t ändras av framtida data")
    if d.get("sharpe", 0.0) <= 0.3:
        out.append(f"svag discovery-Sharpe {d.get('sharpe', 0.0):.2f} efter kostnad")
    if c.get("sharpe_grid", {}).get("2.5", 1.0) <= 0:
        out.append("olönsam med 2,5 gånger kostnaderna")
    if s.get("perm_p", 0.0) > 0.15:
        out.append(f"inte skild från slumpen (permutation p={s.get('perm_p'):.2f})")
    if s.get("dsr") is not None and s["dsr"] < 0.5:
        out.append(f"deflated Sharpe {s['dsr']:.2f} med {s.get('n_eff', '?')} effektiva försök")
    b = q.get("baselines", {})
    if b and q.get("beta_btc", 0.0) > 0.5 and d.get("sharpe", 0.0) <= b.get("bh_btc", -9):
        out.append("slår inte köp-och-behåll BTC riskjusterat")
    if sealed:
        v = sealed.get("valid", {})
        if v and v.get("sharpe", 0.0) <= 0:
            out.append(f"negativ Sharpe i valideringsåret ({v.get('sharpe', 0.0):.2f})")
    return out


def preliminary(ev: dict, iteration: int, max_iter: int) -> tuple[str, list[str]]:
    """Domarens förbedömning på discovery-data (ingen förseglad data): kill, iterate eller advance."""
    fails = hard_fails(ev)
    d = ev.get("quant", {}).get("disc", {})
    sharpe = d.get("sharpe", 0.0)
    objections = ev.get("objections", [])
    fixable = [o for o in objections if o.get("mutable")]
    if any("läckage" in f for f in fails):
        return "kill", fails
    if not fails and sharpe >= 0.6:
        return "advance", []
    # något går att rädda: bra grundsiffror men åtgärdbara invändningar, och det finns iterationer kvar
    if sharpe >= 0.3 and fixable and iteration < max_iter and not any("inte skild från slumpen" in f for f in fails):
        return "iterate", [o["code"] for o in fixable]
    return "kill", fails or ["inget att rädda"]


def final(ev: dict, sealed: dict, *, paper_gate: bool = True) -> dict:
    """Slutdom. `sealed` = {"valid": mått, "final": mått eller None}."""
    comp = components(ev, sealed)
    sc = score(comp)
    fails = hard_fails(ev, sealed)
    d, s = ev.get("quant", {}).get("disc", {}), ev.get("skeptic", {})
    if fails or sc < 40:
        verdict = "REJECT"
    elif sc < 55:
        verdict = "MORE_RESEARCH"
    else:
        verdict = "PROMISING"
    vs = sealed.get("valid", {}).get("sharpe", 0.0) if sealed else 0.0
    if verdict == "PROMISING" and vs < 0.5:                  # discovery räcker inte: valideringsåret måste hålla
        verdict = "MORE_RESEARCH"
        fails = list(fails) + [f"valideringsårets Sharpe {vs:.2f} < 0,5 (PROMISING kräver minst 0,5)"]
    fin = sealed.get("final")
    notes = list(fails)
    if verdict == "PROMISING" and paper_gate and fin:
        beta = abs(ev.get("quant", {}).get("beta_btc", 1.0))
        div = ev.get("portfolio", {}).get("div_value", 0.0)
        gates = {"final_sharpe>=0.5": fin.get("sharpe", 0) >= 0.5, "valid_sharpe>=0.5": sealed["valid"].get("sharpe", 0) >= 0.5,
                 "perm_p<=0.02": s.get("perm_p", 1) <= 0.02, "dsr>=0.9": (s.get("dsr", 0) or 0) >= 0.9, "beta<=0.3_or_beats_baseline": beta <= 0.3 or d.get("sharpe", 0) > ev["quant"].get("baselines", {}).get("bh_btc", 9),
                 "diversifies": div > 0}
        if all(gates.values()):
            verdict = "READY_FOR_PAPER"
            notes.append("KANDIDAT: kräver formell registrering i research/registry.md och ett färskt test framåt före papper")
        else:
            notes += [f"grind ej uppfylld: {k}" for k, v in gates.items() if not v]
    return {"verdict": verdict, "score": sc, "components": {k: round(v, 3) for k, v in comp.items()}, "notes": notes, "judge_version": JUDGE_VERSION}
