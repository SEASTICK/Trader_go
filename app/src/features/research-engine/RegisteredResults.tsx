import { useMemo, useState } from "react";
import market from "../../../data/fas1-market.json";
import { CandleChart } from "../../components/CandleChart";
import type { Candle } from "../../lib/candles";
import data from "../../../data/registered-results.json";
import { StatusDot } from "../../components/ui";
import { Chart, number } from "./ResultViews";

const historical: Candle[] = market.rows.map(([open_time,open,high,low,close,volume]) => ({open_time,open,high,low,close,volume,close_time:open_time+14400000-1,closed:true}));
const historicalSeries = {provider:"binance",market:"um",symbol:"BTCUSDT",interval:"4h"} as const;

const NAMES: Record<string, string> = { ema_adx_trend: "EMA / ADX-trend", donchian_breakout: "Donchian-utbrott",
  bb_rsi_reversion: "Bollinger / RSI", squeeze_breakout: "Squeeze-utbrott" };
const CRITERIA: Record<string, string> = { t_at_least_required: "Statistisk styrka över kravet",
  stressed_costs_positive: "Positivt med 2,5 gånger kostnaderna", sharpe_above_buy_and_hold: "Högre Sharpe än köp och behåll",
  stability_at_least_half: "Minst hälften av närliggande parametrar håller" };
export type RegisteredResult = typeof data[number];

export default function RegisteredResults() {
  const [selected, setSelected] = useState(data[0]?.hypothesis_id ?? "");
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState("hypothesis");
  const results = useMemo(() => {
    const rows = data.filter(r => `${r.hypothesis_id} ${NAMES[r.strategy]} ${r.decision}`.toLocaleLowerCase("sv-SE").includes(filter.toLocaleLowerCase("sv-SE")));
    return [...rows].sort((a,b) => sort === "return" ? b.stats.net_return-a.stats.net_return : sort === "sharpe" ? b.stats.sharpe-a.stats.sharpe : a.hypothesis_id.localeCompare(b.hypothesis_id));
  }, [filter, sort]);
  const current = data.find(r => r.hypothesis_id === selected);
  return <>
    <div className="card pad"><h2>HISTORIK · Registrerade Fas 1-resultat</h2>
      <p className="muted">Verifierade resultat från BTC/USDT-terminer, 4H. Testperiod 2022–2024 efter träning på tidigare data.
        Dessa resultat följer med appen och kan läsas utan serveranslutning. Nya resultat kräver en appuppdatering.</p>
      <p>{data.every(r => r.decision === "REJECT") ? <>Alla fyra har beslutet <b>REJECT</b>. Ingen är godkänd för papperstest.</> : <>Besluten kommer från hypotesregistret.</>} Sortering ändrar inte beslutet.</p>
      <div className="research-grid research-form">
        <label>Sök hypotes, strategi eller beslut<input value={filter} onChange={e => setFilter(e.target.value)} /></label>
        <label>Sortera<select value={sort} onChange={e => setSort(e.target.value)}><option value="hypothesis">Hypotes</option><option value="return">Nettoavkastning</option><option value="sharpe">Sharpe</option></select></label>
      </div>
      <div className="research-table registered-comparison"><table><thead><tr><th>Hypotes / strategi</th><th>Netto</th><th>Sharpe</th><th>Max nedgång</th><th>Affärer</th><th>Beslut</th></tr></thead><tbody>
        {results.map(r => <tr key={r.hypothesis_id}><td><button className="btn" aria-pressed={selected === r.hypothesis_id} onClick={() => setSelected(r.hypothesis_id)}>{r.hypothesis_id} · {NAMES[r.strategy]}</button></td>
          <td>{number(r.stats.net_return,true)}</td><td>{number(r.stats.sharpe)}</td><td>{number(r.stats.max_drawdown,true)}</td><td>{r.stats.trades}</td><td><StatusDot status={r.decision} /></td></tr>)}
      </tbody></table>{results.length === 0 && <p>Inga resultat matchar sökningen.</p>}</div>
    </div>
    {current && <RegisteredDetail result={current} />}
  </>;
}

