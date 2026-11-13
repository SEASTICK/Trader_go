// Ett gemensamt språk för hur ett försök (hypotes) står sig, hämtat ur registrets riktiga status.
// REJECT betyder "klarade inte testkraven", aldrig "negativ avkastning". OGILTIG räknas aldrig som godkänd eller vidare.
import { groupRegistry, type Hypothesis, type Registry } from "./registry";

export type Outcome = "rejected" | "further" | "paper" | "invalid" | "pending";

export function outcomeOf(h: Pick<Hypothesis, "decision" | "invalid">): Outcome {
  if (h.decision === "REJECT") return "rejected";
  if (h.decision === "MORE_RESEARCH") return "further";
  if (h.decision === "READY_FOR_PAPER") return "paper";
  if (h.invalid) return "invalid";
  return "pending";
}

export const OUTCOME_LABEL: Record<Outcome, string> = {
  rejected: "Klarade inte testkraven",
  further: "Klarade kraven, behöver mer research",
  paper: "Redo för papper",
  invalid: "Kunde inte avgöras",
  pending: "Väntar på test",
};

/** Kort förklaring till de statusar som lätt missförstås. */
export const OUTCOME_HELP: Partial<Record<Outcome, string>> = {
  rejected: "Idén uppfyllde inte de krav som sattes i förväg. Det säger inget om historiken var plus eller minus.",
  invalid: "Datan räckte inte för ett rättvist test. Det räknas aldrig som godkänt.",
};

export type Summary = { total: number; rejected: number; advanced: number; invalid: number; pending: number; decided: number };

export function summarize(reg: Registry): Summary {
  const groups = groupRegistry(reg);
  const count = (o: Outcome) => groups.filter((h) => outcomeOf(h) === o).length;
  const rejected = count("rejected");
  const advanced = count("further") + count("paper");
  return { total: groups.length, rejected, advanced, invalid: count("invalid"), pending: count("pending"), decided: rejected + advanced };
}
