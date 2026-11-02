// Simulerade mätvärden för rutorna i Research. Allt härifrån är PÅHITTAT och visar inga resultat.
// Samma id ger alltid samma siffror (fast frö), så ni ser samma sak.
import { hashSeed, rng, walk } from "./sim";
import { tKrav } from "./stats";

export type Experiment = {
  id: string; spår: string; namn: string; strategi: string; grupp: string;
  marknad: string; tidsram: string; riktning: string;
  mål?: Mål;   // forskningsspår (research/tracks.md), standard A
};

/** Forskningsspåren i research/tracks.md. Kriterierna är bestämda innan något i spåret kördes. */
export type Mål = "A" | "B" | "C";
export const MÅL: { key: Mål; label: string; desc: string; krav: string }[] = [
  { key: "A", label: "Slå marknaden", desc: "Bättre riskjusterad avkastning än att bara köpa och behålla.",
    krav: "t över kravet, plus även med 2,5 gånger kostnaderna, och högre Sharpe än köp-och-behåll." },
  { key: "B", label: "Lägre risk", desc: "En jämnare resa med betydligt mindre fall.",
    krav: "t över kravet, plus även med 2,5 gånger kostnaderna, och minst 40 % mindre största fall än köp-och-behåll." },
  { key: "C", label: "Marknadsneutral", desc: "Tjänar pengar oavsett om Bitcoin går upp eller ned.",
    krav: "t över kravet, plus även med 2,5 gånger kostnaderna, och följer Bitcoin högst lite (beta mellan −0,2 och 0,2)." },
];
export const målFör = (e: Experiment): Mål => e.mål ?? "A";

export type Trade = { nr: number; datum: string; riktning: "Long" | "Short"; in: number; ut: number; brutto: number; kostnad: number; netto: number };
export type Position = { läge: "Long" | "Short" | "Ingen"; sedan?: string; storlek?: number; orealiserat?: number };

export type Källa = "SIM" | "HISTORIK";

export type Computed = {
  exp: Experiment;
  källa: Källa;
  krav?: number;              // eget krav från registret (bara HISTORIK)
  passes?: boolean;
  deflated?: number | null;   // Deflated Sharpe, 0..1
  stressad?: number;          // avkastning i procent med 2,5 gånger kostnaderna
  beta?: number | null;       // mot Bitcoin, dagsavkastning (bara HISTORIK)
  klararMål?: boolean;        // alla kriterier i rutans spår (bara HISTORIK)
  fas1?: { windows: NonNullable<RealResult["windows"]>; stability: number | null; runId: string };
  hypotes?: string;
  registerCommit?: string;
  period?: [string, string];
  resultatfil?: string;
  trades: Trade[];
  /** Riktiga affärer med tider och priser (bara HISTORIK), för markörer i prisdiagrammet. */
  affärer?: { entry_time: string; exit_time: string | null; side: string; entry_price: number; exit_price: number | null }[];
  equity: number[];
  baseline: number[];
  labels: string[];
  avkastning: number;     // procent, efter kostnader
  maxDrawdown: number;    // procent, negativt
  antal: number;
  vinstandel: number;     // procent
  t: number;              // förenklat t-värde per affär
  position: Position;
  kostnadPerAffär: number;
};

const STEP_DAYS: Record<string, number> = { "1h": 0.5, "4h": 1.5, "1d": 4, "1 mån": 30 };
const SD: Record<string, number> = { "1h": 0.008, "4h": 0.015, "1d": 0.025, "1 mån": 0.05 };

const fmtDate = (d: Date) => d.toLocaleDateString("sv-SE", { day: "numeric", month: "short", year: "2-digit" });

export function compute(exp: Experiment): Computed {
  const r = rng(hashSeed(exp.id));
  const n = 24 + Math.floor(r() * 26);
  const step = STEP_DAYS[exp.tidsram] ?? 4;
  const sd = SD[exp.tidsram] ?? 0.025;
  const mu = (r() - 0.5) * 0.006; // slumpat kring noll
  const cost = exp.grupp === "terminer" ? 0.0016 : exp.grupp === "aktier" ? 0.0008 : 0.0012; // avgift + spread + slippage (+ ränta)
  const end = Date.now();
  const trades: Trade[] = [];
  let equity = 100, price = 100;
  const eq = [100];
  const labels = [fmtDate(new Date(end - n * step * 86400000))];
  let wins = 0; const rets: number[] = [];
  for (let i = 0; i < n; i++) {
    const side: "Long" | "Short" = exp.riktning === "Short" ? "Short" : exp.riktning === "Long" ? "Long" : r() < 0.5 ? "Long" : "Short";
    const gross = mu + sd * ((r() + r() + r() + r() - 2) * 1.7);
    const net = gross - cost;
    const pIn = price, pOut = price * (1 + (side === "Long" ? gross : -gross) * 3);
    price = pOut > 1 ? pOut : price;
    equity *= 1 + net;
    eq.push(equity);
    rets.push(net);
    if (net > 0) wins++;
    const date = new Date(end - (n - 1 - i) * step * 86400000);
    labels.push(fmtDate(date));
    trades.push({ nr: i + 1, datum: fmtDate(date), riktning: side, in: +pIn.toFixed(2), ut: +pOut.toFixed(2), brutto: gross * 100, kostnad: cost * 100, netto: net * 100 });
  }
  const mean = rets.reduce((a, b) => a + b, 0) / n;
  const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1);
  const t = variance > 0 ? mean / Math.sqrt(variance / n) : 0;
  let peak = 100, dd = 0;
  for (const v of eq) { peak = Math.max(peak, v); dd = Math.min(dd, v / peak - 1); }
  const b = walk(hashSeed(exp.id) + 7, n + 1, 0.002, 0.02);
  const baseline = b.map((v) => (v / b[0]) * 100);
  const open = r() < 0.5;
  const position: Position = open
    ? { läge: exp.riktning === "Short" ? "Short" : exp.riktning === "Long" ? "Long" : r() < 0.5 ? "Long" : "Short", sedan: labels[labels.length - 1], storlek: 25, orealiserat: (r() - 0.45) * 4 }
    : { läge: "Ingen" };
  return { exp, källa: "SIM", trades, equity: eq, baseline, labels, avkastning: (equity / 100 - 1) * 100, maxDrawdown: dd * 100, antal: n, vinstandel: (wins / n) * 100, t, position, kostnadPerAffär: cost * 100 };
}

