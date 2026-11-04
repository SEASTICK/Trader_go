import { describe, expect, it } from "vitest";
import { groupRegistry, parseRegistry } from "./registry";

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

describe("groupRegistry", () => {
  const md = `| id | datum | commit | hypotes | marknad | beslutskriterier | resultat | beslut |
|---|---|---|---|---|---|---|---|
| H-0003 | 2026-11-01 | a | Volstyrd BTC: håll BTC men skala ned. Mer text. | BTC | t ≥ 2,33 | | |
| H-0003 | 2026-11-01 | b | OGILTIG KÖRNING. Motorfel. | BTC | – | Ogiltig | OGILTIG |
| H-0003 | 2026-11-01 | c | Resultat efter rättning. | BTC | – | t 2,19 (krav 2,33). Avkastning +452 % | REJECT |
| H-0014 | 2026-11-02 | d | Spår C (marknadsneutral). Tvärsnittsmomentum över terminer. Mer. | 11 mynt | t ≥ 2,71 | | |
| H-0014 | 2026-11-02 | e | Resultat. Spår C. | 11 mynt | – | t −1,43 (krav 2,71). | REJECT |
| H-0016 | 2026-11-04 | f | Fas 3, spår B. Ny idé. | BTC | – | | |
| H-0013 | 2026-11-03 | g | Fas 2, spår A med skärpta krav. Spelbok. | BTC | – | Alla fem krav fallerade. Netto −10,86 %, t −1,8023 mot 2,67; Sharpe −0,77 | REJECT |
`;
  const hs = groupRegistry(parseRegistry(md));
  it("slår ihop rader per id och tar senaste giltiga beslut", () => {
    expect(hs.map((h) => h.id)).toEqual(["H-0003", "H-0014", "H-0016", "H-0013"]);
    const h3 = hs[0];
    expect(h3.decision).toBe("REJECT");
    expect(h3.t).toBe(2.19); expect(h3.krav).toBe(2.33);
    expect(h3.runs).toBe(2);
    expect(h3.title).toBe("Volstyrd BTC: håll BTC men skala ned");
  });
  it("läser spår, rubrik utan prefix och negativa t-värden", () => {
    expect(hs[1].track).toBe("C");
    expect(hs[1].title).toBe("Tvärsnittsmomentum över terminer");
    expect(hs[1].t).toBe(-1.43);
    expect(hs[2].track).toBe("B"); expect(hs[2].decision).toBeNull();
    expect(hs[3].t).toBe(-1.8023); expect(hs[3].krav).toBe(2.67); expect(hs[3].title).toBe("Spelbok");
  });
});
