import { useMemo, useState } from "react";
import registryMd from "../../../research/registry.md?raw";
import { groupRegistry, parseRegistry, type Hypothesis } from "../lib/registry";
import { strategyName } from "../lib/strategyNames";

const KEY = "valdStrategi";
const fmt = (v: number) => v.toFixed(2).replace(".", ",").replace("-", "−");

/** Vad resultatet betyder, med vardagsord. */
export function verdict(h: Hypothesis): { label: string; text: string } {
  if (h.decision === "READY_FOR_PAPER") return { label: "Klarade testkraven", text: "Strategin klarade kraven som sattes i förväg och får prövas framåt på papper." };
  if (h.decision === "MORE_RESEARCH") return { label: "Behöver mer forskning", text: "Resultatet räckte inte för papper men var inte avvisat. Mer prövning krävs." };
  if (h.decision === "REJECT") return { label: "Klarade inte kraven", text: "Strategin uppfyllde inte kraven som sattes i förväg. Det betyder inte att historiken var negativ." };
  if (h.invalid) return { label: "Kunde inte avgöras", text: h.noRun ? "Testets eget datakrav kan inte uppfyllas, så ingen körning har gjorts." : "Datan räckte inte för ett giltigt test. Räknas aldrig som godkänd." };
  return { label: "Väntar på test", text: "Hypotesen är registrerad men inte testad än." };
}

function load(ids: string[]): string | null {
  try { const v = window.localStorage.getItem(KEY); return v && ids.includes(v) ? v : null; } catch { return null; }
}

/** Välj en registrerad strategi och se dess resultat i test, på enkel svenska. Data: research/registry.md, samma källa
 * som Resultat. Id, rå status och hela resultattexten visas inte här utan under Resultat; id:t finns kvar som
 * verktygstips och värde, så valet går att spåra till registret. */
export function StrategyPicker({ onOpenResults }: { onOpenResults?: () => void }) {
  const list = useMemo(() => groupRegistry(parseRegistry(registryMd)).slice().reverse(), []);
  const ids = list.map((h) => h.id);
  const [id, setId] = useState<string>(() => load(ids) ?? ids[0] ?? "");
  const h = list.find((x) => x.id === id);
  if (!h) return null;
  const n = strategyName(h.id, h.title);
  const v = verdict(h);
  const pick = (next: string) => {
    setId(next);
    try { window.localStorage.setItem(KEY, next); } catch { /* ignoreras: valet gäller bara den här visningen */ }
  };

  return (
    <section className="card pad strategy" aria-labelledby="strategy-head">
      <div className="strategy-top">
        <div>
          <h2 id="strategy-head">Strategier och resultat</h2>
          <p className="muted">Välj en strategi för att se hur den gick i det historiska testet.</p>
        </div>
        <label className="strategy-select">
          <span className="k">Strategi</span>
          <select value={h.id} onChange={(e) => pick(e.target.value)}>
            {list.map((x) => <option key={x.id} value={x.id} title={x.id}>{strategyName(x.id, x.title).name}</option>)}
          </select>
        </label>
      </div>

      <div className="strategy-body">
        <div className="strategy-name" title={h.id} data-id={h.id}>
          <h3>{n.name}</h3>
          <span className="muted small">Registrerad {h.date}, före testet</span>
          {n.idea && <p>{n.idea}</p>}
        </div>
        <dl className="dl compact">
          <dt>Utfall i test</dt>
          <dd><span className={`verdict ${h.decision === "READY_FOR_PAPER" ? "good" : h.decision === "REJECT" ? "bad" : "warn"}`}><i />{v.label}</span><br /><span className="muted">{v.text}</span></dd>
          {h.t !== null && h.krav !== null && (
            <>
              <dt>Styrka i testet</dt>
              <dd>{fmt(h.t)} mot kravet {fmt(h.krav)} <span className="muted">({h.t >= h.krav ? "över kravet" : "under kravet"})</span></dd>
            </>
          )}
          <dt>Körningar</dt><dd>{h.runs}</dd>
        </dl>
      </div>

      <p className="muted small">Ett historiskt test är ingen prognos och lovar ingen avkastning.</p>
      {onOpenResults && <p className="link-line"><button type="button" className="textbtn" onClick={onOpenResults}>Se alla resultat</button></p>}
    </section>
  );
}
