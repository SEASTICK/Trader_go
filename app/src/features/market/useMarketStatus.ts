import { useEffect, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

/** Samma fält som `Status` i src-tauri/src/market/status.rs. Tider är ms UTC. */
export type MarketState = "starting" | "syncing" | "connected" | "reconnecting" | "gap" | "stale" | "stopped" | "error";
export type MarketStatus = {
  schema: number;
  state: MarketState;
  ready: boolean;
  provider: string;
  market: string;
  symbol: string;
  interval: string;
  message: string | null;
  last_received_at: number | null;
  last_event_time: number | null;
  last_closed_open_time: number | null;
  live_open_time: number | null;
  closed_bars: number;
  gaps: [number, number][];
  confirmed_gaps: number;
  corrections: number;
  rejected: number;
  reconnects: number;
  updated_at: number;
  database: string;
};

export const STATE_TEXT: Record<MarketState, string> = {
  starting: "Startar",
  syncing: "Synkroniserar historik",
  connected: "Ansluten",
  reconnecting: "Återansluter",
  gap: "Datalucka",
  stale: "Gammal data",
  stopped: "Stoppad",
  error: "Fel",
};

/** Insamlingens status från appen. Ingen simulerad ersättning om den inte går att läsa. */
export function useMarketStatus(): { status: MarketStatus | null; available: boolean } {
  const available = isTauri();
  const [status, setStatus] = useState<MarketStatus | null>(null);
  useEffect(() => {
    if (!available) return;
    let alive = true;
    const pull = () => invoke<MarketStatus>("market_status").then(s => { if (alive) setStatus(s); }).catch(() => {});
    void pull();
    const off = listen<MarketStatus>("market-status", e => setStatus(e.payload));
    const timer = window.setInterval(pull, 5000);
    return () => { alive = false; window.clearInterval(timer); void off.then(f => f()); };
  }, [available]);
  return { status, available };
}
