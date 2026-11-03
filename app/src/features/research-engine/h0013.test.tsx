// H-0013 i Research Lab med syntetiska resultat och simulerade köanrop. Inget nätverk, ingen riktig körning.
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { ResearchApi, Run } from "./api";
import { CRITERIA, describeRun, enqueueBlocker, PROTOCOL, readResult } from "./h0013";
import { H0013Intro, H0013Result, PrepareCard, ProtocolCard, RunDetail, RunsCard } from "./H0013Panel";

const repo = (path: string) => readFileSync(new URL("../../../../" + path, import.meta.url), "utf8");
afterEach(() => vi.unstubAllGlobals());

const crit = { t_at_least_required: false, stressed_costs_positive: false, sharpe_above_buy_and_hold: true,
  sharpe_above_best_candidate: false, sharpe_above_equal_weight_mix: false };
const summary = (sharpe: number) => ({ total_return: 0.12, sharpe, t_daily_nw: 1.1, sharpe_ci95: [-0.4, 1.3], max_drawdown: -0.21,
  trades: 40, best_year: "2023", without_best_year: { total_return: 0.01, sharpe: 0.05 } });
const book = (c: string) => ({ contract: "h0013-adaptive/1.0.0", choices: { "upp/hög vol": c, "upp/låg vol": "platt", "ned/hög vol": "platt", "ned/låg vol": "bb_rsi_reversion" } });
function payload(over: Record<string, unknown> = {}, inner: Record<string, unknown> = {}) {
  return {
    mode: "registered", hypothesis_id: "H-0013", evaluation_version: "h0013-evaluation/1.0.0", status: "completed",
    decision: "REJECT", criteria: crit, stats: summary(0.4), curves: { t: ["2022-01-01T04:00:00+00:00", "2022-01-01T08:00:00+00:00", "2022-01-01T12:00:00+00:00"], equity: [1, 1.02, 0.99] },
    dataset_sha256: PROTOCOL.dataset, manifest_sha256: "m".repeat(64), holdout_loaded: false, attempt: 1, run_id: "run-1",
    data: { sha256: "d".repeat(64) }, revision: { commit: "c".repeat(40), source: "TRADERGO_REVISION" },
    trades: [{ side: "Long", entry_time: "2022-01-03T04:00:00+00:00", exit_time: "2022-01-04T00:00:00+00:00", net_return: 0.01, exit_reason: "signal" }],
    warnings: ["Historisk forskning på utvecklingsperioden 2020–2024; slutprovet har inte lästs"],
    result: { simulated: false, t_required_now: 2.71, stressed: summary(0.1),
      comparisons: { buy_and_hold: summary(0.3), ema_adx_trend: summary(0.5), bb_rsi_reversion: summary(0.2), equal_weight_mix: summary(0.45), risk_filter: summary(0.35) },
      regimes: Object.fromEntries(["upp/hög vol", "upp/låg vol", "ned/hög vol", "ned/låg vol", "okänt"].map(l => [l, { days: 100, trades: 5, return: 0.01, sharpe: 0.2 }])),
      walk_forward: { windows: PROTOCOL.testStarts.map((s, i) => ({ train: ["2020-01-01", s], test: [s, PROTOCOL.testStarts[i + 1] ?? "2025-01-01"], playbook: book("ema_adx_trend"), trades: 6, local_return: 0.02 })), final: { playbook: book("platt") } },
      permutation: { n: 200, at_least_as_high: 37, p_value: 0.185 }, deflated_sharpe: { default_variance: 0.31, playbook_variance: 0.28 }, ...inner },
    ...over,
  };
}

describe("Låst protokoll", () => {
  it("stämmer med migrationen, motorn och workerns kontrakt", () => {
    const sql = repo("supabase/migrations/0005_h0013_queue.sql");
    expect(sql).toContain(`'${PROTOCOL.strategy}', '${PROTOCOL.version}'`);
    expect(sql).toContain(`"n_permutations":${PROTOCOL.nPermutations},"playbooks":${PROTOCOL.playbooks}`);
    expect(sql).toContain(`'${PROTOCOL.development[0]}T00:00:00Z', '${PROTOCOL.development[1]}T00:00:00Z'`);
    expect(sql).toContain(JSON.stringify(PROTOCOL.costs));
    expect(sql).toContain(PROTOCOL.dataset);
    const fas2 = repo("engine/traderlab/fas2.py");
    expect(fas2).toContain(`TEST_STARTS = ${JSON.stringify(PROTOCOL.testStarts).split(",").join(", ")}`);
    expect(fas2).toContain(`MIN_TRADES = ${PROTOCOL.minTrades}`);
    const evaluation = repo("engine/traderlab/fas2_eval.py");
    expect(evaluation).toContain(`T_REQUIRED = ${PROTOCOL.tRequired}`);
    expect(evaluation).toContain(`REGISTERED_N = ${PROTOCOL.registeredN}`);
    expect(evaluation).toContain(`EVALUATION_VERSION = "${PROTOCOL.version}"`);
    expect(repo("engine/traderlab/research_engine/h0013.py")).toContain(`DATASET = "${PROTOCOL.dataset}"`);
    expect(repo("research/registry.md")).toMatch(/^\| H-0013 \|/m);
    expect(Object.keys(CRITERIA).sort()).toEqual(Object.keys(crit).sort());
  });
  it("visas som låsta inställningar", () => {
    const html = renderToStaticMarkup(<ProtocolCard />);
    expect(html).toContain("Låsta inställningar"); expect(html).toContain(PROTOCOL.dataset);
    expect(html).toContain("2025-01-01 och framåt, låst"); expect(html).not.toMatch(/<input|<select|<textarea/);
  });
});

