import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import results from "../../../data/registered-results.json";
import market from "../../../data/fas1-market.json";

describe("Registered Phase 1 artifacts", () => {
  it("preserves original metrics, decisions and source hashes without SIM fallback", () => {
    expect(results.map(r => r.hypothesis_id)).toEqual(["H-0009","H-0010","H-0011","H-0012"]);
    for (const r of results) {
      const raw=readFileSync(new URL("../../../../"+r.result_file,import.meta.url));
      const original=JSON.parse(raw.toString());
      expect(r.source).toBe("HISTORIK"); expect(r.kind).toBe("registered"); expect(r.decision).toBe("REJECT");
      expect(r.stats).toEqual(original.stats); expect(r.curves).toEqual(original.curves);
      expect(r.result_sha256).toBe(createHash("sha256").update(raw).digest("hex"));
      expect(Object.values(r.criteria).every(Boolean)).toBe(false);
      expect(r.audit?.dataset_sha256).toBe(market.dataset_sha256);
      expect(market.baseline_curves.t).toEqual(r.curves.t);
      expect(market.baseline_stats).toEqual(r.baseline_stats);
    }
  });
  it("bundles complete closed futures bars from the verified OOS period only", () => {
    expect(market.market).toBe("um"); expect(market.closed).toBe(true);
    expect(market.rows).toHaveLength(6576);
    market.rows.forEach(([time,open,high,low,close,volume],i) => {
      expect([time,open,high,low,close,volume].every(Number.isFinite)).toBe(true);
      expect(time).toBe(Date.parse("2022-01-01T00:00:00Z")+i*14400000);
      expect(Math.min(open,close)).toBeGreaterThanOrEqual(low);
      expect(Math.max(open,close)).toBeLessThanOrEqual(high);
      expect(low).toBeGreaterThan(0); expect(volume).toBeGreaterThanOrEqual(0);
      expect(time).toBeLessThan(Date.parse("2025-01-01T00:00:00Z"));
    });
  });
});
