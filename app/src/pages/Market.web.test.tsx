// @vitest-environment happy-dom
// Marknad i webbläsaren: riktiga medföljande staplar, val av tidsram som faktiskt byter data, tydlig källa/aktualitet och attribution.
// lightweight-charts ersätts av en spion (ingen canvas i happy-dom); vi kontrollerar vad som skickas till diagrammet.
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import frozen from "../../data/fas1-market.json";
import { resample } from "../lib/marketSources";

const drawn: { candles: { time: number }[][]; volume: unknown[][] } = { candles: [], volume: [] };
vi.mock("lightweight-charts", () => {
  const noop = (): unknown => new Proxy(function () {}, { get: (_t, p) => (p === "then" ? undefined : noop()), apply: () => noop() });
  const lenient = (base: object) => new Proxy(base, { get: (t, p) => (p in t ? (t as Record<string | symbol, unknown>)[p] : noop()) });
  const series = (kind: string) => lenient({ setData: (d: unknown[]) => { (kind === "candles" ? drawn.candles : drawn.volume).push(d as never); } });
  return {
    CandlestickSeries: "candles", HistogramSeries: "volume", LineSeries: "line", ColorType: { Solid: "solid" }, CrosshairMode: { Normal: 0 },
    createChart: () => lenient({ addSeries: (k: string) => series(k), panes: () => [noop()], timeScale: () => lenient({ getVisibleLogicalRange: () => null }), remove: () => {} }),
    createSeriesMarkers: () => lenient({ setMarkers: () => {} }),
  };
});
vi.mock("@tauri-apps/api/core", () => ({ isTauri: () => false, invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn(async () => () => {}) }));

import Market from "./Market";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
beforeEach(() => {
  drawn.candles.length = 0; drawn.volume.length = 0;
  host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host);
  vi.stubGlobal("ResizeObserver", class { observe() {} disconnect() {} });
  vi.stubGlobal("IntersectionObserver", class { observe() {} disconnect() {} });
});
afterEach(() => { act(() => root.unmount()); host.remove(); vi.unstubAllGlobals(); });
const render = async (now = new Date("2025-01-05T12:00:00Z")) => { await act(async () => { root.render(<Market now={now} />); }); };
const buttons = () => [...host.querySelectorAll<HTMLButtonElement>(".candle-tools button")];
const click = async (name: string) => { const b = buttons().find((x) => x.textContent === name); expect(b, name).toBeTruthy(); await act(async () => { b!.click(); }); };
const last = () => drawn.candles[drawn.candles.length - 1];
const FROZEN = frozen.rows.map(([t, o, h, l, c, v]) => ({ open_time: t, open: o, high: h, low: l, close: c, volume: v, close_time: t + 14_399_999, closed: true }));

describe("Marknad i webbläsaren", () => {
  it("ritar riktiga 4h-staplar och erbjuder tidsramar som verkligen finns", async () => {
    await render();
    expect(buttons().map((b) => b.textContent).filter((t) => ["4h", "8h", "12h", "1d", "1w"].includes(t ?? ""))).toEqual(["4h", "8h", "12h", "1d", "1w"]);
    expect(last()).toHaveLength(frozen.rows.length);
    expect(host.textContent).not.toMatch(/Ingen prisdata här/);
  });
  it("tidsramsval byter data: 1d ritar de beräknade dagsstaplarna, aldrig bara en ny etikett", async () => {
    await render();
    await click("1d");
    expect(last()).toHaveLength(resample(FROZEN, "4h", "1d").length);
    expect(last().length).toBeLessThan(frozen.rows.length);
    await click("1w");
    expect(last()).toHaveLength(resample(FROZEN, "4h", "1w").length);
    await click("4h");
    expect(last()).toHaveLength(frozen.rows.length);
  });
  it("visar källa, period, aktualitet och att det är historik, inte realtid", async () => {
    await render(new Date("2025-01-05T12:00:00Z"));
    const t = host.textContent ?? "";
    expect(t).toContain("kontrollsummerad historik"); expect(t).toContain("2022-01-01"); expect(t).toContain("2024-12-31");
    expect(t).toContain("2024-12-31 20:00 UTC"); expect(t).toContain("för 4 dagar sedan"); expect(t).toContain("historik, inte dagens pris");
    expect(t).toContain("bara historiken för ett instrument");
    expect(host.querySelector(".chip-live")?.textContent).toBe("HISTORIK");
  });
  it("visar obligatorisk attribution till TradingView med länk i webbläsaren", async () => {
    await render();
    const a = host.querySelector<HTMLAnchorElement>(".attrib a");
    expect(a?.href).toBe("https://www.tradingview.com/"); expect(a?.rel).toContain("noopener");
    expect(host.querySelector(".attrib")?.textContent).toMatch(/TradingView Lightweight Charts™.*© TradingView, Inc\./);
  });
  it("har ett instrumentval (ett instrument i webbläsaren) och förklarar begränsningen", async () => {
    await render();
    const group = host.querySelector('[role="group"][aria-label="Instrument"]');
    expect(group?.querySelectorAll("button").length).toBe(1);
    expect(group?.textContent).toContain("BTCUSDT terminer");
  });
});
