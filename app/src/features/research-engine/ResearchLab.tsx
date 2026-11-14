import { FormEvent, lazy, Suspense, useEffect, useRef, useState } from "react";
import { Page, Segmented } from "../../components/ui";
import { ResearchApi, Result, Run } from "./api";
import "./research.css";
import { Chart, number } from "./ResultViews";
import { isH0013 } from "./h0013";
const RegisteredResults = lazy(() => import("./RegisteredResults"));
const H0013Panel = lazy(() => import("./H0013Panel"));
const VIEWS = ["Resultat", "Fas 2", "Utforskning"] as const;

const NAMES: Record<string, string> = { ema_adx_trend: "EMA / ADX-trend", donchian_breakout: "Donchian-utbrott",
  bb_rsi_reversion: "Bollinger / RSI", squeeze_breakout: "Squeeze-utbrott" };
const STATUS = { queued: "I kö", running: "Körs", done: "Klar", failed: "Misslyckad", cancelled: "Avbruten" };
const message = (e: unknown) => e instanceof Error ? e.message : "Ett oväntat fel inträffade.";

export default function ResearchLab() {
  const [registeredHypothesis, setRegisteredHypothesis] = useState<string | null>(null);
  const registeredKey = useRef<string | null>(null);
  const [view, setView] = useState<typeof VIEWS[number]>("Resultat");
  const api = useRef(new ResearchApi()).current;
  const [connected, setConnected] = useState(false);
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [runs, setRuns] = useState<Run[]>([]); const [selected, setSelected] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [strategy, setStrategy] = useState("ema_adx_trend"); const [market, setMarket] = useState("spot");
  const [interval, setInterval] = useState("4h"); const [start, setStart] = useState("2022-01-01");
  const [end, setEnd] = useState("2024-01-01"); const [params, setParams] = useState("{}");
  const requestKey = useRef<string | null>(null);
  const current = runs.find(r => r.id === selected);

  useEffect(() => { requestKey.current = null; }, [strategy, market, interval, start, end, params]);
  useEffect(() => {
    if (!connected) return;
    let active = true, polling = false;
    const poll = async () => {
      if (polling) return;
      polling = true;
      try { const next = (await api.runs()).filter(r => !isH0013(r)); if (active) { setRuns(next); setConnectionError(""); } }
      catch (e) { if (active) setConnectionError(message(e)); }
      finally { polling = false; }
    };
    void poll(); const timer = window.setInterval(() => void poll(), 5000);
    return () => { active = false; clearInterval(timer); };
  }, [api, connected]);
  useEffect(() => {
    let active = true; setResult(null);
    if (selected && current?.status === "done") {
      void api.result(selected).then(r => { if (active) setResult(r); }).catch(e => { if (active) setError(message(e)); });
    }
    return () => { active = false; };
  }, [api, selected, current?.status]);
  useEffect(() => () => api.signOut(), [api]);

  async function login(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { await api.signIn(email, password); setPassword(""); setConnected(true); }
    catch (e) { setError(message(e)); setPassword(""); }
    finally { setBusy(false); }
  }
  async function enqueue(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const parsed: unknown = JSON.parse(params);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Parametrar ska vara ett JSON-objekt.");
      requestKey.current ??= crypto.randomUUID();
      const id = await api.enqueue({ request_key: requestKey.current, strategy, market, interval,
        period_start: start + "T00:00:00Z", period_end: end + "T00:00:00Z", params: parsed });
      setSelected(id); setRuns((await api.runs()).filter(r => !isH0013(r))); requestKey.current = null;
    } catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }
  async function cancel(id: string) {
    setBusy(true); setError("");
    try { await api.cancel(id); setRuns((await api.runs()).filter(r => !isH0013(r))); }
    catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }
  async function reproduce() {
    if (!registeredHypothesis) return;
    setBusy(true);setError("");
    try {
      registeredKey.current ??= crypto.randomUUID();
      const id=await api.enqueueRegistered(registeredHypothesis,registeredKey.current);
      setSelected(id);setRuns((await api.runs()).filter(r => !isH0013(r)));setRegisteredHypothesis(null);
    } catch(e) {setError(message(e));}
    finally {setBusy(false);}
  }
  const loginForm = <form className="card pad research-form" onSubmit={login}>
      <h2>Logga in</h2><p className="muted">Endast godkända projektmedlemmar. Sessionen sparas bara medan Research Lab är öppet.</p>
      <label>E-post<input type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required /></label>
      <label>Lösenord<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
      <button className="btn accent" disabled={busy}>{busy ? "Loggar in…" : "Logga in"}</button>
      {error && <p role="alert">{error}</p>}
    </form>;
  return <Page title="Research Lab" sub="Registrerad forskning och historisk utforskning. Inga riktiga order."
    actions={connected && <button className="btn" onClick={() => { api.signOut(); setConnected(false); setRuns([]); setSelected(""); setResult(null); setError(""); }}>Logga ut</button>}>
    <Segmented value={view} options={[...VIEWS]} onChange={setView} />
    {view === "Resultat" ? <Suspense fallback={<p>Läser registrerade resultat…</p>}><RegisteredResults onReproduce={id => {setRegisteredHypothesis(id);registeredKey.current=null;setView("Utforskning");}} /></Suspense>
    : view === "Fas 2" ? <Suspense fallback={<p>Läser H-0013…</p>}><H0013Panel api={api} connected={connected} login={loginForm} /></Suspense> : <>
    {connected && error && <div className="card pad" role="alert">{error}</div>}
    {connected && connectionError && <div className="card pad" role="alert">{connectionError}</div>}
    {!connected ? loginForm : <>
      {registeredHypothesis && <div className="card pad"><h2>Registrerad reproduktion · {registeredHypothesis}</h2><p>Frysta testfönster 2022–2024, samma femårsdataset och parametrar. Beslutet förblir REJECT. Ingen ny optimering eller åtkomst till slutprovet.</p><button className="btn accent" disabled={busy} onClick={() => void reproduce()}>Köa registrerad reproduktion</button> <button className="btn" disabled={busy} onClick={() => setRegisteredHypothesis(null)}>Stäng förberedelsen</button></div>}
      <form className="card pad research-form" onSubmit={enqueue}>
        <h2>Ny utforskning</h2><p className="muted">UTFORSKNING · BTC/USDT · avgift 10, spread 2 och slippage 5 bps (spread räknas som halva per sida) · startkapital 100 000.
          Slutprovet från 2025 är låst. Utforskning ger inget godkännande för papperstest.</p>
        <div className="research-grid">
          <label>Strategi<select value={strategy} onChange={e => setStrategy(e.target.value)}>{Object.entries(NAMES).map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
          <label>Marknad<select value={market} onChange={e => setMarket(e.target.value)}><option value="spot">Spot · long / platt</option><option value="um">USDⓈ-M · long / short · 1×</option></select></label>
          <label>Tidsram<select value={interval} onChange={e => setInterval(e.target.value)}>{["1h", "4h", "1d"].map(v => <option key={v}>{v}</option>)}</select></label>
          <label>Start (UTC)<input type="date" min="2020-01-01" max="2024-12-01" value={start} onChange={e => setStart(e.target.value)} required /></label>
          <label>Slut, exklusivt (UTC)<input type="date" min="2020-01-31" max="2025-01-01" value={end} onChange={e => setEnd(e.target.value)} required /></label>
        </div>
        <label>Parametrar (JSON; tomt objekt använder strategins standardvärden)<textarea rows={3} value={params} onChange={e => setParams(e.target.value)} spellCheck={false} /></label>
        <button className="btn accent" disabled={busy}>{busy ? "Skickar…" : "Köa utforskning"}</button>
      </form>
      <div className="card pad"><h2>Körningar</h2><p className="muted">En aktiv körning åt gången. Visar de senaste 100 körningarna.</p>
        {runs.length === 0 ? <p>Inga körningar ännu.</p> : <div className="research-table"><table><thead><tr><th>Strategi</th><th>Marknad</th><th>Status</th><th>Förlopp</th><th>Åtgärd</th></tr></thead><tbody>
          {runs.map(run => <tr key={run.id}><td><button className="btn" aria-pressed={selected === run.id} onClick={() => setSelected(run.id)}>{NAMES[run.strategy] ?? run.strategy}</button><small>{run.kind === "registered" ? "REGISTRERAD REPRODUKTION" : "UTFORSKNING"}</small><small>{run.created_at.slice(0, 16).replace("T", " ")} UTC</small></td>
            <td>{run.market} · {run.interval}</td><td>{STATUS[run.status]}</td><td><progress value={run.progress} max={1} aria-label="Förlopp" /> {Math.round(run.progress * 100)} %</td>
            <td>{["queued", "running"].includes(run.status) && <button className="btn" disabled={busy} onClick={() => void cancel(run.id)}>Avbryt</button>}</td></tr>)}
        </tbody></table></div>}
      </div>
      {current && <div className="card pad"><h2>{NAMES[current.strategy]} · {STATUS[current.status]}</h2>
        <p className="muted">{current?.kind === "registered" ? "REGISTRERAD REPRODUKTION" : "UTFORSKNING"} · {current.period_start.slice(0, 10)} till {current.period_end.slice(0, 10)} (exklusivt)</p>
        <p><small>Körnings-id: {current.id}</small></p>{current.error && <p role="alert">{current.error}</p>}
        {current.status === "done" && !result && <p>Hämtar resultat…</p>}
      </div>}
      {result && <>
        {result.mode === "registered" && <div className="card pad"><h2>{result.hypothesis_id} · {result.decision}</h2><p>{result.reproduction_match ? "Frysta nyckeltal och kurvor matchar originalet exakt." : "Reproduktion kunde inte verifieras."} Inget nytt godkännande för papperstest.</p></div>}
        <div className="card pad"><h2>HISTORIK · {current?.kind === "registered" ? "REGISTRERAD REPRODUKTION" : "UTFORSKNING"}</h2>
          <div className="research-grid">{[["Nettoavkastning", "net_return", true], ["CAGR", "cagr", true], ["Sharpe", "sharpe", false],
            ["Sortino", "sortino", false], ["Calmar", "calmar", false], ["Max drawdown", "max_drawdown", true],
            ["Affärer", "trades", false], ["Profit factor", "profit_factor", false], ["Vinstandel", "win_rate", true],
            ["Exponering", "exposure", true], ["Kostnader / startkapital", "costs", true], ["Funding / startkapital", "funding", true]].map(([label, key, percent]) =>
            <div key={String(key)}><p className="muted">{String(label)}</p><b>{number(result.stats[String(key)], Boolean(percent))}</b></div>)}</div>
        </div>
        <div className="card pad"><h2>Kapitalutveckling och köp och behåll</h2><Chart curve={result.curves} baseline={result.baseline} /></div>
        <div className="card pad"><h2>Drawdown</h2><Chart curve={result.curves} drawdown /></div>
        <div className="card pad"><h2>Affärer</h2><p className="muted">Senaste 100 av {result.trades.length}; samtliga sparas med körningen.</p><div className="research-table"><table><thead><tr><th>Sida</th><th>Inträde UTC</th><th>Utträde UTC</th><th>Netto</th><th>Orsak</th></tr></thead><tbody>
          {result.trades.slice(-100).map((t, i) => <tr key={i}><td>{t.side}</td><td>{t.entry_time.slice(0, 16)}</td><td>{t.exit_time?.slice(0, 16) ?? (current?.kind === "registered" ? "Öppen vid fönsterslut" : "Öppen vid periodslut")}</td><td>{number(t.net_return, true)}</td><td>{t.exit_reason ?? "—"}</td></tr>)}
        </tbody></table></div></div>
        <div className="card pad"><h2>Spårbarhet och begränsningar</h2><ul>{result.warnings.map(w => <li key={w}>{w}</li>)}</ul>
          <p>Fingerprint: <code className="research-hash">{result.metadata.fingerprint}</code></p>
          <p>Dataset: <code className="research-hash">{result.metadata.dataset_sha256}</code></p>
          <p>Kod: <code className="research-hash">{result.metadata.engine_sha256}</code></p>
          <details><summary>Parametrar och fullständiga nyckeltal</summary><pre>{JSON.stringify({ params: result.effective_params, stats: result.stats }, null, 2)}</pre></details>
        </div>
      </>}
    </>}
    </>}
  </Page>;
}
