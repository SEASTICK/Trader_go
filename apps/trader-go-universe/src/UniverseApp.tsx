// TraderGO Universe: öppnar direkt på projektkartan. Appen läser bara projektmappen; panelen
// Diagnostik visar hur mappen hittades, bevakningens läge, kopplingar och trasiga länkar.
import { useCallback, useEffect, useState } from "react";
import { ProjectMap, type Status } from "./ProjectMap";
import { invoke, listen } from "./tauri";
import { UpdateDialog } from "@trader-go/updates/UpdateDialog";
import { useUpdater } from "@trader-go/updates/useUpdater";

export type Discovery = { root?: string | null; source: "searching" | "saved" | "env" | "dev" | "found" | "none"; tried: string[] };

const SOURCE_LABEL: Record<Discovery["source"], string> = {
  searching: "letar…", saved: "vald av dig", env: "från TRADERGO_ROOT", dev: "utvecklingskopian", found: "hittad automatiskt", none: "inte hittad",
};
const KIND_LABEL: Record<string, string> = { Explicit: "Länkar", Dependency: "Beroenden", Inferred: "Härledda" };
const STATE_LABEL: Record<Status["state"], string> = { unconfigured: "Ingen mapp", indexing: "Indexerar…", idle: "Bevakar", error: "Fel" };

function Diagnostics({ status, discovery, onClose }: { status?: Status; discovery?: Discovery; onClose: () => void }) {
  return (
    <aside className="uv-panel" aria-label="Diagnostik">
      <div className="uv-panel-head"><h3>Diagnostik</h3><button className="icon-btn" onClick={onClose} aria-label="Stäng">✕</button></div>
      <section className="uv-sec">
        <h4>Projektmapp</h4>
        <p className="small">{status?.root ?? discovery?.root ?? "Ingen"}</p>
        {discovery && <p className="muted small">Källa: {SOURCE_LABEL[discovery.source]}. Universe ändrar aldrig filer i mappen.</p>}
        {discovery?.source === "none" && discovery.tried.length > 0 && (
          <details><summary className="muted small">Platser som provades</summary><ul className="uv-list">{discovery.tried.map((t) => <li key={t}>{t}</li>)}</ul></details>
        )}
      </section>
      {status && status.state !== "unconfigured" && (
        <>
          <section className="uv-sec">
            <h4>Bevakning</h4>
            <p className={status.state === "error" ? "error" : "muted"}>
              {STATE_LABEL[status.state]}{status.message ? `: ${status.message}` : ""}
              {status.last_run ? ` · senast ${new Date(status.last_run).toLocaleTimeString("sv-SE")}` : ""}
            </p>
          </section>
          <section className="uv-sec">
            <h4>Kopplingar</h4>
            <ul className="uv-list">
              <li>{status.files} filer på kartan</li>
              {Object.entries(status.by_kind ?? {}).map(([k, n]) => <li key={k}>{KIND_LABEL[k] ?? k}: {n}</li>)}
              <li>{status.unconnected} filer utan koppling (gruppen Unconnected / To review)</li>
            </ul>
          </section>
          <section className="uv-sec">
            <h4>Trasiga länkar ({status.broken?.length ?? 0})</h4>
            {!status.broken?.length ? <p className="muted">Alla länkar pekar på filer som finns.</p> : (
              <>
                <p className="muted small">Länkar i anteckningar som inte hittar sin fil. Universe rättar dem inte; ändra i Obsidian eller i editorn.</p>
                <ul className="uv-list">{status.broken.map((b, i) => <li key={i}><b>{b.from}</b> → {b.target}</li>)}</ul>
              </>
            )}
          </section>
        </>
      )}
      <p className="muted small">Undantaget från kartan: .gitignore, .env*, nycklar, node_modules, target, dist, gen, cachemappar och .obsidian.</p>
    </aside>
  );
}

export default function UniverseApp() {
  const updater = useUpdater(__APP_VERSION__);
  const [status, setStatus] = useState<Status>();
  const [discovery, setDiscovery] = useState<Discovery>();
  // Öppnar på kartan med diagnostikpanelen synlig; den går att stänga.
  const [panel, setPanel] = useState(true);
  const onStatus = useCallback((s: Status) => setStatus(s), []);

  useEffect(() => {
    const off = listen<Discovery>("universe-discovery", (e) => setDiscovery(e.payload));
    off.then(() => invoke<Discovery>("universe_discovery")).then(setDiscovery).catch(() => {});
    return () => { off.then((f) => f()); };
  }, []);

  const broken = status?.broken?.length ?? 0;
  const u = updater.notice;

  return (
    <div className="uv">
      <header className="uv-bar">
        <img src="/universe.svg" className="logo" alt="" />
        <b>TraderGO Universe</b>
        <span className="muted">v{__APP_VERSION__} · bara läsning</span>
        <span className="uv-spacer" />
        <button className={`uv-sync ${status?.state === "error" ? "error" : status?.state === "idle" ? "synced" : ""}${broken ? " warn" : ""}`} onClick={() => setPanel(!panel)}>
          <i /> Diagnostik{status ? ` · ${STATE_LABEL[status.state]}` : ""}{broken ? ` · ${broken} trasiga länkar` : ""}
        </button>
        {updater.enabled && (
          <button className="btn small" disabled={u.status === "checking" || u.status === "installing"} onClick={() => { if (u.status === "available") updater.openPrompt(); else void updater.checkNow(false); }}>
            {u.status === "available" ? `v${u.version} finns` : u.status === "checking" ? "Söker…" : u.status === "current" ? "Senaste versionen" : u.status === "error" ? "Uppdateringsfel" : "Sök uppdatering"}
          </button>
        )}
      </header>
      <div className="uv-main">
        <ProjectMap onStatus={onStatus} searching={!discovery || discovery.source === "searching"} />
        {panel && <Diagnostics status={status} discovery={discovery} onClose={() => setPanel(false)} />}
      </div>
      <UpdateDialog notice={u} currentVersion={__APP_VERSION__} onInstall={() => { void updater.install(); }} onLater={updater.later} onDismissError={updater.dismissError} />
    </div>
  );
}