describe("Läsning av resultat", () => {
  it("visar ett kontraktsenligt resultat med spårbarhet och utan SIM", () => {
    const v = readResult(payload());
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.decision).toBe("REJECT"); expect(v.criteria).toHaveLength(5); expect(v.missing).toEqual([]);
    expect(v.windows).toHaveLength(6); expect(v.windows[0].choices[0]).toEqual(["upp/hög vol", "EMA / ADX-trend"]);
    expect(v.trace.find(t => t.label === "Kodrevision")?.value).toBe("c".repeat(40));
    const html = renderToStaticMarkup(<H0013Result view={v} />);
    expect(html).toContain("HISTORIK · H-0013"); expect(html).toContain("REJECT");
    expect(html).not.toMatch(/SIMULERAD|SIM\b/); expect(html).toContain("Köp och behåll"); expect(html).toContain("0,19");
  });
  it("accepterar MORE_RESEARCH bara när alla fem kriterier är uppfyllda", () => {
    const all = Object.fromEntries(Object.keys(crit).map(k => [k, true]));
    expect(readResult(payload({ decision: "MORE_RESEARCH", criteria: all })).ok).toBe(true);
    expect(readResult(payload({ decision: "MORE_RESEARCH" })).ok).toBe(false);
    expect(readResult(payload({ decision: "REJECT", criteria: all })).ok).toBe(false);
  });
  it.each([
    ["hypotes", { hypothesis_id: "H-0012" }], ["version", { evaluation_version: "h0013-evaluation/2.0.0" }],
    ["ofullständig", { status: "aborted" }], ["slutprov läst", { holdout_loaded: true }], ["slutprov som sträng", { holdout_loaded: "false" }],
    ["fel dataset", { dataset_sha256: "f".repeat(64) }], ["simulerad", { simulated: true }],
    ["saknat kriterium", { criteria: { ...crit, t_at_least_required: undefined } }], ["extra kriterium", { criteria: { ...crit, stability: true } }],
    ["kriterium som sträng", { criteria: { ...crit, t_at_least_required: "false" } }], ["nyckeltal saknas", { stats: undefined }],
  ])("visas inte som verkligt resultat: %s", (_name, over) => {
    const v = readResult(JSON.parse(JSON.stringify(payload(over as Record<string, unknown>))));
    expect(v.ok).toBe(false);
    const html = renderToStaticMarkup(<H0013Result view={v} />);
    expect(html).toContain("Resultatet kan inte visas"); expect(html).not.toContain("HISTORIK · H-0013");
  });
  it("visar saknade delar som saknade, utan att fylla i värden", () => {
    const v = readResult(payload({ curves: undefined, revision: undefined }, { comparisons: { buy_and_hold: summary(0.3) }, permutation: undefined, walk_forward: {} }));
    expect(v.ok).toBe(true); if (!v.ok) return;
    expect(v.missing).toEqual(expect.arrayContaining(["Kapitalkurva", "Kodrevision", "Permutationstest", "Alla sex testfönster", "Slutlig spelbok", "EMA / ADX-trend ensam"]));
    const html = renderToStaticMarkup(<H0013Result view={v} />);
    expect(html).toContain("Saknas i resultatet"); expect(html).toContain("Kapitalkurvan saknas i resultatet");
    expect(html).toContain("Kodrevision</th><td><code class=\"research-hash\">Saknas");
  });
});

const run = (over: Partial<Run>): Run => ({ id: "run-1", kind: "registered", hypothesis_id: "H-0013", attempts: 1, strategy: PROTOCOL.strategy,
  market: "um", interval: "4h", status: "queued", progress: 0, error: null, created_at: "2026-11-03T09:00:00Z",
  period_start: "2020-01-01T00:00:00Z", period_end: "2025-01-01T00:00:00Z", params: {}, ...over });

