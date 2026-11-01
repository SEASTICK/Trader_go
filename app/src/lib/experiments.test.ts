import { describe, expect, it } from "vitest";
import { compute, fromResult, klararMål, type Experiment, type RealResult } from "./experiments";

const exp: Experiment = { id: "E-01", spår: "S-01", namn: "BTC 4h", strategi: "Trend", grupp: "krypto", marknad: "Bitcoin", tidsram: "4h", riktning: "Long/short" };

const real: RealResult = {
  source: "HISTORIK", hypothesis: "H-0001", registry_commit: "abcdef1234567", run_at: "2026-11-01T00:00:00+00:00",
  period: ["2021-01-01 00:00:00+00:00", "2024-12-31 20:00:00+00:00"], total_return: 0.123, max_drawdown: -0.2,
  trades: 40, win_rate: 0.55, t: 1.4, t_required: 2.0, passes: false, deflated_sharpe: 0.31, stressed_total_return: 0.05,
  costs_bps_per_side: 16, curve: { t: ["2021-01-01T00:00:00+00:00", "2024-12-31T20:00:00+00:00"], strategy: [100, 112.3], buy_and_hold: [100, null] },
  recent_trades: [{ entry_time: "2024-12-01T00:00:00+00:00", exit_time: "2024-12-02T00:00:00+00:00", side: "Short", entry_price: 100, exit_price: 95, gross: 0.05, costs: 0.0032, funding: 0, net: 0.0468, liquidated: false }],
  position_now: -0.5, result_file: "research/results/H-0001-x.json",
};

describe("fromResult", () => {
  it("visar riktiga siffror som procent och märker dem HISTORIK", () => {
    const c = fromResult(exp, real);
    expect(c.källa).toBe("HISTORIK");
    expect(c.avkastning).toBeCloseTo(12.3);
    expect(c.maxDrawdown).toBeCloseTo(-20);
    expect(c.vinstandel).toBeCloseTo(55);
    expect(c.krav).toBe(2.0);
    expect(c.passes).toBe(false);
    expect(c.stressad).toBeCloseTo(5);
    expect(c.kostnadPerAffär).toBeCloseTo(0.16);
    expect(c.baseline).toEqual([100, 112.3]); // saknat värde fylls, ingen lucka i kurvan
    expect(c.trades[0]).toMatchObject({ nr: 40, riktning: "Short", netto: expect.closeTo(4.68, 2) });
    expect(c.position).toEqual({ läge: "Short", storlek: 50 });
  });

  it("påhittade rutor är alltid SIM", () => {
    expect(compute(exp).källa).toBe("SIM");
  });
});

describe("klararMål", () => {
  const base = { passes: true, stressed_total_return: 0.1, sharpe: 1.2, max_drawdown: -0.4, beta: 0.1,
    baseline: { total_return: 2, max_drawdown: -0.76, sharpe: 1.1, t_daily_nw: 2 } } as unknown as RealResult;
  it("A kräver högre Sharpe än köp-och-behåll", () => {
    expect(klararMål("A", base)).toBe(true);
    expect(klararMål("A", { ...base, sharpe: 1.0 })).toBe(false);
  });
  it("B kräver minst 40 % mindre fall", () => {
    expect(klararMål("B", base)).toBe(true);            // 0,40 <= 0,6 × 0,76
    expect(klararMål("B", { ...base, max_drawdown: -0.5 })).toBe(false);
  });
  it("C kräver låg beta och alla kräver t och stresstest", () => {
    expect(klararMål("C", base)).toBe(true);
    expect(klararMål("C", { ...base, beta: -0.3 })).toBe(false);
    expect(klararMål("C", { ...base, beta: null })).toBe(false);
    expect(klararMål("C", { ...base, stressed_total_return: -0.01 })).toBe(false);
    expect(klararMål("A", { ...base, passes: false })).toBe(false);
  });
});
