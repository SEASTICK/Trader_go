import { useEffect, useMemo, useRef, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import {
  CandlestickSeries, ColorType, createChart, createSeriesMarkers, CrosshairMode, HistogramSeries, LineSeries,
  type IChartApi, type ISeriesApi, type ISeriesMarkersPluginApi, type SeriesMarker, type Time, type UTCTimestamp,
} from "lightweight-charts";
import {
  applyEvent, fromPage, indicatorValues, INDICATORS, INTERVAL_MS, prepend, sameSeries, tradeMarkers, utc, warmupNote,
  type BarsPage, type Candle, type SeriesInfo, type SeriesRef, type TradeEvent,
} from "../lib/candles";
import { STATE_TEXT, useMarketStatus } from "../features/market/useMarketStatus";
import { subscribeBars, type Listen } from "../lib/barSubscription";
import { dataProblems, isSupportedLive } from "../lib/marketSources";

import { observeChartViewport } from "../lib/chartViewport";

const PAGE = 1000;
/** Högst så här ofta ritas strömuppdateringar (ms). */
const FLUSH_MS = 250;
const sec = (ms: number) => (ms / 1000) as UTCTimestamp;
/** "#5aa56f" + 0.5 → "rgba(90,165,111,0.5)". Canvas förstår inte color-mix. */
const alpha = (hex: string, a: number) => {
  const h = hex.replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map(x => x + x).join("") : h, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

type Props = {
  /** Serien rutan handlar om, eller null om marknaden saknar en datakälla i appen. */
  series: SeriesRef | null;
  /** Verified closed historical bars bundled with the app; disables live IO. */
  historical?: Candle[];
  /** Verifierad historik per tidsram (riktiga staplar, tidsramarna räknade ur stängda staplar). Ger tidsramsval utan datorprogrammet. */
  historicalSets?: Record<string, Candle[]>;
  /** Källa, period och aktualitet för historiken, visas under diagrammet. */
  historyNote?: React.ReactNode;
  /** Visas när series är null. */
  noSourceReason?: string;
  /** Riktiga affärer från ett registrerat backtest (HISTORIK). Aldrig simulerade. */
  trades?: TradeEvent[];
  tradesLabel?: string;
};

/**
 * Prisdiagram med instrumentets verkliga OHLCV från datalagret. Används av alla detaljvyer för handel.
 * Ingen egen anslutning: staplarna läses med `market_bars` och uppdateras av insamlingens `market-bar`.
 */
export function CandleChart({ series, noSourceReason, trades = [], tradesLabel, historical: historicalOne, historicalSets, historyNote }: Props) {
  const desktop = isTauri();
  const { status } = useMarketStatus();
  const [available, setAvailable] = useState<SeriesInfo[] | null>(null);
  const [tf, setTf] = useState(series?.interval ?? "");
  const [active, setActive] = useState<string[]>(["sma20"]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<Candle | null>(null);
  const [outside, setOutside] = useState(0);

  useEffect(() => setTf(series?.interval ?? ""), [series?.symbol, series?.interval]);
  const isHist = !!historicalOne || !!historicalSets;
  const historical = historicalSets ? historicalSets[tf] : historicalOne;
  const problems = useMemo(() => historical ? dataProblems(historical, tf || series?.interval || "") : [], [historical, tf, series?.interval]);

  // Vilka tidsramar datalagret faktiskt har för instrumentet.
  useEffect(() => {
    if (isHist || !desktop || !series) return;
    let alive = true;
    invoke<SeriesInfo[]>("market_series").then(s => { if (alive) setAvailable(s); }).catch(e => alive && setError(String(e)));
    return () => { alive = false; };
  }, [desktop, isHist, series?.symbol, status?.closed_bars ? 1 : 0]);

  const intervals = useMemo(() => historicalSets ? Object.keys(historicalSets) : historicalOne && series ? [series.interval] : (available ?? []).filter(s => series && s.provider === series.provider && s.market === series.market && s.symbol === series.symbol).map(s => s.interval), [available, series, historical]);
  const current: SeriesRef | null = series && (isHist || isSupportedLive(series)) && intervals.includes(tf) ? { ...series, interval: tf } : null;
  const step = current ? INTERVAL_MS[current.interval] : 0;

  const box = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const viewport = useRef<ReturnType<typeof observeChartViewport> | null>(null);
  const candleS = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volS = useRef<ISeriesApi<"Histogram"> | null>(null);
  const lines = useRef<Map<string, ISeriesApi<"Line">>>(new Map());
  const markersApi = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const data = useRef<Candle[]>([]);
  const hasMore = useRef(false);
  const colors = useRef({ up: "#5aa56f", down: "#e0705f", ind: ["#d9a441", "#6fa8dc", "#c58af9"], entry: "#6fa8dc", exit: "#d9a441" });

  // Diagrammet skapas en gång per serie och städas bort helt vid byte.
  useEffect(() => {
    if (!current || !box.current) return;
    const css = getComputedStyle(box.current);
    const v = (n: string) => css.getPropertyValue(n).trim();
    colors.current = { up: v("--good"), down: v("--bad"), ind: [v("--ind1"), v("--ind2"), v("--ind3")], entry: v("--mark-entry"), exit: v("--mark-exit") };
    const c = createChart(box.current, {
      autoSize: false,
      layout: { background: { type: ColorType.Solid, color: v("--card") }, textColor: v("--muted"), fontFamily: "Inter Variable, system-ui, sans-serif", panes: { separatorColor: v("--line"), enableResize: false } },
      grid: { vertLines: { color: v("--line") }, horzLines: { color: v("--line") } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: v("--line") },
      timeScale: { borderColor: v("--line"), timeVisible: true, secondsVisible: false, rightOffset: 4, minBarSpacing: isHist ? 0.01 : 0.5 },
      localization: { locale: "sv-SE", timeFormatter: (t: Time) => utc((t as number) * 1000) },
    });
    const cs = c.addSeries(CandlestickSeries, { upColor: colors.current.up, downColor: colors.current.down, borderUpColor: colors.current.up, borderDownColor: colors.current.down, wickUpColor: colors.current.up, wickDownColor: colors.current.down });
    const vs = c.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false }, 1);
    c.panes()[1]?.setHeight(90);
    chart.current = c; candleS.current = cs; volS.current = vs;
    markersApi.current = createSeriesMarkers(cs, []);
    viewport.current = observeChartViewport(box.current, c);
    c.subscribeCrosshairMove(p => {
      if (!p.time) { setHover(null); return; }
      const t = (p.time as number) * 1000;
      setHover(data.current.find(x => x.open_time === t) ?? null);
    });
    return () => {
      viewport.current?.close();
      viewport.current = null;
      c.remove();
      chart.current = null; candleS.current = null; volS.current = null; markersApi.current = null; lines.current.clear();
      data.current = []; setCandles([]); setHover(null);
    };
  }, [current?.symbol, current?.interval, isHist]);

  const toCandle = (x: Candle) => {
    const fade = (col: string) => alpha(col, 0.45);
    const col = x.close >= x.open ? colors.current.up : colors.current.down;
    // Den pågående stapeln ritas halvgenomskinlig, så att den inte förväxlas med en stängd.
    return x.closed
      ? { time: sec(x.open_time), open: x.open, high: x.high, low: x.low, close: x.close }
      : { time: sec(x.open_time), open: x.open, high: x.high, low: x.low, close: x.close, color: fade(col), borderColor: col, wickColor: fade(col) };
  };
  const toVol = (x: Candle) => ({ time: sec(x.open_time), value: x.volume, color: alpha(x.close >= x.open ? colors.current.up : colors.current.down, x.closed ? 0.5 : 0.25) });

  /** Ritar om allt men behåller användarens zoom och position (förskjutet om staplar lagts till före). */
  const redraw = (next: Candle[], addedBefore = 0) => {
    const c = chart.current, cs = candleS.current, vs = volS.current;
    if (!c || !cs || !vs) return;
    const range = c.timeScale().getVisibleLogicalRange();
    data.current = next;
    cs.setData(next.map(toCandle));
    vs.setData(next.map(toVol));
    if (range && addedBefore) c.timeScale().setVisibleLogicalRange({ from: range.from + addedBefore, to: range.to + addedBefore });
    setCandles(next);
  };

  // Historik: senaste sidan, och äldre sidor när man panorerar bakåt.
  useEffect(() => {
    if (!current) return;
    if (isHist) { redraw(problems.length ? [] : historical ?? []); viewport.current?.fitWhenVisible(); return; }
    let alive = true;
    let loadingOlder = false;
    let initialized = false;
    const load = () => invoke<BarsPage>("market_bars", { symbol: current.symbol, interval: current.interval, limit: PAGE })
      .then(p => { if (!alive) return; hasMore.current = p.has_more; setError(null);
        const fresh = fromPage(p);
        const keep = data.current.filter(x => x.open_time < (fresh[0]?.open_time ?? Infinity));
        const next = [...keep, ...fresh];
        redraw(next);
        if (!initialized && next.length) { viewport.current?.latestWhenVisible(next.length); initialized = true; }
      })
      .catch(e => alive && setError(String(e)));
    void load();
    const ts = chart.current?.timeScale();
    const onRange = (r: { from: number; to: number } | null) => {
      if (!r || r.from > 10 || !hasMore.current || loadingOlder || !data.current.length) return;
      loadingOlder = true;
      invoke<BarsPage>("market_bars", { symbol: current.symbol, interval: current.interval, before: data.current[0].open_time, limit: PAGE })
        .then(p => { if (!alive) return; hasMore.current = p.has_more; const next = prepend(p.bars, data.current); redraw(next, next.length - data.current.length); })
        .finally(() => { loadingOlder = false; });
    };
    ts?.subscribeVisibleLogicalRangeChange(onRange);

    // Strömmen: samma händelser som insamlingen redan skickar (lib/barSubscription), högst var 250:e ms.
    const sub = subscribeBars(listen as Listen, current, events => {
      let next = data.current;
      const cs = candleS.current, vs = volS.current;
      for (const e of events) {
        if (!e.bar) continue;
        const r = applyEvent(next, e.bar, e.kind === "closed");
        if (r.change === "ignored") continue;
        next = r.candles;
        const last = next[next.length - 1];
        cs?.update(toCandle(last));
        vs?.update(toVol(last));
      }
      if (next !== data.current) { data.current = next; setCandles(next); }
    }, () => { void load(); }, FLUSH_MS);
    return () => {
      alive = false;
      ts?.unsubscribeVisibleLogicalRangeChange(onRange);
      sub.close();
    };
  }, [current?.symbol, current?.interval, historical, isHist, problems]);

  // Indikatorer: beräknas från stängningspriserna i diagrammet; tomt under uppvärmningen.
  useEffect(() => {
    const c = chart.current;
    if (!c) return;
    for (const [id, s] of lines.current) if (!active.includes(id)) { c.removeSeries(s); lines.current.delete(id); }
    INDICATORS.filter(i => active.includes(i.id)).forEach(ind => {
      let s = lines.current.get(ind.id);
      if (!s) {
        s = c.addSeries(LineSeries, { color: colors.current.ind[INDICATORS.indexOf(ind)], lineWidth: 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: ind.label });
        lines.current.set(ind.id, s);
      }
      const vals = indicatorValues(ind, candles);
      s.setData(candles.map((x, i) => (vals[i] == null ? { time: sec(x.open_time) } : { time: sec(x.open_time), value: vals[i] as number })));
    });
  }, [candles, active]);

  // Signalmarkörer: bara riktiga affärer inom de laddade staplarna.
  useEffect(() => {
    if (!markersApi.current || !step) return;
    const { markers, outside } = tradeMarkers(trades, candles, step);
    setOutside(outside);
    markersApi.current.setMarkers(markers.map((m): SeriesMarker<Time> => ({ time: sec(m.time), position: m.position, shape: m.shape, text: m.text, color: m.kind === "entry" ? colors.current.entry : colors.current.exit })));
  }, [candles, trades, step]);

  const last = candles[candles.length - 1];
  const shown = hover ?? last;
  const stale = status && sameSeries(status, current ?? ({} as SeriesRef)) && !status.ready;
  const empty = (title: string, text: string) => (
    <div className="candle-empty"><b>{title}</b><p>{text}</p></div>
  );

  let body: JSX.Element;
  if (!desktop && !isHist) body = empty("Ingen prisdata här", "Prisdiagrammet läser datalagret i skrivbordsappen. I webbläsaren finns ingen riktig OHLCV, och ingen simulerad data visas i stället.");
  else if (series && !isHist && !isSupportedLive(series)) body = empty("Marknaden stöds inte i datavägen", `${series.provider} ${series.market} ${series.symbol} kan inte läsas av datalagret (bara Binance spot stöds). Ingen graf ritas hellre än en felmärkt.`);
  else if (!series) body = empty("Ingen datakälla för den här marknaden", noSourceReason ?? "Appen samlar bara in data för marknader med en publik datakälla. Inget simulerat pris visas i stället.");
  else if (!isHist && available === null && !error) body = empty("Läser datalagret…", "");
  else if (!current) body = empty(
    `${series.symbol} ${tf || series.interval} samlas inte in`,
    intervals.length ? `Datalagret har ${series.symbol} i ${intervals.join(", ")}. Välj en av dem ovan; tidsramen byts aldrig bara på etiketten.` : `Datalagret har ingen data för ${series.symbol} än. Insamlingen styrs i appens datamapp (market/config.json, se docs/marknadsdata.md).`,
  );
  else if (problems.length) body = empty("Datafel i historiken", problems.join(" "));
  else body = <div className="candle-box" ref={box} />;

  return (
    <div className="candle-card">
      <div className="candle-head">
        <div className="candle-title">
          <b>{series ? series.symbol : "–"}</b>
          <span className="muted">{series ? `${series.provider === "binance" ? "Binance" : series.provider} ${series.market === "um" ? "USDⓈ-M terminer" : series.market === "spot" ? "spot" : series.market}` : "ingen leverantör"}</span>
          <span className="chip-live" title={isHist ? "Kontrollsummerade stängda staplar från det historiska datasetet." : "Riktiga priser från datalagret. Resultatet i rutan är fortfarande HISTORIK eller SIM, inte livehandel."}>{isHist ? "HISTORIK" : "REALTIDSDATA"}</span>
          {current && status && sameSeries(status, current) && (
            <span className={`candle-state ${status.ready ? "ok" : "warn"}`}>{STATE_TEXT[status.state]}</span>
          )}
        </div>
        {series && intervals.length > 0 && (
          <div className="candle-tools">
            {intervals.map(i => <button key={i} className={i === tf ? "on" : ""} onClick={() => setTf(i)}>{i}</button>)}
            {isHist && <button onClick={() => chart.current?.timeScale().fitContent()}>Hela perioden</button>}
            <span className="sep" />
            {INDICATORS.map(i => (
              <button key={i.id} className={active.includes(i.id) ? "on" : ""} onClick={() => setActive(a => a.includes(i.id) ? a.filter(x => x !== i.id) : [...a, i.id])}>{i.label}</button>
            ))}
          </div>
        )}
      </div>

      {current && shown && (
        <div className="candle-ohlc" aria-live="polite">
          <span>{utc(shown.open_time)}</span>
          <span>Ö {shown.open.toLocaleString("sv-SE")}</span><span>H {shown.high.toLocaleString("sv-SE")}</span>
          <span>L {shown.low.toLocaleString("sv-SE")}</span><span>S {shown.close.toLocaleString("sv-SE")}</span>
          <span>Vol {shown.volume.toLocaleString("sv-SE", { maximumFractionDigits: 2 })}</span>
          <span className={shown.closed ? "muted" : "live"}>{shown.closed ? "stängd" : "pågående"}</span>
        </div>
      )}
      {current && status && sameSeries(status, current) && (
        <div className="candle-meta">
          <span>Senast mottagen händelse: <b>{status.last_received_at ? utc(status.last_received_at) : "ingen än"}</b>{status.last_received_at ? ` (lokal tid ${new Date(status.last_received_at).toLocaleTimeString("sv-SE")})` : ""}</span>
          <span>Senaste stängda stapel: <b>{status.last_closed_open_time ? utc(status.last_closed_open_time) : "ingen än"}</b></span>
        </div>
      )}
      {stale && <div className="candle-warn">Datan är inte färsk: {STATE_TEXT[status!.state].toLowerCase()}{status!.message ? ` (${status!.message})` : ""}. Senast kända data visas tills anslutningen är tillbaka.</div>}
      {error && <div className="candle-warn" role="alert">Kunde inte läsa datalagret: {error}</div>}
      {problems.length > 0 && <div className="candle-warn" role="alert">Datafel i historiken: {problems.join(" ")} Diagrammet ritas inte förrän datan är rättad.</div>}
      {body}
      {isHist && historyNote && <div className="candle-source">{historyNote}</div>}

      {current && (
        <div className="candle-foot">
          <span>Tider i UTC. Halvgenomskinlig stapel = pågående, inte analysunderlag. Strategibeslut tas bara på stängda staplar.</span>
          <span className="attrib">Diagram: {desktop ? "TradingView Lightweight Charts™" : <a href="https://www.tradingview.com/" target="_blank" rel="noopener noreferrer">TradingView Lightweight Charts™</a>}, © TradingView, Inc. (tradingview.com)</span>
          {INDICATORS.filter(i => active.includes(i.id)).map(i => warmupNote(i, candles.length)).filter(Boolean).map(n => <span key={n} className="warn">{n}</span>)}
          {trades.length > 0 && <span>{tradesLabel ?? "Markörer: registrerade backtest-affärer"}{outside ? ` (${outside} av ${trades.length} ligger utanför den data som finns här)` : ""}.</span>}
        </div>
      )}
    </div>
  );
}
