import { useEffect, useState } from "react";
import paper from "../../data/paper13f.json";
import { LineChart } from "../components/Charts";
import { Page } from "../components/ui";

type Holding = { ticker: string; shares: number; value: number };
type Event = { day: string; filed: string; manager: string; accession: string; top10: { ticker: string | null; weight: number }[] };
type Paper = {
  start: string; start_capital: number; updated_at: string | null; managers: string[]; value: number; spy_value: number;
  holdings: Holding[]; history: { day: string; value: number; spy: number }[]; events: Event[];
};
const p = paper as unknown as Paper;
const usd = (v: number) => `${Math.round(v).toLocaleString("sv-SE")} USD`;
const pct = (v: number) => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2).replace(".", ",")} %`;
export const SEEN_KEY = "trader_go.seenFilings";

/** Antal redovisningar som kommit sedan användaren senast öppnade sidan (för "ping" i menyn). */
export function unseenFilings(): number {
  let seen = "";
  try { seen = localStorage.getItem(SEEN_KEY) ?? ""; } catch { /* ignoreras */ }
  return p.events.filter((e) => e.day > seen).length;
}

export default function Investors() {
  const [seenBefore] = useState(() => { try { return localStorage.getItem(SEEN_KEY) ?? ""; } catch { return ""; } });
  useEffect(() => {
    const last = p.events.length ? p.events[p.events.length - 1].day : "";
    try { if (last) localStorage.setItem(SEEN_KEY, last); } catch { /* ignoreras */ }
  }, []);
  const started = p.history.length > 0;
  const ret = p.value / p.start_capital - 1;
  const spyRet = p.spy_value / p.start_capital - 1;
  const events = [...p.events].reverse();
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

      <div className="split">
        <section className="card table-card">
          <div className="card-head"><div><h2>Nya redovisningar</h2><p className="muted">När en investerare lämnar en ny 13F flyttas pengarna nästa handelsdag.</p></div></div>
          {events.length === 0 ? <div className="empty">Inga nya redovisningar sedan start. Nästa period är runt 15 februari (helåret).</div> : events.map((e) => (
            <div key={e.accession} className={e.day > seenBefore ? "inv-event new" : "inv-event"}>
              <div><b>{e.manager}</b>{e.day > seenBefore && <span className="inv-new">Ny</span>}<span className="muted"> · inlämnad {e.filed}, ombalanserat {e.day}</span></div>
              <div className="muted inv-top">{e.top10.filter((h) => h.ticker).slice(0, 10).map((h) => `${h.ticker} ${Math.round(h.weight * 100)} %`).join(" · ")}</div>
            </div>
          ))}
        </section>
        <section className="card table-card">
          <div className="card-head"><div><h2>Innehav nu</h2><p className="muted">Papper. Inga riktiga order.</p></div></div>
          {p.holdings.length === 0 ? <div className="empty">Inga innehav än.</div> : p.holdings.map((h) => (
            <div key={h.ticker} className="inv-row"><b>{h.ticker}</b><span className="muted">{h.shares.toLocaleString("sv-SE", { maximumFractionDigits: 2 })} st</span><span>{usd(h.value)}</span><span className="muted">{((h.value / p.value) * 100).toFixed(1).replace(".", ",")} %</span></div>
          ))}
        </section>
      </div>

      <p className="footnote">Följer: {p.managers.join(", ")}. Regler: <code>{"research/13f-protokoll.md"}</code>. Redovisningarna kommer upp till 45 dagar efter kvartalet, så portföljen ligger alltid efter investerarna. Det här är en observation, inte ett godkänt test, och inget löfte om avkastning.</p>
    </Page>
  );
}
