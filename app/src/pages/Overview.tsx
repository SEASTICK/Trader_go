import { useMemo, useState } from "react";
import tracks from "../../data/tracks.json";
import { LineChart } from "../components/Charts";
import { Page, Segmented, SimChip } from "../components/ui";
import { walk } from "../lib/sim";
import { tKrav } from "../lib/stats";

const PERIODS = { "1M": 30, "3M": 90, "6M": 180, "1 år": 365, "Max": 730 } as const;
type Period = keyof typeof PERIODS;
const STEPS = ["Idé", "Research", "Fryst", "Papper", "Liten live", "Live", "Pensionerad"];

function labelsFor(n: number): string[] {
  const end = new Date();
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(end.getTime() - (n - 1 - i) * 86400000);
    return d.toLocaleDateString("sv-SE", { day: "numeric", month: "short" });
  });
}

export default function Overview({ go }: { go: (p: "Research") => void }) {
  const [period, setPeriod] = useState<Period>("6M");
  const strat = useMemo(() => walk(11, 730, 0.0006), []);
  const base = useMemo(() => walk(23, 730, 0.0003, 0.016), []);
  const n = PERIODS[period];
  const rebase = (a: number[]) => { const s = a.slice(-n); return s.map((v) => (v / s[0]) * 100); };
  const labels = useMemo(() => labelsFor(n), [n]);
  const attempts = 0;
  const idle = tracks.filter((t) => t.status === "Idé").length;

  return (
    <Page
      title={`${tracks.length} spår under research`}
      sub="Inga resultat än. Allt står på Idé. Det är normalt att de flesta spår blir REJECT."
      actions={<button className="btn" onClick={() => go("Research")}>Öppna Research</button>}
    >
      <div className="kpis">
        <div className="card kpi"><span className="k">Spår</span><b>{tracks.length}</b><span className="muted">{idle} på Idé</span></div>
        <div className="card kpi"><span className="k">Registrerade försök</span><b>{attempts}</b><span className="muted">Alla försök räknas, även övergivna</span></div>
        <div className="card kpi"><span className="k">Krav på t-värde</span><b>{tKrav(attempts).toFixed(1).replace(".", ",")}</b><span className="muted">Stiger med antal försök</span></div>
        <div className="card kpi"><span className="k">Livscykelsteg</span><b>Research</b><span className="muted">Inget är fryst eller på papper</span></div>
      </div>

      <section className="card chart-card">
        <div className="card-head">
          <div>
            <h2>Så här kommer ett resultat att visas</h2>
            <p className="muted">Exempelkurvor efter kostnader mot baslinjen köp-och-behåll. <SimChip /></p>
          </div>
          <Segmented value={period} options={Object.keys(PERIODS) as Period[]} onChange={setPeriod} />
        </div>
        <LineChart
          labels={labels}
          series={[
            { name: "Exempelstrategi", data: rebase(strat), cls: "s1" },
            { name: "Baslinje", data: rebase(base), cls: "s2" },
          ]}
        />
        <div className="legend"><span><i className="swatch s1" />Exempelstrategi</span><span><i className="swatch s2" />Baslinje (köp-och-behåll)</span></div>
        <p className="footnote">Kurvorna är slumpade och visar inget verkligt. Riktiga resultat får en annan etikett (HISTORIK) och kräver granskning enligt <code>granska-backtest</code>.</p>
      </section>

      <section className="card">
        <div className="card-head"><div><h2>Livscykel</h2><p className="muted">Inget steg får hoppas över.</p></div></div>
        <ol className="steps">
          {STEPS.map((s, i) => (
            <li key={s} className={i === 1 ? "now" : i < 1 ? "done" : ""}>
              <span className="bullet">{i + 1}</span>{s}
            </li>
          ))}
        </ol>
      </section>
    </Page>
  );
}
