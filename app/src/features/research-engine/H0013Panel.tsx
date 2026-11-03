import { ReactNode, useEffect, useRef, useState } from "react";
import { Segmented } from "../../components/ui";
import { LineChart } from "../../components/Charts";
import { StatusDot } from "../../components/ui";
import type { ResearchApi, Run } from "./api";
import { ComparisonCurves, COMPARISONS, CRITERIA, describeRun, drawdown, enqueueBlocker, H0013View, isH0013, PROTOCOL, readResult, STATUS } from "./h0013";
import { number } from "./ResultViews";

const message = (e: unknown) => e instanceof Error ? e.message : "Ett oväntat fel inträffade.";
export const RETRY_MS = 15_000;

/** Fas 2 i Research Lab. Registrerad historisk forskning, skild från Fas 1, tvärsnitt och utforskning. */
export default function H0013Panel({ api, connected, login }: { api: ResearchApi; connected: boolean; login: ReactNode }) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [selected, setSelected] = useState("");
  const [payload, setPayload] = useState<{ id: string; value: unknown } | null>(null);
  // Resultathämtningens fel hålls skilt från listans, så att en lyckad listpoll inte döljer det.
  const [payloadError, setPayloadError] = useState<{ id: string; message: string } | null>(null);
  const [retry, setRetry] = useState(0);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const [preparing, setPreparing] = useState(false); const [confirmed, setConfirmed] = useState(false);
  const requestKey = useRef<string | null>(null);
  const current = runs.find(r => r.id === selected) ?? runs[0];

  useEffect(() => {
    if (!connected) { setRuns([]); setPayload(null); setPayloadError(null); return; }
    let active = true, polling = false;
    const poll = async () => {
      if (polling) return; polling = true;
      try { const next = (await api.h0013Runs()).filter(isH0013); if (active) { setRuns(next); setError(""); } }
      catch (e) { if (active) setError(message(e)); }
      finally { polling = false; }
    };
    void poll(); const timer = window.setInterval(() => void poll(), 5000);
    return () => { active = false; clearInterval(timer); };
  }, [api, connected]);
  useEffect(() => {
    let active = true;
    if (connected && current?.status === "done" && payload?.id !== current.id) {
      const id = current.id;
      setPayloadError(null);
      void api.payload(id).then(v => { if (active) setPayload({ id, value: v }); })
        .catch(e => { if (active) setPayloadError({ id, message: message(e) }); });
    }
    return () => { active = false; };   // byte av körning eller utloggning: ett sent svar används inte
  }, [api, connected, current?.id, current?.status, payload?.id, retry]);
  useEffect(() => {
    if (!payloadError) return;
    const timer = window.setTimeout(() => setRetry(r => r + 1), RETRY_MS);
    return () => clearTimeout(timer);
  }, [payloadError]);

  async function enqueue() {
    setBusy(true); setError("");
    try {
      requestKey.current ??= crypto.randomUUID();   // samma nyckel vid nytt försök: inget dubbelt jobb
      const id = await api.enqueueH0013(requestKey.current);
      setSelected(id); setRuns((await api.h0013Runs()).filter(isH0013));
      setPreparing(false); setConfirmed(false); requestKey.current = null;
    } catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }
  async function cancel(id: string) {
    setBusy(true); setError("");
    try { await api.cancel(id); setRuns((await api.h0013Runs()).filter(isH0013)); }
    catch (e) { setError(message(e)); }
    finally { setBusy(false); }
  }

  return <>
    <H0013Intro hasResult={runs.some(r => r.status === "done")} connected={connected} />
    <ProtocolCard />
    {error && <div className="card pad" role="alert">{error}</div>}
    {!connected ? login : <>
      <PrepareCard runs={runs} preparing={preparing} confirmed={confirmed} busy={busy}
        onPrepare={() => { setPreparing(true); setConfirmed(false); requestKey.current = null; }}
        onConfirm={setConfirmed} onClose={() => setPreparing(false)} onEnqueue={() => void enqueue()} />
      <RunsCard runs={runs} selected={current?.id ?? ""} busy={busy} onSelect={setSelected} onCancel={id => void cancel(id)} />
      {current && <RunDetail run={current} payload={payload?.id === current.id ? payload.value : undefined}
        payloadError={payloadError?.id === current.id ? payloadError.message : null} onRetry={() => setRetry(r => r + 1)} />}
    </>}
  </>;
}

