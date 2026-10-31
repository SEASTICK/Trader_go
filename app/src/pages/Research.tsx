import { useMemo, useState } from "react";
import experiments from "../../data/experiments.json";
import { Sparkline } from "../components/Charts";
import { Page, Segmented, SimChip } from "../components/ui";
import { compute, kravFör, num, pct, type Computed, type Experiment } from "../lib/experiments";
import ExperimentDetail from "./ExperimentDetail";
import { TrackList } from "./TrackList";

const VIEWS = ["Rutor", "Spår"] as const;
type View = (typeof VIEWS)[number];
const SORTS = ["Standard", "Namn", "Avkastning", "t-värde"] as const;
type Sort = (typeof SORTS)[number];
const GROUP_LABEL: Record<string, string> = { krypto: "Krypto", terminer: "Terminer", aktier: "Aktier", makro: "Makro / nyheter", baslinje: "Baslinje" };

function Tile({ c, krav, onOpen }: { c: Computed; krav: number; onOpen: () => void }) {
  const up = c.avkastning >= 0;
  const passes = c.t >= krav;
  return (
    <button type="button" className="rtile" data-group={c.exp.grupp} onClick={onOpen} aria-label={`${c.exp.namn}, öppna detaljer`}>
      <span className="rtile-top"><b>{c.exp.id}</b><span className="sim-tag">SIM</span></span>
      <span className="rtile-name">{c.exp.namn}</span>
      <span className="rtile-sub">{c.exp.strategi}</span>
      <span className="rtile-mid">
        <span className="rtile-ret">{up ? "▲" : "▼"} {pct(c.avkastning)}</span>
        <Sparkline data={c.equity} w={92} h={34} />
      </span>
      <span className="rtile-foot">
        <span>t {num(c.t, 1)} <i>/ krav {num(krav, 1)}</i></span>
        <span className={passes ? "pass" : "fail"}>{passes ? "över kravet" : "under kravet"}</span>
      </span>
    </button>
  );
}

export default function Research() {
  const [view, setView] = useState<View>("Rutor");
  const [sort, setSort] = useState<Sort>("Standard");
  const [open, setOpen] = useState<string | null>(null);
  const all = useMemo(() => (experiments as Experiment[]).map(compute), []);
  const krav = kravFör(all.length);
  const sorted = useMemo(() => {
    const a = [...all];
    if (sort === "Namn") a.sort((x, y) => x.exp.namn.localeCompare(y.exp.namn, "sv"));
    if (sort === "Avkastning") a.sort((x, y) => y.avkastning - x.avkastning);
    if (sort === "t-värde") a.sort((x, y) => y.t - x.t);
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
            <SimChip />
          </div>
          <div className="rgrid">
            {sorted.map((c) => <Tile key={c.exp.id} c={c} krav={krav} onOpen={() => setOpen(c.exp.id)} />)}
          </div>
          <div className="legend-groups">
            {Object.entries(GROUP_LABEL).map(([k, v]) => <span key={k}><i className="gdot" data-group={k} />{v}</span>)}
          </div>
          {(sort === "Avkastning" || sort === "t-värde") && (
            <p className="callout">
              <b>Se upp:</b> att sortera många rutor efter resultat ger alltid några "vinnare" av ren slump. Med {all.length} rutor är kravet på t-värde {num(krav, 1)}, inte 2. Av slump brukar flera rutor se bra ut, så titta på <i>över kravet</i>, antal affärer och om resultatet håller på ny data, inte bara på procenten.
            </p>
          )}
          <p className="footnote">Alla siffror är påhittade exempel, märkta SIM. Ingen ruta har ett riktigt resultat, och inget är registrerat som hypotes än.</p>
        </>
      )}
    </Page>
  );
}
