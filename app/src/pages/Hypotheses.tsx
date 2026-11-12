import { useMemo, useState } from "react";
import registryMd from "../../../research/registry.md?raw";
import { Segmented, StatusDot } from "../components/ui";
import { groupRegistry, missingPrices, parseRegistry } from "../lib/registry";
import { tKrav } from "../lib/stats";

const f = (n: number) => n.toFixed(2).replace(".", ",");
const reg = parseRegistry(registryMd);
const FILTERS = ["Alla", "Avvisade", "Pågår", "Ogiltiga", "Vidare"] as const;
type Filter = (typeof FILTERS)[number];
const MÅL_NAMN: Record<string, string> = { A: "Slå marknaden", B: "Lägre risk", C: "Marknadsneutral" };

/** Registret som en lista: en rad per hypotes (registrering, resultat och beslut ihop). Klick visar allt. */
export default function Hypotheses() {
  const all = useMemo(() => groupRegistry(reg).reverse(), []);
  const [filter, setFilter] = useState<Filter>("Alla");
  const [open, setOpen] = useState<string | null>(null);
  const [n, setN] = useState(Math.max(1, reg.attempts));
  const shown = all.filter((h) => filter === "Alla" ? true : filter === "Avvisade" ? h.decision === "REJECT"
    : filter === "Pågår" ? !h.decision && !h.invalid : filter === "Ogiltiga" ? h.invalid
    : h.decision === "MORE_RESEARCH" || h.decision === "READY_FOR_PAPER");
  const avvisade = all.filter((h) => h.decision === "REJECT").length;
  const vidare = all.filter((h) => h.decision === "MORE_RESEARCH" || h.decision === "READY_FOR_PAPER").length;
  return (
    <>
      <div className="kpis">
        <div className="card kpi"><span className="k">Registrerade</span><b>{reg.attempts}</b><span className="muted">Alla försök räknas, även avvisade</span></div>
        <div className="card kpi"><span className="k">Krav på t-värde nu</span><b>{f(tKrav(reg.attempts))}</b><span className="muted">Stiger med antalet försök</span></div>
        <div className="card kpi"><span className="k">Avvisade</span><b>{avvisade}</b><span className="muted">REJECT är ett bra utfall</span></div>
        <div className="card kpi"><span className="k">Gått vidare</span><b>{vidare}</b><span className="muted">Till slutprov eller papper</span></div>
      </div>

      <div className="toolbar"><Segmented value={filter} options={[...FILTERS]} onChange={setFilter} /></div>
      <section className="card hyp-list">
        {shown.length === 0 && <div className="empty">Inga hypoteser här.</div>}
        {shown.map((h) => (
          <div key={h.id} className={open === h.id ? "hyp open" : "hyp"}>
            <button type="button" className="hyp-row" onClick={() => setOpen(open === h.id ? null : h.id)} aria-expanded={open === h.id}>
              <b className="hyp-id">{h.id}</b>
              <span className="hyp-title">{h.title}<span className="muted"> · {h.market}</span></span>
              <span className="hyp-goal" title={MÅL_NAMN[h.track]}>{h.track}</span>
              <span className="hyp-t">{h.t === null ? "" : <>t {f(h.t)} <i>/ {f(h.krav ?? 0)}</i></>}</span>
              <span className="hyp-dec">{h.decision ? <StatusDot status={h.decision} /> : h.invalid ? <StatusDot status="OGILTIG" /> : <span className="muted">Pågår</span>}</span>
            </button>
            {open === h.id && (
              <div className="hyp-detail">
                <div><span className="k">Hypotes, registrerad {h.date}</span><p>{h.statement}</p></div>
                {h.criteria && h.criteria !== "Se registreringen" && <div><span className="k">Krav, bestämda i förväg</span><p>{h.criteria}</p></div>}
                {h.invalid && (() => {
                  const m = missingPrices(h.result);
                  return (
                    <div><span className="k">Ogiltig körning, inget beslut</span>
                      <p>Datakravet uppfylls inte{m ? <>: <b>{String(m.share).replace(".", ",")} % av vikten saknar kurs</b>, gränsen i förväg är {m.limit} %</> : ""}.
                        Siffrorna nedan är bara diagnostik och räknas inte som ett resultat.</p></div>
                  );
                })()}
                <div><span className="k">{h.invalid ? "Registrets text (diagnostik)" : "Resultat"}</span><p>{(h.result ?? "Inte kört än.").replace(/\*\*/g, "")}</p></div>
                {h.runs > 1 && <p className="muted">{h.runs} körningar i registret. Alla finns kvar, även ogiltiga.</p>}
              </div>
            )}
          </div>
        ))}
      </section>
      <p className="footnote">Från <code>research/registry.md</code> när appen byggdes. Rader ändras eller tas aldrig bort; nya resultat läggs till.</p>

      <details className="card pad calc">
        <summary><b>Varför stiger kravet?</b> <span className="muted">Räkna själv</span></summary>
        <p className="muted" style={{ marginTop: 8 }}>Ju fler idéer man testar, desto fler ser bra ut av ren tur. Därför höjs kravet med antalet försök.</p>
        <div className="bignum">{f(tKrav(n))}</div>
        <label className="slider">
          <span>Antal försök: <b>{n}</b></span>
          <input type="range" min={1} max={200} value={n} onChange={(e) => setN(Number(e.target.value))} />
        </label>
      </details>
    </>
  );
}
