import { LineChart } from "../components/Charts";
import { Icon } from "../components/icons";
import { Page, SimChip, StatusDot } from "../components/ui";
import { num, pct, type Computed } from "../lib/experiments";

export default function ExperimentDetail({ c, krav, total, onBack }: { c: Computed; krav: number; total: number; onBack: () => void }) {
  const { exp } = c;
  const passes = c.t >= krav;
  const pos = c.position;
  const recent = [...c.trades].reverse().slice(0, 20);
  return (
    <Page
      title={`${exp.id} · ${exp.namn}`}
      sub={`${exp.strategi} · ${exp.marknad} · ${exp.tidsram} · ${exp.riktning}`}
      actions={<button className="btn" onClick={onBack}>← Tillbaka till rutorna</button>}
    >
      <div className="banner-sim" role="note"><SimChip /> Allt på den här sidan är påhittat. Det visar hur ett resultat kommer att se ut, inte ett verkligt resultat.</div>

      <div className="kpis">
        <div className="card kpi"><span className="k">Avkastning efter kostnader</span><b className={c.avkastning >= 0 ? "up" : "down"}>{pct(c.avkastning)}</b><span className="muted">Simulerat</span></div>
        <div className="card kpi"><span className="k">Största nedgång</span><b>{pct(c.maxDrawdown)}</b><span className="muted">Från topp till botten</span></div>
        <div className="card kpi"><span className="k">Affärer</span><b>{c.antal}</b><span className="muted">{num(c.vinstandel, 0)} % vinnande</span></div>
        <div className="card kpi"><span className="k">t-värde mot krav</span><b>{num(c.t, 1)} <small>/ {num(krav, 1)}</small></b><span className={passes ? "pass" : "fail"}>{passes ? "över kravet" : "under kravet"}</span></div>
      </div>

      <section className="card chart-card">
        <div className="card-head"><div><h2>Utveckling</h2><p className="muted">Strategin efter kostnader mot baslinjen köp-och-behåll. Start = 100.</p></div></div>
        <LineChart labels={c.labels} series={[{ name: exp.namn, data: c.equity, cls: "s1" }, { name: "Baslinje", data: c.baseline, cls: "s2" }]} />
        <div className="legend"><span><i className="swatch s1" />{exp.namn}</span><span><i className="swatch s2" />Baslinje (köp-och-behåll)</span></div>
      </section>

      <div className="split">
        <section className="card pad">
          <h2>Innehav nu</h2>
          {pos.läge === "Ingen" ? <p className="muted" style={{ marginTop: 10 }}>Ingen öppen position (simulerat).</p> : (
            <dl className="dl" style={{ marginTop: 14 }}>
              <dt>Läge</dt><dd><b>{pos.läge}</b></dd>
              <dt>Sedan</dt><dd>{pos.sedan}</dd>
              <dt>Storlek</dt><dd>{pos.storlek} % av kapitalet</dd>
              <dt>Orealiserat</dt><dd className={(pos.orealiserat ?? 0) >= 0 ? "up" : "down"}>{pct(pos.orealiserat ?? 0)}</dd>
            </dl>
          )}
          <p className="footnote" style={{ padding: "14px 0 0" }}>Papper. Aldrig riktiga order.</p>
        </section>
        <section className="card pad">
          <h2>Om testet</h2>
          <dl className="dl" style={{ marginTop: 14 }}>
            <dt>Status</dt><dd><StatusDot status="Idé" /></dd>
            <dt>Hypotes</dt><dd className="muted">Inte registrerad än (<code>research/registry.md</code>)</dd>
            <dt>Beslut</dt><dd>På stängd stapel, fyllning vid nästa öppning</dd>
            <dt>Kostnad per affär</dt><dd>{num(c.kostnadPerAffär, 2)} % (avgift, spread, slippage{exp.grupp === "terminer" ? ", finansiering" : ""})</dd>
            <dt>Räknas som försök</dt><dd>{total} rutor, därför är kravet t ≥ {num(krav, 1)}</dd>
          </dl>
        </section>
      </div>

      <section className="card table-card">
        <div className="card-head"><div><h2>Senaste affärer</h2><p className="muted">De {recent.length} senaste av {c.antal}. Siffror i procent.</p></div></div>
        <div className="ttable" role="table">
          <div className="ttr head" role="row"><span>#</span><span>Datum</span><span>Läge</span><span>In</span><span>Ut</span><span>Brutto</span><span>Kostnad</span><span>Netto</span></div>
          {recent.map((t) => (
            <div className="ttr" role="row" key={t.nr}>
              <span>{t.nr}</span><span>{t.datum}</span><span>{t.riktning}</span><span>{num(t.in)}</span><span>{num(t.ut)}</span>
              <span>{pct(t.brutto, 2)}</span><span>{num(t.kostnad)} %</span><span className={t.netto >= 0 ? "up" : "down"}>{pct(t.netto, 2)}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="card pad">
        <h2><Icon name="alert" size={16} /> Innan du tror på ett resultat</h2>
        <ul className="checklist">
          <li>Är det <b>över kravet</b> för alla försök, inte bara ett bra år eller en bra ruta?</li>
          <li>Hur många affärer? Under ca 30 säger t-värdet lite.</li>
          <li>Håller det på <b>ny data</b> som inte användes för att välja idén?</li>
          <li>Slår det baslinjen köp-och-behåll efter kostnader?</li>
          <li>Är kostnader och slippage med, och för terminer finansiering och likvidation?</li>
        </ul>
        <p className="footnote" style={{ padding: "12px 0 0" }}>Se skillen <code>granska-backtest</code>. <code>REJECT</code> är ett bra utfall.</p>
      </section>
    </Page>
  );
}
