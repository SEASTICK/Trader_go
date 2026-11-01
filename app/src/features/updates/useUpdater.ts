import { useCallback, useEffect, useRef, useState } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { checkForUpdate, installUpdate, shouldCheckOnFocus, snoozeUpdate, text, type UpdaterDeps } from "../../lib/updater";

// Appen kan ligga öppen hela dagen, så kontrollen görs ofta. Det är en liten JSON-fil.
const CHECK_INTERVAL_MS = 30 * 60 * 1000;

export type UpdateNotice = {
  status: "idle" | "checking" | "current" | "available" | "installing" | "error";
  version?: string;
  notes?: string;
  date?: string | null;
  message?: string;
  progress?: number | null;
  promptOpen?: boolean;
};

export type UpdateDiagnostics = { checkedAt: number; result: "current" | "available" | "error"; version?: string; detail?: string };

const defaultDeps = (): UpdaterDeps => ({
  check: () => check({ timeout: 15_000 }),
  relaunch,
  storage: window.localStorage,
  now: () => Date.now(),
});

/** Uppdateringsläget för hela appen: kontroll vid start och var sjätte timme, dialogen och installationen. */
export function useUpdater(currentVersion: string, deps?: UpdaterDeps, enabled = isTauri()) {
  const depsRef = useRef<UpdaterDeps | null>(null);
  const getDeps = () => (depsRef.current ??= deps ?? defaultDeps());
  const [notice, setNotice] = useState<UpdateNotice>({ status: "idle" });
  const lastCheck = useRef<number | null>(null);
  const [diagnostics, setDiagnostics] = useState<UpdateDiagnostics | null>(null);

  const checkNow = useCallback(async (silent: boolean) => {
    if (!enabled) return;
    if (!silent) setNotice(current => ({ ...current, status: "checking", message: text.checking }));
    lastCheck.current = getDeps().now();
    const outcome = await checkForUpdate(getDeps(), currentVersion);
    setDiagnostics({
      checkedAt: getDeps().now(),
      result: outcome.kind,
      version: outcome.kind === "available" ? outcome.version : undefined,
      detail: outcome.kind === "error" ? outcome.detail : undefined,
    });
    if (outcome.kind === "available") setNotice({ status: "available", version: outcome.version, notes: outcome.notes, date: outcome.date, promptOpen: outcome.prompt });
    else if (outcome.kind === "current") setNotice(current => (silent && current.status === "available" ? current : { status: silent ? "idle" : "current", message: silent ? undefined : text.upToDate }));
    else if (!silent) setNotice({ status: "error", message: outcome.message });
  }, [currentVersion, enabled]);

  useEffect(() => {
    if (!enabled || !currentVersion) return;
    const first = window.setTimeout(() => { void checkNow(true); }, 2500);
    const repeat = window.setInterval(() => { void checkNow(true); }, CHECK_INTERVAL_MS);
    // Kontrollera också när man kommer tillbaka till fönstret, så en öppen app inte missar en ny version.
    const onFocus = () => {
      if (document.visibilityState === "visible" && shouldCheckOnFocus(lastCheck.current, getDeps().now())) void checkNow(true);
    };
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      window.clearTimeout(first); window.clearInterval(repeat);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, [checkNow, currentVersion, enabled]);

  const install = useCallback(async () => {
    setNotice(current => ({ ...current, status: "installing", progress: null, promptOpen: true, message: text.phase.download }));
    const result = await installUpdate(getDeps(), currentVersion, progress => {
      setNotice(current => ({ ...current, status: "installing", progress: progress.phase === "download" ? progress.fraction : null, message: text.phase[progress.phase] }));
    });
    if (!result.ok) setNotice(current => ({ ...current, status: "error", progress: null, promptOpen: true, message: result.message }));
  }, [currentVersion]);

  const later = useCallback(() => {
    if (notice.version) snoozeUpdate(getDeps().storage, notice.version, getDeps().now());
    setNotice(current => ({ ...current, status: current.version ? "available" : "idle", promptOpen: false }));
  }, [notice.version]);

  const dismissError = useCallback(() => setNotice(current => ({ ...current, status: current.version ? "available" : "idle", promptOpen: false, message: undefined })), []);

  const openPrompt = useCallback(() => setNotice(current => (current.status === "available" ? { ...current, promptOpen: true } : current)), []);

  return { enabled, notice, diagnostics, checkNow, install, later, dismissError, openPrompt };
}
