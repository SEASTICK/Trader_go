import { useCallback, useEffect, useRef, useState } from "react";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { checkForUpdate, installUpdate, snoozeUpdate, text, type UpdaterDeps } from "../../lib/updater";

const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;

export type UpdateNotice = {
  status: "idle" | "checking" | "current" | "available" | "installing" | "error";
  version?: string;
  notes?: string;
  date?: string | null;
  message?: string;
  progress?: number | null;
  promptOpen?: boolean;
};

const defaultDeps = (): UpdaterDeps => ({
  check: () => check({ timeout: 15_000 }),
  relaunch,
  storage: window.localStorage,
  now: () => Date.now(),
  beforeInstall: () => invoke<string>("prepare_update_install").then(() => null, (e: unknown) => String(e)),
});

/** Uppdateringsläget för hela appen: kontroll vid start och var sjätte timme, dialogen och installationen. */
export function useUpdater(currentVersion: string, deps?: UpdaterDeps, enabled = isTauri()) {
  const depsRef = useRef<UpdaterDeps | null>(null);
  const getDeps = () => (depsRef.current ??= deps ?? defaultDeps());
  const [notice, setNotice] = useState<UpdateNotice>({ status: "idle" });

  const checkNow = useCallback(async (silent: boolean) => {
    if (!enabled) return;
    if (!silent) setNotice(current => ({ ...current, status: "checking", message: text.checking }));
    const outcome = await checkForUpdate(getDeps(), currentVersion);
    if (outcome.kind === "available") setNotice({ status: "available", version: outcome.version, notes: outcome.notes, date: outcome.date, promptOpen: outcome.prompt });
    else if (outcome.kind === "current") setNotice(current => (silent && current.status === "available" ? current : { status: silent ? "idle" : "current", message: silent ? undefined : text.upToDate }));
    else if (!silent) setNotice({ status: "error", message: outcome.message });
  }, [currentVersion, enabled]);

  useEffect(() => {
    if (!enabled || !currentVersion) return;
    const first = window.setTimeout(() => { void checkNow(true); }, 2500);
    const repeat = window.setInterval(() => { void checkNow(true); }, CHECK_INTERVAL_MS);
    return () => { window.clearTimeout(first); window.clearInterval(repeat); };
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

  return { enabled, notice, checkNow, install, later, dismissError };
}
