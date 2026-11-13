import { describe, expect, it } from "vitest";
import { parseRegistry } from "./registry";
import { OUTCOME_LABEL, outcomeOf, summarize } from "./status";

const HEAD = "| id | datum | commit | hypotes | marknad | tidsram | period | modell | kostnader | beslutskriterier | ren period? | resultat | beslut |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n";
const row = (id: string, text: string, result = "", decision = "") => `| ${id} | 2026-11-01 | abc1234 | ${text} | m | 1d | p | x | k | c | Nej | ${result} | ${decision} |\n`;

describe("status", () => {
  const md = HEAD
    + row("H-0001", "Spår A. Idé ett.") + row("H-0001", "Resultat. Spår A.", "t 1,0 (krav 2,0)", "REJECT")
    + row("H-0002", "Spår A. Idé två.") + row("H-0002", "OGILTIG. Spår A.", "Datakravet föll", "OGILTIG")
    + row("H-0003", "Spår B. Idé tre.")
    + row("H-0004", "Spår C. Idé fyra.") + row("H-0004", "Resultat. Spår C.", "t 4,0 (krav 3,0)", "MORE_RESEARCH");
  const s = summarize(parseRegistry(md));
  it("räknar varje status för sig och OGILTIG aldrig som avgjord eller vidare", () => {
    expect(s).toEqual({ total: 4, rejected: 1, advanced: 1, invalid: 1, pending: 1, decided: 2 });
  });
  it("REJECT heter 'Klarade inte testkraven', aldrig 'negativ'", () => {
    expect(OUTCOME_LABEL.rejected).toBe("Klarade inte testkraven");
    expect(outcomeOf({ decision: "REJECT", invalid: false })).toBe("rejected");
    expect(outcomeOf({ decision: null, invalid: true })).toBe("invalid");
    expect(outcomeOf({ decision: null, invalid: false })).toBe("pending");
    expect(Object.values(OUTCOME_LABEL).join(" ")).not.toMatch(/negativ|förlust/i);
  });
});