export function H0013Intro({ hasResult, connected }: { hasResult: boolean; connected: boolean }) {
  return <div className="card pad"><h2>FAS 2 · H-0013 · Registrerad historisk forskning</h2>
    <p className="muted">En inlärd spelbok som väljer EMA / ADX-trend, Bollinger / RSI eller platt per marknadsläge, prövad i
      walk-forward på BTC/USDT-terminer 2022–2024. Skild från Fas 1-resultaten (H-0009–H-0012), tvärsnittshypoteserna
      (H-0014, H-0015) och utforskande körningar. Kandidaterna är REJECT ensamma.</p>
    <p>{!connected ? "Logga in för att se körningar och resultat från kön."
      : hasResult ? "Ett resultat finns och visas nedan." : <><b>Inget resultat ännu.</b> Ingen H-0013-körning är klar; inga siffror visas förrän kön har levererat ett verifierat resultat.</>}</p>
  </div>;
}

export function ProtocolCard() {
  const p = PROTOCOL;
  const rows: [string, ReactNode][] = [
    ["Protokoll", <code key="p">{p.protocolFile}</code>], ["Utvärdering", <code key="v">{p.version}</code>],
    ["Marknad", `Binance USDⓈ-M ${p.symbol} · ${p.interval} · med finansieringsränta`],
    ["Utvecklingsperiod", `${p.development[0]} till ${p.development[1]} (exklusivt)`],
    ["Testfönster (halvår)", p.testStarts.join(", ")], ["Slutprov", p.holdout],
    ["Kandidater", "EMA / ADX-trend 1.0.0, Bollinger / RSI 1.0.0 och platt, standardparametrar"],
    ["Urval per läge", `Bäst Sharpe med minst ${p.minTrades} affärer och t > 0, annars platt`],
    ["Kostnader per sida", `Avgift ${p.costs.fee_bps}, spread ${p.costs.spread_bps}, slippage ${p.costs.slippage_bps} bps · stress 2,5×`],
    ["Kapital", `${p.capital.toLocaleString("sv-SE")} · 1× · long i upp-lägen, short i ned-lägen`],
    ["Kontroller", `${p.nPermutations} permutationer · ${p.playbooks} spelböcker i Deflated Sharpe`],
    ["Krav", `t ≥ ${number(p.tRequired)} (N = ${p.registeredN}) och fyra jämförelser, se kriterierna`],
    ["Dataset", <code key="d" className="research-hash">{p.dataset}</code>],
  ];
  return <div className="card pad"><h2>Låsta inställningar</h2>
    <p className="muted">Fasta i protokollet och i databasens kö. Inget av detta kan ändras i appen; en ändring blir en ny hypotes.</p>
    <div className="research-table"><table><tbody>{rows.map(([k, v]) => <tr key={k}><th>{k}</th><td className="research-wrap">{v}</td></tr>)}</tbody></table></div>
  </div>;
}

export function PrepareCard({ runs, preparing, confirmed, busy, onPrepare, onConfirm, onClose, onEnqueue }: {
  runs: Run[]; preparing: boolean; confirmed: boolean; busy: boolean; onPrepare: () => void;
  onConfirm: (v: boolean) => void; onClose: () => void; onEnqueue: () => void }) {
  const blocker = enqueueBlocker(runs);
  return <div className="card pad"><h2>Fast forskningskörning</h2>
    {blocker ? <p>{blocker}</p> : !preparing
      ? <><p className="muted">Kör hela den registrerade utvärderingen en gång på servern: walk-forward, jämförelser, kostnadsstress, {PROTOCOL.nPermutations} permutationer och {PROTOCOL.playbooks} spelböcker. Det tar upp till två timmar.</p>
          <button className="btn" onClick={onPrepare}>Förbered H-0013-körning</button></>
      : <div className="research-form">
          <p>Inställningarna ovan används oförändrade. Slutprovet läses inte. Resultatet blir REJECT eller MORE_RESEARCH enligt de förregistrerade kriterierna och ändrar inte registret förrän det har granskats.</p>
          <label className="research-check"><input type="checkbox" checked={confirmed} onChange={e => onConfirm(e.target.checked)} /> Jag förstår att detta är den enda registrerade H-0013-körningen; en ny körning kräver ett nytt beslut.</label>
          <div><button className="btn accent" disabled={!confirmed || busy} onClick={onEnqueue}>{busy ? "Skickar…" : "Köa H-0013"}</button> <button className="btn" disabled={busy} onClick={onClose}>Stäng</button></div>
        </div>}
  </div>;
}

