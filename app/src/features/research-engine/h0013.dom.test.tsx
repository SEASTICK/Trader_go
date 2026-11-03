// @vitest-environment happy-dom
// H-0013-vyn renderad i en riktig DOM med React-effekter: diagram, resultathämtning och felåterhämtning.
// Simulerat API, inget nätverk, ingen riktig körning.
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { chartDomain, LineChart } from "../../components/Charts";
import type { ResearchApi, Run } from "./api";
import { comparisonAxisProblem, CURVE_TOLERANCE, readComparisonCurves, readResult, readTrades } from "./h0013";
import H0013Panel, { H0013Result, RETRY_MS } from "./H0013Panel";
import { comparisonCurves, MAIN_EQUITY, MAIN_T, payload, run } from "./h0013.fixtures";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
beforeEach(() => { vi.useFakeTimers(); host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); vi.useRealTimers(); });
const render = async (node: React.ReactNode) => { await act(async () => { root.render(node); }); await flush(); };
const flush = async (ms = 0) => { await act(async () => { await vi.advanceTimersByTimeAsync(ms); }); };
const text = () => host.textContent ?? "";
const paths = () => [...host.querySelectorAll("svg path")].map(p => p.getAttribute("d") ?? "");

function fakeApi(runs: Run[], payloads: (() => Promise<unknown>)[]) {
  const api = {
    h0013Runs: vi.fn(async () => runs),
    payload: vi.fn((id: string) => { const next = payloads.shift(); if (!next) throw new Error("oväntat resultatanrop " + id); return next(); }),
    cancel: vi.fn(async () => null),
    enqueueH0013: vi.fn(async () => "never"),
  };
  return api;
}
const asApi = (api: ReturnType<typeof fakeApi>) => api as unknown as ResearchApi;

