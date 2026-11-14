// Strategiväljaren: varje registrerad hypotes blir en valbar strategi, och bara READY_FOR_PAPER öppnar för papper.
import { describe, expect, it } from "vitest";
import registryMd from "../../../research/registry.md?raw";
import experiments from "../../data/experiments.json";
import results from "../../data/results.json";
import { fromResult, type Experiment, type RealResult } from "./experiments";
import { groupRegistry, parseRegistry } from "./registry";
import { buildStrategies, filterStrategies, paperStatus, type PaperObservation } from "./strategies";

const reg = parseRegistry(registryMd);
const real = results as unknown as Record<string, RealResult>;
const computed = (experiments as Experiment[]).filter((e) => real[e.id]?.source === "HISTORIK").map((e) => fromResult(e, real[e.id]));
const obs: PaperObservation = { start: "2026-11-05", value: 98000, spy_value: 99000, start_capital: 100000, updated_at: "2026-11-14T00:00:00Z" };

describe("buildStrategies", () => {
  const list = buildStrategies(reg, computed, obs);
  it("har en strategi per registrerad hypotes, nyaste först", () => {
    expect(list.length).toBe(groupRegistry(reg).length);
    expect(new Set(list.map((s) => s.id)).size).toBe(list.length);
    expect(list.map((s) => s.id)).toContain("H-0026");
    expect(list[list.length - 1].id).toBe("H-0001");
  });
  it("kopplar motorns resultatrad till rätt hypotes", () => {
    const h1 = list.find((s) => s.id === "H-0001")!;
    expect(h1.result?.exp.id).toBe("E-01");
    expect(h1.name).toContain("BTC 4h");
    for (const c of computed) expect(list.find((s) => s.id === c.hypotes)?.result).toBe(c);
  });
  it("låter ingen avvisad, ogiltig eller otestad strategi gå till papper", () => {
    for (const s of list) {
      if (s.outcome !== "paper" && s.id !== "H-0016") expect(s.paper.kind).toBe("blocked");
    }
  });
  it("visar 13F-observationen som papper, aldrig som godkänt test", () => {
    const h16 = list.find((s) => s.id === "H-0016")!;
    expect(h16.paper.kind).toBe("observation");
    expect(h16.outcome).not.toBe("paper");
  });
  it("filtrerar", () => {
    expect(filterStrategies(list, "Alla")).toHaveLength(list.length);
    expect(filterStrategies(list, "Med resultat").every((s) => s.result)).toBe(true);
    expect(filterStrategies(list, "Kunde inte avgöras").every((s) => s.outcome === "invalid")).toBe(true);
    expect(filterStrategies(list, "Väntar").every((s) => s.outcome === "pending")).toBe(true);
  });
});

describe("paperStatus", () => {
  it("öppnar bara för READY_FOR_PAPER", () => {
    expect(paperStatus("H-9999", "paper").kind).toBe("ready");
    for (const o of ["rejected", "further", "invalid", "pending"] as const) expect(paperStatus("H-9999", o).kind).toBe("blocked");
  });
  it("visar observationen bara när datan finns", () => {
    expect(paperStatus("H-0016", "invalid").kind).toBe("blocked");
    expect(paperStatus("H-0016", "invalid", obs).kind).toBe("observation");
  });
});

describe("namn", () => {
  it("tar bara bort ett kort spårprefix, aldrig själva hypotesen", async () => {
    const { shortTitle } = await import("./registry");
    expect(shortTitle("Spår C (marknadsneutral). Par-handel ETH mot BTC.")).toBe("Par-handel ETH mot BTC");
    expect(shortTitle("Fas 1, spår A. Trend på BTC.")).toBe("Trend på BTC");
    expect(shortTitle("Spår A med skärpta krav: en fast momentummodell på BTCUSDT, long eller platt. Vald efter H-0016.")).toBe("En fast momentummodell på BTCUSDT, long eller platt");
  });
  it("ger H-0025 och H-0026 namn som beskriver strategin", () => {
    const list = buildStrategies(reg, computed, obs);
    expect(list.find((s) => s.id === "H-0026")!.name).toMatch(/^En fast riskstyrd tidsseriemomentummodell/);
    expect(list.find((s) => s.id === "H-0025")!.name).toMatch(/^En fast long\/platt squeeze-breakout/);
  });
});
