// Logiken bakom prisdiagrammet, utan React eller diagrambibliotek, så att den går att testa.
// Staplarna kommer från datalagret (src-tauri/src/market). Tider är ms UTC; diagrammet visar UTC.

/** Samma fält som `Bar` i src-tauri/src/market/model.rs. */
export type Bar = { open_time: number; open: number; high: number; low: number; close: number; volume: number; close_time: number };
export type BarsPage = { bars: Bar[]; live: Bar | null; has_more: boolean };
export type SeriesInfo = { provider: string; market: string; symbol: string; interval: string; closed_bars: number; first_open_time: number; last_open_time: number };
export type BarEvent = { provider: string; market: string; symbol: string; interval: string; kind: "live" | "closed" | "resync"; bar: Bar | null };

/** En stapel i diagrammet. `closed` skiljer stängda staplar från den pågående. */
export type Candle = Bar & { closed: boolean };

/** Rutornas marknader som datalagret kan ha riktig data för. Övriga marknader har ingen OHLCV i appen. */
const SYMBOLS: Record<string, string> = { Bitcoin: "BTCUSDT", Ethereum: "ETHUSDT" };
export type SeriesRef = { provider: "binance"; market: "spot"; symbol: string; interval: string };

export function seriesFor(marknad: string, tidsram: string): SeriesRef | null {
  const symbol = SYMBOLS[marknad];
  return symbol ? { provider: "binance", market: "spot", symbol, interval: tidsram } : null;
}

export const sameSeries = (a: { provider: string; market: string; symbol: string; interval: string }, b: SeriesRef) =>
  a.provider === b.provider && a.market === b.market && a.symbol === b.symbol && a.interval === b.interval;

/** Stängda staplar plus den pågående, sorterade och utan dubbletter. */
export function fromPage(page: BarsPage): Candle[] {
  const out = page.bars.map(b => ({ ...b, closed: true }));
  if (page.live) out.push({ ...page.live, closed: false });
  return normalize(out);
}

/** Sorterar på öppningstid och behåller en stapel per tid (en stängd vinner över en pågående). */
export function normalize(c: Candle[]): Candle[] {
  const byTime = new Map<number, Candle>();
  for (const x of c) {
    const prev = byTime.get(x.open_time);
    if (!prev || x.closed || !prev.closed) byTime.set(x.open_time, x);
  }
  return [...byTime.values()].sort((a, b) => a.open_time - b.open_time);
}

/** Äldre sida före de befintliga staplarna. */
export function prepend(older: Bar[], current: Candle[]): Candle[] {
  return normalize([...older.map(b => ({ ...b, closed: true })), ...current]);
}

export type Applied = { candles: Candle[]; change: "update" | "append" | "ignored" };

/**
 * En händelse från strömmen. Samma öppningstid uppdaterar stapeln på plats, en ny tid läggs sist.
 * Äldre händelser ignoreras, och en stängd stapel ändras aldrig av en senare pågående uppdatering.
 */
export function applyEvent(candles: Candle[], bar: Bar, closed: boolean): Applied {
  const last = candles[candles.length - 1];
  if (!last || bar.open_time > last.open_time) return { candles: [...candles, { ...bar, closed }], change: "append" };
  if (bar.open_time === last.open_time) {
    if (last.closed && !closed) return { candles, change: "ignored" };
    const next = candles.slice(0, -1);
    next.push({ ...bar, closed });
    return { candles: next, change: "update" };
  }
  return { candles, change: "ignored" };
}

export type Indicator = { id: string; kind: "SMA" | "EMA"; period: number; label: string };
export const INDICATORS: Indicator[] = [
  { id: "sma20", kind: "SMA", period: 20, label: "SMA 20" },
  { id: "sma50", kind: "SMA", period: 50, label: "SMA 50" },
  { id: "ema20", kind: "EMA", period: 20, label: "EMA 20" },
];

/** Glidande medelvärde av stängningspriset. `null` tills det finns `period` staplar (uppvärmning). */
export function sma(close: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < close.length; i++) {
    sum += close[i];
    if (i >= period) sum -= close[i - period];
    out.push(i >= period - 1 ? sum / period : null);
  }
  return out;
}

/** Exponentiellt medelvärde, startat med SMA av de första `period` staplarna. `null` under uppvärmningen. */
export function ema(close: number[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const out: (number | null)[] = [];
  let prev: number | null = null;
  for (let i = 0; i < close.length; i++) {
    if (i < period - 1) { out.push(null); continue; }
    if (prev === null) {
      let s = 0;
      for (let j = i - period + 1; j <= i; j++) s += close[j];
      prev = s / period;
    } else prev = close[i] * k + prev * (1 - k);
    out.push(prev);
  }
  return out;
}

export function indicatorValues(ind: Indicator, candles: Candle[]): (number | null)[] {
  const close = candles.map(c => c.close);
  return ind.kind === "SMA" ? sma(close, ind.period) : ema(close, ind.period);
}

/** Text om uppvärmningen inte räcker, annars null. */
export function warmupNote(ind: Indicator, n: number): string | null {
  return n < ind.period ? `${ind.label} behöver ${ind.period} staplar, ${n} finns. Linjen visas när historiken räcker.` : null;
}

/** En riktig affär från ett registrerat backtest (results.json, recent_trades). */
export type TradeEvent = { entry_time: string; exit_time: string | null; side: string; entry_price: number; exit_price: number | null };
export type Marker = { time: number; position: "aboveBar" | "belowBar"; shape: "arrowUp" | "arrowDown"; text: string; kind: "entry" | "exit" };

/**
 * Markörer bara för affärer som faller inom de laddade staplarna. In sätts på stapeln där affären fylldes
 * (beslutet togs på föregående stängda stapel); ut på stapeln där den stängdes. Inget hittas på.
 */
export function tradeMarkers(trades: TradeEvent[], candles: Candle[], stepMs: number): { markers: Marker[]; outside: number } {
  if (!candles.length) return { markers: [], outside: trades.length };
  const first = candles[0].open_time;
  const last = candles[candles.length - 1].open_time + stepMs;
  const markers: Marker[] = [];
  let outside = 0;
  const barOf = (iso: string) => {
    const t = Date.parse(iso);
    return t - (((t % stepMs) + stepMs) % stepMs);
  };
  for (const tr of trades) {
    const entry = Date.parse(tr.entry_time);
    const exit = tr.exit_time ? Date.parse(tr.exit_time) : null;
    const inside = (t: number) => t >= first && t < last;
    if (!inside(entry) && !(exit !== null && inside(exit))) { outside++; continue; }
    const long = tr.side !== "Short";
    if (inside(entry)) markers.push({ time: barOf(tr.entry_time), position: long ? "belowBar" : "aboveBar", shape: long ? "arrowUp" : "arrowDown", text: `In ${long ? "long" : "short"}`, kind: "entry" });
    if (exit !== null && tr.exit_time && inside(exit)) markers.push({ time: barOf(tr.exit_time), position: long ? "aboveBar" : "belowBar", shape: long ? "arrowDown" : "arrowUp", text: "Ut", kind: "exit" });
  }
  return { markers: markers.sort((a, b) => a.time - b.time), outside };
}

const pad = (n: number) => String(n).padStart(2, "0");
/** "2026-11-01 08:00 UTC" */
export function utc(ms: number): string {
  const d = new Date(ms);
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

export const INTERVAL_MS: Record<string, number> = { "1m": 60_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000 };
