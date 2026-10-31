import { useEffect, useRef, useState } from "react";
import { Icon } from "./components/icons";
import { Page, Segmented } from "./components/ui";
import { isDesktop, Paper } from "./desktop";
import Overview from "./pages/Overview";
import Research from "./pages/Research";
import Hypotheses from "./pages/Hypotheses";
import Status from "./pages/Status";
import { UpdateDialog } from "./features/updates/UpdateDialog";
import { useUpdater } from "./features/updates/useUpdater";

const NAV = [
  { id: "Översikt", icon: "home" },
  { id: "Research", icon: "flask" },
  { id: "Hypoteser", icon: "list" },
  { id: "Status", icon: "info" },
] as const;
// Bara i datorprogrammet; webbversionen har ingen Tauri-brygga.
const DESKTOP_NAV = [
  { id: "Papper", icon: "shield" },
] as const;
const ALL_NAV = isDesktop ? [...NAV, ...DESKTOP_NAV] : NAV;
type PageId = (typeof NAV)[number]["id"] | (typeof DESKTOP_NAV)[number]["id"];
type Theme = "Ljust" | "Mörkt" | "System";

function loadTheme(): Theme {
  try { const t = localStorage.getItem("theme"); if (t === "Ljust" || t === "Mörkt" || t === "System") return t; } catch { /* ignoreras */ }
  return "System";
}

export default function App() {
  const [page, setPage] = useState<PageId>("Översikt");
  const [theme, setTheme] = useState<Theme>(loadTheme);
  const [menu, setMenu] = useState(false);
  const [settings, setSettings] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const updater = useUpdater(__APP_VERSION__);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "System") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme === "Mörkt" ? "dark" : "light");
    try { localStorage.setItem("theme", theme); } catch { /* ignoreras */ }
  }, [theme]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { setSettings(false); setMenu(false); } };
    const onClick = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(false); };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("mousedown", onClick); };
  }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="logo">T</span><b>Trader_go</b></div>
        <nav>
          {ALL_NAV.map((n) => (
            <button key={n.id} className={page === n.id ? "nav on" : "nav"} onClick={() => setPage(n.id)}>
              <Icon name={n.icon} /> {n.id}
            </button>
          ))}
        </nav>
        <div className="side-foot" ref={menuRef}>
          {menu && (
            <div className="popup" role="menu">
              <div className="popup-head"><b>Trader_go</b><span className="muted">Privat forskning</span></div>
              <button className="item" onClick={() => { setSettings(true); setMenu(false); }}><Icon name="settings" /> Inställningar</button>
              <button className="item" onClick={() => setTheme(theme === "Mörkt" ? "Ljust" : "Mörkt")}>
                <Icon name={theme === "Mörkt" ? "sun" : "moon"} /> Utseende <span className="muted right">{theme}</span>
              </button>
              {updater.enabled && (
                <button className="item" disabled={updater.notice.status === "checking" || updater.notice.status === "installing"}
                  onClick={() => { void updater.checkNow(false); }}>
                  <Icon name="info" /> Sök efter uppdateringar
                  <span className="muted right">{updater.notice.status === "available" ? `v${updater.notice.version}` : updater.notice.status === "checking" ? "Söker…" : updater.notice.status === "current" ? "Aktuell" : updater.notice.status === "error" ? "Fel" : ""}</span>
                </button>
              )}
              <div className="item static"><Icon name="info" /> Om Trader_go <span className="muted right">v{__APP_VERSION__}</span></div>
            </div>
          )}
          <button className="user" onClick={() => setMenu(!menu)}>
            <span className="avatar">TG</span>
            <span className="who"><b>Trader_go</b><span className="muted">Privat forskning</span></span>
            <span className="dots">···</span>
          </button>
        </div>
      </aside>

      <main>
        <div className="topbar"><span className="saved"><i />Papper · inga riktiga pengar · {__COMMIT__}</span></div>
        {page === "Översikt" && <Overview go={(p) => setPage(p)} />}
        {page === "Research" && <Research />}
        {page === "Hypoteser" && <Hypotheses />}
        {page === "Status" && <Status />}
        {page === "Papper" && <Page title="Papper" sub="Bara papper. Ingen riktig order läggs."><div className="card pad desk"><Paper /></div></Page>}
      </main>

      <UpdateDialog notice={updater.notice} currentVersion={__APP_VERSION__} onInstall={() => { void updater.install(); }} onLater={updater.later} onDismissError={updater.dismissError} />

      {settings && (
        <div className="overlay" onMouseDown={() => setSettings(false)}>
          <div className="modal" role="dialog" aria-label="Inställningar" onMouseDown={(e) => e.stopPropagation()}>
            <div className="modal-side"><h3>Inställningar</h3><button className="nav on">Allmänt</button></div>
            <div className="modal-body">
              <div className="modal-head"><h2>Allmänt</h2><button className="icon-btn" onClick={() => setSettings(false)} aria-label="Stäng"><Icon name="x" /></button></div>
              <h4>Utseende</h4>
              <div className="setting"><div><b>Färgtema</b><p className="muted">Sparas på den här datorn.</p></div>
                <Segmented value={theme} options={["Ljust", "Mörkt", "System"]} onChange={setTheme} /></div>
              <h4>Säkerhet</h4>
              <div className="setting"><div><b>Inga riktiga pengar</b><p className="muted">Appen visar bara. Den handlar inte, ansluter inte till någon börs och hanterar inga nycklar.</p></div></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
