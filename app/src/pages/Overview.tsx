import { CandleChart } from "../components/CandleChart";
import { Page } from "../components/ui";
import { tKrav } from "../lib/stats";
import registryMd from "../../../research/registry.md?raw";
import { groupRegistry, parseRegistry } from "../lib/registry";
import type { SeriesRef } from "../lib/candles";

const STEPS = ["Idé", "Research", "Fryst", "Papper", "Liten live", "Live", "Pensionerad"];
const BTC_4H: SeriesRef = { provider: "binance", market: "spot", symbol: "BTCUSDT", interval: "4h" };

export default function Overview({ go }: { go: (p: "Research" | "Marknad") => void }) {
  const reg = parseRegistry(registryMd);
  const attempts = reg.attempts;
  const beslut = Object.values(reg.decisions);
  const rejects = beslut.filter((d) => d === "REJECT").length;
  const vidare = beslut.length - rejects;
  const väntar = attempts - beslut.length;
  // Närmast målet: avgjorda hypoteser med högst t i förhållande till sitt eget krav.
  const nära = groupRegistry(reg).filter((h) => h.t !== null && h.krav).sort((a, b) => (b.t! / b.krav!) - (a.t! / a.krav!)).slice(0, 3);
  const title = attempts === 0 ? "Inga hypoteser testade än" : `${attempts} ${attempts === 1 ? "hypotes" : "hypoteser"} registrerade`;
  const sub = attempts === 0
    ? "Varje idé registreras innan den testas. Det är normalt att de flesta blir REJECT."
    : `${rejects} REJECT, ${vidare} vidare${väntar ? `, ${väntar} väntar på resultat` : ""}. REJECT är ett bra utfall: idén höll inte efter kostnader, och inga pengar riskerades.`;

  return (
    <Page
      title={title}
      sub={sub}
      actions={<button className="btn" onClick={() => go("Research")}>Öppna Research</button>}
    >
      <div className="kpis">
        <div className="card kpi"><span className="k">Testade</span><b>{beslut.length}</b><span className="muted">{rejects} REJECT · {vidare} vidare</span></div>
        <div className="card kpi"><span className="k">Registrerade försök</span><b>{attempts}</b><span className="muted">Alla försök räknas, även övergivna</span></div>
        <div className="card kpi"><span className="k">Krav på t-värde</span><b>{tKrav(attempts).toFixed(1).replace(".", ",")}</b><span className="muted">Stiger med antal försök</span></div>
        <div className="card kpi"><span className="k">Gått vidare</span><b>{vidare}</b><span className="muted">Till slutprov eller papper</span></div>
      </div>

      {nära.length > 0 && (
        <section style={{ marginBottom: 22 }}>
          <div className="card-head" style={{ padding: "0 0 10px" }}>
            <div><h2>Närmast målet</h2><p className="muted">Högst t-värde i förhållande till kravet. Inget har klarat kravet än, så ingenting här är en signal att handla på.</p></div>
          </div>
          <div className="near">
            {nära.map((h) => (
              <button type="button" key={h.id} className="near-item" onClick={() => go("Research")}>
                <span className="muted">{h.id} · mål {h.track}</span>
                <b>{h.title}</b>
                <span className="near-bar" aria-label={`t ${h.t} av ${h.krav}`}><i style={{ width: `${Math.max(0, Math.min(100, (h.t! / h.krav!) * 100))}%` }} /></span>
                <span className="muted">t {h.t!.toFixed(2).replace(".", ",")} av krav {h.krav!.toFixed(2).replace(".", ",")} · {h.decision}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      <section style={{ marginBottom: 18 }}>
        <div className="card-head" style={{ padding: "0 0 10px" }}>
          <div><h2>Bitcoin just nu</h2><p className="muted">Verkliga priser från Binance spot. Inga riktiga order.</p></div>
          <button className="btn" onClick={() => go("Marknad")}>Öppna Marknad</button>
        </div>
        <CandleChart series={BTC_4H} noSourceReason="Ingen datakälla för den här marknaden än." />
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
