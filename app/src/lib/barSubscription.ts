// Prenumeration på insamlingens stapelhändelser för ett diagram. Ingen egen anslutning: händelserna kommer
// från datalagrets enda insamlare (`market-bar`). Fristående från React så att städningen kan testas.
import { sameSeries, type BarEvent, type SeriesRef } from "./candles";

/** Samma form som `listen` i @tauri-apps/api/event: ger en funktion som slutar lyssna. */
export type Listen = (event: string, handler: (e: { payload: BarEvent }) => void) => Promise<() => void>;

export type BarSubscription = {
  /** Slutar lyssna. Säker att anropa flera gånger och innan lyssnaren hunnit kopplas in. */
  close: () => void;
  /** Antal händelser som väntar på nästa ritning (för tester). */
  pending: () => number;
};

/**
 * Lyssnar på `market-bar` för en serie. Händelser för andra serier ignoreras. Händelserna samlas och
 * lämnas till `onBars` högst en gång per `flushMs`; en `resync` (REST-ikappkörning) ger `onResync` i
 * stället, så att slutet läses om från datalagret.
 */
export function subscribeBars(
  listen: Listen,
  series: SeriesRef,
  onBars: (events: BarEvent[]) => void,
  onResync: () => void,
  flushMs = 250,
  timers: { set: (f: () => void, ms: number) => number; clear: (id: number) => void } = {
    set: (f, ms) => window.setTimeout(f, ms),
    clear: id => window.clearTimeout(id),
  },
): BarSubscription {
  let closed = false;
  let queue: BarEvent[] = [];
  let timer: number | null = null;

  const flush = () => {
    timer = null;
    if (closed) return;
    const events = queue;
    queue = [];
    if (events.some(e => e.kind === "resync")) onResync();
    else if (events.length) onBars(events);
  };

  const unlisten = listen("market-bar", e => {
    if (closed || !sameSeries(e.payload, series)) return;
    queue.push(e.payload);
    if (timer === null) timer = timers.set(flush, flushMs);
  });

  return {
    close: () => {
      if (closed) return;
      closed = true;
      queue = [];
      if (timer !== null) timers.clear(timer);
      timer = null;
      void unlisten.then(off => off());
    },
    pending: () => queue.length,
  };
}
