import { useEffect, useState } from "react";
import paper from "../../data/paper13f.json";
import snap from "../../data/investors13f.json";
import pelosiData from "../../data/pelosi.json";
import registryMd from "../../../research/registry.md?raw";
import { LineChart } from "../components/Charts";
import { groupRegistry, missingPrices, parseRegistry } from "../lib/registry";
import { Details, Page } from "../components/ui";

type Holding = { ticker: string; shares: number; value: number };
type Event = { day: string; filed: string; manager: string; accession: string; top10: { ticker: string | null; weight: number }[] };
type Paper = {
  start: string; start_capital: number; updated_at: string | null; managers: string[]; value: number; spy_value: number;
  holdings: Holding[]; history: { day: string; value: number; spy: number }[]; events: Event[];
};
const p = paper as unknown as Paper;
type Manager = { manager: string; filed: string; period: string; top10: { ticker: string | null; name: string; weight: number }[] };
type Snapshot = {
  updated_at: string;
  managers: Manager[];
  others?: Manager[];
  consensus: { ticker: string | null; name: string; weight: number; holders: string[] }[];
  recent_filings: { manager: string; filed: string; period: string; in_portfolio?: boolean }[];
};
const sn = snap as unknown as Snapshot;
type Pelosi = { updated_at: string | null; start: string; filings: { filed: string; doc_id: string; trades: { ticker: string; kind: string; asset: string; traded: string }[] }[] };
const pel = pelosiData as unknown as Pelosi;
const latestFiling = [sn.recent_filings[0]?.filed ?? "", pel.filings[0]?.filed ?? ""].sort().pop() ?? "";
/** Läget för de historiska testen av investeringsidén, rakt ur registret (inget hårdkodat). */
const history = groupRegistry(parseRegistry(registryMd)).filter((h) => h.id === "H-0016" || h.id === "H-0017")
  .map((h) => ({ id: h.id, decision: h.decision, invalid: h.invalid, missing: missingPrices(h.result) }));
const usd = (v: number) => `${Math.round(v).toLocaleString("sv-SE")} USD`;
const pct = (v: number) => `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(2).replace(".", ",")} %`;
export const SEEN_KEY = "trader_go.seenFilings";
/** En 13F äldre än 200 dagar räknas som inaktuell (samma gräns som i research/13f-protokoll.md). */
export function isStale(filed: string, today = new Date()): boolean {
  return (today.getTime() - new Date(filed).getTime()) / 86400000 > 200;
}

/** Antal redovisningar som kommit sedan användaren senast öppnade sidan (för "ping" i menyn). */
export function unseenFilings(): number {
  let seen = "";
  try { seen = localStorage.getItem(SEEN_KEY) ?? ""; } catch { /* ignoreras */ }
  // Första gången (inget sparat): bara redovisningar från de senaste 14 dagarna räknas som nya.
  if (!seen) seen = new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10);
  return sn.recent_filings.filter((f) => f.filed > seen).length + pel.filings.filter((f) => f.filed > seen).length;
}

