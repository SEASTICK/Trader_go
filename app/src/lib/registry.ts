// Läser research/registry.md (samma regler som engine/traderlab/registry.py).
export type RegistryRow = { id: string; cells: Record<string, string> };
export type Registry = { rows: RegistryRow[]; attempts: number; decisions: Record<string, string> };

const ID = /^\s*\|\s*(H-\d{4})\s*\|/;
const DECISIONS = ["REJECT", "MORE_RESEARCH", "READY_FOR_PAPER"];

export function parseRegistry(md: string): Registry {
  let header: string[] | null = null;
  const rows: RegistryRow[] = [];
  const decisions: Record<string, string> = {};
  for (const line of md.split(/\r?\n/)) {
    const t = line.trim();
    if (!t.startsWith("|")) continue;
    const cells = t.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
    if (!header && cells.some((c) => c.toLowerCase() === "id")) { header = cells.map((c) => c.toLowerCase()); continue; }
    if (!header || !ID.test(line)) continue;
    const rec: Record<string, string> = {};
    header.forEach((h, i) => { rec[h] = cells[i] ?? ""; });
    rows.push({ id: cells[0], cells: rec });
    const d = rec["beslut"];
    if (d && DECISIONS.includes(d)) decisions[cells[0]] = d;
  }
  return { rows, attempts: new Set(rows.map((r) => r.id)).size, decisions };
}

/** En hypotes med alla sina rader ihopslagna: registreringen, senaste resultatet och beslutet. */
export type Hypothesis = {
  id: string; date: string; title: string; statement: string; market: string; track: "A" | "B" | "C";
  decision: string | null; result: string | null; t: number | null; krav: number | null; criteria: string; runs: number;
  /** Senaste körningen blev OGILTIG och hypotesen har inget giltigt beslut. Siffrorna i resultatet är då bara diagnostik. */
  invalid: boolean;
  /** Ogiltig utan att någon körning gjorts: protokollets eget datakrav kan inte uppfyllas. Resultatet är då en datadiagnos, inget strategiutfall. */
  noRun: boolean;
};

/** Förklaring i vyn när en hypotes är ogiltig utan att någon körning gjorts. */
export const NO_RUN_HEADING = "Ogiltig utan körning, inget beslut";
export const NO_RUN_TEXT = "Testets eget datakrav kan inte uppfyllas, så det kan inte ge ett giltigt utfall. Ingen körning har gjorts, och ingen strategiavkastning, inget t-värde och ingen beta har räknats. Slutprovet är oläst. Texten nedan är en datadiagnos, inte ett resultat.";
const NO_RUN = /^OGILTIG \(ingen körning/;

/** "Genomsnittlig vikt utan kurs 14,8 % (gräns 10 %)" ur resultattexten: [andel, gräns] i procent, annars null. */
export function missingPrices(result: string | null): { share: number; limit: number } | null {
  const m = (result ?? "").match(/vikt utan kurs (\d+(?:,\d+)?) % \(gräns (\d+(?:,\d+)?) %\)/);
  return m ? { share: num(m[1]), limit: num(m[2]) } : null;
}

const num = (s: string) => Number(s.replace("−", "-").replace(",", "."));

/** Kort rubrik: första meningen, utan inledande "Spår C (...)." eller "Fas 1, spår A.". */
export function shortTitle(statement: string): string {
  const rest = statement.replace(/^(Fas \d+,\s*)?[Ss]pår [ABC][^.]*\.\s*/, "");
  const first = rest.split(/(?<=[a-zåäö0-9)])\.\s/)[0];
  return first.length > 150 ? `${first.slice(0, 147)}…` : first.replace(/\.$/, "");
}

export function groupRegistry(reg: Registry): Hypothesis[] {
  const out = new Map<string, Hypothesis>();
  const hypCol = (r: RegistryRow) => Object.keys(r.cells).find((k) => k.startsWith("hypotes")) ?? "hypotes";
  for (const r of reg.rows) {
    const text = r.cells[hypCol(r)] ?? "";
    const isResult = /^(Resultat|OGILTIG)/.test(text);
    let h = out.get(r.id);
    if (!h) {
      const track = (text.match(/[Ss]pår ([ABC])/)?.[1] ?? "A") as "A" | "B" | "C";
      h = { id: r.id, date: r.cells["datum"] ?? "", title: shortTitle(text), statement: text, market: r.cells["marknad"] ?? "",
            track, decision: null, result: null, t: null, krav: null, criteria: r.cells["beslutskriterier"] ?? "", runs: 0, invalid: false, noRun: false };
      out.set(r.id, h);
    }
    const noRun = NO_RUN.test(text);
    if (isResult && !noRun) h.runs += 1;       // en ogiltig rad utan körning är ingen körning
    const d = r.cells["beslut"];
    if (d === "OGILTIG" && !h.decision) {
      // Ogiltig körning utan giltigt beslut: visas som ogiltig, aldrig som avgjord. Ett senare beslut skriver över.
      h.invalid = true;
      h.noRun = noRun;
      h.result = r.cells["resultat"] ?? null;
    }
    if (d && d !== "OGILTIG") {
      h.invalid = false;
      h.noRun = false;
      h.decision = d;
      h.result = r.cells["resultat"] ?? null;
      // "t 1,43 (krav 2,71)" eller "t −1,8023 mot 2,67".
      const m = (h.result ?? "").match(/\bt (−?-?\d+,\d+) (?:\(krav|mot) (\d+,\d+)/);
      if (m) { h.t = num(m[1]); h.krav = num(m[2]); }
    }
  }
  return [...out.values()];
}
