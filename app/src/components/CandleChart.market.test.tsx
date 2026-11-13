// @vitest-environment happy-dom
// Datavägen i datorprogrammet: diagrammet läser bara Binance spot och ritar aldrig en felmärkt serie.
// Tauri-bryggan och lightweight-charts är ersatta av spioner.
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SeriesInfo, SeriesRef } from "../lib/candles";

const calls: { cmd: string; args?: Record<string, unknown> }[] = [];
const info = (symbol: string, market: string, interval: string): SeriesInfo => ({ provider: "binance", market, symbol, interval, closed_bars: 10, first_open_time: 0, last_open_time: 1 });
const bar = (t: number, c: number) => ({ open_time: t, open: c, high: c + 1, low: c - 1, close: c, volume: 5, close_time: t + 3_599_999 });
vi.mock("@tauri-apps/api/core", () => ({
  isTauri: () => true,
  invoke: vi.fn(async (cmd: string, args?: Record<string, unknown>) => {
    calls.push({ cmd, args });
    if (cmd === "market_series") return [info("BTCUSDT", "spot", "4h"), info("BTCUSDT", "um", "4h")];
    if (cmd === "market_bars") return { bars: [bar(0, 100), bar(3_600_000, 101)], live: null, has_more: false };
    return null;
  }),
}));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn(async () => () => {}) }));
vi.mock("../features/market/useMarketStatus", () => ({ STATE_TEXT: {}, useMarketStatus: () => ({ status: null, available: true }) }));
vi.mock("../lib/barSubscription", () => ({ subscribeBars: () => ({ close: () => {}, resync: () => {} }) }));
const noop = (): unknown => new Proxy(function () {}, { get: (_t, p) => (p === "then" ? undefined : noop()), apply: () => noop() });
const lenient = (base: object) => new Proxy(base, { get: (t, p) => (p in t ? (t as Record<string | symbol, unknown>)[p] : noop()) });
vi.mock("lightweight-charts", () => ({
  CandlestickSeries: "c", HistogramSeries: "h", LineSeries: "l", ColorType: { Solid: "s" }, CrosshairMode: { Normal: 0 },
  createChart: () => lenient({ addSeries: () => lenient({ setData: () => {} }), panes: () => [noop()], timeScale: () => lenient({ getVisibleLogicalRange: () => null }), remove: () => {} }),
  createSeriesMarkers: () => lenient({ setMarkers: () => {} }),
}));

import { CandleChart } from "./CandleChart";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
beforeEach(() => {
  calls.length = 0; host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host);
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
  vi.stubGlobal("IntersectionObserver", class { observe() {} disconnect() {} });
});
afterEach(() => { act(() => root.unmount()); host.remove(); vi.unstubAllGlobals(); });
const render = async (series: SeriesRef) => { await act(async () => { root.render(<CandleChart series={series} />); }); await act(async () => {}); };
const barCalls = () => calls.filter((c) => c.cmd === "market_bars");

describe("datavägen i datorprogrammet", () => {
  it("läser staplar för en spotserie med rätt symbol och tidsram", async () => {
    await render({ provider: "binance", market: "spot", symbol: "BTCUSDT", interval: "4h" });
    expect(barCalls().length).toBeGreaterThan(0);
    expect(barCalls()[0].args).toMatchObject({ symbol: "BTCUSDT", interval: "4h" });
    expect(host.textContent).not.toContain("stöds inte");
  });
  it("ritar och läser ALDRIG en terminsserie (samma symbol och tidsram som spot): ingen felmärkt graf", async () => {
    await render({ provider: "binance", market: "um", symbol: "BTCUSDT", interval: "4h" });
    expect(barCalls()).toHaveLength(0);                                              // market_bars läser bara spot och anropas inte
    expect(host.querySelector(".candle-empty")?.textContent).toMatch(/Marknaden stöds inte i datavägen/);
    expect(host.querySelector(".candle-box")).toBeNull();
  });
  it("startar om och läser nytt när bara marknaden ändras tillbaka till spot", async () => {
    await render({ provider: "binance", market: "um", symbol: "BTCUSDT", interval: "4h" });
    await render({ provider: "binance", market: "spot", symbol: "BTCUSDT", interval: "4h" });
    expect(barCalls().length).toBeGreaterThan(0);
    expect(host.querySelector(".candle-empty")).toBeNull();
  });
});
