import { Details, Page } from "../components/ui";
import registryMd from "../../../research/registry.md?raw";
import { parseRegistry } from "../lib/registry";
import { agoText, freshness } from "../lib/freshness";
import { summarize } from "../lib/status";
import { tKrav } from "../lib/stats";
import paper from "../../data/paper13f.json";
import snap from "../../data/investors13f.json";
import { unseenFilings } from "./Investors";

export type GoTarget = "Resultat" | "Papper" | "Marknad";
type PaperSummary = { start: string; start_capital: number; updated_at: string | null; value: number; spy_value: number; history: unknown[] };

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

      <div className="stats">
        <section className="stat" aria-labelledby="st-hist">
          <header><span className="k" id="st-hist">Historiska tester</span><span className="stat-tag">Bakåt i tiden</span></header>
          <b className="big">{s.advanced} <small>av {s.decided}</small></b>
          <div className="meter" role="img" aria-label={`${s.advanced} av ${s.decided} idéer klarade testkraven`}><i style={{ width: `${s.decided ? (s.advanced / s.decided) * 100 : 0}%` }} /></div>
          <p>idéer klarade testkraven. {s.rejected > 0 ? `${s.rejected} klarade inte kraven.` : ""}</p>
          <span className="src">Testat på historik</span>
        </section>
        <section className="stat" aria-labelledby="st-paper">
          <header><span className="k" id="st-paper">Papperportfölj</span><span className="stat-tag">Framåt</span></header>
          <b className="big">{started ? usd(p.value) : "Ej startad"}</b>
          {started
            ? <span className={`delta ${ret >= 0 ? "up" : "down"}`}>{fmtPct(ret)}</span>
            : <span className="delta idle">Startar <D>{p.start}</D></span>}
          <p>{started ? <>sedan <D>{p.start}</D>, {fmtPct(vsSpy).replace(" %", " procentenheter")} mot S&P 500.</> : "Ingen observation har börjat än."}</p>
          <span className="src">Observation. Inga riktiga pengar</span>
        </section>
        <section className="stat" aria-labelledby="st-data">
          <header><span className="k" id="st-data">Data</span><span className="stat-tag">Aktualitet</span></header>
          <b className={fresh.state === "ok" ? "big" : "big warn"}>{fresh.state === "ok" ? "Aktuell" : fresh.state === "old" ? "Gammal" : "Saknas"}</b>
          <span className={`delta ${fresh.state === "ok" ? "up" : "warn"}`}>{fresh.state === "ok" ? "Uppdaterad" : fresh.state === "old" ? "Kan vara inaktuell" : "Inget datum"}</span>
          <p>{fresh.date ? <>Papperportföljen uppdaterades <D>{fresh.date}</D> ({agoText(fresh.days)}).</> : "Ingen uppdatering har registrerats."}</p>
          <span className="src">{filings.date ? <>Investerardata: <D>{filings.date}</D></> : "Investerardata saknas"}</span>
        </section>
      </div>

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