/** Krav på t-värde om alla rutor räknas som försök (Bonferroni, ensidigt, aldrig under 2,0). */
export const kravFör = (antalRutor: number) => tKrav(antalRutor);

export const pct = (v: number, d = 1) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(d).replace(".", ",")} %`;
export const num = (v: number, d = 2) => v.toFixed(d).replace(".", ",");


/** Riktigt resultat exporterat av motorn (engine/traderlab/batch.py → app/data/results.json). */
export type RealResult = {
  source: "HISTORIK";
  hypothesis: string;
  registry_commit: string;
  run_at: string;
  period: [string, string];
  total_return: number;
  max_drawdown: number;
  trades: number;
  win_rate: number;
  t: number;
  t_required: number;
  passes: boolean;
  deflated_sharpe: number | null;
  stressed_total_return: number;
  costs_bps_per_side: number;
  curve: { t: string[]; strategy: number[]; buy_and_hold: (number | null)[] } | null;
  recent_trades: { entry_time: string; exit_time: string | null; side: string; entry_price: number; exit_price: number | null;
                   gross: number | null; costs: number | null; funding: number | null; net: number; liquidated: boolean;
                   exit_reason?: string | null }[];
  position_now: number;
  result_file: string;
  sharpe?: number | null;
  baseline?: { total_return: number; max_drawdown: number; sharpe: number | null; t_daily_nw: number | null } | null;
  track?: Mål;
  phase?: "fas1";
  criteria?: Record<string, boolean>;
  strategy_run_id?: string;
  stability?: number | null;
  windows?: { test: [string, string]; sharpe_in_sample: number | null; sharpe_out_of_sample: number | null }[];
  beta?: number | null;
  correlation?: number | null;
};

/** Klarar resultatet alla kriterier i sitt spår? Samma regler som research/tracks.md. */
export function klararMål(mål: Mål, r: RealResult): boolean {
  if (r.phase === "fas1") return !!r.criteria && Object.keys(r.criteria).length === 4 && Object.values(r.criteria).every(v => v === true);
  const grund = r.passes && r.stressed_total_return > 0;
  if (!grund) return false;
  if (mål === "A") return r.sharpe != null && r.baseline?.sharpe != null && r.sharpe > r.baseline.sharpe;
  if (mål === "B") return r.baseline != null && Math.abs(r.max_drawdown) <= 0.6 * Math.abs(r.baseline.max_drawdown);
  return r.beta != null && Math.abs(r.beta) <= 0.2;
}

/** Gör om ett riktigt resultat till samma form som rutorna använder. Andelar blir procent. */
export function fromResult(exp: Experiment, r: RealResult): Computed {
  const curve = r.curve ?? { t: [], strategy: [], buy_and_hold: [] };
  const labels = curve.t.map((t) => fmtDate(new Date(t)));
  const baseline = curve.buy_and_hold.every(v => v != null && Number.isFinite(v))
    ? curve.buy_and_hold as number[] : [];
  const trades: Trade[] = r.recent_trades.map((t, i) => ({
    nr: r.trades - r.recent_trades.length + i + 1,
    datum: fmtDate(new Date(t.exit_time ?? t.entry_time)),
    riktning: t.side === "Short" ? "Short" : "Long",
    in: t.entry_price,
    ut: t.exit_price ?? t.entry_price,
    brutto: t.gross == null ? NaN : t.gross * 100,
    kostnad: t.costs == null || t.funding == null ? NaN : (t.costs + t.funding) * 100,
    netto: t.net * 100,
  }));
  const pos = r.position_now;
  return {
    exp, källa: "HISTORIK", trades, equity: curve.strategy, baseline, labels,
    affärer: r.recent_trades.map(({ entry_time, exit_time, side, entry_price, exit_price }) => ({ entry_time, exit_time, side, entry_price, exit_price })),
    avkastning: r.total_return * 100, maxDrawdown: r.max_drawdown * 100, antal: r.trades,
    vinstandel: r.win_rate * 100, t: r.t, krav: r.t_required, passes: r.passes,
    deflated: r.deflated_sharpe, stressad: r.stressed_total_return * 100, hypotes: r.hypothesis,
    beta: r.beta ?? null, klararMål: klararMål(r.track ?? målFör(exp), r),
    fas1: r.phase === "fas1" ? { windows: r.windows ?? [], stability: r.stability ?? null, runId: r.strategy_run_id ?? "" } : undefined,
    registerCommit: r.registry_commit, period: r.period, resultatfil: r.result_file,
    position: pos === 0 ? { läge: "Ingen" } : { läge: pos > 0 ? "Long" : "Short", storlek: Math.round(Math.abs(pos) * 100) },
    kostnadPerAffär: r.costs_bps_per_side / 100,
  };
}
