import { describe, expect, it, vi } from "vitest";
import { subscribeBars, type Listen } from "./barSubscription";
import type { BarEvent, SeriesRef } from "./candles";

const BTC4H: SeriesRef = { provider: "binance", market: "spot", symbol: "BTCUSDT", interval: "4h" };
const bar = (t: number) => ({ open_time: t, open: 1, high: 2, low: 0.5, close: 1.5, volume: 3, close_time: t + 14_399_999 });
const ev = (kind: BarEvent["kind"], series: Partial<SeriesRef> = {}, t = 0): BarEvent => ({ ...BTC4H, ...series, kind, bar: kind === "resync" ? null : bar(t) });

/** En påhittad händelsebuss med samma form som Tauris listen, som räknar aktiva lyssnare. */
function bus(delayMs = 0) {
  const handlers = new Set<(e: { payload: BarEvent }) => void>();
  const listen: Listen = (_name, h) => new Promise(resolve => setTimeout(() => { handlers.add(h); resolve(() => handlers.delete(h)); }, delayMs));
  return { listen, emit: (p: BarEvent) => handlers.forEach(h => h({ payload: p })), active: () => handlers.size };
}

const fake = () => {
  const pending = new Map<number, () => void>();
  let id = 0;
  return { set: (f: () => void) => { pending.set(++id, f); return id; }, clear: (i: number) => void pending.delete(i), run: () => { const fs = [...pending.values()]; pending.clear(); fs.forEach(f => f()); }, size: () => pending.size };
};

describe("stapelprenumeration", () => {
  it("samlar händelser och ritar högst en gång per intervall, bara för rätt serie", async () => {
    vi.useFakeTimers();
    const b = bus(); const t = fake(); const onBars = vi.fn(); const onResync = vi.fn();
    const sub = subscribeBars(b.listen, BTC4H, onBars, onResync, 250, t);
    await vi.runAllTimersAsync();
    b.emit(ev("live", {}, 1)); b.emit(ev("live", {}, 1)); b.emit(ev("live", { interval: "1h" }, 1)); b.emit(ev("closed", { symbol: "ETHUSDT" }, 1));
    expect(t.size()).toBe(1);
    expect(sub.pending()).toBe(2);
    t.run();
    expect(onBars).toHaveBeenCalledOnce();
    expect(onBars.mock.calls[0][0]).toHaveLength(2);
    expect(onResync).not.toHaveBeenCalled();
    sub.close();
    vi.useRealTimers();
  });

  it("en resync läser om i stället för att rita enskilda staplar", async () => {
    vi.useFakeTimers();
    const b = bus(); const t = fake(); const onBars = vi.fn(); const onResync = vi.fn();
    subscribeBars(b.listen, BTC4H, onBars, onResync, 250, t);
    await vi.runAllTimersAsync();
    b.emit(ev("live", {}, 1)); b.emit(ev("resync"));
    t.run();
    expect(onResync).toHaveBeenCalledOnce();
    expect(onBars).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("stängning slutar lyssna, kastar väntande händelser och ritar inget mer", async () => {
    vi.useFakeTimers();
    const b = bus(); const t = fake(); const onBars = vi.fn();
    const sub = subscribeBars(b.listen, BTC4H, onBars, () => {}, 250, t);
    await vi.runAllTimersAsync();
    expect(b.active()).toBe(1);
    b.emit(ev("live", {}, 1));
    sub.close(); sub.close();
    await vi.runAllTimersAsync();
    t.run();
    expect(onBars).not.toHaveBeenCalled();
    expect(b.active()).toBe(0);
    b.emit(ev("live", {}, 2));
    expect(sub.pending()).toBe(0);
    vi.useRealTimers();
  });

  it("stängning innan lyssnaren kopplats in lämnar ingen lyssnare kvar (snabb navigering)", async () => {
    vi.useFakeTimers();
    const b = bus(50);
    const sub = subscribeBars(b.listen, BTC4H, vi.fn(), vi.fn(), 250, fake());
    sub.close();
    await vi.runAllTimersAsync();
    expect(b.active()).toBe(0);
    vi.useRealTimers();
  });

  it("byte av tidsram: den gamla prenumerationen stängs och bara den nya tar emot", async () => {
    vi.useFakeTimers();
    const b = bus(); const t = fake(); const old = vi.fn(); const next = vi.fn();
    const a = subscribeBars(b.listen, BTC4H, old, () => {}, 250, t);
    await vi.runAllTimersAsync();
    a.close();
    const n = subscribeBars(b.listen, { ...BTC4H, interval: "1h" }, next, () => {}, 250, t);
    await vi.runAllTimersAsync();
    expect(b.active()).toBe(1);
    b.emit(ev("live", {}, 1)); b.emit(ev("live", { interval: "1h" }, 1));
    t.run();
    expect(old).not.toHaveBeenCalled();
    expect(next).toHaveBeenCalledOnce();
    expect(next.mock.calls[0][0][0].interval).toBe("1h");
    n.close();
    vi.useRealTimers();
  });
});
