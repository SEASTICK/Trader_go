import { describe, expect, it } from "vitest";
import { applyEvent, ema, fromPage, indicatorValues, INDICATORS, normalize, prepend, seriesFor, sma, tradeMarkers, utc, warmupNote, type Bar, type Candle } from "./candles";

const STEP = 14_400_000;
const T0 = Date.UTC(2026, 10, 1, 8); // 2026-11-01 08:00 UTC
const bar = (i: number, close = 100 + i): Bar => ({ open_time: T0 + i * STEP, open: close - 1, high: close + 2, low: close - 2, close, volume: 10 + i, close_time: T0 + (i + 1) * STEP - 1 });
const candles = (n: number): Candle[] => Array.from({ length: n }, (_, i) => ({ ...bar(i), closed: true }));

describe("stapeldata", () => {
  it("sätter ihop stängda och pågående i tidsordning utan dubbletter", () => {
    const c = fromPage({ bars: [bar(2), bar(0), bar(1)], live: bar(3), has_more: false });
    expect(c.map(x => [x.open_time - T0, x.closed])).toEqual([[0, true], [STEP, true], [2 * STEP, true], [3 * STEP, false]]);
    expect(normalize([{ ...bar(1), closed: false }, { ...bar(1), closed: true }])[0].closed).toBe(true);
  });
  it("pågående stapel uppdateras på plats, nästa läggs till, äldre ignoreras", () => {
    let c = fromPage({ bars: [bar(0), bar(1)], live: bar(2), has_more: false });
    const up = applyEvent(c, { ...bar(2), close: 999, high: 1001 }, false);
    expect(up.change).toBe("update");
    expect(up.candles.length).toBe(3);
    expect(up.candles[2].close).toBe(999);
    c = up.candles;
    const closed = applyEvent(c, { ...bar(2), close: 998 }, true);
    expect(closed.change).toBe("update");
    expect(closed.candles[2].closed).toBe(true);
    expect(applyEvent(closed.candles, bar(2), false).change).toBe("ignored");
    const next = applyEvent(closed.candles, bar(3), false);
    expect(next.change).toBe("append");
    expect(next.candles.length).toBe(4);
    expect(applyEvent(next.candles, bar(1), true).change).toBe("ignored");
  });
  it("äldre historik läggs före utan att röra slutet", () => {
    const c = prepend([bar(0), bar(1)], fromPage({ bars: [bar(2)], live: bar(3), has_more: false }));
    expect(c.map(x => (x.open_time - T0) / STEP)).toEqual([0, 1, 2, 3]);
    expect(c[3].closed).toBe(false);
  });
  it("tider visas i UTC", () => {
    expect(utc(T0)).toBe("2026-11-01 08:00 UTC");
    expect(utc(Date.UTC(2026, 2, 29, 0))).toBe("2026-03-29 00:00 UTC"); // sommartid i Sverige påverkar inte
  });
});

describe("indikatorer", () => {
  it("SMA räknas rätt och är tom under uppvärmningen", () => {
    expect(sma([1, 2, 3, 4, 5], 3)).toEqual([null, null, 2, 3, 4]);
  });
  it("EMA startar med SMA och följer formeln", () => {
    const e = ema([1, 2, 3, 4, 5], 3);
    expect(e.slice(0, 2)).toEqual([null, null]);
    expect(e[2]).toBeCloseTo(2);
    expect(e[3]).toBeCloseTo(4 * 0.5 + 2 * 0.5);
    expect(e[4]).toBeCloseTo(5 * 0.5 + 3 * 0.5);
  });
  it("beräknas från stängningspriset och säger till när historiken inte räcker", () => {
    const c = candles(30);
    const sma20 = INDICATORS.find(i => i.id === "sma20")!;
    const sma50 = INDICATORS.find(i => i.id === "sma50")!;
    const v = indicatorValues(sma20, c);
    expect(v.filter(x => x === null).length).toBe(19);
    expect(v[19]).toBeCloseTo(c.slice(0, 20).reduce((s, x) => s + x.close, 0) / 20);
    expect(warmupNote(sma20, 30)).toBeNull();
    expect(warmupNote(sma50, 30)).toContain("behöver 50");
    expect(indicatorValues(sma50, c).every(x => x === null)).toBe(true);
  });
});

describe("marknad och signaler", () => {
  it("bara marknader med riktig data får en serie, med rätt tidsram", () => {
    expect(seriesFor("Bitcoin", "4h")).toEqual({ provider: "binance", market: "spot", symbol: "BTCUSDT", interval: "4h" });
    expect(seriesFor("Bitcoin", "1d")?.interval).toBe("1d");
    expect(seriesFor("Guld", "1d")).toBeNull();
  });
  it("markörer bara för riktiga affärer inom de laddade staplarna, på rätt stapel", () => {
    const c = candles(10);
    const iso = (ms: number) => new Date(ms).toISOString();
    const trades = [
      { entry_time: iso(T0 + 2 * STEP), exit_time: iso(T0 + 5 * STEP), side: "Long", entry_price: 1, exit_price: 2 },
      { entry_time: iso(T0 - 50 * STEP), exit_time: iso(T0 - 40 * STEP), side: "Long", entry_price: 1, exit_price: 2 },
      { entry_time: iso(T0 + 7 * STEP + 1000), exit_time: null, side: "Short", entry_price: 1, exit_price: null },
    ];
    const { markers, outside } = tradeMarkers(trades, c, STEP);
    expect(outside).toBe(1);
    expect(markers.map(m => [(m.time - T0) / STEP, m.kind, m.shape])).toEqual([[2, "entry", "arrowUp"], [5, "exit", "arrowDown"], [7, "entry", "arrowDown"]]);
    expect(tradeMarkers(trades, [], STEP)).toEqual({ markers: [], outside: 3 });
  });
});