describe("Kö, förlopp, fel och avbrott", () => {
  it("visar status, förlopp, försök och avbrott", () => {
    expect(describeRun(run({ status: "running", progress: 0.42, attempts: 2 }))).toMatchObject({ status: "Körs", progress: 0.42, attempts: "2 av 3", canCancel: true });
    expect(describeRun(run({ status: "failed", error: "Arkiven matchar inte" })).canCancel).toBe(false);
    const html = renderToStaticMarkup(<RunsCard runs={[run({ status: "running", progress: 0.42, attempts: 2 })]} selected="run-1" busy={false} onSelect={() => {}} onCancel={() => {}} />);
    expect(html).toContain("Körs"); expect(html).toContain("42 %"); expect(html).toContain("2 av 3"); expect(html).toContain("Avbryt");
  });
  it.each([
    ["queued", "Inget resultat ännu"], ["running", "Inget resultat ännu"],
    ["failed", "Misslyckad: Worker stoppad eller tidsgräns nådd"], ["cancelled", "Avbruten. Inget resultat finns"],
  ])("en %s körning visar inget resultat", (status, text) => {
    const html = renderToStaticMarkup(<RunDetail run={run({ status: status as Run["status"], error: status === "failed" ? "Worker stoppad eller tidsgräns nådd" : null })} payload={undefined} />);
    expect(html).toContain(text); expect(html).not.toContain("HISTORIK · H-0013");
  });
  it("en klar körning utan resultat visar att resultatet saknas", () => {
    expect(renderToStaticMarkup(<RunDetail run={run({ status: "done" })} payload={null} />)).toContain("Resultatet saknas");
  });
  it("tillåter bara förberedelse när ingen körning är aktiv och inget resultat finns", () => {
    expect(enqueueBlocker([])).toBeNull();
    expect(enqueueBlocker([run({ status: "running" })])).toMatch(/redan köad eller pågår/);
    expect(enqueueBlocker([run({ status: "done" })])).toMatch(/redan ett resultat/);
    expect(enqueueBlocker([run({ status: "failed" }), run({ id: "x", status: "cancelled" })])).toBeNull();
    const props = { preparing: false, confirmed: false, busy: false, onPrepare() {}, onConfirm() {}, onClose() {}, onEnqueue() {} };
    expect(renderToStaticMarkup(<PrepareCard runs={[run({ status: "done" })]} {...props} />)).not.toContain("Köa H-0013");
    const prepared = renderToStaticMarkup(<PrepareCard runs={[]} {...props} preparing />);
    expect(prepared).toMatch(/<button class="btn accent" disabled="">Köa H-0013/);
    expect(renderToStaticMarkup(<PrepareCard runs={[]} {...props} preparing confirmed />)).toMatch(/<button class="btn accent">Köa H-0013/);
  });
  it("visar att inget resultat finns ännu, och skiljer H-0013 från Fas 1 och tvärsnitt", () => {
    const html = renderToStaticMarkup(<H0013Intro hasResult={false} connected />);
    expect(html).toContain("Inget resultat ännu"); expect(html).toContain("H-0009–H-0012"); expect(html).toContain("H-0014, H-0015");
  });
});

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const session = { access_token: "user-session", refresh_token: "refresh", expires_in: 3600 };
async function signedIn(...rest: Response[]) {
  const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response([{ user_id: "member" }]));
  rest.forEach(r => fetcher.mockResolvedValueOnce(r));
  vi.stubGlobal("fetch", fetcher);
  const api = new ResearchApi(); await api.signIn("member@example.test", "password");
  return { api, fetcher };
}

describe("Simulerade köanrop", () => {
  it("köar bara den fasta körningen med användarens token och en nyckel", async () => {
    const { api, fetcher } = await signedIn(response("new-run-id"));
    expect(await api.enqueueH0013("key-1")).toBe("new-run-id");
    const [url, init] = fetcher.mock.calls[2];
    expect(url).toMatch(/\/rest\/v1\/rpc\/research_enqueue_h0013$/);
    expect(JSON.parse(init.body)).toEqual({ p_request_key: "key-1" });
    expect(init.headers.Authorization).toBe("Bearer user-session");
  });
  it("läser bara H-0013-körningar och resultat", async () => {
    const { api, fetcher } = await signedIn(response([run({})]), response([{ payload: payload() }]));
    expect((await api.h0013Runs())[0].hypothesis_id).toBe("H-0013");
    expect(fetcher.mock.calls[2][0]).toContain("hypothesis_id=eq.H-0013");
    expect(readResult(await api.payload("run-1")).ok).toBe(true);
  });
  it("visar databasens avvisning och upprepar inte köanropet", async () => {
    const { api, fetcher } = await signedIn(response({ message: "H-0013 har redan ett resultat; en ny körning kräver ett nytt beslut" }, 400));
    await expect(api.enqueueH0013("key-2")).rejects.toThrow("Begäran nekades: H-0013 har redan ett resultat");
    expect(fetcher).toHaveBeenCalledTimes(3);
  });
});
