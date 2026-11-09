import { describe, expect, it } from "vitest";
import { isStale } from "./Investors";

describe("isStale", () => {
  it("en 13F äldre än 200 dagar är gammal", () => {
    const today = new Date("2026-11-09");
    expect(isStale("2026-08-14", today)).toBe(false);
    expect(isStale("2025-11-03", today)).toBe(true);
  });
});
