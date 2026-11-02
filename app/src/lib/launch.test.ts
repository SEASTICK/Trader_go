import { describe, expect, it } from "vitest";
import { LAST_VERSION_KEY, launchKind, readLaunch } from "./launch";

const mem = (init: Record<string, string> = {}) => {
  const m = new Map(Object.entries(init));
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), m };
};

describe("launchKind", () => {
  it("visar uppdatering bara när versionen höjts", () => {
    expect(launchKind(null, "0.1.18")).toBe("start");
    expect(launchKind("0.1.17", "0.1.18")).toBe("update");
    expect(launchKind("0.1.18", "0.1.18")).toBe("start");
    expect(launchKind("0.1.19", "0.1.18")).toBe("start");   // nedgradering firas inte
    expect(launchKind("skräp", "0.1.18")).toBe("start");
  });
  it("sparar aktuell version och visar uppdateringen bara en gång", () => {
    const s = mem({ [LAST_VERSION_KEY]: "0.1.17" });
    expect(readLaunch(s, "0.1.18")).toEqual({ kind: "update", previous: "0.1.17" });
    expect(s.m.get(LAST_VERSION_KEY)).toBe("0.1.18");
    expect(readLaunch(s, "0.1.18").kind).toBe("start");
  });
  it("tål att lagringen saknas eller kastar fel", () => {
    expect(readLaunch(null, "0.1.18").kind).toBe("start");
    const broken = { getItem: () => { throw new Error("x"); }, setItem: () => { throw new Error("x"); } };
    expect(readLaunch(broken, "0.1.18").kind).toBe("start");
  });
});
