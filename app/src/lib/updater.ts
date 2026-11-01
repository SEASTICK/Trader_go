/**
 * Uppdateringsflödet utan beroende av Tauri, så alla vägar går att testa.
 *
 * Kedjan i appen:
 *   1. check()            pluginen läser latest.json från den publika uppdateringssidan och verifierar
 *                         signaturen mot pubkey i tauri.conf.json.
 *   2. isNewerVersion     appen erbjuder bara en strikt nyare version.
 *   3. download           hämtas i bakgrunden direkt när en nyare version finns. Pluginen verifierar
 *                         signaturen här, så en ogiltig uppdatering stoppas innan någon frågas.
 *   4. install + omstart  först när användaren väljer "Starta om nu". Windows-installationen startar
 *                         om appen själv (passiv installation), på macOS byts appen ut och startas om.
 *
 * Trader_go har ingen lokal användardata, så ingen säkerhetskopia tas före installation.
 * Om appen får lokal data ska en säkerhetskopia läggas till före steg 3, som i Vinstly.
 */
import { isNewerVersion, readSnooze, shouldPromptForUpdate, SNOOZE_KEY, UPDATE_SNOOZE_MS } from "./version";

export const text = {
  checking: "Söker efter uppdateringar…",
  upToDate: "Du har den senaste versionen.",
  phase: { download: "Hämtar uppdateringen…", install: "Installerar…", restart: "Startar om…" },
  ready: "Uppdateringen är hämtad och verifierad. Programmet startar om när du installerar.",
  error: {
    signature: "Uppdateringen kunde inte verifieras och installerades inte.",
    networkCheck: "Kunde inte söka efter uppdateringar. Kontrollera internetanslutningen.",
    networkInstall: "Hämtningen avbröts. Kontrollera internetanslutningen och försök igen.",
    check: "Uppdateringskontrollen misslyckades.",
    install: "Uppdateringen kunde inte installeras.",
    gone: "Uppdateringen finns inte längre. Sök igen om en stund.",
    platform: "Den senaste versionen finns inte för den här datorn ännu (ingen fil för den här plattformen i latest.json).",
  },
};

export type UpdateHandle = {
  version: string;
  body?: string | null;
  date?: string | null;
  downloadAndInstall: (onEvent?: (event: DownloadEvent) => void) => Promise<void>;
  download?: (onEvent?: (event: DownloadEvent) => void) => Promise<void>;
  install?: () => Promise<void>;
  close?: () => Promise<void>;
};

export type DownloadEvent =
  | { event: "Started"; data: { contentLength?: number } }
  | { event: "Progress"; data: { chunkLength: number } }
  | { event: "Finished" };

export type UpdaterDeps = {
  check: () => Promise<UpdateHandle | null>;
  relaunch: () => Promise<void>;
  storage: Pick<Storage, "getItem" | "setItem" | "removeItem">;
  now: () => number;
};

export type CheckOutcome =
  | { kind: "available"; version: string; notes: string; date: string | null; prompt: boolean }
  | { kind: "current" }
  | { kind: "error"; message: string; detail: string };

/** "Senare": fråga inte om samma version igen på ett dygn. */
export function snoozeUpdate(storage: Pick<Storage, "setItem">, version: string, now: number) {
  try { storage.setItem(SNOOZE_KEY, JSON.stringify({ version, untilUnixMs: now + UPDATE_SNOOZE_MS })); } catch { /* ignoreras */ }
}

/** Pluginens egen feltext, för felsökning. Visas under Status. */
export function rawReason(reason: unknown): string {
  if (typeof reason === "string") return reason;
  if (reason instanceof Error) return reason.message;
  try { return JSON.stringify(reason) ?? String(reason); } catch { return String(reason); }
}

/** Översätter pluginens felmeddelanden till något användaren kan agera på. */
export function describeUpdateError(reason: unknown, phase: "check" | "install"): string {
  const raw = typeof reason === "string" ? reason : reason instanceof Error ? reason.message : "";
  const lower = raw.toLowerCase();
  if (/signature|signatur|verif/.test(lower)) return text.error.signature;
  if (/platform/.test(lower)) return text.error.platform;
  if (/network|timeout|timed out|dns|connect|offline|request|http|resolve/.test(lower) || lower === "") {
    return phase === "check" ? text.error.networkCheck : text.error.networkInstall;
  }
  return phase === "check" ? text.error.check : text.error.install;
}

