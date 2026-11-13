// Marknadens datakällor i appen. I datorprogrammet läser diagrammet datalagret (Binance, via insamlingen). I webbläsaren finns bara
// den kontrollsummerade historiken som följer med appen (BTCUSDT USDⓈ-M, 4h). Längre tidsramar räknas ur de riktiga stängda
// 4h-staplarna (första öppning, högsta, lägsta, sista stängning, summerad volym). Aldrig påhittade eller utfyllda staplar.
import { INTERVAL_MS, type Candle } from "./candles";

const DAY = 86_400_000;
/** Binance veckor börjar måndag 00:00 UTC. 1970-01-01 var en torsdag, så första måndagen är dag 4. */
const WEEK_ANCHOR = 4 * DAY;
const STEP: Record<string, number> = { ...INTERVAL_MS, "8h": 28_800_000, "12h": 43_200_000, "1w": 7 * DAY };
/** Tidsramar som går att räkna ur 4h-historiken, i visningsordning. */
export const HISTORY_INTERVALS = ["4h", "8h", "12h", "1d", "1w"] as const;

/** Början av stapeln som innehåller `t` för tidsramen (UTC, veckor från måndag). */
export function bucketStart(t: number, interval: string): number {
  const step = STEP[interval];
  if (!step) throw new Error(`Okänd tidsram ${interval}`);
  return interval === "1w" ? Math.floor((t - WEEK_ANCHOR) / step) * step + WEEK_ANCHOR : Math.floor(t / step) * step;
}

/**
 * Slår ihop stängda staplar till en längre tidsram. En ny stapel skapas bara när **alla** delstaplar finns. En ofullständig första eller
 * sista period (till exempel en halv vecka) hoppas över i stället för att fyllas ut.
 */
export function resample(bars: Candle[], from: string, to: string): Candle[] {
  const src = STEP[from], dst = STEP[to];
  if (!src || !dst || dst < src || dst % src !== 0) throw new Error(`Kan inte räkna ${to} ur ${from}`);
  if (from === to) return bars.map((b) => ({ ...b }));
  const need = dst / src;
  const groups = new Map<number, Candle[]>();
  for (const b of bars) {
    const k = bucketStart(b.open_time, to);
    const g = groups.get(k);
    if (g) g.push(b); else groups.set(k, [b]);
  }
  const out: Candle[] = [];
  for (const [open, g] of [...groups].sort((a, b) => a[0] - b[0])) {
    if (g.length !== need) continue;
    g.sort((a, b) => a.open_time - b.open_time);
    if (g.some((b, i) => b.open_time !== open + i * src)) continue;           // glapp i delstaplarna: räknas inte
    out.push({
      open_time: open, open: g[0].open, high: Math.max(...g.map((b) => b.high)), low: Math.min(...g.map((b) => b.low)),
      close: g[g.length - 1].close, volume: g.reduce((s, b) => s + b.volume, 0), close_time: open + dst - 1, closed: true,
    });
  }
  return out;
}

/** Datafel i en serie, på enkel svenska. Tom lista = serien går att rita. */
export function dataProblems(bars: Candle[], interval: string): string[] {
  const step = STEP[interval];
  const out: string[] = [];
  if (!bars.length) return ["Inga staplar finns."];
  let bad = 0, gaps = 0, unordered = 0;
  bars.forEach((b, i) => {
    const vals = [b.open, b.high, b.low, b.close];
    if (!vals.every((v) => Number.isFinite(v) && v > 0) || !Number.isFinite(b.volume) || b.volume < 0 || b.high < Math.max(b.open, b.close, b.low) || b.low > Math.min(b.open, b.close, b.high)) bad += 1;
    if (i > 0) {
      const d = b.open_time - bars[i - 1].open_time;
      if (d <= 0) unordered += 1; else if (step && d !== step) gaps += 1;
    }
  });
  if (bad) out.push(`${bad} staplar har ogiltiga priser eller volym.`);
  if (unordered) out.push(`${unordered} staplar ligger i fel ordning eller är dubbletter.`);
  if (gaps) out.push(`${gaps} luckor mellan staplarna.`);
  return out;
}
