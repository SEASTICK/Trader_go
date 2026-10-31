// Sidor som bara finns i datorprogrammet. På webben (Cloudflare Pages) finns ingen Tauri-brygga.
import { FormEvent, useEffect, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";

export const isDesktop = isTauri();

type Counts = { paper: number; backtest: number };
type Trade = { id: number; opened_at: string; symbol: string; side: string; quantity: number; entry_price: number };

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
      <p className="muted">Uppdateringar installeras först när inget nedan pågår.</p>
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
