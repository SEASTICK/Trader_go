// Avgör vilken intro som visas när appen startar: vanlig start, eller "uppdaterad" om versionen har höjts
// sedan förra starten. Senast sedda version sparas på datorn; går det inte att läsa visas en vanlig start.
import { compareVersions } from "./version";

export const LAST_VERSION_KEY = "trader_go.lastVersion";
export type LaunchKind = "start" | "update";

export function launchKind(previous: string | null, current: string): LaunchKind {
  if (!previous) return "start";
  return compareVersions(current, previous) === 1 ? "update" : "start";
}

export function readLaunch(storage: Pick<Storage, "getItem" | "setItem"> | null, current: string): { kind: LaunchKind; previous: string | null } {
  let previous: string | null = null;
  try { previous = storage?.getItem(LAST_VERSION_KEY) ?? null; } catch { /* ignoreras */ }
  const kind = launchKind(previous, current);
  try { storage?.setItem(LAST_VERSION_KEY, current); } catch { /* ignoreras */ }
  return { kind, previous };
}

export function prefersReducedMotion(): boolean {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
}
