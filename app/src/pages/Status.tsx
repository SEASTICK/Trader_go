import { Page } from "../components/ui";
import type { useUpdater } from "../features/updates/useUpdater";
import { STATE_TEXT, useMarketStatus } from "../features/market/useMarketStatus";

type Updater = ReturnType<typeof useUpdater>;

function statusText(u: Updater): string {
  const { notice } = u;
  if (!u.enabled) return "Uppdateringar fungerar bara i skrivbordsprogrammet.";
  if (notice.status === "checking") return "Söker efter uppdateringar…";
  if (notice.status === "installing") return notice.message ?? "Uppdaterar…";
  if (notice.status === "available") return `Ny version v${notice.version} finns.`;
  if (notice.status === "downloading") return `Hämtar v${notice.version}…`;
  if (notice.status === "ready") return notice.message ?? `v${notice.version} är hämtad och verifierad.`;
  if (notice.status === "error") return notice.message ?? "Uppdateringskontrollen misslyckades.";
  if (notice.status === "current") return "Du har den senaste versionen.";
  if (u.diagnostics?.result === "error") return `${u.diagnostics.message ?? "Senaste kontrollen misslyckades."} Appen försöker igen av sig själv.`;
  if (u.diagnostics?.result === "current") return "Du har den senaste versionen.";
  return "Ingen kontroll gjord än.";
}

export default function Status({ updater }: { updater: Updater }) {
  const { notice, diagnostics } = updater;
  const busy = notice.status === "checking" || notice.status === "installing";
  const ready = notice.status === "ready" || (notice.status === "installing" && !!notice.version);
  return (
    <Page title="Status" sub="Är versionen densamma hos er båda ser ni samma program.">
      <section className="card pad">
        <h2>Uppdateringar</h2>
        <dl className="dl" style={{ marginTop: 16 }}>
          <dt>Installerad version</dt><dd><b>v{__APP_VERSION__}</b> <span className="muted">({__COMMIT__})</span></dd>
          <dt>Kanal</dt><dd>{__UPDATE_CHANNEL__ === "test" ? "Test (bara testbyggen)" : "Stable"} <span className="muted">({__UPDATE_FEED__})</span></dd>
          <dt>Läge</dt><dd>{statusText(updater)}</dd>
        </dl>
        <div className="update-actions" style={{ marginTop: 18 }}>
          {ready && <button type="button" className="btn accent" disabled={busy} onClick={updater.openPrompt}>{notice.status === "installing" ? "Uppdaterar…" : `Starta om med v${notice.version}`}</button>}
          <button type="button" className="btn" disabled={!updater.enabled || busy} onClick={() => { void updater.checkNow(false); }}>Sök efter uppdateringar</button>
        </div>
        {notice.status === "downloading" && notice.progress != null && (
          <div className="progress" style={{ marginTop: 14 }} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(notice.progress * 100)}>
            <i style={{ width: `${Math.round(notice.progress * 100)}%` }} />
          </div>
        )}
        {diagnostics && (
          <p className="footnote" style={{ padding: "16px 0 0" }}>
            Senaste kontrollen {new Date(diagnostics.checkedAt).toLocaleTimeString("sv-SE")}:{" "}
            {diagnostics.result === "available" ? `ny version v${diagnostics.version}` : diagnostics.result === "current" ? "ingen ny version" : "fel"}
            {diagnostics.detail ? ` (${diagnostics.detail})` : ""}
          </p>
        )}
      </section>
      <MarketData />
      <section className="card pad">
        <h2>Det här bygget</h2>
        <dl className="dl" style={{ marginTop: 16 }}>
          <dt>Senaste ändring</dt><dd>{__COMMIT_MSG__ || "okänd"}</dd>
          <dt>Byggd</dt><dd>{new Date(__BUILT_AT__).toLocaleString("sv-SE")}</dd>
          <dt>Läge</dt><dd>Forskning. Inga riktiga pengar, inga börskonton, inga order.</dd>
        </dl>
      </section>
    </Page>
  );
}

const time = (ms: number | null) => (ms == null ? "–" : new Date(ms).toLocaleString("sv-SE"));
const utc = (ms: number | null) => (ms == null ? "–" : new Date(ms).toISOString().slice(0, 16).replace("T", " ") + " UTC");

/** Insamlingen av publik marknadsdata (src-tauri/src/market). Bara läsning, inga nycklar eller order. */
function MarketData() {
  const { status: m, available } = useMarketStatus();
  return (
    <section className="card pad">
      <h2>Marknadsdata</h2>
      {!available ? (
        <p className="muted" style={{ marginTop: 12 }}>Insamlingen körs bara i skrivbordsprogrammet.</p>
      ) : !m ? (
        <p className="muted" style={{ marginTop: 12 }}>Väntar på status från insamlingen…</p>
      ) : (
        <dl className="dl" style={{ marginTop: 16 }}>
          <dt>Läge</dt><dd><b>{STATE_TEXT[m.state]}</b>{m.ready ? " · redo som analysunderlag" : " · inte redo"}{m.message ? ` (${m.message})` : ""}</dd>
          <dt>Källa</dt><dd>{m.provider} {m.market} {m.symbol} {m.interval} <span className="muted">(publik data, inga nycklar)</span></dd>
          <dt>Senast mottaget</dt><dd>{time(m.last_received_at)} <span className="muted">(serverns händelsetid {utc(m.last_event_time)})</span></dd>
          <dt>Senaste stängda stapel</dt><dd>{utc(m.last_closed_open_time)} <span className="muted">({m.closed_bars} stängda staplar sparade)</span></dd>
          <dt>Pågående stapel</dt><dd>{utc(m.live_open_time)} <span className="muted">(används inte som analysunderlag)</span></dd>
          <dt>Kvalitet</dt><dd>{m.gaps.length} öppna luckor, {m.confirmed_gaps} luckor som källan saknar, {m.corrections} rättelser, {m.rejected} avvisade meddelanden, {m.reconnects} återanslutningar</dd>
          <dt>Sparas i</dt><dd className="muted">{m.database}</dd>
        </dl>
      )}
      <p className="footnote" style={{ padding: "16px 0 0" }}>Varje dator samlar in själv. Det finns ingen gemensam server, så era datorer har inte en gemensam papperssession.</p>
    </section>
  );
}