export default function Investors({ actions }: { actions?: React.ReactNode } = {}) {
  const [openMgr, setOpenMgr] = useState<string | null>(null);
  const [seenBefore] = useState(() => {
    let v = "";
    try { v = localStorage.getItem(SEEN_KEY) ?? ""; } catch { /* ignoreras */ }
    return v || new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10);
  });
  useEffect(() => {
    try { if (latestFiling) localStorage.setItem(SEEN_KEY, latestFiling); } catch { /* ignoreras */ }
  }, []);
  const managerRow = (m: Manager) => (
    <div key={m.manager} className={openMgr === m.manager ? "hyp open" : "hyp"}>
      <button type="button" className="hyp-row inv-mgr" onClick={() => setOpenMgr(openMgr === m.manager ? null : m.manager)} aria-expanded={openMgr === m.manager}>
        <b>{m.manager}</b>
        <span className="muted">{m.top10.slice(0, 3).map((t) => t.ticker ?? t.name).join(", ")} …</span>
        <span className="muted" title={`Avser kvartalet som slutar ${m.period}`}>inlämnad {m.filed}{isStale(m.filed) ? " (gammal)" : ""}</span>
      </button>
      {openMgr === m.manager && (
        <div className="inv-mgr-detail">
          {m.top10.map((t) => (
            <div key={(t.ticker ?? "") + t.name} className="inv-row cons"><b>{t.ticker ?? "–"}</b><span className="muted">{t.name}</span>
              <span>{(t.weight * 100).toFixed(1).replace(".", ",")} %</span><span /></div>
          ))}
        </div>
      )}
    </div>
  );
  const started = p.history.length > 0;
  const ret = p.value / p.start_capital - 1;
  const spyRet = p.spy_value / p.start_capital - 1;
    return (
    <Page title="Papperportfölj" sub={`${usd(p.start_capital)} i papper som följer tio kända investerare (13F). Observation framåt, inga riktiga pengar.`} actions={actions}>
      <div className="kpis three">
        <div className="card kpi"><span className="k">Värde nu</span><b>{usd(p.value)}</b><span className={ret >= 0 ? "up" : "down"}>{started ? pct(ret) : "Inte startad än"}</span></div>
        <div className="card kpi"><span className="k">S&P 500 (SPY)</span><b>{usd(p.spy_value)}</b><span className="muted">{started ? pct(spyRet) : "Samma start"}</span></div>
        <div className="card kpi"><span className="k">Skillnad mot SPY</span><b className={ret - spyRet >= 0 ? "up" : "down"}>{started ? pct(ret - spyRet) : "–"}</b><span className="muted">Sedan {p.start}</span></div>
      </div>

      {!started ? (
        <section className="card pad"><h2>Inte startad än</h2>
          <p className="muted" style={{ marginTop: 8 }}>Portföljen uppdateras varje lördag av GitHub (flödet Paper 13F) och startar {p.start}. Siffrorna här kommer från den senaste uppdateringen när appen byggdes.</p>
        </section>
      ) : (
        <section className="card chart-card">
          <div className="card-head"><div><h2>Utveckling</h2><p className="muted">Papperportföljen efter kostnader mot S&P 500 (SPY). Uppdaterad {p.updated_at?.slice(0, 10)}.</p></div></div>
          <LineChart labels={p.history.map((h) => h.day)} series={[
            { name: "Investerarportföljen", data: p.history.map((h) => h.value), cls: "s1" },
            { name: "SPY", data: p.history.map((h) => h.spy), cls: "s2" }]} />
          <div className="legend"><span><i className="swatch s1" />Investerarportföljen</span><span><i className="swatch s2" />S&P 500 (SPY)</span></div>
        </section>
      )}

      <Details summary="Visa innehav, investerare och redovisningar">
      <section className="card table-card">
        <div className="card-head"><div><h2>Vad de äger nu</h2><p className="muted">Genomsnitt av de tio investerarnas tio största innehav enligt senaste 13F (samma vikter som portföljen). Uppdaterad {sn.updated_at.slice(0, 10)}.</p></div></div>
        {sn.consensus.slice(0, 15).map((c) => (
          <div key={c.ticker ?? c.name} className="inv-row cons"><b>{c.ticker ?? "–"}</b><span className="muted">{c.name}</span>
            <span>{(c.weight * 100).toFixed(1).replace(".", ",")} %</span><span className="muted" title={c.holders.join(", ")}>{c.holders.length} av {sn.managers.length}</span></div>
        ))}
      </section>

      <section className="card table-card">
        <div className="card-head"><div><h2>Investerarna</h2><p className="muted">Klicka för att se varje investerares tio största innehav enligt senaste 13F.</p></div></div>
        {sn.managers.map(managerRow)}
      </section>

      {(sn.others ?? []).length > 0 && (
        <section className="card table-card">
          <div className="card-head"><div><h2>Fler kända investerare</h2><p className="muted">Visas bara, så att du kan jämföra. De ingår inte i papperportföljen eller i testet H-0016.</p></div></div>
          {(sn.others ?? []).map(managerRow)}
        </section>
      )}

      <section className="card table-card">
        <div className="card-head"><div><h2>Nancy Pelosi</h2><p className="muted">Nya redovisade aktieaffärer från {pel.start} (House PTR). Affärer redovisas upp till 45 dagar i efterhand. Det historiska testet H-0017 är avgjort (se Research, Hypoteser).</p></div></div>
        {pel.filings.length === 0 ? <div className="empty">Inga nya redovisningar sedan {pel.start}.</div> : pel.filings.map((f) => (
          <div key={f.doc_id} className={f.filed > seenBefore ? "inv-event new" : "inv-event"}>
            <div><b>Redovisning {f.filed}</b>{f.filed > seenBefore && <span className="inv-new">Ny</span>}</div>
            <div className="muted inv-top">{f.trades.length === 0 ? "Inga aktieköp eller hela försäljningar." :
              f.trades.map((t) => `${t.kind === "buy" ? "Köp" : "Sälj"} ${t.ticker}${t.asset === "OP" ? " (köpoption)" : ""} ${t.traded}`).join(" · ")}</div>
          </div>
        ))}
      </section>

      <div className="split">
        <section className="card table-card">
          <div className="card-head"><div><h2>Senaste redovisningar</h2><p className="muted">13F lämnas senast 45 dagar efter varje kvartal. En ny från de tio flyttar portföljen nästa handelsdag.</p></div></div>
          {sn.recent_filings.slice(0, 12).map((f) => (
            <div key={f.manager + f.filed} className={f.filed > seenBefore ? "inv-event new" : "inv-event"}>
              <div><b>{f.manager}</b>{f.filed > seenBefore && <span className="inv-new">Ny</span>}<span className="muted"> · inlämnad {f.filed}, avser {f.period}{f.in_portfolio === false ? " · visas bara" : ""}</span></div>
            </div>
          ))}
        </section>
        <section className="card table-card">
          <div className="card-head"><div><h2>Papperportföljens innehav</h2><p className="muted">Papper. Inga riktiga order.</p></div></div>
          {p.holdings.length === 0 ? <div className="empty">Inga innehav än. Portföljen köper vid nästa uppdatering.</div> : p.holdings.map((h) => (
            <div key={h.ticker} className="inv-row"><b>{h.ticker}</b><span className="muted">{h.shares.toLocaleString("sv-SE", { maximumFractionDigits: 2 })} st</span><span>{usd(h.value)}</span><span className="muted">{((h.value / p.value) * 100).toFixed(1).replace(".", ",")} %</span></div>
          ))}
        </section>
      </div>

      </Details>

      <p className="footnote">Följer: {p.managers.join(", ")}. Regler: <code>{"research/13f-protokoll.md"}</code>. Redovisningarna kommer upp till 45 dagar efter kvartalet, så portföljen ligger alltid efter investerarna. Papperportföljen är en observation framåt från 2026-11-05, inte ett validerat historiskt test, och inget löfte om avkastning.</p>
      <p className="footnote">Historiska tester av idén: {history.map((h) => `${h.id} ${h.invalid ? `ogiltig${h.missing ? ` (${String(h.missing.share).replace(".", ",")} % av vikten utan kurs, gräns ${h.missing.limit} %)` : ""}` : h.decision ?? "pågår"}`).join(" · ")}. Se Research, Hypoteser.</p>
    </Page>
  );
}
