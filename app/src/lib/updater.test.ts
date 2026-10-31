import { describe, expect, it, vi } from "vitest";
import { checkForUpdate, installUpdate, shouldCheckOnFocus, snoozeUpdate, text, type UpdateHandle, type UpdaterDeps } from "./updater";
import { compareVersions, isNewerVersion, readSnooze, shouldPromptForUpdate, UPDATE_SNOOZE_MS } from "./version";

function memory(): UpdaterDeps["storage"] {
  const data = new Map<string, string>();
  return { getItem: k => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v), removeItem: k => void data.delete(k) };
}
function handle(version: string, install: UpdateHandle["downloadAndInstall"] = async () => {}): UpdateHandle {
  return { version, body: " Anteckningar ", date: "2026-11-01T10:00:00Z", downloadAndInstall: install, close: vi.fn(async () => {}) };
}
function deps(check: UpdaterDeps["check"], extra: Partial<UpdaterDeps> = {}): UpdaterDeps {
  return { check, relaunch: vi.fn(async () => {}), storage: memory(), now: () => 1_000, ...extra };
}

describe("version", () => {
  it("jämför semver", () => {
    expect(compareVersions("0.1.1", "0.1.0")).toBe(1);
    expect(compareVersions("0.1.0", "0.1.0")).toBe(0);
    expect(compareVersions("0.9.0", "0.10.0")).toBe(-1);
    expect(compareVersions("v1.0.0", "1.0.0-rc.1")).toBe(1);
    expect(compareVersions("abc", "1.0.0")).toBeNull();
  });
  it("erbjuder aldrig samma, äldre eller okänd version", () => {
    expect(isNewerVersion("0.1.0", "0.1.0")).toBe(false);
    expect(isNewerVersion("0.0.9", "0.1.0")).toBe(false);
    expect(isNewerVersion("nonsens", "0.1.0")).toBe(false);
    expect(isNewerVersion("0.1.1", "0.1.0")).toBe(true);
  });
  it("Senare gäller en version i ett dygn, en nyare version frågar direkt", () => {
    const snooze = { version: "0.2.0", untilUnixMs: 10_000 };
    expect(shouldPromptForUpdate("0.2.0", "0.1.0", snooze, 5_000)).toBe(false);
    expect(shouldPromptForUpdate("0.2.0", "0.1.0", snooze, 10_000)).toBe(true);
    expect(shouldPromptForUpdate("0.2.1", "0.1.0", snooze, 5_000)).toBe(true);
    expect(shouldPromptForUpdate(null, "0.1.0", null, 0)).toBe(false);
  });
  it("läser ogiltig uppskjutning som ingen", () => {
    const s = memory();
    s.setItem("trader_go.updateSnooze", "{inte json");
    expect(readSnooze(s)).toBeNull();
  });
});

describe("checkForUpdate", () => {
  it("ingen uppdatering ger current", async () => {
    expect(await checkForUpdate(deps(async () => null), "0.1.0")).toEqual({ kind: "current" });
  });
  it("nyare version ger available med trimmade anteckningar", async () => {
    const r = await checkForUpdate(deps(async () => handle("0.2.0")), "0.1.0");
    expect(r).toMatchObject({ kind: "available", version: "0.2.0", notes: "Anteckningar", prompt: true });
  });
  it("samma eller äldre version ignoreras", async () => {
    expect(await checkForUpdate(deps(async () => handle("0.1.0")), "0.1.0")).toEqual({ kind: "current" });
    expect(await checkForUpdate(deps(async () => handle("0.0.5")), "0.1.0")).toEqual({ kind: "current" });
  });
  it("nätverksfel blir ett begripligt felmeddelande", async () => {
    const r = await checkForUpdate(deps(async () => { throw new Error("request failed: timeout"); }), "0.1.0");
    expect(r).toMatchObject({ kind: "error", message: text.error.networkCheck, detail: "request failed: timeout" });
  });
  it("signaturfel blir ett eget meddelande", async () => {
    const r = await checkForUpdate(deps(async () => { throw "signature verification failed"; }), "0.1.0");
    expect(r).toMatchObject({ kind: "error", message: text.error.signature, detail: "signature verification failed" });
  });
  it("Senare undertrycker frågan men inte uppdateringen", async () => {
    const storage = memory();
    snoozeUpdate(storage, "0.2.0", 1_000);
    const r = await checkForUpdate(deps(async () => handle("0.2.0"), { storage, now: () => 1_000 + UPDATE_SNOOZE_MS - 1 }), "0.1.0");
    expect(r).toMatchObject({ kind: "available", prompt: false });
  });
});

