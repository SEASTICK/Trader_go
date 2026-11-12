import { describe, expect, it } from "vitest";
import { groupRegistry, missingPrices, NO_RUN_TEXT, parseRegistry } from "./registry";

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
| H-0021 | 2026-11-12 | h | Spår A. Investeringsidé. Mer. | USA | – | | |
| H-0021 | 2026-11-12 | i | OGILTIG (datakravet). Spår A. | USA | – | Genomsnittlig vikt utan kurs 14,8 % (gräns 10 %). För information: t 0,18 (krav 2,81). | OGILTIG |
| H-0022 | 2026-11-12 | j | Spår C. Kassa-och-termin på sju altcoins. Mer. | COIN-M | t ≥ 3,42 | | |
| H-0022 | 2026-11-12 | k | OGILTIG (ingen körning: datakrav 4 kan inte uppfyllas). Spår C. | COIN-M | – | Datadiagnos, inte ett strategiutfall. Högst 9 mot kravet 10 cykler. | OGILTIG |
`;
  const hs = groupRegistry(parseRegistry(md));
  it("slår ihop rader per id och tar senaste giltiga beslut", () => {
    expect(hs.map((h) => h.id)).toEqual(["H-0003", "H-0014", "H-0016", "H-0013", "H-0021", "H-0022"]);
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
  it("ogiltig körning utan beslut visas som ogiltig, inte som avgjord, och senare beslut vinner", () => {
    const h21 = hs[4];
    expect(h21.invalid).toBe(true); expect(h21.decision).toBeNull(); expect(h21.t).toBeNull();
    expect(missingPrices(h21.result)).toEqual({ share: 14.8, limit: 10 });
    expect(hs[0].invalid).toBe(false);   // H-0003: OGILTIG och sedan REJECT
    expect(hs[2].invalid).toBe(false);   // aldrig körd
  });
  it("ogiltig utan körning (H-0022) visas som ogiltig, räknas inte som körning och är ingen avvisad eller pågående hypotes", () => {
    const h22 = hs[5];
    expect(h22.invalid).toBe(true); expect(h22.noRun).toBe(true);
    expect(h22.decision).toBeNull(); expect(h22.t).toBeNull(); expect(h22.krav).toBeNull();
    expect(h22.runs).toBe(0);                                  // ingen körning gjordes
    expect(h22.result).toContain("Datadiagnos");
    expect(h22.title).toBe("Kassa-och-termin på sju altcoins");
    expect(NO_RUN_TEXT).toMatch(/Ingen körning har gjorts/);
    expect(NO_RUN_TEXT).toMatch(/ingen strategiavkastning, inget t-värde och ingen beta/);
    expect(NO_RUN_TEXT).toMatch(/datadiagnos, inte ett resultat/);
    expect(hs[4].noRun).toBe(false);                           // H-0021 var en riktig körning som blev ogiltig
  });
  it("registrets H-0022 i det riktiga registret är ogiltig utan körning, inte pågående och inte avvisad", async () => {
    const { readFileSync } = await import("node:fs");
    const real = groupRegistry(parseRegistry(readFileSync(new URL("../../../research/registry.md", import.meta.url), "utf-8")));
    const h = real.find((x) => x.id === "H-0022")!;
    expect(h.invalid).toBe(true); expect(h.noRun).toBe(true); expect(h.decision).toBeNull(); expect(h.runs).toBe(0);
    expect(h.result).toMatch(/Ingen körning har gjorts/);
    expect(h.result).toMatch(/9 mot kravet 10/);
  });
});
