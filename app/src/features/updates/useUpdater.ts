import { useCallback, useEffect, useRef, useState } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { check } from "@tauri-apps/plugin-updater";
import { relaunch } from "@tauri-apps/plugin-process";
import { checkForUpdate, downloadUpdate, installReady, shouldCheckOnFocus, snoozeUpdate, text, type ReadyUpdate, type UpdaterDeps } from "../../lib/updater";

// Appen kan ligga öppen hela dagen, så kontrollen görs ofta. Det är en liten JSON-fil.
const CHECK_INTERVAL_MS = 30 * 60 * 1000;

export type UpdateNotice = {
  /** available → downloading → ready (hämtad och verifierad) → installing. */
  status: "idle" | "checking" | "current" | "available" | "downloading" | "ready" | "installing" | "error";
  version?: string;
  notes?: string;
  date?: string | null;
  message?: string;
  progress?: number | null;
  promptOpen?: boolean;
};

export type UpdateDiagnostics = { checkedAt: number; result: "current" | "available" | "error"; version?: string; message?: string; detail?: string };

const defaultDeps = (): UpdaterDeps => ({
  check: () => check({ timeout: 15_000 }),
  relaunch,
  storage: window.localStorage,
  now: () => Date.now(),
});

/**
 * Uppdateringsläget för hela appen: kontroll vid start, var 30:e minut och när fönstret får fokus. En nyare
 * version hämtas och verifieras direkt i bakgrunden; omstarten sker först när användaren väljer det.
 * Utan nät (vid start eller senare) märks ingenting utom en rad under Status.
 */
export function useUpdater(currentVersion: string, deps?: UpdaterDeps, enabled = isTauri()) {
  const depsRef = useRef<UpdaterDeps | null>(null);
  const getDeps = () => (depsRef.current ??= deps ?? defaultDeps());
  const [notice, setNotice] = useState<UpdateNotice>({ status: "idle" });
  const lastCheck = useRef<number | null>(null);
  const [diagnostics, setDiagnostics] = useState<UpdateDiagnostics | null>(null);
  const ready = useRef<ReadyUpdate | null>(null);
  const downloading = useRef<string | null>(null);

  const download = useCallback(async (version: string, prompt: boolean, userAsked = false) => {
    if (downloading.current === version || ready.current?.version === version) return;
    downloading.current = version;
    setNotice(current => ({ ...current, status: "downloading", version, progress: null, message: text.phase.download }));
    const result = await downloadUpdate(getDeps(), currentVersion, fraction => setNotice(current => ({ ...current, progress: fraction })));
    downloading.current = null;
    if (result.ok) {
      ready.current = result.ready;
      setNotice(current => ({ ...current, status: "ready", version: result.ready.version, progress: 1, message: text.ready, promptOpen: prompt || current.promptOpen }));
    } else {
      setDiagnostics({ checkedAt: getDeps().now(), result: "error", version, message: result.message, detail: result.detail });
      // Ett fel i en hämtning som ingen bett om visas under Status och i menyn, inte som en ruta som dyker upp.
      setNotice(current => ({ ...current, status: "error", progress: null, message: result.message, promptOpen: userAsked || current.promptOpen }));
    }
  }, [currentVersion]);

  const checkNow = useCallback(async (silent: boolean) => {
    if (!enabled) return;
    if (ready.current) { if (!silent) setNotice(current => ({ ...current, promptOpen: true })); return; }
    if (downloading.current) return;
    if (!silent) setNotice(current => ({ ...current, status: "checking", message: text.checking }));
    lastCheck.current = getDeps().now();
    const outcome = await checkForUpdate(getDeps(), currentVersion);
    setDiagnostics({
      checkedAt: getDeps().now(),
      result: outcome.kind,
      version: outcome.kind === "available" ? outcome.version : undefined,
      message: outcome.kind === "error" ? outcome.message : undefined,
      detail: outcome.kind === "error" ? outcome.detail : undefined,
    });
    if (outcome.kind === "available") {
      const prompt = !silent || outcome.prompt;
      setNotice({ status: "available", version: outcome.version, notes: outcome.notes, date: outcome.date, promptOpen: false });
      void download(outcome.version, prompt, !silent);
    } else if (outcome.kind === "current") setNotice(current => (silent && current.status === "error" && current.version ? current : { status: silent ? "idle" : "current", message: silent ? undefined : text.upToDate }));
    else if (!silent) setNotice({ status: "error", message: outcome.message });
  }, [currentVersion, enabled, download]);

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

  /** "Starta om nu": installerar den hämtade versionen. Utan hämtad version (t.ex. efter ett fel) hämtas den igen. */
  const install = useCallback(async () => {
    if (!ready.current) { if (notice.version) void download(notice.version, true, true); return; }
    setNotice(current => ({ ...current, status: "installing", progress: null, promptOpen: true, message: text.phase.install }));
    const result = await installReady(ready.current, getDeps(), progress => setNotice(current => ({ ...current, message: text.phase[progress.phase] })));
    if (!result.ok) setNotice(current => ({ ...current, status: "ready", promptOpen: true, message: result.message }));
  }, [download, notice.version]);

  const later = useCallback(() => {
    if (notice.version) snoozeUpdate(getDeps().storage, notice.version, getDeps().now());
    setNotice(current => ({ ...current, promptOpen: false }));
  }, [notice.version]);

  const dismissError = useCallback(() => setNotice(current => ({ ...current, status: ready.current ? "ready" : "idle", promptOpen: false, message: ready.current ? text.ready : undefined })), []);

  const openPrompt = useCallback(() => setNotice(current => (current.version ? { ...current, promptOpen: true } : current)), []);

  return { enabled, notice, diagnostics, checkNow, install, later, dismissError, openPrompt };
}