export async function checkForUpdate(deps: UpdaterDeps, currentVersion: string): Promise<CheckOutcome> {
  let handle: UpdateHandle | null;
  try { handle = await deps.check(); }
  catch (reason) { return { kind: "error", message: describeUpdateError(reason, "check"), detail: rawReason(reason) }; }
  if (!handle) return { kind: "current" };
  // Pluginen kan i sällsynta fall peka på samma eller en äldre version. Det ska aldrig erbjudas.
  if (!isNewerVersion(handle.version, currentVersion)) {
    try { await handle.close?.(); } catch { /* ignoreras */ }
    return { kind: "current" };
  }
  const version = handle.version;
  const notes = (handle.body ?? "").trim();
  const date = handle.date ?? null;
  try { await handle.close?.(); } catch { /* ignoreras */ }
  return { kind: "available", version, notes, date, prompt: shouldPromptForUpdate(version, currentVersion, readSnooze(deps.storage), deps.now()) };
}

export type InstallProgress = { phase: "download"; fraction: number | null } | { phase: "install" } | { phase: "restart" };
export type InstallOutcome = { ok: true } | { ok: false; message: string };

export type ReadyUpdate = { version: string; handle: UpdateHandle };
export type DownloadOutcome = { ok: true; ready: ReadyUpdate } | { ok: false; message: string; detail: string };

/**
 * Hämtar en nyare version i bakgrunden utan att installera den. Signaturen verifieras av pluginen under
 * hämtningen, så en uppdatering som inte går att verifiera blir ett fel här och erbjuds aldrig.
 */
export async function downloadUpdate(deps: UpdaterDeps, currentVersion: string, onProgress: (fraction: number | null) => void): Promise<DownloadOutcome> {
  let handle: UpdateHandle | null;
  try { handle = await deps.check(); }
  catch (reason) { return { ok: false, message: describeUpdateError(reason, "check"), detail: rawReason(reason) }; }
  if (!handle || !isNewerVersion(handle.version, currentVersion)) return { ok: false, message: text.error.gone, detail: "no newer version in latest.json" };
  if (!handle.download || !handle.install) return { ok: false, message: text.error.install, detail: "updater plugin has no separate download/install" };
  try {
    let total = 0; let received = 0;
    await handle.download(event => {
      if (event.event === "Started") { total = event.data.contentLength ?? 0; onProgress(total ? 0 : null); }
      else if (event.event === "Progress") { received += event.data.chunkLength; onProgress(total ? Math.min(1, received / total) : null); }
      else onProgress(1);
    });
  } catch (reason) {
    try { await handle.close?.(); } catch { /* ignoreras */ }
    return { ok: false, message: describeUpdateError(reason, "install"), detail: rawReason(reason) };
  }
  return { ok: true, ready: { version: handle.version, handle } };
}

/** Installerar en hämtad och verifierad version och startar om. Anropas bara när användaren valt det. */
export async function installReady(ready: ReadyUpdate, deps: UpdaterDeps, onProgress: (progress: InstallProgress) => void): Promise<InstallOutcome> {
  onProgress({ phase: "install" });
  try { await ready.handle.install!(); }
  catch (reason) { return { ok: false, message: describeUpdateError(reason, "install") }; }
  onProgress({ phase: "restart" });
  try { await deps.relaunch(); } catch { /* På Windows har installationen redan startat om appen. */ }
  return { ok: true };
}

/** Kontrollera när fönstret får fokus igen, men inte oftare än var tionde minut. */
export const FOCUS_MIN_GAP_MS = 10 * 60 * 1000;
export function shouldCheckOnFocus(lastCheckedAt: number | null, now: number, minGapMs = FOCUS_MIN_GAP_MS): boolean {
  return lastCheckedAt === null || now - lastCheckedAt >= minGapMs;
}
