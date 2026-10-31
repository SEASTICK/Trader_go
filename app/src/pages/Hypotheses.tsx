import { useState } from "react";
import { Page } from "../components/ui";
import { tKrav } from "../lib/stats";

const ROWS = [1, 5, 10, 20, 50, 100];
const f = (n: number) => n.toFixed(2).replace(".", ",");

export default function Hypotheses() {
  const [n, setN] = useState(12);
  return (
    <Page title="Hypoteser" sub="Varje försök räknas. Ju fler försök, desto strängare krav för att något ska räknas som verkligt.">
      <div className="split">
        <section className="card pad">
          <h2>Kravet på t-värde</h2>
          <p className="muted">Bonferroni, ensidigt, aldrig under 2,0. Se skillen <code>ny-hypotes</code>.</p>
          <div className="bignum">{f(tKrav(n))}</div>
          <label className="slider">
            <span>Antal försök: <b>{n}</b></span>
            <input type="range" min={1} max={200} value={n} onChange={(e) => setN(Number(e.target.value))} />
          </label>
          <p className="footnote">Registret <code>research/registry.md</code> finns inte än, eftersom ingen hypotes är registrerad. Appen visar det riktiga antalet när den första raden finns.</p>
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
