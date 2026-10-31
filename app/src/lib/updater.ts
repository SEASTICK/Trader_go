/**
 * Uppdateringsflödet utan beroende av Tauri, så alla vägar går att testa.
 *
 * Kedjan i appen:
 *   1. check()            pluginen läser latest.json från den publika uppdateringssidan och verifierar
 *                         signaturen mot pubkey i tauri.conf.json.
 *   2. isNewerVersion     appen erbjuder bara en strikt nyare version.
 *   3. downloadAndInstall hämtar och installerar. Signaturen kontrolleras igen av pluginen.
 *   4. Omstart            Windows-installationen startar om appen själv (passiv installation).
 *
 * Före steg 3 anropas beforeInstall: datorprogrammet vägrar medan en papperssession eller ett
 * backtest pågår och säkerhetskopierar sin lokala databas (pappersaffärer, backtester).
 */
import { isNewerVersion, readSnooze, shouldPromptForUpdate, SNOOZE_KEY, UPDATE_SNOOZE_MS } from "./version";

export const text = {
  checking: "Söker efter uppdateringar…",
  upToDate: "Du har den senaste versionen.",
  phase: { download: "Hämtar uppdateringen…", install: "Installerar…", restart: "Startar om…" },
  error: {
    signature: "Uppdateringen kunde inte verifieras och installerades inte.",
    networkCheck: "Kunde inte söka efter uppdateringar. Kontrollera internetanslutningen.",
    networkInstall: "Hämtningen avbröts. Kontrollera internetanslutningen och försök igen.",
    check: "Uppdateringskontrollen misslyckades.",
    install: "Uppdateringen kunde inte installeras.",
    gone: "Uppdateringen finns inte längre. Sök igen om en stund.",
  },
};

export type UpdateHandle = {
  version: string;
  body?: string | null;
  date?: string | null;
  downloadAndInstall: (onEvent?: (event: DownloadEvent) => void) => Promise<void>;
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
  /** Null om installationen får fortsätta, annars ett meddelande till användaren. */
  beforeInstall?: () => Promise<string | null>;
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

/** Hämtar uppdateringen på nytt (en ny kontroll kan ha kommit) och kontrollerar att den fortfarande är nyare. */
export async function installUpdate(deps: UpdaterDeps, currentVersion: string, onProgress: (progress: InstallProgress) => void): Promise<InstallOutcome> {
  let handle: UpdateHandle | null;
  try { handle = await deps.check(); }
  catch (reason) { return { ok: false, message: describeUpdateError(reason, "check") }; }
  if (!handle || !isNewerVersion(handle.version, currentVersion)) return { ok: false, message: text.error.gone };
  const blocked = await deps.beforeInstall?.();
  if (blocked) {
    try { await handle.close?.(); } catch { /* ignoreras */ }
    return { ok: false, message: blocked };
  }

  try {
    let total = 0; let received = 0;
    await handle.downloadAndInstall(event => {
      if (event.event === "Started") { total = event.data.contentLength ?? 0; onProgress({ phase: "download", fraction: total ? 0 : null }); }
      else if (event.event === "Progress") { received += event.data.chunkLength; onProgress({ phase: "download", fraction: total ? Math.min(1, received / total) : null }); }
      else onProgress({ phase: "install" });
    });
  } catch (reason) { return { ok: false, message: describeUpdateError(reason, "install") }; }

  onProgress({ phase: "restart" });
  try { await deps.relaunch(); } catch { /* På Windows har installationen redan startat om appen. */ }
  return { ok: true };
}
