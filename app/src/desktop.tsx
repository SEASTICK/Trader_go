// Flikar som bara finns i datorprogrammet. På webben (Cloudflare Pages) finns ingen Tauri-brygga.
import { FormEvent, useEffect, useState } from "react";

type Tauri = {
  core: { invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> };
  event: { listen<T>(name: string, cb: (e: { payload: T }) => void): Promise<() => void> };
};
const tauri = (window as unknown as { __TAURI__?: Tauri }).__TAURI__;
export const isDesktop = tauri !== undefined;
const invoke = <T,>(cmd: string, args?: Record<string, unknown>) => tauri!.core.invoke<T>(cmd, args);

type AppInfo = { version: string; mode: string; data_dir: string; schema: number; auto_download: boolean };
type Status = {
  state: "checking" | "none" | "available" | "downloading" | "ready" | "error";
  current: string;
  version?: string;
  notes?: string;
  downloaded: number;
  total?: number;
  message?: string;
};
type Counts = { paper: number; backtest: number };
type Trade = { id: number; opened_at: string; symbol: string; side: string; quantity: number; entry_price: number };

const mb = (n: number) => (n / 1048576).toFixed(1) + " MB";

function statusText(s: Status): string {
  switch (s.state) {
    case "checking": return "Letar efter uppdateringar…";
    case "none": return `Du har senaste versionen (${s.current}).`;
    case "available": return `Version ${s.version} finns.`;
    case "downloading": return `Laddar ner ${s.version}…`;
    case "ready": return `Version ${s.version} är nedladdad och kontrollerad.${s.message ? " " + s.message : ""}`;
    case "error": return s.message ?? "Något gick fel.";
  }
}

export function Updates() {
  const [info, setInfo] = useState<AppInfo>();
  const [s, setS] = useState<Status>();
  const [error, setError] = useState("");

  useEffect(() => {
    invoke<AppInfo>("app_info").then(setInfo, (e) => setError(String(e)));
    invoke<Status>("update_status").then(setS);
    const off = tauri!.event.listen<Status>("update-status", (e) => setS(e.payload));
    return () => { off.then((f) => f()); };
  }, []);

  const run = (cmd: string, args?: Record<string, unknown>) =>
    invoke(cmd, args).then(() => setError(""), (e) => setError(String(e)));

  return (
    <section>
      <h2>Uppdateringar</h2>
      <dl>
        <dt>Installerad version</dt><dd><code>{info?.version ?? "…"}</code></dd>
        <dt>Läge</dt><dd><span className="badge">{info?.mode ?? "paper"}</span></dd>
        <dt>Data</dt><dd className="muted">{info?.data_dir} · schema {info?.schema}</dd>
      </dl>
      {s && <p className={s.state === "error" ? "error" : "muted"}>{statusText(s)}</p>}
      {s?.state === "downloading" && (
        <progress max={s.total} value={s.total ? s.downloaded : undefined}
          title={s.total ? `${mb(s.downloaded)} / ${mb(s.total)}` : undefined} />
      )}
      {s?.notes && <details><summary>Versionsnyheter</summary><pre>{s.notes}</pre></details>}
      <div className="actions">
        <button disabled={s?.state === "checking" || s?.state === "downloading"} onClick={() => run("check_for_update")}>
          Leta efter uppdateringar
        </button>
        {s?.state === "available" && <button onClick={() => run("download_update")}>Ladda ner</button>}
        {s?.state === "ready" && <button onClick={() => run("install_update")}>Starta om och uppdatera</button>}
        {info && (
          <label>
            <input type="checkbox" defaultChecked={info.auto_download}
              onChange={(e) => run("set_setting", { key: "auto_download", value: String(e.target.checked) })} />
            {" "}Ladda ner uppdateringar automatiskt
          </label>
        )}
      </div>
      {error && <p className="error">{error}</p>}
    </section>
  );
}

export function Paper() {
  const [counts, setCounts] = useState<Counts>({ paper: 0, backtest: 0 });
  const [trades, setTrades] = useState<Trade[]>([]);
  const [error, setError] = useState("");

  const refresh = () => invoke<Trade[]>("list_paper_trades").then(setTrades, (e) => setError(String(e)));
  useEffect(() => { refresh(); }, []);

  const toggle = (kind: keyof Counts) =>
    invoke<Counts>(counts[kind] > 0 ? "stop_activity" : "start_activity", { kind }).then(setCounts);

  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    try {
      await invoke("add_paper_trade", {
        symbol: f.get("symbol"), side: f.get("side"),
        quantity: Number(f.get("quantity")), entryPrice: Number(f.get("price")),
      });
      form.reset();
      setError("");
      await refresh();
    } catch (err) { setError(String(err)); }
  };

  return (
    <section>
      <h2>Papper</h2>
      <p className="muted">Bara papper. Ingen riktig order läggs. Uppdateringar installeras först när inget nedan pågår.</p>
      <div className="actions">
        <button onClick={() => toggle("paper")}>{counts.paper > 0 ? "Stoppa" : "Starta"} papperssession</button>
        <button onClick={() => toggle("backtest")}>{counts.backtest > 0 ? "Stoppa" : "Starta"} backtest</button>
        <span className="muted">{counts.paper} papperssession(er), {counts.backtest} backtest pågår</span>
      </div>
      <form className="actions" onSubmit={submit}>
        <input name="symbol" placeholder="BTCUSDT" required maxLength={32} />
        <select name="side"><option value="long">long</option><option value="short">short</option></select>
        <input name="quantity" type="number" step="any" min="0" placeholder="Antal" required />
        <input name="price" type="number" step="any" min="0" placeholder="Ingångspris" required />
        <button>Logga pappersaffär</button>
      </form>
      {error && <p className="error">{error}</p>}
      <table>
        <thead><tr><th>#</th><th>Öppnad (UTC)</th><th>Symbol</th><th>Riktning</th><th>Antal</th><th>Ingång</th></tr></thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id}><td>{t.id}</td><td>{t.opened_at}</td><td>{t.symbol}</td><td>{t.side}</td><td>{t.quantity}</td><td>{t.entry_price}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
