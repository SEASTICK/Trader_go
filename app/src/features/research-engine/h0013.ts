// H-0013 (Fas 2) i Research Lab: det låsta protokollet och en strikt läsning av körningar och resultat.
// Inga värden hittas på. Saknas något i resultatet visas det som saknat, och ett resultat som inte följer
// kontraktet (beslut som inte följer kriterierna, slutprov läst, simulerad data) visas inte som ett verkligt resultat.
import type { Run } from "./api";

export const H0013 = "H-0013";

// Samma värden som research/fas2-protokoll.md, engine/traderlab/fas2.py och supabase/migrations/0005_h0013_queue.sql.
// Testet h0013.test.ts jämför dem med källorna.
export const PROTOCOL = {
  hypothesis: H0013,
  protocolFile: "research/fas2-protokoll.md",
  strategy: "h0013_adaptive_playbook",
  version: "h0013-evaluation/1.0.0",
  market: "um", symbol: "BTCUSDT", interval: "4h",
  development: ["2020-01-01", "2025-01-01"] as const,
  testStarts: ["2022-01-01", "2022-07-01", "2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"],
  holdout: "2025-01-01 och framåt, låst",
  candidates: { ema_adx_trend: "1.0.0", bb_rsi_reversion: "1.0.0", platt: null } as Record<string, string | null>,
  costs: { fee_bps: 10, spread_bps: 2, slippage_bps: 5 },
  capital: 100000,
  nPermutations: 200,
  playbooks: 81,
  tRequired: 2.67,
  registeredN: 13,
  minTrades: 20,
  dataset: "6a84c4f44026b6be270ed2f9395edace5edbd598dfdf683428b9f025a64c042c",
};

export const CRITERIA: Record<string, string> = {
  t_at_least_required: "Statistisk styrka minst kravet 2,67",
  stressed_costs_positive: "Positivt med 2,5 gånger kostnaderna",
  sharpe_above_buy_and_hold: "Högre Sharpe än köp och behåll",
  sharpe_above_best_candidate: "Högre Sharpe än bästa ensamma kandidat",
  sharpe_above_equal_weight_mix: "Högre Sharpe än likaviktad blandning",
};
export const COMPARISONS: Record<string, string> = {
  buy_and_hold: "Köp och behåll", ema_adx_trend: "EMA / ADX-trend ensam", bb_rsi_reversion: "Bollinger / RSI ensam",
  equal_weight_mix: "Likaviktad blandning", risk_filter: "Riskfilter (EMA, platt i ned/hög vol)",
};
export const REGIMES = ["upp/hög vol", "upp/låg vol", "ned/hög vol", "ned/låg vol", "okänt"];
export const CHOICES: Record<string, string> = { ema_adx_trend: "EMA / ADX-trend", bb_rsi_reversion: "Bollinger / RSI", platt: "Platt" };

export const STATUS: Record<Run["status"], string> = { queued: "I kö", running: "Körs", done: "Klar", failed: "Misslyckad", cancelled: "Avbruten" };
export const MAX_ATTEMPTS = 3;

export function isH0013(run: Pick<Run, "hypothesis_id">) { return run.hypothesis_id === H0013; }

/** Kan en ny H-0013-körning köas? Kön kräver att ingen körning är aktiv och att inget resultat finns. */
export function enqueueBlocker(runs: Run[]): string | null {
  const own = runs.filter(isH0013);
  if (own.some(r => r.status === "queued" || r.status === "running")) return "En H-0013-körning är redan köad eller pågår.";
  if (own.some(r => r.status === "done")) return "H-0013 har redan ett resultat. En ny körning kräver ett nytt beslut.";
  return null;
}

export function describeRun(run: Run) {
  const attempts = typeof run.attempts === "number" ? run.attempts : null;
  return {
    status: STATUS[run.status] ?? run.status,
    progress: Math.max(0, Math.min(1, Number.isFinite(run.progress) ? run.progress : 0)),
    attempts: attempts === null ? "Saknas" : `${attempts} av ${MAX_ATTEMPTS}`,
    canCancel: run.status === "queued" || run.status === "running",
    error: run.error ?? null,
  };
}