describe("Diagram med konstanta värden", () => {
  it.each([
    ["platt kapital", [1, 1, 1]],
    ["jämnt stigande kapital (drawdown alltid noll)", [1, 1.01, 1.02, 1.03]],
    ["vanlig varierande kurva", [1, 1.05, 0.97, 1.1]],
  ])("%s ritas med ändliga koordinater", async (_name, equity) => {
    const v = readResult(payload({ curves: { t: equity.map((_, i) => `2022-01-0${i + 1}T00:00:00+00:00`), equity } }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    await render(<H0013Result view={v} />);
    const lines = paths().filter(d => d.startsWith("M") && !d.includes("Z"));
    expect(lines).toHaveLength(2);                                   // kapital och drawdown
    for (const d of paths()) expect(d).not.toMatch(/NaN|Infinity/);
    expect(text()).not.toContain("Kapitalkurvan saknas");
  });
  it("den delade grafen ritar en konstant serie som en horisontell linje", async () => {
    await render(<LineChart watermark={null} labels={["a", "b", "c"]} series={[{ name: "x", data: [0, 0, 0], cls: "s1" }]} />);
    const line = paths().find(d => !d.includes("Z"))!;
    const ys = [...line.matchAll(/[ML][\d.]+,([\d.]+)/g)].map(m => Number(m[1]));
    expect(ys).toHaveLength(3); expect(new Set(ys).size).toBe(1); expect(ys.every(Number.isFinite)).toBe(true);
    expect(chartDomain([0, 0, 0])).toEqual([0, 1]);
    expect(chartDomain([100000, 100000])).toEqual([95000, 105000]);
    const [lo, hi] = chartDomain([90, 110]);                         // varierande: samma som tidigare formel
    expect(lo).toBeCloseTo(88.4); expect(hi).toBeCloseTo(111.6);
  });
});

describe("Resultathämtning och felåterhämtning", () => {
  it("ett tillfälligt fel visas, döljs inte av listpollning och hämtas igen automatiskt", async () => {
    const api = fakeApi([run({ status: "done" })], [() => Promise.reject(new Error("Ingen serveranslutning. Försök igen när nätverket fungerar.")),
      async () => payload()]);
    await render(<H0013Panel api={asApi(api)} connected login={<p>login</p>} />);
    expect(text()).toContain("Resultatet kunde inte hämtas"); expect(text()).toContain("Ingen serveranslutning");
    for (let i = 0; i < 2; i++) await flush(5000);                   // två lyckade listpollningar
    expect(api.h0013Runs.mock.calls.length).toBeGreaterThanOrEqual(3);
    expect(text()).toContain("Resultatet kunde inte hämtas");
    expect(api.payload).toHaveBeenCalledTimes(1);
    await flush(RETRY_MS);
    expect(api.payload).toHaveBeenCalledTimes(2);
    expect(text()).toContain("HISTORIK · H-0013"); expect(text()).not.toContain("kunde inte hämtas");
    expect(api.enqueueH0013).not.toHaveBeenCalled();
  });
  it("knappen Försök igen nu hämtar direkt", async () => {
    const api = fakeApi([run({ status: "done" })], [() => Promise.reject(new Error("Servern svarade med fel (502).")), async () => payload()]);
    await render(<H0013Panel api={asApi(api)} connected login={<p>login</p>} />);
    const button = [...host.querySelectorAll("button")].find(b => b.textContent === "Försök igen nu")!;
    await act(async () => { button.click(); }); await flush();
    expect(api.payload).toHaveBeenCalledTimes(2); expect(text()).toContain("HISTORIK · H-0013");
    expect(api.enqueueH0013).not.toHaveBeenCalled();
  });
  it("ett sent svar för en tidigare vald körning visas inte efter byte", async () => {
    let resolveA: (v: unknown) => void = () => {};
    const a = run({ id: "run-a", status: "done", created_at: "2026-11-03T09:00:00Z" });
    const b = run({ id: "run-b", status: "done", created_at: "2026-11-03T10:00:00Z" });
    const api = fakeApi([a, b], [() => new Promise(r => { resolveA = r; }), async () => payload({ run_id: "run-b" })]);
    await render(<H0013Panel api={asApi(api)} connected login={<p>login</p>} />);
    const pick = [...host.querySelectorAll("button")].find(x => x.textContent === "2026-11-03 10:00")!;
    await act(async () => { pick.click(); }); await flush();
    await act(async () => { resolveA(payload({ run_id: "run-a" })); }); await flush();
    expect(text()).toContain("run-b"); expect(host.querySelector("code.research-hash")).toBeTruthy();
    const ids = [...host.querySelectorAll("tr")].filter(r => r.textContent?.startsWith("Körnings-id")).map(r => r.textContent);
    expect(ids).toEqual(["Körnings-idrun-b"]);
  });
  it("utloggning medan ett resultat hämtas visar inget resultat eller fel efteråt", async () => {
    let resolve: (v: unknown) => void = () => {};
    const api = fakeApi([run({ status: "done" })], [() => new Promise(r => { resolve = r; })]);
    await render(<H0013Panel api={asApi(api)} connected login={<p>login</p>} />);
    await render(<H0013Panel api={asApi(api)} connected={false} login={<p>loginform</p>} />);
    await act(async () => { resolve(payload()); }); await flush(RETRY_MS);
    expect(text()).toContain("loginform"); expect(text()).not.toContain("HISTORIK · H-0013");
    expect(text()).not.toContain("kunde inte hämtas"); expect(api.payload).toHaveBeenCalledTimes(1);
  });
});

describe("Affärsloggen", () => {
  it.each([
    ["saknat fält", undefined, 4, null, "Affärsloggen saknas"],
    ["fel typ", "inte en lista", 4, null, "Affärsloggen saknas"],
  ])("%s visas som saknad, inte som noll affärer", async (_n, trades, reported, expected, shown) => {
    expect(readTrades(trades, reported).trades).toBe(expected);
    const v = readResult(payload({ trades, stats: { ...payload().stats, trades: reported } }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.missing).toContain("Affärslogg");
    await render(<H0013Result view={v} />);
    expect(text()).toContain(shown); expect(text()).not.toContain("av 0"); expect(text()).not.toContain("Affärsloggen är tom");
  });
  it("blandat giltiga och ogiltiga rader redovisas utan att döljas", async () => {
    const good = payload().trades[0];
    const v = readResult(payload({ trades: [good, { side: "Long" }, null, good], stats: { ...payload().stats, trades: 4 } }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.trades).toHaveLength(2); expect(v.missing).toContain("Fullständig affärslogg");
    await render(<H0013Result view={v} />);
    expect(text()).toContain("2 av 4 rader i affärsloggen kan inte läsas");
    expect(text()).toContain("Senaste 2 av 2 lästa rader");
  });
  it("avvikelse mot nyckeltalens antal redovisas", () => {
    expect(readTrades([payload().trades[0]], 4).issues).toContain("Affärsloggen har 1 rader men nyckeltalen anger 4 affärer.");
  });
  it("en verifierat tom logg med rapporterat antal 0 visas som tom", async () => {
    const v = readResult(payload({ trades: [], stats: { ...payload().stats, trades: 0 } }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.missing).not.toContain("Affärslogg"); expect(v.tradeIssues).toEqual([]);
    await render(<H0013Result view={v} />);
    expect(text()).toContain("Affärsloggen är tom; nyckeltalen anger också 0 affärer");
  });
});

describe("Jämförelsekurvor", () => {
  it("visas på samma staplar med källor, och byte av jämförelse ritar om utan NaN", async () => {
    const v = readResult(payload());
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.missing).toEqual([]);
    await render(<H0013Result view={v} />);
    expect(text()).toContain("Jämförelsekurvor på samma staplar"); expect(text()).toContain("3 punkter av 6570 staplar");
    expect(text()).toContain("fas2_eval.buy_and_hold"); expect(text()).toContain("b".repeat(64));
    const tab = [...host.querySelectorAll("button")].find(b => b.textContent === "Likaviktad blandning")!;
    await act(async () => { tab.click(); }); await flush();
    expect(text()).toContain("Likaviktad blandning");
    for (const d of paths()) expect(d).not.toMatch(/NaN|Infinity/);
  });
  it("ett äldre resultat utan kurvor visas med kurvorna som saknade och nyckeltalen kvar", async () => {
    const old = payload(); delete (old.curves as Record<string, unknown>).comparisons;
    const v = readResult(old);
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.comparisonCurves).toBeNull(); expect(v.missing).toEqual(["Jämförelsekurvor"]);
    await render(<H0013Result view={v} />);
    expect(text()).toContain("Jämförelsekurvorna saknas i resultatet"); expect(text()).toContain("Köp och behåll");
    expect(text()).toContain("HISTORIK · H-0013");
  });
  it.each([
    ["saknad kurva", { series: { ...comparisonCurves().series, risk_filter: undefined } }, "Kurvan saknas i resultatet."],
    ["fel längd", { series: { ...comparisonCurves().series, risk_filter: [1, 1.12] } }, "andra tidpunkter"],
    ["ogiltigt värde", { series: { ...comparisonCurves().series, risk_filter: [1, null, 1.12] } }, "ogiltiga värden"],
    ["slutvärde mot nyckeltal", { series: { ...comparisonCurves().series, risk_filter: [1, 1, 1.5] } }, "stämmer inte med nyckeltalen"],
  ])("%s visas som saknad, inte ritad", async (_n, over, problem) => {
    const v = readResult(payload({ curves: { ...payload().curves, comparisons: comparisonCurves(JSON.parse(JSON.stringify(over))) } }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    const bad = v.comparisonCurves!.curves.find(c => c.key === "risk_filter")!;
    expect(bad.data).toBeNull(); expect(bad.problem).toContain(problem.replace(".", ""));
    expect(v.missing).toEqual(["Kurva: Riskfilter (EMA, platt i ned/hög vol)"]);
    await render(<H0013Result view={v} />);
    const tab = [...host.querySelectorAll("button")].find(b => b.textContent?.startsWith("Riskfilter"))!;
    await act(async () => { tab.click(); }); await flush();
    expect(text()).toContain(problem.replace(".", ""));
  });
  it("utan giltig tidsaxel räknas alla kurvor som saknade", () => {
    expect(readComparisonCurves({ t: ["x"], series: {} }, {})).toBeNull();
    expect(readComparisonCurves({ t: "nope" }, {})).toBeNull();
    expect(readComparisonCurves(undefined, {})).toBeNull();
  });
});

describe("Jämförelsekurvornas tidsaxel (granskning av PR #78)", () => {
  const withAxis = (t: unknown) => payload({ curves: { ...payload().curves, comparisons: comparisonCurves({ t }) } });
  it.each([
    ["inte datum", ["x", "y", "z"], "inte är UTC-tidpunkter"],
    ["dubbletter", [MAIN_T[0], MAIN_T[0], MAIN_T[0]], "inte strikt stigande"],
    ["fallande", [...MAIN_T].reverse(), "inte strikt stigande"],
    ["slutprovet", ["2025-01-01T00:00:00+00:00", "2025-01-01T04:00:00+00:00", "2025-01-01T08:00:00+00:00"], "utanför testfönstren"],
    ["utan UTC", ["2022-01-01T04:00:00", "2022-01-01T08:00:00", "2022-01-01T12:00:00"], "inte är UTC-tidpunkter"],
    ["fel tidszon", ["2022-01-01T05:00:00+01:00", "2022-01-01T09:00:00+01:00", "2022-01-01T13:00:00+01:00"], "inte är UTC-tidpunkter"],
    ["utanför rutnätet", ["2022-01-01T04:30:00+00:00", "2022-01-01T08:30:00+00:00", "2022-01-01T12:30:00+00:00"], "4h-rutnätet"],
    ["före testfönstren", ["2021-12-31T12:00:00+00:00", "2021-12-31T16:00:00+00:00", "2021-12-31T20:00:00+00:00"], "utanför testfönstren"],
    ["inte i huvudkurvan", ["2022-01-02T04:00:00+00:00", "2022-01-02T08:00:00+00:00", "2022-01-02T12:00:00+00:00"], "inte finns i huvudkurvan"],
  ])("%s avvisas och visas som saknade kurvor med förklaring", async (_n, t, problem) => {
    const v = readResult(withAxis(t));
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.comparisonCurves?.axisProblem).toContain(problem);
    expect(v.comparisonCurves?.curves.every(c => c.data === null)).toBe(true);
    expect(v.missing).toEqual(["Jämförelsekurvor (ogiltig tidsaxel)"]);
    await render(<H0013Result view={v} />);
    expect(text()).toContain("Jämförelsekurvorna kan inte visas"); expect(text()).toContain(problem);
    expect(text()).toContain("Köp och behåll"); expect(text()).toContain("HISTORIK · H-0013");
  });
  it("H-0013-värden som inte stämmer med huvudkurvan vid samma tidpunkter visas inte", () => {
    const series = { ...comparisonCurves().series, h0013: [1, 1.07, 1.12] };
    const v = readResult(payload({ curves: { ...payload().curves, comparisons: comparisonCurves({ series }) } }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    const own = v.comparisonCurves!.curves.find(c => c.key === "h0013")!;
    expect(own.data).toBeNull(); expect(own.problem).toContain("stämmer inte med huvudkurvan");
    expect(v.missing).toEqual(["Kurva: H-0013"]);
  });
  it("avrundning inom toleransen godtas", () => {
    const series = { ...comparisonCurves().series, h0013: MAIN_EQUITY.map(x => x * (1 + CURVE_TOLERANCE / 10)) };
    const v = readResult(payload({ curves: { ...payload().curves, comparisons: comparisonCurves({ series }) } }));
    expect(v.ok && v.comparisonCurves!.curves.every(c => c.data !== null)).toBe(true);
  });
  it("utan huvudkurva kan tidsaxeln inte kopplas och kurvorna visas som saknade", () => {
    const v = readResult(payload({ curves: { comparisons: comparisonCurves() } }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.comparisonCurves?.axisProblem).toContain("Huvudkurvan saknas");
    expect(v.missing).toEqual(expect.arrayContaining(["Kapitalkurva", "Jämförelsekurvor (ogiltig tidsaxel)"]));
  });
  it("fixturens huvudkurva och jämförelsekurvor är samma serie", () => {
    const p = payload();
    expect(p.curves.comparisons.t).toEqual(p.curves.t);
    expect(p.curves.comparisons.series.h0013).toEqual(p.curves.equity);
    expect(comparisonAxisProblem(p.curves.comparisons.t, { t: p.curves.t, equity: p.curves.equity })).toBeNull();
  });
});
