// Hur aktuell är en datakälla? Visar alltid det faktiska datumet, och säger tydligt när något saknas eller är gammalt.
export type Fresh = { state: "ok" | "old" | "missing"; days: number | null; date: string | null };

/** Antal hela dygn sedan `iso`, eller null om värdet saknas eller inte går att läsa. */
export function ageDays(iso: string | null | undefined, now: Date = new Date()): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return null;
  return Math.max(0, Math.floor((now.getTime() - t) / 86400000));
}

/** `maxDays` = längsta ålder som ännu räknas som aktuell (4 dygn täcker helger och röda dagar för börsdata). */
export function freshness(iso: string | null | undefined, now: Date = new Date(), maxDays = 4): Fresh {
  const days = ageDays(iso, now);
  if (days === null || !iso) return { state: "missing", days: null, date: null };
  return { state: days <= maxDays ? "ok" : "old", days, date: iso.slice(0, 10) };
}

export function agoText(days: number | null): string {
  if (days === null) return "okänt";
  if (days === 0) return "i dag";
  if (days === 1) return "i går";
  return `för ${days} dagar sedan`;
}
