import { Details, Page } from "../components/ui";
import registryMd from "../../../research/registry.md?raw";
import { parseRegistry } from "../lib/registry";
import { agoText, freshness } from "../lib/freshness";
import { summarize } from "../lib/status";
import { tKrav } from "../lib/stats";
import paper from "../../data/paper13f.json";
import snap from "../../data/investors13f.json";
import { unseenFilings } from "./Investors";
import { AreaSpark } from "../components/Charts";
import { Outcome } from "../components/ui";
import experiments from "../../data/experiments.json";
import results from "../../data/results.json";
import frozenMarket from "../../data/fas1-market.json";
import { fromResult, pct as pctRet, type Experiment, type RealResult } from "../lib/experiments";
import { ageDays } from "../lib/freshness";

export type GoTarget = "Resultat" | "Papper" | "Marknad";
type PaperSummary = { start: string; start_capital: number; updated_at: string | null; value: number; spy_value: number; history: { day: string; value: number; spy: number }[] };

const fmtPct = (v: number) => `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(1).replace(".", ",")} %`;
const usd = (v: number) => `${Math.round(v).toLocaleString("sv-SE")} USD`;
const D = ({ children }: { children: string }) => <span className="nb">{children}</span>;
const STEPS = ["Idé", "Test", "Fryst", "Papper", "Liten live", "Live"];

