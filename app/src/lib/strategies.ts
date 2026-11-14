// En strategi = en registrerad hypotes (research/registry.md), ihopkopplad med motorns resultat (om det finns)
// och med det som körs på papper. Ingen strategi startas eller ändras härifrån; appen visar bara.
import { MÅL, type Computed, type Mål } from "./experiments";
import { groupRegistry, type Hypothesis, type Registry } from "./registry";
import { outcomeOf, type Outcome } from "./status";

export type PaperObservation = { start: string; value: number; spy_value: number; start_capital: number; updated_at: string };

/** Om strategin får köras på papper. Bara beslutet READY_FOR_PAPER öppnar för ett papperstest (skillen papper-framat). */
export type PaperStatus =
  | { kind: "observation"; obs: PaperObservation }
  | { kind: "ready" }
  | { kind: "blocked"; reason: string };

export type Strategy = {
  id: string;
  name: string;
  market: string;
  track: Mål;
  trackLabel: string;
  outcome: Outcome;
  hyp: Hypothesis;
  /** Motorns resultatrad (bara HISTORIK). Saknas när hypotesen inte har någon egen resultatrad i appen. */
  result?: Computed;
  paper: PaperStatus;
};

/** Hypoteser som just nu följs på papper i appen, och var den datan kommer från. */
export const PAPER_OBSERVATIONS: Record<string, "paper13f"> = { "H-0016": "paper13f" };

function blockedReason(o: Outcome): string {
  switch (o) {
    case "rejected": return "Klarade inte testkraven. En avvisad strategi körs aldrig på papper.";
    case "invalid": return "Testet kunde inte avgöras. Det räknas aldrig som godkänt, så strategin får inte köras på papper.";
    case "further": return "Klarade kraven men behöver mer research innan den får köras på papper.";
    default: return "Inte testad än. Först ett test på historik, sedan ett beslut.";
  }
}

export function paperStatus(id: string, o: Outcome, obs13f?: PaperObservation): PaperStatus {
  if (PAPER_OBSERVATIONS[id] === "paper13f" && obs13f) return { kind: "observation", obs: obs13f };
  if (o === "paper") return { kind: "ready" };
  return { kind: "blocked", reason: blockedReason(o) };
}

/** Alla registrerade hypoteser som valbara strategier, nyaste först. */
export function buildStrategies(reg: Registry, results: Computed[], obs13f?: PaperObservation): Strategy[] {
  const byHyp = new Map(results.filter((c) => c.hypotes).map((c) => [c.hypotes as string, c]));
  return groupRegistry(reg).reverse().map((hyp) => {
    const result = byHyp.get(hyp.id);
    const track = (result?.exp.mål ?? hyp.track) as Mål;
    const outcome = outcomeOf(hyp);
    return {
      id: hyp.id,
      name: result ? `${result.exp.namn} · ${result.exp.strategi}` : hyp.title,
      market: hyp.market,
      track,
      trackLabel: MÅL.find((m) => m.key === track)?.label ?? track,
      outcome,
      hyp,
      result,
      paper: paperStatus(hyp.id, outcome, obs13f),
    };
  });
}

export const STRATEGY_FILTERS = ["Alla", "Med resultat", "Väntar", "Kunde inte avgöras"] as const;
export type StrategyFilter = (typeof STRATEGY_FILTERS)[number];

export function filterStrategies(list: Strategy[], f: StrategyFilter): Strategy[] {
  if (f === "Med resultat") return list.filter((s) => s.result);
  if (f === "Väntar") return list.filter((s) => s.outcome === "pending");
  if (f === "Kunde inte avgöras") return list.filter((s) => s.outcome === "invalid");
  return list;
}
