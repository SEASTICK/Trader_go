import { useMemo, useState } from "react";
import registryMd from "../../../research/registry.md?raw";
import { Outcome, Segmented } from "../components/ui";
import { outcomeOf } from "../lib/status";
import { groupRegistry, missingPrices, NO_RUN_HEADING, NO_RUN_TEXT, parseRegistry } from "../lib/registry";
import { tKrav } from "../lib/stats";

const f = (n: number) => n.toFixed(2).replace(".", ",");
const reg = parseRegistry(registryMd);
const FILTERS = ["Alla", "Klarade inte kraven", "Väntar", "Kunde inte avgöras", "Gick vidare"] as const;
type Filter = (typeof FILTERS)[number];

/** Registret som en lista: en rad per hypotes (registrering, resultat och beslut ihop). Klick visar allt. */
export default function Hypotheses() {
  const all = useMemo(() => groupRegistry(reg).reverse(), []);
  const [filter, setFilter] = useState<Filter>("Alla");
  const [open, setOpen] = useState<string | null>(null);
  const [n, setN] = useState(Math.max(1, reg.attempts));
  const shown = all.filter((h) => filter === "Alla" ? true : filter === "Klarade inte kraven" ? outcomeOf(h) === "rejected"
    : filter === "Väntar" ? outcomeOf(h) === "pending" : filter === "Kunde inte avgöras" ? outcomeOf(h) === "invalid"
    : outcomeOf(h) === "further" || outcomeOf(h) === "paper");
  const avvisade = all.filter((h) => h.decision === "REJECT").length;
  const vidare = all.filter((h) => h.decision === "MORE_RESEARCH" || h.decision === "READY_FOR_PAPER").length;
  return (
    <>
      <p className="lead-line">{reg.attempts} försök är registrerade. Kravet på t-värde är just nu {f(tKrav(reg.attempts))} och stiger med antalet försök. {avvisade} klarade inte testkraven{vidare ? `, ${vidare} gick vidare` : ""}.</p>

      <div className="toolbar"><Segmented value={filter} options={[...FILTERS]} onChange={setFilter} /></div>
      <section className="card hyp-list">
        {shown.length === 0 && <div className="empty">Inga hypoteser här.</div>}
        {shown.map((h) => (
          <div key={h.id} className={open === h.id ? "hyp open" : "hyp"}>
            <button type="button" className="hyp-row" onClick={() => setOpen(open === h.id ? null : h.id)} aria-expanded={open === h.id}>
              <b className="hyp-id">{h.id}</b>
              <span className="hyp-title">{h.title}<span className="muted"> · {h.market}</span></span>
                                          <span className="hyp-dec"><Outcome kind={outcomeOf(h)} /></span>
            </button>
            {open === h.id && (
              <div className="hyp-detail">
                <div><span className="k">Hypotes, registrerad {h.date}</span><p>{h.statement}</p></div>
                {h.criteria && h.criteria !== "Se registreringen" && <div><span className="k">Krav, bestämda i förväg</span><p>{h.criteria}</p></div>}
                {h.invalid && h.noRun && (
                  <div><span className="k">{NO_RUN_HEADING}</span><p>{NO_RUN_TEXT}</p></div>
                )}
                {h.invalid && !h.noRun && (() => {
                  const m = missingPrices(h.result);
                  return (
                    <div><span className="k">Ogiltig körning, inget beslut</span>
                      <p>Datakravet uppfylls inte{m ? <>: <b>{String(m.share).replace(".", ",")} % av vikten saknar kurs</b>, gränsen i förväg är {m.limit} %</> : ""}.
                        Siffrorna nedan är bara diagnostik och räknas inte som ett resultat.</p></div>
                  );
                })()}
                <div><span className="k">{h.invalid ? (h.noRun ? "Datadiagnos (inget strategiutfall)" : "Registrets text (diagnostik)") : "Resultat"}</span><p>{(h.result ?? "Inte kört än.").replace(/\*\*/g, "")}</p></div>
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
