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
