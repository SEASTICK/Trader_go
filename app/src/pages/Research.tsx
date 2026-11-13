import { useMemo, useState } from "react";
import experiments from "../../data/experiments.json";
import results from "../../data/results.json";
import { Details, Page, Segmented } from "../components/ui";
import { MÅL, fromResult, målFör, num, pct, type Computed, type Experiment, type RealResult } from "../lib/experiments";
import ExperimentDetail from "./ExperimentDetail";
import Hypotheses from "./Hypotheses";
import { kravFör } from "../lib/experiments";

const VIEWS = ["Testade idéer", "Alla försök"] as const;
type View = (typeof VIEWS)[number];
const SORTS = ["Standard", "Avkastning"] as const;
type Sort = (typeof SORTS)[number];

/** En rad per testad idé: namn, kort besked och historisk avkastning. Detaljerna ligger på detaljsidan. */
function Row({ c, onOpen }: { c: Computed; onOpen: () => void }) {
  const passes = c.klararMål ?? c.passes ?? false;
  return (
    <button type="button" className="result-row" onClick={onOpen} aria-label={`${c.exp.namn}, ${passes ? "klarade testkraven" : "klarade inte testkraven"}, öppna detaljer`}>
      <span className="rr-main"><b>{c.exp.namn}</b><span className="muted">{c.exp.strategi}</span></span>
      <span className={passes ? "outcome-tag good" : "outcome-tag"}>{passes ? "Klarade testkraven" : "Klarade inte testkraven"}</span>
      <span className="rr-num"><span className="k">Historik</span>{pct(c.avkastning)}</span>
    </button>
  );
}

export default function Research() {
  const [view, setView] = useState<View>("Testade idéer");
  const [sort, setSort] = useState<Sort>("Standard");
  const [open, setOpen] = useState<string | null>(null);
  // JSON-filen skrivs av motorn. Bara poster märkta HISTORIK räknas som resultat.
  const real = useMemo(() => Object.fromEntries(
    Object.entries(results as unknown as Record<string, RealResult>).filter(([, r]) => r && r.source === "HISTORIK"),
  ), []);
  const all = useMemo(() => (experiments as Experiment[]).filter((e) => real[e.id]).map((e) => fromResult(e, real[e.id])), [real]);
  const krav = kravFör(all.length);
  const sorted = useMemo(() => {
    const a = [...all];
    if (sort === "Avkastning") a.sort((x, y) => y.avkastning - x.avkastning);
    return a;
  }, [all, sort]);

  const selected = open ? all.find((c) => c.exp.id === open) : undefined;
  if (selected) return <ExperimentDetail c={selected} krav={krav} total={all.length} onBack={() => setOpen(null)} />;

  const klarar = all.filter((c) => c.klararMål).length;
  return (
    <Page title="Resultat" sub={view === "Testade idéer" ? `${all.length} testade idéer med egen resultatrad. ${klarar === 0 ? "Ingen har klarat testkraven." : `${klarar} klarade testkraven.`} Alla registrerade försök finns under Alla försök.` : "Varje idé skrivs ned innan den testas. Alla försök räknas."}
      actions={<Segmented value={view} options={[...VIEWS]} onChange={setView} />}>
      {view === "Alla försök" && <Hypotheses />}

      {view === "Testade idéer" && (
        <>
          <div className="toolbar">
            <span className="muted">Sortera</span>
            <Segmented value={sort} options={[...SORTS]} onChange={setSort} />
          </div>
          {MÅL.map((m) => {
            const items = sorted.filter((c) => målFör(c.exp) === m.key);
            if (!items.length) return null;
            return (
              <section key={m.key} className="group">
                <h2>{m.label}</h2>
                <p className="muted small">{m.desc}</p>
                <div className="result-list">
                  {items.map((c) => <Row key={c.exp.id} c={c} onOpen={() => setOpen(c.exp.id)} />)}
                </div>
              </section>
            );
          })}
          {sort !== "Standard" && (
            <p className="note" role="note"><b>Se upp:</b> när man sorterar efter avkastning ser några idéer bra ut av ren tur. Titta på om idén klarade testkraven, inte bara på procenten.</p>
          )}
          <Details summary="Så bedöms idéerna">
            <p>Kraven bestäms i förväg och gäller alla försök. <b>Klarade inte testkraven</b> betyder att idén inte uppfyllde dem. Det betyder inte att historiken var negativ.</p>
            <ul className="plain">
              {MÅL.map((m) => <li key={m.key}><b>{m.label}.</b> {m.krav}</li>)}
            </ul>
            <p className="muted small">Ett backtest på historik är inte en prognos.</p>
          </Details>
        </>
      )}
    </Page>
  );
}
