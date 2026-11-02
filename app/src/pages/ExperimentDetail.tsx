import { useState } from "react";
import { LineChart } from "../components/Charts";
import { CandleChart } from "../components/CandleChart";
import { seriesFor } from "../lib/candles";
import { Icon } from "../components/icons";
import { Page, Segmented, StatusDot } from "../components/ui";
import { num, pct, type Computed } from "../lib/experiments";
import registryMd from "../../../research/registry.md?raw";
import { parseRegistry } from "../lib/registry";

const decisions = parseRegistry(registryMd).decisions;

export default function ExperimentDetail({ c, krav: kravAlla, total, onBack }: { c: Computed; krav: number; total: number; onBack: () => void }) {
  const { exp } = c;
  let krav = kravAlla;
  const real = c.källa === "HISTORIK";
  if (real && c.krav !== undefined) krav = c.krav;
  const passes = c.passes ?? c.t >= krav;
  const pos = c.position;
  const recent = [...c.trades].reverse().slice(0, 20);
  const [tab, setTab] = useState<"Marknad" | "Resultat">("Marknad");
  const series = seriesFor(exp.marknad, exp.tidsram);
  if (!real) {
    return (
      <Page title={`${exp.id} · ${exp.namn}`} sub={`${exp.strategi} · ${exp.marknad} · ${exp.tidsram} · ${exp.riktning}`}
        actions={<button className="btn" onClick={onBack}>← Tillbaka till rutorna</button>}>
        <div className="banner-sim" role="note"><b>Inte testad.</b> Den här idén har ingen registrerad hypotes och inget resultat än, så inga siffror visas. Nedan syns marknadens verkliga priser.</div>
        <CandleChart series={series} noSourceReason={`${exp.marknad} har ingen publik datakälla i appen än. Bara Bitcoin samlas in.`} />
      </Page>
    );
  }
  const fas1 = c.fas1;
  return (
    <Page
      title={`${exp.id} · ${exp.namn}`}
      sub={`${exp.strategi} · ${exp.marknad} · ${exp.tidsram} · ${exp.riktning}`}
      actions={<button className="btn" onClick={onBack}>← Tillbaka till rutorna</button>}
    >
      {real ? (
        <div className="banner-real" role="note">
          <span className="chip-real">HISTORIK</span> Backtest på riktig historik för <b>{c.hypotes}</b>
          {c.period && <> ({c.period[0].slice(0, 10)} till {c.period[1].slice(0, 10)})</>}, registrerad i commit <code>{c.registerCommit?.slice(0, 7)}</code>.
          Det är inte en prognos.
        </div>
      ) : null}

      <div className="kpis">
        <div className="card kpi"><span className="k">Avkastning efter kostnader</span><b className={c.avkastning >= 0 ? "up" : "down"}>{pct(c.avkastning)}</b><span className="muted">{c.stressad !== undefined ? `Med 2,5× kostnader: ${pct(c.stressad)}` : ""}</span></div>
        <div className="card kpi"><span className="k">Största nedgång</span><b>{pct(c.maxDrawdown)}</b><span className="muted">Från topp till botten</span></div>
        <div className="card kpi"><span className="k">Affärer</span><b>{c.antal}</b><span className="muted">{num(c.vinstandel, 0)} % vinnande</span></div>
        <div className="card kpi"><span className="k">t-värde mot krav</span><b>{num(c.t, 1)} <small>/ {num(krav, 1)}</small></b><span className={passes ? "pass" : "fail"}>{passes ? "över kravet" : "under kravet"}</span></div>
      </div>

      <div className="detail-tabs">
        <Segmented value={tab} options={["Marknad", "Resultat"]} onChange={setTab} />
        <span className="muted">{tab === "Marknad" ? "Instrumentets verkliga priser (OHLCV)" : "Strategins kapital, HISTORIK"}</span>
      </div>
      {tab === "Marknad" ? (
        <CandleChart
          series={series}
          noSourceReason={`${exp.marknad} har ingen publik datakälla i appen än. Bara Bitcoin och Ethereum (Binance spot) samlas in.`}
          trades={real ? c.affärer : []}
          tradesLabel={real ? `Markörer: affärer från det registrerade backtestet ${c.hypotes ?? ""} (HISTORIK)` : undefined}
        />
      ) : (
        <section className="card chart-card">
          <div className="card-head"><div><h2>Utveckling</h2><p className="muted">Strategin efter kostnader mot baslinjen köp-och-behåll. Start = 100.</p></div></div>
          <LineChart watermark={null} labels={c.labels} series={[{ name: exp.namn, data: c.equity, cls: "s1" }, { name: "Baslinje", data: c.baseline, cls: "s2" }]} />
          <div className="legend"><span><i className="swatch s1" />{exp.namn}</span><span><i className="swatch s2" />Baslinje (köp-och-behåll{fas1 ? ", bara pris utan finansieringsränta" : ""})</span></div>
          {fas1 && <p className="footnote" style={{ padding: "8px 0 0" }}>Kurvan är ihopsatt av sex halvår utanför urvalet (walk-forward): parametrarna för varje halvår valdes bara på data före det.</p>}
        </section>
      )}

      {fas1 && (
        <section className="card table-card">
          <div className="card-head"><div><h2>Walk-forward</h2><p className="muted">Sharpe i urvalet (där parametrarna valdes) mot utanför urvalet (nästa halvår). Stort glapp betyder överanpassning.</p></div></div>
          <div className="ttable" role="table">
            <div className="ttr head wf" role="row"><span>Testhalvår</span><span>I urvalet</span><span>Utanför urvalet</span></div>
            {fas1.windows.map((w) => (
              <div className="ttr wf" role="row" key={w.test[0]}>
                <span>{w.test[0]} till {w.test[1]}</span><span>{w.sharpe_in_sample == null ? "–" : num(w.sharpe_in_sample)}</span>
                <span className={(w.sharpe_out_of_sample ?? 0) >= 0 ? "up" : "down"}>{w.sharpe_out_of_sample == null ? "–" : num(w.sharpe_out_of_sample)}</span>
              </div>
            ))}
          </div>
          <p className="footnote">Parameterstabilitet {fas1.stability == null ? "–" : `${Math.round(fas1.stability * 100)} %`} · strategi <code>{fas1.runId}</code></p>
        </section>
      )}

      <div className="split">
        <section className="card pad">
          <h2>Innehav nu</h2>
          {pos.läge === "Ingen" ? <p className="muted" style={{ marginTop: 10 }}>Ingen öppen position i slutet av testet.</p> : (
            <dl className="dl" style={{ marginTop: 14 }}>
              <dt>Läge</dt><dd><b>{pos.läge}</b></dd>
              {pos.sedan && <><dt>Sedan</dt><dd>{pos.sedan}</dd></>}
              <dt>Storlek</dt><dd>{pos.storlek} % av kapitalet</dd>
              {pos.orealiserat !== undefined && <><dt>Orealiserat</dt><dd className={pos.orealiserat >= 0 ? "up" : "down"}>{pct(pos.orealiserat)}</dd></>}
            </dl>
          )}
          <p className="footnote" style={{ padding: "14px 0 0" }}>Papper. Aldrig riktiga order.</p>
        </section>
        <section className="card pad">
          <h2>Om testet</h2>
          <dl className="dl" style={{ marginTop: 14 }}>
            <dt>Status</dt><dd><StatusDot status={real ? (c.hypotes && decisions[c.hypotes]) || "Pågår" : "Idé"} /></dd>
            <dt>Hypotes</dt><dd>{real ? <b>{c.hypotes}</b> : <span className="muted">Inte registrerad än (<code>research/registry.md</code>)</span>}</dd>
            {real && c.deflated != null && <><dt>Deflated Sharpe</dt><dd>{num(c.deflated * 100, 0)} % sannolikhet att slå bästa tur efter alla försök</dd></>}
            {real && c.resultatfil && <><dt>Resultatfil</dt><dd><code>{c.resultatfil}</code></dd></>}
            <dt>Beslut</dt><dd>På stängd stapel, fyllning vid nästa öppning</dd>
            <dt>Kostnad per affär</dt><dd>{num(c.kostnadPerAffär, 2)} % (avgift, spread, slippage{exp.grupp === "terminer" ? ", finansiering" : ""})</dd>
            <dt>Krav</dt><dd>{real ? `t ≥ ${num(krav, 1)} enligt antalet försök i registret` : `${total} rutor räknas som försök, därför t ≥ ${num(krav, 1)}`}</dd>
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
              <span>{Number.isNaN(t.brutto) ? "–" : pct(t.brutto, 2)}</span><span>{Number.isNaN(t.kostnad) ? "–" : `${num(t.kostnad)} %`}</span><span className={t.netto >= 0 ? "up" : "down"}>{pct(t.netto, 2)}</span>
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
