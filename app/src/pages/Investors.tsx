import { useEffect, useState } from "react";
import paper from "../../data/paper13f.json";
import snap from "../../data/investors13f.json";
import { LineChart } from "../components/Charts";
import { Page } from "../components/ui";

type Holding = { ticker: string; shares: number; value: number };
type Event = { day: string; filed: string; manager: string; accession: string; top10: { ticker: string | null; weight: number }[] };
type Paper = {
  start: string; start_capital: number; updated_at: string | null; managers: string[]; value: number; spy_value: number;
  holdings: Holding[]; history: { day: string; value: number; spy: number }[]; events: Event[];
};
const p = paper as unknown as Paper;
type Snapshot = {
  updated_at: string;
  managers: { manager: string; filed: string; period: string; top10: { ticker: string | null; name: string; weight: number }[] }[];
  consensus: { ticker: string | null; name: string; weight: number; holders: string[] }[];
  recent_filings: { manager: string; filed: string; period: string }[];
};
const sn = snap as unknown as Snapshot;
const latestFiling = sn.recent_filings[0]?.filed ?? "";
const usd = (v: number) => `${Math.round(v).toLocaleString("sv-SE")} USD`;
const pct = (v: number) => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2).replace(".", ",")} %`;
export const SEEN_KEY = "trader_go.seenFilings";

/** Antal redovisningar som kommit sedan användaren senast öppnade sidan (för "ping" i menyn). */
export function unseenFilings(): number {
  let seen = "";
  try { seen = localStorage.getItem(SEEN_KEY) ?? ""; } catch { /* ignoreras */ }
  // Första gången (inget sparat): bara redovisningar från de senaste 14 dagarna räknas som nya.
  if (!seen) seen = new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10);
  return sn.recent_filings.filter((f) => f.filed > seen).length;
}

export default function Investors() {
  const [openMgr, setOpenMgr] = useState<string | null>(null);
  const [seenBefore] = useState(() => {
    let v = "";
    try { v = localStorage.getItem(SEEN_KEY) ?? ""; } catch { /* ignoreras */ }
    return v || new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10);
  });
  useEffect(() => {
    try { if (latestFiling) localStorage.setItem(SEEN_KEY, latestFiling); } catch { /* ignoreras */ }
  }, []);
  const started = p.history.length > 0;
  const ret = p.value / p.start_capital - 1;
  const spyRet = p.spy_value / p.start_capital - 1;
    return (
    <Page title="Investerare" sub={`Papperportfölj på ${usd(p.start_capital)} som följer genomsnittet av tio kända investerares största innehav (13F). Inga riktiga pengar.`}>
      <div className="kpis">
        <div className="card kpi"><span className="k">Värde nu</span><b>{usd(p.value)}</b><span className={ret >= 0 ? "up" : "down"}>{started ? pct(ret) : "Inte startad än"}</span></div>
        <div className="card kpi"><span className="k">S&P 500 (SPY)</span><b>{usd(p.spy_value)}</b><span className="muted">{started ? pct(spyRet) : "Samma start"}</span></div>
        <div className="card kpi"><span className="k">Skillnad mot SPY</span><b className={ret - spyRet >= 0 ? "up" : "down"}>{started ? pct(ret - spyRet) : "–"}</b><span className="muted">Sedan {p.start}</span></div>
        <div className="card kpi"><span className="k">Innehav</span><b>{p.holdings.length}</b><span className="muted">{p.managers.length} investerare följs</span></div>
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

      <section className="card table-card">
        <div className="card-head"><div><h2>Vad de äger nu</h2><p className="muted">Genomsnitt av de tio investerarnas tio största innehav enligt senaste 13F (samma vikter som portföljen). Uppdaterad {sn.updated_at.slice(0, 10)}.</p></div></div>
        {sn.consensus.slice(0, 15).map((c) => (
          <div key={c.ticker ?? c.name} className="inv-row cons"><b>{c.ticker ?? "–"}</b><span className="muted">{c.name}</span>
            <span>{(c.weight * 100).toFixed(1).replace(".", ",")} %</span><span className="muted" title={c.holders.join(", ")}>{c.holders.length} av {sn.managers.length}</span></div>
        ))}
      </section>

      <section className="card table-card">
        <div className="card-head"><div><h2>Investerarna</h2><p className="muted">Klicka för att se varje investerares tio största innehav enligt senaste 13F.</p></div></div>
        {sn.managers.map((m) => (
          <div key={m.manager} className={openMgr === m.manager ? "hyp open" : "hyp"}>
            <button type="button" className="hyp-row inv-mgr" onClick={() => setOpenMgr(openMgr === m.manager ? null : m.manager)} aria-expanded={openMgr === m.manager}>
              <b>{m.manager}</b>
              <span className="muted">{m.top10.slice(0, 3).map((t) => t.ticker ?? t.name).join(", ")} …</span>
              <span className="muted">avser {m.period}, inlämnad {m.filed}</span>
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
        ))}
      </section>

      <div className="split">
        <section className="card table-card">
          <div className="card-head"><div><h2>Senaste redovisningar</h2><p className="muted">13F lämnas senast 45 dagar efter varje kvartal. En ny flyttar portföljen nästa handelsdag.</p></div></div>
          {sn.recent_filings.slice(0, 12).map((f) => (
            <div key={f.manager + f.filed} className={f.filed > seenBefore ? "inv-event new" : "inv-event"}>
              <div><b>{f.manager}</b>{f.filed > seenBefore && <span className="inv-new">Ny</span>}<span className="muted"> · inlämnad {f.filed}, avser {f.period}</span></div>
            </div>
          ))}
        </section>
        <section className="card table-card">
          <div className="card-head"><div><h2>Papperportföljens innehav</h2><p className="muted">Papper. Inga riktiga order.</p></div></div>
          {p.holdings.length === 0 ? <div className="empty">Inga innehav än. Portföljen köper när kurskällan är på plats.</div> : p.holdings.map((h) => (
            <div key={h.ticker} className="inv-row"><b>{h.ticker}</b><span className="muted">{h.shares.toLocaleString("sv-SE", { maximumFractionDigits: 2 })} st</span><span>{usd(h.value)}</span><span className="muted">{((h.value / p.value) * 100).toFixed(1).replace(".", ",")} %</span></div>
          ))}
        </section>
      </div>

      <p className="footnote">Följer: {p.managers.join(", ")}. Regler: <code>{"research/13f-protokoll.md"}</code>. Redovisningarna kommer upp till 45 dagar efter kvartalet, så portföljen ligger alltid efter investerarna. Det här är en observation, inte ett godkänt test, och inget löfte om avkastning.</p>
    </Page>
  );
}
