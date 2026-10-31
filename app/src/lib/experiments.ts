// Simulerade mätvärden för rutorna i Research. Allt härifrån är PÅHITTAT och visar inga resultat.
// Samma id ger alltid samma siffror (fast frö), så ni ser samma sak.
import { hashSeed, rng, walk } from "./sim";
import { tKrav } from "./stats";

export type Experiment = {
  id: string; spår: string; namn: string; strategi: string; grupp: string;
  marknad: string; tidsram: string; riktning: string;
};

export type Trade = { nr: number; datum: string; riktning: "Long" | "Short"; in: number; ut: number; brutto: number; kostnad: number; netto: number };
export type Position = { läge: "Long" | "Short" | "Ingen"; sedan?: string; storlek?: number; orealiserat?: number };

export type Computed = {
  exp: Experiment;
  trades: Trade[];
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
  return { exp, trades, equity: eq, baseline, labels, avkastning: (equity / 100 - 1) * 100, maxDrawdown: dd * 100, antal: n, vinstandel: (wins / n) * 100, t, position, kostnadPerAffär: cost * 100 };
}

/** Krav på t-värde om alla rutor räknas som försök (Bonferroni, ensidigt, aldrig under 2,0). */
export const kravFör = (antalRutor: number) => tKrav(antalRutor);

export const pct = (v: number, d = 1) => `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(d).replace(".", ",")} %`;
export const num = (v: number, d = 2) => v.toFixed(d).replace(".", ",");
