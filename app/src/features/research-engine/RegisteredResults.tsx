import { useMemo, useState } from "react";
import market from "../../../data/fas1-market.json";
import { CandleChart } from "../../components/CandleChart";
import type { Candle } from "../../lib/candles";
import data from "../../../data/registered-results.json";
import { Details, StatusDot } from "../../components/ui";
import { agoText, ageDays } from "../../lib/freshness";
import { Chart, number } from "./ResultViews";

const historical: Candle[] = market.rows.map(([open_time,open,high,low,close,volume]) => ({open_time,open,high,low,close,volume,close_time:open_time+14400000-1,closed:true}));
const historicalSeries = {provider:"binance",market:"um",symbol:"BTCUSDT",interval:"4h"} as const;

const NAMES: Record<string, string> = { ema_adx_trend: "EMA / ADX-trend", donchian_breakout: "Donchian-utbrott",
  bb_rsi_reversion: "Bollinger / RSI", squeeze_breakout: "Squeeze-utbrott" };
const CRITERIA: Record<string, string> = { t_at_least_required: "Statistisk styrka över kravet",
  stressed_costs_positive: "Positivt med 2,5 gånger kostnaderna", sharpe_above_buy_and_hold: "Högre Sharpe än köp och behåll",
  stability_at_least_half: "Minst hälften av närliggande parametrar håller" };
export type RegisteredResult = typeof data[number];

const dateOf = (ms: number) => new Date(ms).toISOString().slice(0, 10);

export default function RegisteredResults({onReproduce, now = new Date()}: {onReproduce?: (hypothesis:string) => void; now?: Date}) {
  const [selected, setSelected] = useState(data[0]?.hypothesis_id ?? "");
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState("hypothesis");
  const results = useMemo(() => {
    const rows = data.filter(r => `${r.hypothesis_id} ${NAMES[r.strategy]} ${r.decision}`.toLocaleLowerCase("sv-SE").includes(filter.toLocaleLowerCase("sv-SE")));
    return [...rows].sort((a,b) => sort === "return" ? b.stats.net_return-a.stats.net_return : sort === "sharpe" ? b.stats.sharpe-a.stats.sharpe : a.hypothesis_id.localeCompare(b.hypothesis_id));
  }, [filter, sort]);
  const current = data.find(r => r.hypothesis_id === selected);
  const allRejected = data.every(r => r.decision === "REJECT");
  const rejected = data.filter(r => r.decision === "REJECT").length;
  const lastBar = historical[historical.length - 1];
  const age = lastBar ? ageDays(new Date(lastBar.open_time).toISOString(), now) : null;
  return <>
    <p className={allRejected ? "note warn" : "note"} role="note">{allRejected
      ? <><b>Alla {data.length} har beslutet REJECT.</b> Ingen är godkänd för papperstest. Det är ett giltigt utfall, inte ett fel. Sortering ändrar inte beslutet.</>
      : <>Besluten kommer från hypotesregistret. Sortering ändrar inte beslutet.</>}</p>
    <div className="stats">
      <section className="stat" aria-labelledby="rr-n">
        <header><span className="k" id="rr-n">Registrerade hypoteser</span><span className="stat-tag">Historik</span></header>
        <b className="big">{data.length}</b>
        <p>Testperiod 2022–2024 efter träning på tidigare data.</p>
        <span className="src">BTC/USDT-terminer, 4h</span>
      </section>
      <section className="stat" aria-labelledby="rr-d">
        <header><span className="k" id="rr-d">Beslut</span><span className="stat-tag">Förregistrerade krav</span></header>
        <b className="big">{rejected} <small>av {data.length} REJECT</small></b>
        <span className={`delta ${rejected === data.length ? "down" : "idle"}`}>{rejected === data.length ? "Ingen godkänd" : `${data.length - rejected} går vidare`}</span>
        <span className="src">Inget godkänt för papper eller live</span>
      </section>
      <section className="stat" aria-labelledby="rr-s">
        <header><span className="k" id="rr-s">Datakälla</span><span className="stat-tag">Aktualitet</span></header>
        <b className="big">{lastBar ? dateOf(lastBar.open_time) : "Saknas"}</b>
        <span className={`delta ${age === null ? "warn" : "idle"}`}>{age === null ? "Okänd ålder" : `Senaste stapel, ${agoText(age)}`}</span>
        <span className="src">Binance USDⓈ-M, kontrollsummerad historik (SHA-256 {market.dataset_sha256.slice(0, 8)}…). Följer med appen, kräver ingen serveranslutning.</span>
      </section>
    </div>

    <div className="toolbar">
      <label className="field">Sök<input value={filter} onChange={e => setFilter(e.target.value)} placeholder="Hypotes, strategi eller beslut" aria-label="Sök hypotes, strategi eller beslut" /></label>
      <label className="field">Sortera<select value={sort} onChange={e => setSort(e.target.value)}><option value="hypothesis">Hypotes</option><option value="return">Nettoavkastning</option><option value="sharpe">Sharpe</option></select></label>
    </div>
    <div className="result-list reg-list">
      {results.map(r => <button type="button" key={r.hypothesis_id} className="result-row reg-row" aria-pressed={selected === r.hypothesis_id} onClick={() => setSelected(r.hypothesis_id)}>
        <span className="rr-main"><b>{r.hypothesis_id} · {NAMES[r.strategy]}</b><span className="muted">{r.stats.trades} affärer · max nedgång {number(r.stats.max_drawdown,true)}</span></span>
        <span className="rr-num"><span className="k">Netto</span><b className={r.stats.net_return >= 0 ? "up" : "down"}>{number(r.stats.net_return,true)}</b></span>
        <span className="rr-num"><span className="k">Sharpe</span><b>{number(r.stats.sharpe)}</b></span>
        <StatusDot status={r.decision} />
      </button>)}
      {results.length === 0 && <p className="empty">Inga resultat matchar sökningen.</p>}
    </div>
    {current && <RegisteredDetail result={current} onReproduce={onReproduce} />}
  </>;
}

