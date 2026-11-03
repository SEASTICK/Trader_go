// Syntetiska H-0013-resultat för testerna. Inga riktiga värden.
import type { Run } from "./api";
import { PROTOCOL } from "./h0013";

export const crit = { t_at_least_required: false, stressed_costs_positive: false, sharpe_above_buy_and_hold: true,
  sharpe_above_best_candidate: false, sharpe_above_equal_weight_mix: false };
export const summary = (sharpe: number) => ({ total_return: 0.12, sharpe, t_daily_nw: 1.1, sharpe_ci95: [-0.4, 1.3], max_drawdown: -0.21,
  trades: 40, best_year: "2023", without_best_year: { total_return: 0.01, sharpe: 0.05 } });
export const book = (c: string) => ({ contract: "h0013-adaptive/1.0.0", choices: { "upp/hög vol": c, "upp/låg vol": "platt", "ned/hög vol": "platt", "ned/låg vol": "bb_rsi_reversion" } });
export const CURVE_NAMES = ["h0013", "buy_and_hold", "ema_adx_trend", "bb_rsi_reversion", "equal_weight_mix", "risk_filter"];
/** Kurvor som slutar i 1 + total_return (0,12 för alla syntetiska sammanfattningar). */
/** Huvudkurvan och jämförelsekurvorna är samma serie: samma tidpunkter, och H-0013-värdena är huvudkurvans. */
export const MAIN_T = ["2022-01-01T04:00:00+00:00", "2022-01-01T08:00:00+00:00", "2022-01-01T12:00:00+00:00"];
export const MAIN_EQUITY = [1, 1.05, 1.12];
export function comparisonCurves(over: Record<string, unknown> = {}) {
  return { t: MAIN_T, points: 3, bars: 6570,
    series: Object.fromEntries(CURVE_NAMES.map((k, i) => [k, k === "h0013" ? MAIN_EQUITY : [1, 1 + 0.01 * i, 1.12]])),
    sources: Object.fromEntries(CURVE_NAMES.map(k => [k, { source: `fas2_eval.${k}`, bars: 6570, returns_sha256: k[0].repeat(64) }])),
    start_capital: 1, evaluation_version: "h0013-evaluation/1.0.0", ...over };
}
export function payload(over: Record<string, unknown> = {}, inner: Record<string, unknown> = {}) {
  return {
    mode: "registered", hypothesis_id: "H-0013", evaluation_version: "h0013-evaluation/1.0.0", status: "completed",
    decision: "REJECT", criteria: crit, stats: { ...summary(0.4), trades: 1 }, curves: { t: MAIN_T, equity: MAIN_EQUITY, comparisons: comparisonCurves() },
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

export const run = (over: Partial<Run>): Run => ({ id: "run-1", kind: "registered", hypothesis_id: "H-0013", attempts: 1, strategy: PROTOCOL.strategy,
  market: "um", interval: "4h", status: "queued", progress: 0, error: null, created_at: "2026-11-03T09:00:00Z",
  period_start: "2020-01-01T00:00:00Z", period_end: "2025-01-01T00:00:00Z", params: {}, ...over });