export function RunsCard({ runs, selected, busy, onSelect, onCancel }: { runs: Run[]; selected: string; busy: boolean;
  onSelect: (id: string) => void; onCancel: (id: string) => void }) {
  return <div className="card pad"><h2>H-0013-körningar</h2>
    <p className="muted">Samma kö och samma enda worker som övrig forskning. Avbrutna och misslyckade försök sparas och räknas.</p>
    {runs.length === 0 ? <p>Inga H-0013-körningar.</p> : <div className="research-table"><table>
      <thead><tr><th>Skapad (UTC)</th><th>Status</th><th>Förlopp</th><th>Försök</th><th>Åtgärd</th></tr></thead><tbody>
      {runs.map(run => { const d = describeRun(run); return <tr key={run.id}>
        <td><button className="btn" aria-pressed={selected === run.id} onClick={() => onSelect(run.id)}>{run.created_at.slice(0, 16).replace("T", " ")}</button><small>{run.id}</small></td>
        <td>{d.status}{d.error && <small role="alert">{d.error}</small>}</td>
        <td><progress value={d.progress} max={1} aria-label="Förlopp" /> {Math.round(d.progress * 100)} %</td>
        <td>{d.attempts}</td>
        <td>{d.canCancel && <button className="btn" disabled={busy} onClick={() => onCancel(run.id)}>Avbryt</button>}</td></tr>; })}
    </tbody></table></div>}
  </div>;
}

export function RunDetail({ run, payload, payloadError = null, onRetry }: { run: Run; payload: unknown | undefined;
  payloadError?: string | null; onRetry?: () => void }) {
  const d = describeRun(run);
  if (run.status !== "done") return <div className="card pad"><h2>H-0013 · {STATUS[run.status]}</h2>
    <p className="muted">Körnings-id {run.id} · försök {d.attempts}</p>
    {run.status === "failed" && <p role="alert">Misslyckad: {d.error ?? "felorsak saknas"}. Inget resultat finns.</p>}
    {run.status === "cancelled" && <p>Avbruten. Inget resultat finns; försöket och dess delresultat är sparade på servern.</p>}
    {(run.status === "queued" || run.status === "running") && <p>Inget resultat ännu.</p>}
  </div>;
  if (payload === undefined && payloadError) return <div className="card pad" role="alert"><h2>Resultatet kunde inte hämtas</h2>
    <p>{payloadError}</p><p className="muted">Försöker igen automatiskt om {RETRY_MS / 1000} sekunder. Inget köas.</p>
    {onRetry && <button className="btn" onClick={onRetry}>Försök igen nu</button>}</div>;
  if (payload === undefined) return <div className="card pad"><p>Hämtar resultat…</p></div>;
  return <H0013Result view={readResult(payload)} />;
}

const pct = (v: number | null) => number(v, true);

