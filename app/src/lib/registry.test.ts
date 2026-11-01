import { describe, expect, it } from "vitest";
import { parseRegistry } from "./registry";

const MD = `# Register

| id | datum | hypotes (en mening som kan vara fel) | marknad | beslut |
|---|---|---|---|---|
| H-0001 | 2026-11-01 | Trend i BTC | BTC | MORE_RESEARCH |
| H-0001 | 2026-11-05 | resultat | BTC | READY_FOR_PAPER |
| H-0002 | 2026-11-02 | Mean-reversion | ETH |  |
`;

describe("parseRegistry", () => {
  it("räknar olika id som försök och tar senaste beslutet", () => {
    const r = parseRegistry(MD);
    expect(r.rows).toHaveLength(3);
    expect(r.attempts).toBe(2);
    expect(r.decisions).toEqual({ "H-0001": "READY_FOR_PAPER" });
    expect(r.rows[2].cells["marknad"]).toBe("ETH");
  });
  it("tomt register ger noll försök", () => {
    expect(parseRegistry("| id | beslut |\n|---|---|\n").attempts).toBe(0);
  });
});
