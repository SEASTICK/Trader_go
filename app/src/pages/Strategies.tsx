import { useMemo, useState } from "react";
import registryMd from "../../../research/registry.md?raw";
import paper13f from "../../data/paper13f.json";
import { Details, Outcome, Segmented } from "../components/ui";
import { num, pct, type Computed } from "../lib/experiments";
import { parseRegistry } from "../lib/registry";
import { OUTCOME_HELP } from "../lib/status";
import { buildStrategies, filterStrategies, STRATEGY_FILTERS, type PaperObservation, type Strategy, type StrategyFilter } from "../lib/strategies";

const reg = parseRegistry(registryMd);
const KEY = "strategy";
const money = (v: number) => `${Math.round(v).toLocaleString("sv-SE")} kr`;

function loadChoice(): string | null { try { return window.localStorage.getItem(KEY); } catch { return null; } }
function saveChoice(id: string) { try { window.localStorage.setItem(KEY, id); } catch { /* ignoreras */ } }

function PaperBox({ s, goPaper }: { s: Strategy; goPaper?: () => void }) {
  const p = s.paper;
  if (p.kind === "observation") {
    const diff = (p.obs.value / p.obs.start_capital - 1) * 100;
    const spy = (p.obs.spy_value / p.obs.start_capital - 1) * 100;
    return (
      <div className="strat-paper on">
        <span className="k">Papper</span>
        <p><b>Följs på papper sedan {p.obs.start}</b> som observation, inte som ett godkänt test. Värde {money(p.obs.value)} ({pct(diff)}), jämfört med S&amp;P 500 {pct(spy)}. Inga riktiga pengar.</p>
        {goPaper && <button type="button" className="btn" onClick={goPaper}>Visa på Papper</button>}
      </div>
    );
  }
  if (p.kind === "ready") {
    return (
      <div className="strat-paper on">
        <span className="k">Papper</span>
        <p><b>Redo för papper.</b> Ett papperstest startas enligt våra regler (papper-framat), inte från appen. Appen lägger aldrig några order.</p>
      </div>
    );
  }
  return (
    <div className="strat-paper">
      <span className="k">Papper</span>
      <p><b>Körs inte på papper.</b> {p.reason}</p>
    </div>
  );
}

function Numbers({ c }: { c: Computed }) {
  const krav = c.krav;
  return (
    <div className="strat-kpis">
      <div><span className="k">Historik</span><b className={c.avkastning >= 0 ? "up" : "down"}>{pct(c.avkastning)}</b></div>
      <div><span className="k">Största fall</span><b>{pct(c.maxDrawdown)}</b></div>
      <div><span className="k">{c.portfölj ? "Ombalanseringar" : "Affärer"}</span><b>{c.antal}</b></div>
      <div><span className="k">t-värde</span><b>{num(c.t)}</b>{krav !== undefined && <span className="muted small">{c.t >= krav ? "över" : "under"} kravet {num(krav)}</span>}</div>
    </div>
  );
}

/** Välj en strategi i listan och se status, siffror och om den körs på papper. Bara visning. */
export default function Strategies({ results, onOpenResult, goPaper }: { results: Computed[]; onOpenResult: (expId: string) => void; goPaper?: () => void }) {
  const all = useMemo(() => buildStrategies(reg, results, paper13f as unknown as PaperObservation), [results]);
  const [filter, setFilter] = useState<StrategyFilter>("Alla");
  const [chosen, setChosen] = useState<string | null>(() => { const c = loadChoice(); return all.some((s) => s.id === c) ? c : all[0]?.id ?? null; });
  const shown = filterStrategies(all, filter);
  const s = shown.find((x) => x.id === chosen) ?? shown[0];
  const choose = (id: string) => { setChosen(id); saveChoice(id); };
  const onPaper = all.filter((x) => x.paper.kind !== "blocked").length;

  return (
    <>
      <p className="lead-line">{all.length} strategier är registrerade. Välj en för att se status och resultat. {onPaper === 0 ? "Ingen är redo för papper än." : `${onPaper} följs på papper.`}</p>
      <div className="toolbar"><Segmented value={filter} options={[...STRATEGY_FILTERS]} onChange={setFilter} /></div>
      <div className="strat">
        <section className="card strat-list" aria-label="Strategier">
          {shown.length === 0 && <div className="empty">Inga strategier här.</div>}
          {shown.map((x) => (
            <button key={x.id} type="button" className={s?.id === x.id ? "strat-item on" : "strat-item"} aria-pressed={s?.id === x.id} onClick={() => choose(x.id)}>
              <b className="hyp-id">{x.id}</b>
              <span className="strat-name">{x.name}</span>
              <Outcome kind={x.outcome} />
            </button>
          ))}
        </section>

        {s && (
          <section className="card pad strat-detail" aria-live="polite" aria-label={`Vald strategi ${s.id}`}>
            <div className="strat-head">
              <div>
                <span className="k">{s.id} · {s.trackLabel}</span>
                <h2>{s.name}</h2>
                <p className="muted">{s.market}</p>
              </div>
              <Outcome kind={s.outcome} />
            </div>
            {OUTCOME_HELP[s.outcome] && <p className="muted small">{OUTCOME_HELP[s.outcome]}</p>}

            {s.result ? <Numbers c={s.result} /> : (
              <p className="muted small">{s.hyp.invalid ? "Ingen giltig resultatrad: testet kunde inte avgöras." : s.outcome === "pending" ? "Inget resultat än." : "Ingen egen resultatrad i appen. Utfallet står i registret nedan."}</p>
            )}
            {s.result && <p className="muted small">Resultat i test på historik, efter kostnader. Inte en prognos.</p>}

            <PaperBox s={s} goPaper={goPaper} />

            <div className="strat-text">
              <span className="k">Hypotes, registrerad {s.hyp.date}</span>
              <p>{s.hyp.statement}</p>
            </div>
            {s.hyp.result && (
              <div className="strat-text">
                <span className="k">{s.hyp.invalid ? "Registrets text (diagnostik)" : "Utfall i registret"}</span>
                <p>{s.hyp.result.replace(/\*\*/g, "")}</p>
              </div>
            )}
            {s.hyp.criteria && s.hyp.criteria !== "Se registreringen" && (
              <Details summary="Krav, bestämda i förväg"><p>{s.hyp.criteria}</p></Details>
            )}
            {s.result && (
              <div className="strat-actions"><button type="button" className="btn accent" onClick={() => onOpenResult(s.result!.exp.id)}>Öppna hela resultatet</button></div>
            )}
          </section>
        )}
      </div>
      <p className="footnote">Från <code>research/registry.md</code> och motorns resultat när appen byggdes. Nya strategier syns först i nästa version av appen.</p>
    </>
  );
}
