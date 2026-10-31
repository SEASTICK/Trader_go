/** Versionsjämförelse enligt semver. Pluginen jämför också, men appen behöver samma regler för att
 *  avgöra om en uppdatering ska erbjudas, skjutas upp eller aldrig nedgradera. */

export type ParsedVersion = { major: number; minor: number; patch: number; prerelease: string[] };

export function parseVersion(value: string): ParsedVersion | null {
  const match = /^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/.exec(value.trim());
  if (!match) return null;
  return { major: Number(match[1]), minor: Number(match[2]), patch: Number(match[3]), prerelease: match[4] ? match[4].split(".") : [] };
}

function comparePrerelease(left: string[], right: string[]): number {
  if (!left.length && !right.length) return 0;
  if (!left.length) return 1;
  if (!right.length) return -1;
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const a = left[index]; const b = right[index];
    if (a === undefined) return -1;
    if (b === undefined) return 1;
    const aNumber = /^\d+$/.test(a); const bNumber = /^\d+$/.test(b);
    if (aNumber && bNumber) { if (Number(a) !== Number(b)) return Number(a) < Number(b) ? -1 : 1; }
    else if (aNumber !== bNumber) return aNumber ? -1 : 1;
    else if (a !== b) return a < b ? -1 : 1;
  }
  return 0;
}

/** -1 om a < b, 0 om lika, 1 om a > b. Null om någon av dem inte är en giltig version. */
export function compareVersions(a: string, b: string): -1 | 0 | 1 | null {
  const left = parseVersion(a); const right = parseVersion(b);
  if (!left || !right) return null;
  for (const key of ["major", "minor", "patch"] as const) {
    if (left[key] !== right[key]) return left[key] < right[key] ? -1 : 1;
  }
  const pre = comparePrerelease(left.prerelease, right.prerelease);
  return pre < 0 ? -1 : pre > 0 ? 1 : 0;
}

/** Erbjud bara strikt nyare versioner. En äldre eller okänd version ska aldrig installeras över en nyare. */
export function isNewerVersion(candidate: string, current: string): boolean {
  return compareVersions(candidate, current) === 1;
}

export const UPDATE_SNOOZE_MS = 24 * 60 * 60 * 1000;
export const SNOOZE_KEY = "trader_go.updateSnooze";

export type Snooze = { version: string; untilUnixMs: number } | null;

/** Ska användaren bli tillfrågad nu? "Senare" gäller en viss version i ett dygn; en ännu nyare version frågar direkt. */
export function shouldPromptForUpdate(available: string | null | undefined, current: string, snooze: Snooze, now: number): boolean {
  if (!available || !isNewerVersion(available, current)) return false;
  if (!snooze) return true;
  if (compareVersions(available, snooze.version) === 1) return true;
  return now >= snooze.untilUnixMs;
}

export function readSnooze(storage: Pick<Storage, "getItem">): Snooze {
  try {
    const parsed = JSON.parse(storage.getItem(SNOOZE_KEY) || "null") as Snooze;
    return parsed && typeof parsed.version === "string" && Number.isFinite(parsed.untilUnixMs) ? parsed : null;
  } catch { return null; }
}
