import { lazy, Suspense, useState } from "react";
import tracks from "../data/tracks.json";
import { isDesktop, Paper, Updates } from "./desktop";
// React Flow loads only when the map is opened, so the web build stays small.
const ProjectMap = lazy(() => import("./projectmap").then((m) => ({ default: m.ProjectMap })));

type Track = (typeof tracks)[number];
type Tab = "Översikt" | "Research" | "Hypoteser" | "Status" | "Projektkarta" | "Papper" | "Uppdateringar";
const TABS: Tab[] = ["Översikt", "Research", "Hypoteser", "Status", ...(isDesktop ? (["Projektkarta", "Papper", "Uppdateringar"] as Tab[]) : [])];

function Overview() {
  return (
    <section>
      <h2>Översikt</h2>
      <p>
        Trader_go är en tradingbot som byggs för eget bruk. Vi forskar brett på flera spår
        och går vidare med det som håller efter kostnader och efter att alla försök räknats.
      </p>
      <p>
        Livscykel: <strong>Idé → Research</strong> → Fryst → Papper → Liten live → Live → Pensionerad.
        Just nu är allt på <strong>Idé/Research</strong>. Inget är fryst, inget är på papper.
      </p>
      <p>Det är normalt att de flesta spår blir <code>REJECT</code>.</p>
    </section>
  );
}

function Research() {
  return (
    <section>
      <h2>Research</h2>
      <table>
        <thead>
          <tr>
            <th>Spår</th>
            <th>Marknad</th>
            <th>Tidsram</th>
            <th>Status</th>
            <th>Utfall</th>
            <th>Nästa steg</th>
          </tr>
        </thead>
        <tbody>
          {tracks.map((t: Track) => (
            <tr key={t.id}>
              <td>
                <strong>{t.id} {t.namn}</strong>
                <div className="muted">{t.idé}</div>
              </td>
              <td>{t.marknad}</td>
              <td>{t.tidsram}</td>
              <td><span className="badge">{t.status}</span></td>
              <td className="muted">Inga resultat än</td>
              <td>{t.nästaSteg}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Hypotheses() {
  return (
    <section>
      <h2>Hypoteser</h2>
      <p className="muted">
        Kommer att läsa <code>research/registry.md</code> och visa antal försök och aktuellt
        krav på t-värde. Registret finns inte än, eftersom ingen hypotes är registrerad.
      </p>
    </section>
  );
}

function Status() {
  return (
    <section>
      <h2>Status</h2>
      <dl>
        <dt>Version (commit)</dt><dd><code>{__COMMIT__}</code></dd>
        <dt>Senaste ändring</dt><dd>{__COMMIT_MSG__ || "okänd"}</dd>
        <dt>Byggd</dt><dd>{new Date(__BUILT_AT__).toLocaleString("sv-SE")}</dd>
      </dl>
      <p className="muted">Är commit-koden densamma hos dig och Edwin ser ni samma version.</p>
    </section>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("Översikt");
  return (
    <>
      <div className="banner">Inga riktiga pengar. Inga prognoser. Allt här är forskning.</div>
      <header>
        <h1>Trader_go</h1>
        <nav>
          {TABS.map((t) => (
            <button key={t} className={t === tab ? "active" : ""} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "Översikt" && <Overview />}
        {tab === "Research" && <Research />}
        {tab === "Hypoteser" && <Hypotheses />}
        {tab === "Status" && <Status />}
        {tab === "Projektkarta" && <Suspense fallback={<p className="muted">Laddar…</p>}><ProjectMap /></Suspense>}
        {tab === "Papper" && <Paper />}
        {tab === "Uppdateringar" && <Updates />}
      </main>
    </>
  );
}