export function H0013Result({ view }: { view: H0013View }) {
  if (!view.ok) return <div className="card pad" role="alert"><h2>Resultatet kan inte visas</h2>
    <ul>{view.reasons.map(r => <li key={r}>{r}</li>)}</ul><p>Inga siffror visas från ett resultat som inte följer H-0013-kontraktet.</p></div>;
  const v = view;
  return <>
    <div className="card pad"><h2>HISTORIK · H-0013 · <StatusDot status={v.decision} /></h2>
      <p className="muted">Resultat i test på utvecklingsperioden 2022–2024. Ingen prognos, och inget godkännande för papper eller live.</p>
      <ul>{v.criteria.map(([k, pass]) => <li key={k}><b>{pass ? "Uppfyllt" : "Inte uppfyllt"}</b> · {CRITERIA[k]}</li>)}</ul>
      <p>Statistisk styrka: {number(v.main.t)} / krav {number(PROTOCOL.tRequired)}{v.tRequiredNow !== null && <> (kravet för dagens antal försök: {number(v.tRequiredNow)}, avgör inte)</>}. Med 2,5× kostnader: {pct(v.stressedReturn)}.</p>
    </div>
    <div className="card pad"><h2>Osäkerhet och slump</h2><div className="research-grid">
      <div><p className="muted">Sharpe</p><b>{number(v.main.sharpe)}</b></div>
      <div><p className="muted">95 % intervall för Sharpe</p><b>{number(v.main.ci[0])} till {number(v.main.ci[1])}</b></div>
      <div><p className="muted">Utan bästa året ({v.main.best_year ?? "saknas"})</p><b>{number(v.main.without_best_year_sharpe)}</b></div>
      <div><p className="muted">Permutationstest, andel lika bra</p><b>{v.permutation ? `${number(v.permutation.p)} (${number(v.permutation.k)} av ${number(v.permutation.n)})` : "Saknas"}</b></div>
      <div><p className="muted">Deflated Sharpe (81 försök)</p><b>{v.deflated ? number(v.deflated.standard) : "Saknas"}</b></div>
      <div><p className="muted">Med spelböckernas spridning</p><b>{v.deflated ? number(v.deflated.playbooks) : "Saknas"}</b></div>
    </div></div>
    <div className="card pad"><h2>Jämförelser på samma staplar</h2><div className="research-table"><table>
      <thead><tr><th>Kurva</th><th>Netto</th><th>Sharpe</th><th>Max nedgång</th><th>Affärer</th></tr></thead><tbody>
      <tr><td><b>H-0013</b></td><td>{pct(v.main.total_return)}</td><td>{number(v.main.sharpe)}</td><td>{pct(v.main.max_drawdown)}</td><td>{number(v.main.trades)}</td></tr>
      {v.comparisons.map(([k, s]) => <tr key={k}><td>{COMPARISONS[k]}</td>{s ? <><td>{pct(s.total_return)}</td><td>{number(s.sharpe)}</td><td>{pct(s.max_drawdown)}</td><td>{number(s.trades)}</td></> : <td colSpan={4}>Saknas i resultatet</td>}</tr>)}
    </tbody></table></div></div>
    <ComparisonCurvesCard curves={v.comparisonCurves} />
    <div className="card pad"><h2>Kapitalutveckling</h2>{v.equity
      ? <><LineChart watermark={null} labels={v.equity.t.map(t => t.slice(0, 10))} series={[{ name: "H-0013 (start 100 000)", data: v.equity.equity.map(e => e * PROTOCOL.capital), cls: "s1" }]} />
          <h3>Drawdown</h3><LineChart watermark={null} labels={v.equity.t.map(t => t.slice(0, 10))} series={[{ name: "Drawdown (%)", data: drawdown(v.equity.equity).map(x => x * 100), cls: "s2" }]} /></>
      : <p>Kapitalkurvan saknas i resultatet.</p>}</div>
    <div className="card pad"><h2>Marknadslägen</h2><div className="research-table"><table>
      <thead><tr><th>Läge</th><th>Dagar</th><th>Affärer</th><th>Netto</th><th>Sharpe</th></tr></thead><tbody>
      {v.regimes.map(r => <tr key={r.label}><td>{r.label}</td><td>{number(r.days)}</td><td>{number(r.trades)}</td><td>{pct(r.return)}</td><td>{number(r.sharpe)}</td></tr>)}
    </tbody></table></div><p className="muted">Läget för en dag är gårdagens stängda läge med tre dagars hysteres; ned/hög vol och okänt gäller direkt.</p></div>
    <div className="card pad"><h2>Kandidatval per testfönster</h2>{v.windows.length === 0 ? <p>Saknas i resultatet.</p> : <div className="research-table"><table>
      <thead><tr><th>Test (slut exklusivt)</th><th>Träning</th>{["upp/hög vol", "upp/låg vol", "ned/hög vol", "ned/låg vol"].map(l => <th key={l}>{l}</th>)}<th>Affärer</th><th>Netto i fönstret</th></tr></thead><tbody>
      {v.windows.map(w => <tr key={w.test}><td>{w.test}</td><td>{w.train}</td>{(w.choices.length ? w.choices : [["", "Saknas"], ["", "Saknas"], ["", "Saknas"], ["", "Saknas"]]).map(([l, c], i) => <td key={l + i}>{c}</td>)}<td>{number(w.trades)}</td><td>{pct(w.localReturn)}</td></tr>)}
    </tbody></table></div>}
      <p>Slutlig spelbok (hela utvecklingsperioden): {v.finalPlaybook ? v.finalPlaybook.map(([l, c]) => `${l}: ${c}`).join(" · ") : "Saknas"}</p></div>
    <div className="card pad"><h2>Affärer</h2>
      {v.tradeIssues.map(i => <p key={i} role="note">{i}</p>)}
      {v.trades === null ? <p>Affärsloggen saknas, så antalet affärer i loggen är okänt.</p>
      : v.trades.length === 0 ? <p>Affärsloggen är tom{v.main.trades === 0 ? "; nyckeltalen anger också 0 affärer" : ""}.</p> : <><p className="muted">Senaste {Math.min(100, v.trades.length)} av {v.trades.length} lästa rader. Tider i UTC.</p><div className="research-table"><table>
      <thead><tr><th>Sida</th><th>Inträde</th><th>Utträde</th><th>Netto</th><th>Orsak</th></tr></thead><tbody>
      {v.trades.slice(-100).map((t, i) => <tr key={i}><td>{String(t.side)}</td><td>{String(t.entry_time).slice(0, 16)}</td><td>{t.exit_time ? String(t.exit_time).slice(0, 16) : "—"}</td><td>{number(t.net_return, true)}</td><td>{String(t.exit_reason ?? "—")}</td></tr>)}
    </tbody></table></div></>}</div>
    <div className="card pad"><h2>Spårbarhet</h2><div className="research-table"><table><tbody>
      {v.trace.map(t => <tr key={t.label}><th>{t.label}</th><td><code className="research-hash">{t.value}</code></td></tr>)}
    </tbody></table></div>
      {v.missing.length > 0 && <p role="note">Saknas i resultatet: {v.missing.join(", ")}.</p>}
      <ul>{v.warnings.map(w => <li key={w}>{w}</li>)}</ul></div>
  </>;
}