type Dict = Record<string, unknown>;
const isDict = (v: unknown): v is Dict => typeof v === "object" && v !== null && !Array.isArray(v);
const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
const str = (v: unknown) => (typeof v === "string" && v ? v : null);

export type Summary = { total_return: number | null; sharpe: number | null; t: number | null; max_drawdown: number | null;
  trades: number | null; ci: [number | null, number | null]; without_best_year_sharpe: number | null; best_year: string | null };
function summary(v: unknown): Summary | null {
  if (!isDict(v)) return null;
  const ci = Array.isArray(v.sharpe_ci95) ? v.sharpe_ci95 : [];
  const wby = isDict(v.without_best_year) ? v.without_best_year : {};
  return { total_return: num(v.total_return), sharpe: num(v.sharpe), t: num(v.t_daily_nw), max_drawdown: num(v.max_drawdown),
    trades: num(v.trades), ci: [num(ci[0]), num(ci[1])], without_best_year_sharpe: num(wby.sharpe), best_year: str(v.best_year) };
}

export type H0013View =
  | { ok: false; reasons: string[] }
  | { ok: true; decision: "REJECT" | "MORE_RESEARCH"; criteria: [string, boolean][]; main: Summary;
      stressedReturn: number | null; comparisons: [string, Summary | null][];
      regimes: { label: string; days: number | null; trades: number | null; return: number | null; sharpe: number | null }[];
      windows: { test: string; train: string; choices: [string, string][]; trades: number | null; localReturn: number | null }[];
      finalPlaybook: [string, string][] | null;
      permutation: { p: number | null; n: number | null; k: number | null } | null;
      deflated: { standard: number | null; playbooks: number | null } | null;
      tRequiredNow: number | null; equity: { t: string[]; equity: number[] } | null;
      trace: { label: string; value: string }[]; trades: Dict[]; warnings: string[]; missing: string[] };

