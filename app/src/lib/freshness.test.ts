import { describe, expect, it } from "vitest";
import { agoText, ageDays, freshness } from "./freshness";

const NOW = new Date("2026-11-13T12:00:00Z");
describe("aktualitet", () => {
  it("räknar hela dygn och aldrig negativt", () => {
    expect(ageDays("2026-11-09T17:16:19+00:00", NOW)).toBe(3);
    expect(ageDays("2026-11-14T00:00:00Z", NOW)).toBe(0);
    expect(ageDays(null, NOW)).toBeNull();
    expect(ageDays("inte ett datum", NOW)).toBeNull();
  });
  it("aktuell inom gränsen, gammal över den, saknad utan datum", () => {
    expect(freshness("2026-11-09T17:16:19+00:00", NOW)).toEqual({ state: "ok", days: 3, date: "2026-11-09" });
    expect(freshness("2026-11-01T00:00:00Z", NOW)).toMatchObject({ state: "old", days: 12, date: "2026-11-01" });
    expect(freshness(undefined, NOW)).toEqual({ state: "missing", days: null, date: null });
  });
  it("skriver ålder på enkel svenska", () => {
    expect(agoText(0)).toBe("i dag"); expect(agoText(1)).toBe("i går"); expect(agoText(4)).toBe("för 4 dagar sedan"); expect(agoText(null)).toBe("okänt");
  });
});
