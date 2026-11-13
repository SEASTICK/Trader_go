import { useEffect, useMemo, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { CandleChart } from "../components/CandleChart";
import { Page, Segmented } from "../components/ui";
import frozenMarket from "../../data/fas1-market.json";
import type { Candle, SeriesInfo, SeriesRef } from "../lib/candles";
import { agoText, ageDays } from "../lib/freshness";
import { HISTORY_INTERVALS, isSupportedLive, resample } from "../lib/marketSources";

const ms = (t: number) => new Date(t).toISOString().slice(0, 16).replace("T", " ");
const label = (s: { symbol: string; market: string }) => `${s.symbol} ${s.market === "spot" ? "spot" : s.market === "um" ? "terminer" : s.market}`;
const key = (s: { provider: string; market: string; symbol: string }) => `${s.provider}:${s.market}:${s.symbol}`;

/** De riktiga stängda 4h-staplarna som följer med appen (kontrollsummerade, BTCUSDT USDⓈ-M). */
const FROZEN: Candle[] = frozenMarket.rows.map(([open_time, open, high, low, close, volume]) => ({ open_time, open, high, low, close, volume, close_time: open_time + 14_400_000 - 1, closed: true }));
const HISTORY_SERIES: SeriesRef = { provider: "binance", market: "um", symbol: "BTCUSDT", interval: "4h" };

/** Prisdiagram med val av instrument och tidsram. Datorprogrammet läser datalagret, webbläsaren visar den medföljande historiken. */
export default function Market({ now = new Date() }: { now?: Date }) {
  const desktop = isTauri();
  return desktop ? <DesktopMarket /> : <WebMarket now={now} />;
}

function WebMarket({ now }: { now: Date }) {
  const sets = useMemo(() => Object.fromEntries(HISTORY_INTERVALS.map((i) => [i, resample(FROZEN, "4h", i)])), []);
  const last = FROZEN[FROZEN.length - 1];
  const first = FROZEN[0];
  const days = last ? ageDays(new Date(last.open_time).toISOString(), now) : null;
  const note = last && (
    <>
      <span>Källa: Binance USDⓈ-M terminer {HISTORY_SERIES.symbol}, kontrollsummerad historik <b>{ms(first.open_time).slice(0, 10)}</b> till <b>{ms(last.open_time).slice(0, 10)}</b> (SHA-256 {frozenMarket.dataset_sha256.slice(0, 8)}…).</span>
      <span>Senaste stapel: <b>{ms(last.open_time)} UTC</b> ({agoText(days)}). Det här är historik, inte dagens pris.</span>
      <span>8h, 12h, 1d och 1w är räknade ur de riktiga stängda 4h-staplarna, aldrig påhittade.</span>
    </>
  );
  return (
    <Page title="Marknad" sub="Historik för Bitcoin-terminer. Realtid finns i skrivbordsappen."
      actions={<div role="group" aria-label="Instrument"><Segmented value={label(HISTORY_SERIES)} options={[label(HISTORY_SERIES)]} onChange={() => {}} /></div>}>
      <CandleChart series={HISTORY_SERIES} historicalSets={sets} historyNote={note} noSourceReason="Ingen datakälla för den här marknaden än." />
      <p className="note" role="note">I webbläsaren finns bara historiken för <b>ett instrument</b>. Fler instrument, fler tidsramar och realtidspriser kommer från datalagret i skrivbordsappen.</p>
      <p className="footnote">Riktiga priser betyder inte riktig handel. Allt i Trader_go är papper eller historik.</p>
    </Page>
  );
}

function DesktopMarket() {
  const [all, setAll] = useState<SeriesInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pick, setPick] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    invoke<SeriesInfo[]>("market_series").then((s) => { if (alive) setAll(s); }, (e) => { if (alive) setError(String(e)); });
    return () => { alive = false; };
  }, []);
  const instruments = useMemo(() => {
    // Bara serier som hela datavägen stöder (Binance spot). `market_bars` läser bara spot, så en annan marknad med samma symbol skulle annars bli en felmärkt graf.
    const seen = new Map<string, SeriesInfo>();
    for (const s of (all ?? []).filter(isSupportedLive)) if (!seen.has(key(s))) seen.set(key(s), s);
    return [...seen.values()];
  }, [all]);
  const chosen = instruments.find((s) => key(s) === pick) ?? instruments.find((s) => s.symbol === "BTCUSDT" && s.market === "spot") ?? instruments[0];
  const series: SeriesRef | null = chosen ? { provider: "binance", market: chosen.market as SeriesRef["market"], symbol: chosen.symbol, interval: (all ?? []).filter(isSupportedLive).find((s) => key(s) === key(chosen) && s.interval === "4h")?.interval ?? (all ?? []).filter(isSupportedLive).find((s) => key(s) === key(chosen))!.interval } : null;
  return (
    <Page title="Marknad" sub="Riktiga priser från Binance, utan konto och utan nycklar."
      actions={instruments.length > 0 && chosen ? <div role="group" aria-label="Instrument"><Segmented value={label(chosen)} options={instruments.map(label)} onChange={(v) => setPick(key(instruments.find((s) => label(s) === v)!))} /></div> : undefined}>
      {error && <p className="note warn" role="alert"><b>Kunde inte läsa datalagret.</b> {error}</p>}
      {all !== null && instruments.length === 0 && !error && <p className="note warn" role="alert"><b>Datalagret har ingen marknadsdata än.</b> Insamlingen styrs i appens datamapp (se docs/marknadsdata.md).</p>}
      <CandleChart series={series} noSourceReason="Ingen datakälla för den här marknaden än." />
      <p className="footnote">Riktiga priser betyder inte riktig handel. Allt i Trader_go är papper eller historik.</p>
    </Page>
  );
}