export function ComparisonCurvesCard({ curves }: { curves: ComparisonCurves | null }) {
  const options = Object.values(COMPARISONS);
  const [chosen, setChosen] = useState(options[0]);
  if (!curves) return <div className="card pad"><h2>Jämförelsekurvor</h2>
    <p>Jämförelsekurvorna saknas i resultatet. Resultat från den driftsatta workern före denna version innehåller bara jämförelsernas nyckeltal.</p></div>;
  if (curves.axisProblem) return <div className="card pad" role="note"><h2>Jämförelsekurvor</h2>
    <p>Jämförelsekurvorna kan inte visas: {curves.axisProblem} Nyckeltalen för jämförelserna ovan påverkas inte.</p></div>;
  const own = curves.curves.find(c => c.key === "h0013")!;
  const other = curves.curves.find(c => c.label === chosen)!;
  const labels = curves.t.map(t => t.slice(0, 10));
  return <div className="card pad"><h2>Jämförelsekurvor på samma staplar</h2>
    <p className="muted">Kapital med start 100 000. {curves.points ?? "?"} punkter av {curves.bars ?? "?"} staplar, samma urval för alla kurvor.</p>
    <Segmented value={chosen} options={options} onChange={setChosen} />
    {own.data && other.data
      ? <LineChart watermark={null} labels={labels} series={[{ name: "H-0013", data: own.data.map(x => x * PROTOCOL.capital), cls: "s1" },
          { name: other.label, data: other.data.map(x => x * PROTOCOL.capital), cls: "s2" }]} />
      : <p role="note">{!own.data ? `H-0013: ${own.problem}` : `${other.label}: ${other.problem}`}</p>}
    <details><summary>Källor och kontrollsummor</summary><div className="research-table"><table>
      <thead><tr><th>Kurva</th><th>Källa</th><th>Staplar</th><th>SHA-256 för avkastningen</th></tr></thead><tbody>
      {curves.curves.map(c => <tr key={c.key}><td>{c.label}{c.problem && <small role="note">{c.problem}</small>}</td><td><code>{c.source}</code></td>
        <td>{c.bars ?? "Saknas"}</td><td><code className="research-hash">{c.sha ?? "Saknas"}</code></td></tr>)}
    </tbody></table></div></details>
  </div>;
}
