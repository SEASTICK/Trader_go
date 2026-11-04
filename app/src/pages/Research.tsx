import { useMemo, useState } from "react";
import experiments from "../../data/experiments.json";
import results from "../../data/results.json";
import { Sparkline } from "../components/Charts";
import { Page, Segmented } from "../components/ui";
import { MÅL, fromResult, kravFör, målFör, num, pct, type Computed, type Experiment, type RealResult } from "../lib/experiments";
import ExperimentDetail from "./ExperimentDetail";
import Hypotheses from "./Hypotheses";

const VIEWS = ["Resultat", "Hypoteser"] as const;
type View = (typeof VIEWS)[number];
const SORTS = ["Standard", "Avkastning", "t-värde"] as const;
type Sort = (typeof SORTS)[number];
function Tile({ c, krav: kravAlla, onOpen }: { c: Computed; krav: number; onOpen: () => void }) {
  if (c.källa !== "HISTORIK") {
    return (
      <button type="button" className="rtile untested" data-group={c.exp.grupp} onClick={onOpen} aria-label={`${c.exp.namn}, inte testad, öppna`}>
        <span className="rtile-top"><b>{c.exp.id}</b><span className="sim-tag">EJ TESTAD</span></span>
        <span className="rtile-name">{c.exp.namn}</span>
        <span className="rtile-sub">{c.exp.strategi}</span>
        <span className="rtile-empty">Ingen registrerad hypotes än. Inga siffror visas förrän den är testad på riktig historik.</span>
      </button>
    );
  }
  const up = c.avkastning >= 0;
  const krav = c.krav ?? kravAlla;
  // Riktiga resultat bedöms mot alla kriterier i sitt spår, påhittade bara mot t-kravet.
  const passes = c.klararMål ?? c.passes ?? c.t >= krav;
  return (
    <button type="button" className="rtile" data-group={c.exp.grupp} onClick={onOpen} aria-label={`${c.exp.namn}, öppna detaljer`}>
      <span className="rtile-top"><b>{c.exp.id}</b><span className={c.källa === "HISTORIK" ? "sim-tag real" : "sim-tag"}>{c.källa === "HISTORIK" ? "HISTORIK" : "SIM"}</span></span>
      <span className="rtile-name">{c.exp.namn}</span>
      <span className="rtile-sub">{c.exp.strategi}</span>
      <span className="rtile-mid">
        <span className={`rtile-ret ${up ? "up" : "down"}`}>{up ? "▲" : "▼"} {pct(c.avkastning)}</span>
        <Sparkline data={c.equity} w={92} h={34} />
      </span>
      <span className="rtile-foot">
        <span>t {num(c.t, 1)} <i>/ krav {num(krav, 1)}</i></span>
        <span className={passes ? "pass" : "fail"}>{c.klararMål === undefined ? (passes ? "över kravet" : "under kravet") : (passes ? "klarar målet" : "klarar inte målet")}</span>
      </span>
    </button>
  );
}

export default function Research() {
  const [view, setView] = useState<View>("Resultat");
  const [sort, setSort] = useState<Sort>("Standard");
  const [open, setOpen] = useState<string | null>(null);
  // JSON-filen skrivs av motorn. Bara poster märkta HISTORIK räknas som resultat.
  const real = useMemo(() => Object.fromEntries(
    Object.entries(results as unknown as Record<string, RealResult>).filter(([, r]) => r && r.source === "HISTORIK"),
  ), []);
  // Bara rutor med ett riktigt resultat visas. Nya idéer läggs till när de registrerats och körts (skillen ny-ruta).
  const all = useMemo(() => (experiments as Experiment[]).filter((e) => real[e.id]).map((e) => fromResult(e, real[e.id])), [real]);
  const tested = all;
  const krav = kravFör(all.length);
  const sorted = useMemo(() => {
    const a = [...tested];
    if (sort === "Avkastning") a.sort((x, y) => y.avkastning - x.avkastning);
    if (sort === "t-värde") a.sort((x, y) => y.t - x.t);
    return a;
  }, [tested, sort]);

  const selected = open ? all.find((c) => c.exp.id === open) : undefined;
  if (selected) return <ExperimentDetail c={selected} krav={krav} total={all.length} onBack={() => setOpen(null)} />;

  const sub = view === "Resultat" ? `${tested.length} idéer testade på riktig historik, grupperade efter mål.`
    : "Varje idé skrivs ned med krav innan den testas. Alla försök räknas.";
  return (
    <Page title="Research" sub={sub} actions={<Segmented value={view} options={[...VIEWS]} onChange={setView} />}>
      {view === "Hypoteser" && <Hypotheses />}

      {view === "Resultat" && (
        <>
          <div className="toolbar">
            <span className="muted">Sortera efter</span>
            <Segmented value={sort} options={[...SORTS]} onChange={setSort} />
          </div>
          {MÅL.map((m) => {
            const items = sorted.filter((c) => målFör(c.exp) === m.key);
            if (!items.length) return null;
            const klarar = items.filter((c) => c.klararMål).length;
            return (
              <section key={m.key} className="rsection">
                <div className="rsection-head">
                  <span className="mål-badge">{m.key}</span>
                  <h2>{m.label}</h2>
                  <span className="muted">{items.length} testade · {klarar} klarar målet</span>
                </div>
                <p className="mål-krav">{m.desc} <b>Krav:</b> {m.krav}</p>
                <div className="rgrid">
                  {items.map((c) => <Tile key={c.exp.id} c={c} krav={krav} onOpen={() => setOpen(c.exp.id)} />)}
                </div>
              </section>
            );
          })}
          {sort !== "Standard" && (
            <p className="callout">
              <b>Se upp:</b> att sortera efter resultat ger alltid några "vinnare" av ren tur. Titta på om rutan <i>klarar målet</i>, inte bara på procenten.
            </p>
          )}
          <p className="footnote">Ett backtest på historik är inte en prognos.</p>
        </>
      )}
    </Page>
  );
}
