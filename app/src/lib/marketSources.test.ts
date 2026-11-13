import { describe, expect, it } from "vitest";
import type { Candle } from "./candles";
import { bucketStart, dataProblems, HISTORY_INTERVALS, resample } from "./marketSources";

const H4 = 14_400_000, DAY = 86_400_000;
const bar = (t: number, o: number, h: number, l: number, c: number, v = 10): Candle => ({ open_time: t, open: o, high: h, low: l, close: c, volume: v, close_time: t + H4 - 1, closed: true });
/** 4h-staplar från och med `start` (UTC-ms), pris stiger 1 per stapel. */
const series = (start: number, n: number) => Array.from({ length: n }, (_, i) => bar(start + i * H4, 100 + i, 102 + i, 99 + i, 101 + i));
const MON = Date.UTC(2024, 0, 1);   // måndag 2024-01-01

describe("resample", () => {
  it("räknar 1d ur sex 4h: första öppning, högsta, lägsta, sista stängning och summerad volym", () => {
    const d = resample(series(MON, 6), "4h", "1d");
    expect(d).toHaveLength(1);
    expect(d[0]).toMatchObject({ open_time: MON, open: 100, high: 107, low: 99, close: 106, volume: 60, close_time: MON + DAY - 1, closed: true });
  });
  it("hoppar över en ofullständig period i stället för att fylla ut den", () => {
    const d = resample(series(MON + H4, 10), "4h", "1d");       // 5 + 5 staplar: ingen full dag
    expect(d).toHaveLength(0);
    expect(resample(series(MON, 8), "4h", "1d")).toHaveLength(1);   // en full dag och två lösa staplar
  });
  it("räknar inte med en period där en delstapel saknas", () => {
    const s = series(MON, 6); s.splice(2, 1);
    expect(resample(s, "4h", "1d")).toHaveLength(0);
  });
  it("veckor börjar måndag 00:00 UTC", () => {
    expect(bucketStart(MON + 3 * DAY, "1w")).toBe(MON);
    expect(bucketStart(MON - 1, "1w")).toBe(MON - 7 * DAY);
    const w = resample(series(MON, 42 + 5), "4h", "1w");
    expect(w).toHaveLength(1); expect(w[0].open_time).toBe(MON);
  });
  it("8h och 12h ger rätt antal staplar och samma intervall ger en kopia", () => {
    expect(resample(series(MON, 12), "4h", "8h")).toHaveLength(6);
    expect(resample(series(MON, 12), "4h", "12h")).toHaveLength(4);
    const same = resample(series(MON, 3), "4h", "4h");
    expect(same).toEqual(series(MON, 3));
  });
  it("avvisar tidsramar som inte går jämnt att räkna fram", () => {
    expect(() => resample(series(MON, 6), "1d", "4h")).toThrow();
    expect(() => resample(series(MON, 6), "4h", "5m")).toThrow();
  });
  it("visar tidsramarna i en bestämd ordning", () => { expect([...HISTORY_INTERVALS]).toEqual(["4h", "8h", "12h", "1d", "1w"]); });
});

describe("dataProblems", () => {
  it("godkänner en riktig serie och rapporterar ogiltiga priser, luckor, dubbletter och tomma serier", () => {
    expect(dataProblems(series(MON, 6), "4h")).toEqual([]);
    expect(dataProblems([], "4h")).toEqual(["Inga staplar finns."]);
    const nan = series(MON, 3); nan[1].close = NaN;
    expect(dataProblems(nan, "4h").join(" ")).toMatch(/ogiltiga priser/);
    const hi = series(MON, 3); hi[1].high = 1;
    expect(dataProblems(hi, "4h").join(" ")).toMatch(/ogiltiga priser/);
    const gap = series(MON, 4); gap.splice(2, 1);
    expect(dataProblems(gap, "4h").join(" ")).toMatch(/1 luckor/);
    const dup = series(MON, 3); dup[2].open_time = dup[1].open_time;
    expect(dataProblems(dup, "4h").join(" ")).toMatch(/fel ordning|dubbletter/);
  });
});
