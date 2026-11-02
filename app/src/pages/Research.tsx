import { useMemo, useState } from "react";
import experiments from "../../data/experiments.json";
import results from "../../data/results.json";
import { Sparkline } from "../components/Charts";
import { Page, Segmented } from "../components/ui";
import { MÅL, compute, fromResult, kravFör, målFör, num, pct, type Computed, type Experiment, type RealResult } from "../lib/experiments";
import ExperimentDetail from "./ExperimentDetail";
import { TrackList } from "./TrackList";

const VIEWS = ["Rutor", "Spår"] as const;
type View = (typeof VIEWS)[number];
const SORTS = ["Standard", "Namn", "Avkastning", "t-värde"] as const;
type Sort = (typeof SORTS)[number];
const GROUPINGS = ["Mål", "Marknad"] as const;
type Grouping = (typeof GROUPINGS)[number];
const GROUPS = [
  { key: "krypto", label: "Krypto", desc: "Bitcoin och Ethereum, köpta och sålda direkt." },
  { key: "terminer", label: "Krypto-terminer", desc: "Short och finansieringsränta. Kräver koll på likvidation." },
  { key: "aktier", label: "Aktier", desc: "Aktier och index." },
  { key: "makro", label: "Makro och volatilitet", desc: "Regimer, räntor och volatilitet över flera marknader." },
  { key: "baslinje", label: "Baslinje", desc: "Köp-och-behåll. Det alla andra rutor måste slå efter kostnader." },
];

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
  const [view, setView] = useState<View>("Rutor");
  const [sort, setSort] = useState<Sort>("Standard");
  const [grouping, setGrouping] = useState<Grouping>("Mål");
  const [open, setOpen] = useState<string | null>(null);
  // JSON-filen skrivs av motorn. Bara poster som är märkta HISTORIK används, allt annat förblir SIM.
  const real = useMemo(() => Object.fromEntries(
    Object.entries(results as unknown as Record<string, RealResult>).filter(([, r]) => r && r.source === "HISTORIK"),
  ), []);
  const all = useMemo(() => (experiments as Experiment[]).map((e) => (real[e.id] ? fromResult(e, real[e.id]) : compute(e))), [real]);
  const antalRiktiga = all.filter((c) => c.källa === "HISTORIK").length;
  const krav = kravFör(all.length);
  const sorted = useMemo(() => {
    const a = [...all];
    if (sort === "Namn") a.sort((x, y) => x.exp.namn.localeCompare(y.exp.namn, "sv"));
    const tested = (c: Computed) => (c.källa === "HISTORIK" ? 1 : 0);
    if (sort === "Avkastning") a.sort((x, y) => tested(y) - tested(x) || y.avkastning - x.avkastning);
    if (sort === "t-värde") a.sort((x, y) => tested(y) - tested(x) || y.t - x.t);
    if (sort === "Standard") a.sort((x, y) => tested(y) - tested(x));
    return a;
  }, [all, sort]);

  const selected = open ? all.find((c) => c.exp.id === open) : undefined;
  if (selected) return <ExperimentDetail c={selected} krav={krav} total={all.length} onBack={() => setOpen(null)} />;

  return (
    <Page
      title="Research"
      sub={`${all.length} rutor. Varje ruta är ett test av en idé på en marknad och en tidsram.`}
      actions={<Segmented value={view} options={[...VIEWS]} onChange={setView} />}
    >
      {view === "Spår" ? <TrackList /> : (
        <>
          <div className="toolbar">
            <span className="muted">Sortera efter</span>
            <Segmented value={sort} options={[...SORTS]} onChange={setSort} />
            <span className="muted">Gruppera efter</span>
            <Segmented value={grouping} options={[...GROUPINGS]} onChange={setGrouping} />
          </div>
          {grouping === "Mål" && MÅL.map((m) => {
            const items = sorted.filter((c) => målFör(c.exp) === m.key);
            if (!items.length) return null;
            const testade = items.filter((c) => c.källa === "HISTORIK");
            const klarar = testade.filter((c) => c.klararMål).length;
            return (
              <section key={m.key} className="rsection">
                <div className="rsection-head">
                  <span className="mål-badge">{m.key}</span>
                  <h2>{m.label}</h2>
                  <span className="muted">{m.desc} {testade.length} testade på historik, {klarar} klarar målet.</span>
                </div>
                <p className="mål-krav"><b>Krav:</b> {m.krav}</p>
                <div className="rgrid">
                  {items.map((c) => <Tile key={c.exp.id} c={c} krav={krav} onOpen={() => setOpen(c.exp.id)} />)}
                </div>
              </section>
            );
          })}
          {grouping === "Marknad" && GROUPS.map((g) => {
            const items = sorted.filter((c) => c.exp.grupp === g.key);
            if (!items.length) return null;
            return (
              <section key={g.key} className="rsection">
                <div className="rsection-head">
                  <i className="gdot" data-group={g.key} />
                  <h2>{g.label}</h2>
                  <span className="muted">{items.length} {items.length === 1 ? "ruta" : "rutor"} · {g.desc}</span>
                </div>
                <div className="rgrid">
                  {items.map((c) => <Tile key={c.exp.id} c={c} krav={krav} onOpen={() => setOpen(c.exp.id)} />)}
                </div>
              </section>
            );
          })}
          {(sort === "Avkastning" || sort === "t-värde") && (
            <p className="callout">
              <b>Se upp:</b> att sortera många rutor efter resultat ger alltid några "vinnare" av ren slump. Med {all.length} rutor är kravet på t-värde {num(krav, 1)}, inte 2. Av slump brukar flera rutor se bra ut, så titta på <i>över kravet</i>, antal affärer och om resultatet håller på ny data, inte bara på procenten.
            </p>
          )}
          <p className="footnote">
            {antalRiktiga === 0
              ? "Ingen ruta har ett riktigt resultat än."
              : `${antalRiktiga} av ${all.length} rutor har ett riktigt backtest på historik (HISTORIK). Övriga är idéer som inte är testade och visar inga siffror. Ett backtest är inte en prognos.`}
          </p>
        </>
      )}
    </Page>
  );
}
