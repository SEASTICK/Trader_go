import { useState } from "react";
import registryMd from "../../../research/registry.md?raw";
import { Page, StatusDot } from "../components/ui";
import { parseRegistry } from "../lib/registry";
import { tKrav } from "../lib/stats";

const ROWS = [1, 5, 10, 20, 50, 100];
const f = (n: number) => n.toFixed(2).replace(".", ",");
const reg = parseRegistry(registryMd);

export default function Hypotheses() {
  const [n, setN] = useState(Math.max(1, reg.attempts));
  const hypCol = Object.keys(reg.rows[0]?.cells ?? {}).find((k) => k.startsWith("hypotes")) ?? "hypotes";
  return (
    <Page title="Hypoteser" sub="Varje försök räknas. Ju fler försök, desto strängare krav för att något ska räknas som verkligt.">
      <div className="kpis">
        <div className="card kpi"><span className="k">Registrerade försök</span><b>{reg.attempts}</b><span className="muted">Olika id i registret</span></div>
        <div className="card kpi"><span className="k">Krav på t-värde nu</span><b>{f(tKrav(reg.attempts))}</b><span className="muted">Bonferroni, minst 2,0</span></div>
        <div className="card kpi"><span className="k">Klara för papper</span><b>{Object.values(reg.decisions).filter((d) => d === "READY_FOR_PAPER").length}</b><span className="muted">READY_FOR_PAPER</span></div>
        <div className="card kpi"><span className="k">Avvisade</span><b>{Object.values(reg.decisions).filter((d) => d === "REJECT").length}</b><span className="muted">REJECT är ett bra utfall</span></div>
      </div>

      <section className="card table-card">
        <div className="card-head"><div><h2>Registret</h2><p className="muted">Från <code>research/registry.md</code> när appen byggdes. Rader ändras aldrig, resultat läggs till som nya rader.</p></div></div>
        {reg.rows.length === 0 ? (
          <div className="empty">Inga hypoteser registrerade än. Den första skrivs in och committas innan något testas (skillen <code>ny-hypotes</code>).</div>
        ) : (
          <div className="ttable">
            <div className="ttr head reg"><span>Id</span><span>Datum</span><span>Hypotes</span><span>Marknad</span><span>Beslut</span></div>
            {reg.rows.map((r, i) => (
              <div className="ttr reg" key={`${r.id}-${i}`}>
                <b>{r.id}</b><span>{r.cells["datum"]}</span><span>{r.cells[hypCol]}</span><span>{r.cells["marknad"]}</span>
                <span>{r.cells["beslut"] ? <StatusDot status={r.cells["beslut"]} /> : <span className="muted">—</span>}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="split">
        <section className="card pad">
          <h2>Räkna själv</h2>
          <p className="muted">Hur strängt blir kravet med fler försök?</p>
          <div className="bignum">{f(tKrav(n))}</div>
          <label className="slider">
            <span>Antal försök: <b>{n}</b></span>
            <input type="range" min={1} max={200} value={n} onChange={(e) => setN(Number(e.target.value))} />
          </label>
        </section>
        <section className="card table-card">
          <div className="thead two"><span>Antal försök</span><span>Krav på t-värde</span></div>
          {ROWS.map((r) => (
            <div key={r} className="trow two"><span>{r}</span><b>{f(tKrav(r))}</b></div>
          ))}
        </section>
      </div>
    </Page>
  );
}