/** Startsidan: vad visar projektet nu, hur går papperportföljen, och är datan aktuell? */
export default function Overview({ go, now = new Date() }: { go: (p: GoTarget) => void; now?: Date }) {
  const reg = parseRegistry(registryMd);
  const s = summarize(reg);
  const p = paper as unknown as PaperSummary;
  const started = p.history.length > 0;
  const ret = p.value / p.start_capital - 1;
  const vsSpy = ret - (p.spy_value / p.start_capital - 1);
  const fresh = freshness(p.updated_at, now);
  const filings = freshness((snap as unknown as { updated_at: string }).updated_at, now);
  const nya = unseenFilings();

  const marketEnd = new Date(frozenMarket.rows[frozenMarket.rows.length - 1][0]).toISOString().slice(0, 10);
  const marketAge = ageDays(new Date(frozenMarket.rows[frozenMarket.rows.length - 1][0]).toISOString(), now);
  const realResults = results as unknown as Record<string, RealResult>;
  const latest = (experiments as Experiment[]).filter((e) => realResults[e.id]?.source === "HISTORIK").map((e) => fromResult(e, realResults[e.id])).slice(-5).reverse();

  const headline = s.advanced > 0
    ? `${s.advanced} ${s.advanced === 1 ? "idé" : "idéer"} klarade testkraven`
    : "Ingen idé har klarat testkraven än";
  const lead = `${s.decided} ${s.decided === 1 ? "idé" : "idéer"} är testade på historik. Alla räknas, även de som inte höll.`;

  return (
    <Page title={headline} sub={lead} actions={<button className="btn accent" onClick={() => go("Resultat")}>Se resultaten</button>}>
      {s.invalid > 0 && (
        <p className="note warn" role="note">
          <b>{s.invalid} försök kunde inte avgöras</b> eftersom datan inte räckte. De räknas aldrig som godkända.
        </p>
      )}
      {fresh.state !== "ok" && (
        <p className="note warn" role="alert">
          <b>{fresh.state === "missing" ? "Papperdatan saknar datum." : <>Papperdatan är gammal (<D>{fresh.date ?? ""}</D>).</>}</b> Siffrorna nedan kan vara inaktuella.
        </p>
      )}

      <div className="stats dash">
        <section className="stat hero" aria-labelledby="st-paper">
          <header><span className="k" id="st-paper">Papperportfölj</span><span className="src-inline">Observation framåt. Inga riktiga pengar</span></header>
          <div className="hero-row">
            <b className="big">{started ? usd(p.value) : "Ej startad"}</b>
            {started
              ? <span className={`delta ${ret >= 0 ? "up" : "down"}`}>{fmtPct(ret)}</span>
              : <span className="delta idle">Startar <D>{p.start}</D></span>}
          </div>
          <p>{started ? <>sedan <D>{p.start}</D>, {fmtPct(vsSpy).replace(" %", " procentenheter")} mot S&P 500.</> : "Ingen observation har börjat än."}</p>
          {started && p.history.length > 1 && <AreaSpark main={p.history.map((h) => h.value)} other={p.history.map((h) => h.spy)} label="Papperportföljens värde (heldragen) mot S&P 500 (streckad) sedan start" />}
        </section>
        <section className="stat" aria-labelledby="st-hist">
          <header><span className="k" id="st-hist">Historiska tester</span></header>
          <b className="big">{s.advanced} <small>av {s.decided}</small></b>
          <div className="meter" role="img" aria-label={`${s.advanced} av ${s.decided} idéer klarade testkraven`}><i style={{ width: `${s.decided ? (s.advanced / s.decided) * 100 : 0}%` }} /></div>
          <p>idéer klarade testkraven. Alla räknas.</p>
          <ul className="facts">
            <li><i className="dot" /><span>{s.rejected} klarade inte kraven</span></li>
            {s.invalid > 0 && <li><i className="dot warn" /><span>{s.invalid} kunde inte avgöras (räknas aldrig som godkända)</span></li>}
            {s.pending > 0 && <li><i className="dot" /><span>{s.pending} väntar på test</span></li>}
            {s.advanced > 0 && <li><i className="dot ok" /><span>{s.advanced} gick vidare</span></li>}
          </ul>
          <span className="src">Testat bakåt i tiden, på historik</span>
        </section>
        <section className="stat" aria-labelledby="st-data">
          <header><span className="k" id="st-data">Data</span></header>
          <b className={fresh.state === "ok" ? "big" : "big warn"}>{fresh.state === "ok" ? "Aktuell" : fresh.state === "old" ? "Gammal" : "Saknas"}</b>
          <ul className="facts">
            <li><i className={`dot ${fresh.state === "ok" ? "ok" : "warn"}`} /><span>{fresh.date ? <>Papperportföljen uppdaterades <D>{fresh.date}</D> ({agoText(fresh.days)})</> : "Papperportföljen: ingen uppdatering registrerad"}</span></li>
            <li><i className={`dot ${filings.state === "ok" ? "ok" : "warn"}`} /><span>{filings.date ? <>Investerardata <D>{filings.date}</D></> : "Investerardata saknas"}</span></li>
            <li><i className={`dot ${marketAge !== null && marketAge <= 7 ? "ok" : "warn"}`} /><span>Prishistorik till <D>{marketEnd}</D>{marketAge !== null && ` (${agoText(marketAge)})`}. Historik, inte live.</span></li>
          </ul>
        </section>
      </div>

      {latest.length > 0 && (
        <section className="card latest" aria-labelledby="latest-h">
          <h2 id="latest-h">Senast testade idéer</h2>
          <ul>
            {latest.map((c) => {
              const ok = c.klararMål ?? c.passes ?? false;
              return <li key={c.exp.id}><span className="l-name"><b>{c.exp.namn}</b><span className="muted">{c.exp.strategi}</span></span><span className={c.avkastning >= 0 ? "up l-ret" : "down l-ret"}>{pctRet(c.avkastning)}</span><Outcome kind={ok ? "further" : "rejected"} /></li>;
            })}
          </ul>
          <button type="button" className="textbtn" onClick={() => go("Resultat")}>Alla resultat</button>
        </section>
      )}

      {nya > 0 && (
        <p className="link-line"><button type="button" className="textbtn" onClick={() => go("Papper")}>{nya} {nya === 1 ? "ny redovisning" : "nya redovisningar"} sedan du tittade senast</button></p>
      )}

      <Details summary="Visa detaljer">
        <dl className="dl compact">
          <dt>Registrerade försök</dt><dd>{s.total} ({s.rejected} klarade inte kraven, {s.invalid} kunde inte avgöras, {s.pending} väntar{s.advanced ? `, ${s.advanced} gick vidare` : ""})</dd>
          <dt>Krav på t-värde</dt><dd>{tKrav(Math.max(1, reg.attempts)).toFixed(1).replace(".", ",")} <span className="muted">Kravet stiger med antal försök, så att slumpen inte räknas som kant.</span></dd>
          <dt>Klarade inte testkraven</dt><dd>Idén uppfyllde inte kraven som sattes i förväg. Det betyder inte att historiken var negativ.</dd>
        </dl>
        <h3 className="mini">Så arbetar vi</h3>
        <ol className="flow">{STEPS.map((x) => <li key={x}>{x}</li>)}</ol>
        <p className="muted small">Inget steg hoppas över. Allt här är papper eller historik, aldrig riktiga order.</p>
      </Details>
    </Page>
  );
}