/** Läser ett H-0013-resultat från kön. Returnerar skälen om det inte kan visas som ett verkligt resultat. */
export function readResult(payload: unknown): H0013View {
  if (!isDict(payload)) return { ok: false, reasons: ["Resultatet saknas."] };
  const reasons: string[] = [];
  if (payload.hypothesis_id !== H0013) reasons.push("Resultatet gäller inte H-0013.");
  if (payload.evaluation_version !== PROTOCOL.version) reasons.push("Okänd utvärderingsversion.");
  if (payload.status !== "completed") reasons.push("Körningen är inte fullständig.");
  if (payload.holdout_loaded !== false) reasons.push("Det går inte att visa att slutprovet var oläst.");
  if (payload.dataset_sha256 !== PROTOCOL.dataset) reasons.push("Datasetet är inte det frysta datasetet.");
  const inner = isDict(payload.result) ? payload.result : {};
  if (payload.simulated === true || inner.simulated === true) reasons.push("Simulerad data visas inte som resultat.");
  const crit = isDict(payload.criteria) ? payload.criteria : null;
  const keys = Object.keys(CRITERIA);
  if (!crit || Object.keys(crit).sort().join() !== [...keys].sort().join() || !keys.every(k => typeof crit[k] === "boolean")) {
    reasons.push("Kriterierna följer inte kontraktet.");
  } else {
    const expected = keys.every(k => crit[k] === true) ? "MORE_RESEARCH" : "REJECT";
    if (payload.decision !== expected) reasons.push("Beslutet följer inte kriterierna.");
  }
  const main = summary(payload.stats);
  if (!main) reasons.push("Nyckeltalen saknas.");
  if (reasons.length) return { ok: false, reasons };

  const missing: string[] = [];
  const need = <T,>(label: string, value: T | null): T | null => { if (value === null) missing.push(label); return value; };
  const comparisonsRaw = isDict(inner.comparisons) ? inner.comparisons : {};
  const comparisons = Object.keys(COMPARISONS).map(k => [k, summary(comparisonsRaw[k])] as [string, Summary | null]);
  comparisons.forEach(([k, s]) => { if (!s) missing.push(COMPARISONS[k]); });
  const regimesRaw = isDict(inner.regimes) ? inner.regimes : null;
  if (!regimesRaw) missing.push("Resultat per marknadsläge");
  const regimes = REGIMES.map(label => {
    const r = regimesRaw && isDict(regimesRaw[label]) ? regimesRaw[label] as Dict : {};
    return { label, days: num(r.days), trades: num(r.trades), return: num(r.return), sharpe: num(r.sharpe) };
  });
  const wf = isDict(inner.walk_forward) ? inner.walk_forward : {};
  const choicesOf = (book: unknown): [string, string][] | null => {
    const choices = isDict(book) && isDict(book.choices) ? book.choices : null;
    return choices ? REGIMES.slice(0, 4).map(l => [l, CHOICES[String(choices[l])] ?? "Saknas"] as [string, string]) : null;
  };
  const windows = (Array.isArray(wf.windows) ? wf.windows : []).filter(isDict).map(w => ({
    test: Array.isArray(w.test) ? w.test.join(" → ") : "Saknas", train: Array.isArray(w.train) ? w.train.join(" → ") : "Saknas",
    choices: choicesOf(w.playbook) ?? [], trades: num(w.trades), localReturn: num(w.local_return) }));
  if (windows.length !== PROTOCOL.testStarts.length) missing.push("Alla sex testfönster");
  const finalPlaybook = choicesOf(isDict(wf.final) ? wf.final.playbook : null);
  if (!finalPlaybook) missing.push("Slutlig spelbok");
  const perm = isDict(inner.permutation) ? inner.permutation : null;
  if (!perm) missing.push("Permutationstest");
  const dsr = isDict(inner.deflated_sharpe) ? inner.deflated_sharpe : null;
  if (!dsr) missing.push("Deflated Sharpe");
  const stressed = isDict(inner.stressed) ? num(inner.stressed.total_return) : null;
  const curves = isDict(payload.curves) ? payload.curves : {};
  const equity = Array.isArray(curves.t) && Array.isArray(curves.equity) && curves.t.length === curves.equity.length && curves.t.length > 1
    && curves.equity.every(v => typeof v === "number" && Number.isFinite(v))
    ? { t: curves.t.map(String), equity: curves.equity as number[] } : null;
  if (!equity) missing.push("Kapitalkurva");
  const revision = isDict(payload.revision) ? payload.revision : {};
  const data = isDict(payload.data) ? payload.data : {};
  const trace = [
    ["Kodrevision", need("Kodrevision", str(revision.commit))],
    ["Dataset", PROTOCOL.dataset],
    ["Inlästa data (SHA-256)", need("Datafingeravtryck", str(data.sha256))],
    ["Manifest (SHA-256)", need("Manifest", str(payload.manifest_sha256))],
    ["Utvärdering", PROTOCOL.version],
    ["Körnings-id", need("Körnings-id", str(payload.run_id))],
    ["Försök", num(payload.attempt) === null ? null : String(payload.attempt)],
  ].map(([label, value]) => ({ label: String(label), value: value ?? "Saknas" }));
  return {
    ok: true, decision: payload.decision as "REJECT" | "MORE_RESEARCH",
    criteria: keys.map(k => [k, (crit as Dict)[k] as boolean]), main: main!, stressedReturn: need("Kostnadsstress", stressed),
    comparisons, regimes, windows, finalPlaybook,
    permutation: perm ? { p: num(perm.p_value), n: num(perm.n), k: num(perm.at_least_as_high) } : null,
    deflated: dsr ? { standard: num(dsr.default_variance), playbooks: num(dsr.playbook_variance) } : null,
    tRequiredNow: num(inner.t_required_now), equity, trace,
    trades: (Array.isArray(payload.trades) ? payload.trades : []).filter(isDict),
    warnings: (Array.isArray(payload.warnings) ? payload.warnings : []).filter((w): w is string => typeof w === "string"),
    missing,
  };
}

export function drawdown(equity: number[]) {
  let peak = -Infinity;
  return equity.map(v => { peak = Math.max(peak, v); return v / peak - 1; });
}
