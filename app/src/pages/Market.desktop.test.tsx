// @vitest-environment happy-dom
// Marknad i datorprogrammet: instrumentvalet kommer från datalagret (market_series) och byter serie i diagrammet. Diagrammet är ersatt av en spion.
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SeriesInfo, SeriesRef } from "../lib/candles";

const info = (symbol: string, market: string, interval: string): SeriesInfo => ({ provider: "binance", market, symbol, interval, closed_bars: 100, first_open_time: 0, last_open_time: 1 });
// Samma symbol och tidsram finns på två marknader (BTCUSDT 4h på spot och um): bara spot stöds av datavägen och får erbjudas.
const SERIES = [info("BTCUSDT", "spot", "1h"), info("BTCUSDT", "spot", "4h"), info("ETHUSDT", "spot", "1h"), info("BTCUSDT", "um", "4h"), info("BTCUSDT", "um", "1d"), info("SOLUSDT", "um", "1d")];
let result: { value: SeriesInfo[] | Error } = { value: SERIES };
const seen: (SeriesRef | null)[] = [];
vi.mock("@tauri-apps/api/core", () => ({ isTauri: () => true, invoke: vi.fn(async () => { if (result.value instanceof Error) throw result.value; return result.value; }) }));
vi.mock("../components/CandleChart", () => ({ CandleChart: ({ series }: { series: SeriesRef | null }) => { seen.push(series); return <div data-testid="chart">{series ? `${series.symbol} ${series.market} ${series.interval}` : "inget"}</div>; } }));

import Market from "./Market";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
beforeEach(() => { seen.length = 0; result = { value: SERIES }; host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); });
const render = async () => { await act(async () => { root.render(<Market />); }); await act(async () => {}); };
const chart = () => host.querySelector('[data-testid="chart"]')?.textContent;

describe("Marknad i datorprogrammet", () => {
  it("erbjuder bara serier som datavägen stöder (Binance spot), aldrig terminer, och väljer Bitcoin spot 4h som start", async () => {
    await render();
    const group = host.querySelector('[role="group"][aria-label="Instrument"]');
    expect([...group!.querySelectorAll("button")].map((b) => b.textContent)).toEqual(["BTCUSDT spot", "ETHUSDT spot"]);
    expect(host.textContent).not.toMatch(/terminer|SOLUSDT/);
    expect(chart()).toBe("BTCUSDT spot 4h");
  });
  it("byter serie i diagrammet när man väljer ett annat instrument, och tidsramen är en som instrumentet har på spot", async () => {
    await render();
    const eth = [...host.querySelectorAll<HTMLButtonElement>('[aria-label="Instrument"] button')].find((b) => b.textContent === "ETHUSDT spot")!;
    await act(async () => { eth.click(); });
    expect(chart()).toBe("ETHUSDT spot 1h");
    expect(seen.every((x) => x === null || x.market === "spot")).toBe(true);            // diagrammet får aldrig en annan marknad
  });
  it("visar ett tydligt fel när datalagret inte kan läsas och ritar inget påhittat", async () => {
    result = { value: new Error("datalagret är låst") };
    await render();
    expect(host.querySelector('[role="alert"]')?.textContent).toContain("datalagret är låst");
    expect(chart()).toBe("inget");
  });
  it("säger att datalagret är tomt i stället för att visa en graf", async () => {
    result = { value: [] };
    await render();
    expect(host.querySelector('[role="alert"]')?.textContent).toContain("ingen marknadsdata");
    expect(chart()).toBe("inget");
  });
});