function RegisteredDetail({ result: r, onReproduce }: { result: RegisteredResult; onReproduce?: (hypothesis:string) => void }) {
  const marketMatches = r.audit?.dataset_sha256 === market.dataset_sha256 && JSON.stringify(r.curves.t) === JSON.stringify(market.baseline_curves.t);
  const key: [string, number, boolean][] = [["Nettoavkastning",r.stats.net_return,true],["Sharpe",r.stats.sharpe,false],["Max drawdown",r.stats.max_drawdown,true],
    ["Köp och behåll: netto",r.baseline_stats.total_return,true],["Köp och behåll: Sharpe",r.baseline_stats.sharpe,false],["Affärer",r.stats.trades,false]];
  return <>
    <div className="card pad detail-head"><div className="dh-top"><h2>{r.hypothesis_id} · {NAMES[r.strategy]}</h2><StatusDot status={r.decision} /></div>
      <p className="muted">HISTORIK · {r.period[0]} till {r.period[1]} (exklusivt) · {r.market} · {r.interval}. Ett backtest på historik är ingen prognos.</p>
      <div className="research-grid kpi-grid">{key.map(([label,value,percent]) => <div key={label}><p className="k">{label}</p><b>{number(value,percent)}</b></div>)}</div>
      <Details summary="Visa alla nyckeltal"><div className="research-grid">{[["CAGR",r.stats.cagr,true],["Sortino",r.stats.sortino,false],["Calmar",r.stats.calmar,false],["Profit factor",r.stats.profit_factor,false],["Vinstandel",r.stats.win_rate,true],
        ["Utfall per affär",r.stats.expectancy,true],["Exponering",r.stats.exposure,true],["Kostnader / startkapital",r.stats.costs,true],["Funding / startkapital",r.stats.funding,true]].map(([label,value,percent]) =>
        <div key={String(label)}><p className="muted">{String(label)}</p><b>{number(value,Boolean(percent))}</b></div>)}</div></Details>
    </div>
    <div className="card pad"><h2>Beslut mot förregistrerade krav</h2><ul className="criteria">{Object.entries(r.criteria).map(([key,pass]) => <li key={key} className={pass ? "ok" : "no"}><b>{pass ? "Uppfyllt" : "Inte uppfyllt"}</b> · {CRITERIA[key]}</li>)}</ul>
      <p>Statistisk styrka: {number(r.t_daily_nw)} / krav {number(r.t_required)}. Med 2,5× kostnader: {number(r.stressed_total_return,true)}.
        Parameterstabilitet: {number(r.stability,true)}.</p>
      <p className="muted">{r.attempts} registrerade hypotesförsök; {r.trials_total} parameterförsök i denna körning. Fler försök ökar risken att hitta något av slump.</p>
      {r.audit && <p>95 % osäkerhetsintervall för Sharpe: {number(r.audit.bootstrap_sharpe_ci[0])} till {number(r.audit.bootstrap_sharpe_ci[1])}.
        Utan bästa året ({r.audit.excluded_best_year}): Sharpe {number(r.audit.without_best_year_sharpe)}.</p>}
    </div>
    <div className="card pad"><h2>Kapitalutveckling och köp och behåll</h2><Chart curve={r.curves} baseline={marketMatches ? market.baseline_curves : undefined} />
      <p className="muted">{marketMatches ? "Start 100 000. Baslinjen använder samma terminsdata, funding och kostnader. Kurvorna är matchade på exakt samma tidpunkter." : "Ingen verifierad jämförelsekurva finns för detta dataset."}</p>
      <h3 className="mini">Drawdown</h3><Chart curve={r.curves} drawdown /></div>
    <h2 className="section-title">Historiska priser och affärsmarkörer</h2>
    {marketMatches ? <CandleChart series={historicalSeries} historical={historical} trades={r.trades} tradesLabel={`HISTORIK · ${r.hypothesis_id} · In/ut från originalresultatet`} /> : <p className="note warn" role="alert">Diagrammets dataset kunde inte matchas mot resultatets audit.</p>}
    <div className="card pad"><h2>Begränsningar</h2>
      <ul className="plain">{r.warnings.map(w => <li key={w}>{w}</li>)}</ul>
      <p className="muted">{r.audit ? "Kontrollsummerat femårsdataset. Reproduktionen matchar originalets nyckeltal, kurvor och parametrar exakt." : "Ingen matchande dataaudit kopplad till detta resultat."}</p>
    </div>
    <Details summary="Visa detaljer: walk-forward, månader, affärer, spårbarhet och rådata">
      <div className="card pad"><h2>Walk-forward · träna före varje testperiod</h2><div className="research-table"><table><thead><tr><th>Träning</th><th>Test, slut exklusivt</th><th>Sharpe träning</th><th>Sharpe test</th><th>Valda parametrar</th></tr></thead><tbody>
        {r.windows.map(w => <tr key={w.test[0]}><td>{w.train.join(" → ")}</td><td>{w.test.join(" → ")}</td><td>{number(w.sharpe_in_sample)}</td><td>{number(w.sharpe_out_of_sample)}</td><td><code>{JSON.stringify(w.params)}</code></td></tr>)}
      </tbody></table></div><p className="muted">Testperioderna användes inte för parameterurvalet i respektive fönster. Hela utvecklingsperioden har använts i tidigare forskning.</p></div>
      <div className="card pad"><h2>Månadsresultat och marknadsläge</h2><details><summary>Visa månader</summary><div className="research-grid">{Object.entries(r.stats.monthly_returns).map(([month,value]) => <div key={month}>{month}: <b>{number(value,true)}</b></div>)}</div></details>
        <div className="research-table"><table><thead><tr><th>Marknadsläge</th><th>Staplar</th><th>Netto</th><th>Sharpe</th></tr></thead><tbody>{Object.entries(r.stats.by_regime).map(([name,v]) => <tr key={name}><td>{name}</td><td>{v.bars}</td><td>{number(v.return,true)}</td><td>{number(v.sharpe)}</td></tr>)}</tbody></table></div></div>
      <div className="card pad"><h2>Affärshistorik</h2><p className="muted">{r.trades.length} exporterade affärer; {r.stats.trades} avslutade i statistiken. Tider i UTC. Varje testfönster körs separat; en affär utan utträde var öppen vid det fönstrets slut, inte i dag.</p><div className="research-table"><table><thead><tr><th>Sida</th><th>Inträde</th><th>Utträde</th><th>Inpris</th><th>Utpris</th><th>Netto</th><th>Orsak</th></tr></thead><tbody>
        {r.trades.map((t,i) => <tr key={i}><td>{t.side}</td><td>{t.entry_time.slice(0,16)}</td><td>{t.exit_time?.slice(0,16) ?? "Öppen vid fönsterslut"}</td><td>{number(t.entry_price)}</td><td>{number(t.exit_price)}</td><td>{number(t.net,true)}</td><td>{t.exit_reason ?? "—"}</td></tr>)}
      </tbody></table></div></div>
      <div className="card pad"><h2>Spårbarhet</h2>
        <p>Originalresultat: <code className="research-hash">{r.result_file}</code></p><p>SHA256: <code className="research-hash">{r.result_sha256}</code></p>
        <p>Registrering: <code className="research-hash">{r.registry_commit}</code> · Strategiversion {r.version} · Körning {r.run_at}</p>
        {r.audit && <><p>Dataset: <code className="research-hash">{r.audit.dataset_sha256}</code></p><p>Reproducerad med kod: <code className="research-hash">{r.audit.code_commit}</code></p></>}
        <details><summary>Slutparametrar och fullständigt exporterat resultat</summary><pre className="research-json">{JSON.stringify(r,null,2)}</pre></details>
      </div>
      {onReproduce && <div className="card pad"><h2>Teknisk reproduktion</h2><p>Kör om de frysta testfönstren för {r.hypothesis_id} med samma data och parametrar. Inget nytt strategiurval görs och beslutet ändras inte.</p><button className="btn" onClick={() => onReproduce(r.hypothesis_id)}>Förbered reproduktion av {r.hypothesis_id}</button></div>}
    </Details>
  </>;
}