function RegisteredDetail({ result: r }: { result: RegisteredResult }) {
  const marketMatches = r.audit?.dataset_sha256 === market.dataset_sha256 && JSON.stringify(r.curves.t) === JSON.stringify(market.baseline_curves.t);
  return <>
    <div className="card pad"><h2>{r.hypothesis_id} · {NAMES[r.strategy]} <StatusDot status={r.decision} /></h2>
      <p className="muted">HISTORIK · {r.period[0]} till {r.period[1]} (exklusivt) · {r.market} · {r.interval}</p>
      <div className="research-grid">{[["Nettoavkastning",r.stats.net_return,true],["CAGR",r.stats.cagr,true], ["Sharpe",r.stats.sharpe,false], ["Sortino",r.stats.sortino,false],
        ["Calmar",r.stats.calmar,false],["Max drawdown",r.stats.max_drawdown,true], ["Profit factor",r.stats.profit_factor,false],["Vinstandel",r.stats.win_rate,true],
        ["Utfall per affär",r.stats.expectancy,true],["Exponering",r.stats.exposure,true],["Kostnader / startkapital",r.stats.costs,true],["Funding / startkapital",r.stats.funding,true],
        ["Köp och behåll: netto",r.baseline_stats.total_return,true],["Köp och behåll: Sharpe",r.baseline_stats.sharpe,false]].map(([label,value,percent]) =>
        <div key={String(label)}><p className="muted">{String(label)}</p><b>{number(value,Boolean(percent))}</b></div>)}</div>
    </div>
    <div className="card pad"><h2>Beslut mot förregistrerade krav</h2><ul>{Object.entries(r.criteria).map(([key,pass]) => <li key={key}><b>{pass ? "Uppfyllt" : "Inte uppfyllt"}</b> · {CRITERIA[key]}</li>)}</ul>
      <p>Statistisk styrka: {number(r.t_daily_nw)} / krav {number(r.t_required)}. Med 2,5× kostnader: {number(r.stressed_total_return,true)}.
        Parameterstabilitet: {number(r.stability,true)}.</p>
      <p className="muted">{r.attempts} registrerade hypotesförsök; {r.trials_total} parameterförsök i denna körning. Fler försök ökar risken att hitta något av slump.</p>
      {r.audit && <p>95 % osäkerhetsintervall för Sharpe: {number(r.audit.bootstrap_sharpe_ci[0])} till {number(r.audit.bootstrap_sharpe_ci[1])}.
        Utan bästa året ({r.audit.excluded_best_year}): Sharpe {number(r.audit.without_best_year_sharpe)}.</p>}
    </div>
    <div className="card pad"><h2>Kapitalutveckling och köp och behåll</h2><Chart curve={r.curves} baseline={marketMatches ? market.baseline_curves : undefined} />
      <p className="muted">{marketMatches ? "Start 100 000. Baslinjen använder samma terminsdata, funding och kostnader. Kurvorna är matchade på exakt samma tidpunkter." : "Ingen verifierad jämförelsekurva finns för detta dataset."}</p></div>
    <div className="card pad"><h2>Drawdown</h2><Chart curve={r.curves} drawdown /></div>
    <div className="card pad"><h2>Walk-forward · träna före varje testperiod</h2><div className="research-table"><table><thead><tr><th>Träning</th><th>Test, slut exklusivt</th><th>Sharpe träning</th><th>Sharpe test</th><th>Valda parametrar</th></tr></thead><tbody>
      {r.windows.map(w => <tr key={w.test[0]}><td>{w.train.join(" → ")}</td><td>{w.test.join(" → ")}</td><td>{number(w.sharpe_in_sample)}</td><td>{number(w.sharpe_out_of_sample)}</td><td><code>{JSON.stringify(w.params)}</code></td></tr>)}
    </tbody></table></div><p className="muted">Testperioderna användes inte för parameterurvalet i respektive fönster. Hela utvecklingsperioden har använts i tidigare forskning.</p></div>
    <div className="card pad"><h2>Månadsresultat och marknadsläge</h2><details><summary>Visa månader</summary><div className="research-grid">{Object.entries(r.stats.monthly_returns).map(([month,value]) => <div key={month}>{month}: <b>{number(value,true)}</b></div>)}</div></details>
      <div className="research-table"><table><thead><tr><th>Marknadsläge</th><th>Staplar</th><th>Netto</th><th>Sharpe</th></tr></thead><tbody>{Object.entries(r.stats.by_regime).map(([name,v]) => <tr key={name}><td>{name}</td><td>{v.bars}</td><td>{number(v.return,true)}</td><td>{number(v.sharpe)}</td></tr>)}</tbody></table></div></div>
    <div className="card pad"><h2>Historiska priser och affärsmarkörer</h2>{marketMatches ? <CandleChart series={historicalSeries} historical={historical} trades={r.trades} tradesLabel={`HISTORIK · ${r.hypothesis_id} · In/ut från originalresultatet`} /> : <p role="alert">Diagrammets dataset kunde inte matchas mot resultatets audit.</p>}</div>
    <div className="card pad"><h2>Affärshistorik</h2><p className="muted">{r.trades.length} exporterade affärer; {r.stats.trades} avslutade i statistiken. Tider i UTC. Varje testfönster körs separat; en affär utan utträde var öppen vid det fönstrets slut, inte i dag.</p><div className="research-table"><table><thead><tr><th>Sida</th><th>Inträde</th><th>Utträde</th><th>Inpris</th><th>Utpris</th><th>Netto</th><th>Orsak</th></tr></thead><tbody>
      {r.trades.map((t,i) => <tr key={i}><td>{t.side}</td><td>{t.entry_time.slice(0,16)}</td><td>{t.exit_time?.slice(0,16) ?? "Öppen vid fönsterslut"}</td><td>{number(t.entry_price)}</td><td>{number(t.exit_price)}</td><td>{number(t.net,true)}</td><td>{t.exit_reason ?? "—"}</td></tr>)}
    </tbody></table></div></div>
    <div className="card pad"><h2>Datakvalitet och spårbarhet</h2><p>{r.audit ? "Kontrollsummerat femårsdataset. Reproduktionen matchar originalets nyckeltal, kurvor och parametrar exakt." : "Ingen matchande dataaudit kopplad till detta resultat."}</p>
      <ul>{r.warnings.map(w => <li key={w}>{w}</li>)}</ul>
      <p>Originalresultat: <code className="research-hash">{r.result_file}</code></p><p>SHA256: <code className="research-hash">{r.result_sha256}</code></p>
      <p>Registrering: <code className="research-hash">{r.registry_commit}</code> · Strategiversion {r.version} · Körning {r.run_at}</p>
      {r.audit && <><p>Dataset: <code className="research-hash">{r.audit.dataset_sha256}</code></p><p>Reproducerad med kod: <code className="research-hash">{r.audit.code_commit}</code></p></>}
      <details><summary>Slutparametrar och fullständigt exporterat resultat</summary><pre className="research-json">{JSON.stringify(r,null,2)}</pre></details>
    </div>
  </>;
}
