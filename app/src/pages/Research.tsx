import { useMemo, useState } from "react";
import tracks from "../../data/tracks.json";
import { Sparkline } from "../components/Charts";
import { Icon } from "../components/icons";
import { Page, Segmented, SimChip, StatusDot } from "../components/ui";
import { hashSeed, walk } from "../lib/sim";

const FILTERS = ["Alla", "Idé", "Pågår", "REJECT", "Klara för papper"] as const;
type Filter = (typeof FILTERS)[number];

export default function Research() {
  const [filter, setFilter] = useState<Filter>("Alla");
  const [open, setOpen] = useState<string | null>(null);
  const rows = useMemo(
    () => tracks.map((t) => ({ ...t, spark: walk(hashSeed(t.id), 40, 0.001, 0.02) })),
    []
  );
  const shown = rows.filter((t) =>
    filter === "Alla" ? true : filter === "Klara för papper" ? t.status === "READY_FOR_PAPER" : t.status === filter
  );

  return (
    <Page
      title="Research"
      sub={`${tracks.length} spår. Utfallet står bredvid varje spår när det finns.`}
      actions={<Segmented value={filter} options={[...FILTERS]} onChange={setFilter} />}
    >
      <div className="card table-card">
        <div className="thead">
          <span>Spår</span><span>Marknad</span><span>Tidsram</span><span>Status</span>
          <span>Utfall <SimChip /></span><span />
        </div>
        {shown.length === 0 && <div className="empty">Inga spår med den statusen.</div>}
        {shown.map((t) => (
          <div key={t.id} className="trow-wrap">
            <div className="trow">
              <div className="cell-main"><b>{t.namn}</b><span className="muted">{t.id}</span></div>
              <span>{t.marknad}</span>
              <span>{t.tidsram}</span>
              <StatusDot status={t.status} />
              <div className="outcome"><Sparkline data={t.spark} /><span className="muted">Inga resultat än</span></div>
              <button className="link" onClick={() => setOpen(open === t.id ? null : t.id)} aria-expanded={open === t.id}>
                Varför? <Icon name={open === t.id ? "down" : "chevron"} size={14} />
              </button>
            </div>
            {open === t.id && (
              <div className="detail">
                <div><span className="k">Hypotes</span><p>{t.idé}</p></div>
                <div><span className="k">Nästa steg</span><p>{t.nästaSteg}</p></div>
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="footnote">Trendlinjerna är påhittade exempel och visar inga resultat. Ett spår får riktiga siffror först efter att hypotesen registrerats och granskats.</p>
    </Page>
  );
}