describe("installUpdate", () => {
  it("installerar inte när beforeInstall stoppar (pågående session)", async () => {
    const install = vi.fn(async () => {});
    const h = handle("0.2.0", install);
    const d = deps(async () => h, { beforeInstall: async () => "Uppdateringen installeras när 1 papperssession(er) har avslutats." });
    const r = await installUpdate(d, "0.1.0", () => {});
    expect(r).toEqual({ ok: false, message: "Uppdateringen installeras när 1 papperssession(er) har avslutats." });
    expect(install).not.toHaveBeenCalled();
    expect(h.close).toHaveBeenCalled();
  });
  it("installerar när beforeInstall godkänner", async () => {
    const d = deps(async () => handle("0.2.0"), { beforeInstall: async () => null });
    expect(await installUpdate(d, "0.1.0", () => {})).toEqual({ ok: true });
  });

  it("hämtar, rapporterar framsteg och startar om", async () => {
    const phases: string[] = [];
    const d = deps(async () => handle("0.2.0", async onEvent => {
      onEvent?.({ event: "Started", data: { contentLength: 100 } });
      onEvent?.({ event: "Progress", data: { chunkLength: 50 } });
      onEvent?.({ event: "Finished" });
    }));
    const r = await installUpdate(d, "0.1.0", p => phases.push(p.phase === "download" ? `download:${p.fraction}` : p.phase));
    expect(r).toEqual({ ok: true });
    expect(phases).toEqual(["download:0", "download:0.5", "install", "restart"]);
    expect(d.relaunch).toHaveBeenCalledOnce();
  });
  it("installerar inte om uppdateringen försvunnit", async () => {
    const d = deps(async () => null);
    expect(await installUpdate(d, "0.1.0", () => {})).toEqual({ ok: false, message: text.error.gone });
    expect(d.relaunch).not.toHaveBeenCalled();
  });
  it("installerar aldrig en äldre version", async () => {
    const install = vi.fn(async () => {});
    const d = deps(async () => handle("0.0.9", install));
    expect((await installUpdate(d, "0.1.0", () => {})).ok).toBe(false);
    expect(install).not.toHaveBeenCalled();
  });
  it("fel vid hämtning startar inte om", async () => {
    const d = deps(async () => handle("0.2.0", async () => { throw new Error("network down"); }));
    const r = await installUpdate(d, "0.1.0", () => {});
    expect(r).toEqual({ ok: false, message: text.error.networkInstall });
    expect(d.relaunch).not.toHaveBeenCalled();
  });
  it("fel vid omstart är inte ett installationsfel", async () => {
    const d = deps(async () => handle("0.2.0"), { relaunch: async () => { throw new Error("redan omstartad"); } });
    expect(await installUpdate(d, "0.1.0", () => {})).toEqual({ ok: true });
  });
});

describe("shouldCheckOnFocus", () => {
  it("kontrollerar första gången och efter tio minuter, inte däremellan", () => {
    expect(shouldCheckOnFocus(null, 1_000)).toBe(true);
    expect(shouldCheckOnFocus(1_000, 1_000 + 9 * 60_000)).toBe(false);
    expect(shouldCheckOnFocus(1_000, 1_000 + 10 * 60_000)).toBe(true);
  });
});
