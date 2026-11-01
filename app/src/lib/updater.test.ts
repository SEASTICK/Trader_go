import { describe, expect, it, vi } from "vitest";
import { checkForUpdate, downloadUpdate, installReady, shouldCheckOnFocus, snoozeUpdate, text, type UpdateHandle, type UpdaterDeps } from "./updater";
import { compareVersions, isNewerVersion, readSnooze, shouldPromptForUpdate, UPDATE_SNOOZE_MS } from "./version";

function memory(): UpdaterDeps["storage"] {
  const data = new Map<string, string>();
  return { getItem: k => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v), removeItem: k => void data.delete(k) };
}
function handle(version: string, download: NonNullable<UpdateHandle["download"]> = async () => {}, install: NonNullable<UpdateHandle["install"]> = vi.fn(async () => {})): UpdateHandle {
  return { version, body: " Anteckningar ", date: "2026-11-01T10:00:00Z", downloadAndInstall: async () => {}, download, install, close: vi.fn(async () => {}) };
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
  it("en version utan fil för den här plattformen sägs rakt ut", async () => {
    const raw = "None of the fallback platforms `[\"darwin-aarch64-app\", \"darwin-aarch64\"]` were found in the response `platforms` object";
    const r = await checkForUpdate(deps(async () => { throw raw; }), "0.1.0");
    expect(r).toMatchObject({ kind: "error", message: text.error.platform, detail: raw });
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

describe("downloadUpdate och installReady", () => {
  it("hämtar i bakgrunden och rapporterar framsteg utan att installera", async () => {
    const install = vi.fn(async () => {});
    const seen: (number | null)[] = [];
    const d = deps(async () => handle("0.2.0", async onEvent => {
      onEvent?.({ event: "Started", data: { contentLength: 100 } });
      onEvent?.({ event: "Progress", data: { chunkLength: 50 } });
      onEvent?.({ event: "Finished" });
    }, install));
    const r = await downloadUpdate(d, "0.1.0", f => seen.push(f));
    expect(r.ok && r.ready.version).toBe("0.2.0");
    expect(seen).toEqual([0, 0.5, 1]);
    expect(install).not.toHaveBeenCalled();
    expect(d.relaunch).not.toHaveBeenCalled();
  });
  it("en uppdatering med ogiltig signatur blir ett fel och kan inte installeras", async () => {
    const install = vi.fn(async () => {});
    const d = deps(async () => handle("0.2.0", async () => { throw "the signature verification failed: Invalid signature"; }, install));
    const r = await downloadUpdate(d, "0.1.0", () => {});
    expect(r).toMatchObject({ ok: false, message: text.error.signature });
    expect(install).not.toHaveBeenCalled();
  });
  it("utan nät blir det ett begripligt fel, inget kraschar", async () => {
    const r = await downloadUpdate(deps(async () => { throw new Error("error sending request: dns error"); }), "0.1.0", () => {});
    expect(r).toMatchObject({ ok: false, message: text.error.networkCheck });
  });
  it("hämtar inte om uppdateringen försvunnit eller är äldre", async () => {
    expect(await downloadUpdate(deps(async () => null), "0.1.0", () => {})).toMatchObject({ ok: false, message: text.error.gone });
    const download = vi.fn(async () => {});
    expect((await downloadUpdate(deps(async () => handle("0.0.9", download)), "0.1.0", () => {})).ok).toBe(false);
    expect(download).not.toHaveBeenCalled();
  });
  it("installerar och startar om först när installReady anropas", async () => {
    const install = vi.fn(async () => {});
    const d = deps(async () => handle("0.2.0", async () => {}, install));
    const r = await downloadUpdate(d, "0.1.0", () => {});
    if (!r.ok) throw new Error("expected a ready update");
    const phases: string[] = [];
    expect(await installReady(r.ready, d, p => phases.push(p.phase))).toEqual({ ok: true });
    expect(install).toHaveBeenCalledOnce();
    expect(d.relaunch).toHaveBeenCalledOnce();
    expect(phases).toEqual(["install", "restart"]);
  });
  it("fel vid installation startar inte om", async () => {
    const d = deps(async () => handle("0.2.0", async () => {}, async () => { throw new Error("permission denied"); }));
    const r = await downloadUpdate(d, "0.1.0", () => {});
    if (!r.ok) throw new Error("expected a ready update");
    expect(await installReady(r.ready, d, () => {})).toEqual({ ok: false, message: text.error.install });
    expect(d.relaunch).not.toHaveBeenCalled();
  });
  it("fel vid omstart är inte ett installationsfel", async () => {
    const d = deps(async () => handle("0.2.0"), { relaunch: async () => { throw new Error("redan omstartad"); } });
    const r = await downloadUpdate(d, "0.1.0", () => {});
    if (!r.ok) throw new Error("expected a ready update");
    expect(await installReady(r.ready, d, () => {})).toEqual({ ok: true });
  });
});

describe("beforeInstall (#6) med tvåstegsflödet", () => {
  it("hämtning i bakgrunden kör inte spärren, installationen gör det och stoppas", async () => {
    const install = vi.fn(async () => {});
    const before = vi.fn(async () => "Uppdateringen installeras när 1 papperssession(er) har avslutats.");
    const d = deps(async () => handle("0.2.0", async () => {}, install), { beforeInstall: before });
    const r = await downloadUpdate(d, "0.1.0", () => {});
    if (!r.ok) throw new Error("hämtningen borde lyckas");
    expect(before).not.toHaveBeenCalled();          // ingen spärr eller backup vid bakgrundshämtning
    const out = await installReady(r.ready, d, () => {});
    expect(out).toEqual({ ok: false, message: "Uppdateringen installeras när 1 papperssession(er) har avslutats." });
    expect(before).toHaveBeenCalledOnce();
    expect(install).not.toHaveBeenCalled();
    expect(d.relaunch).not.toHaveBeenCalled();
  });

  it("säkerhetskopian tas före install och omstart när spärren godkänner", async () => {
    const order: string[] = [];
    const install = vi.fn(async () => { order.push("install"); });
    const d = deps(async () => handle("0.2.0", async () => {}, install), {
      beforeInstall: async () => { order.push("backup"); return null; },
      relaunch: async () => { order.push("relaunch"); },
    });
    const r = await downloadUpdate(d, "0.1.0", () => {});
    if (!r.ok) throw new Error("hämtningen borde lyckas");
    expect(await installReady(r.ready, d, () => {})).toEqual({ ok: true });
    expect(order).toEqual(["backup", "install", "relaunch"]);
  });
});

describe("shouldCheckOnFocus", () => {
  it("kontrollerar första gången och efter tio minuter, inte däremellan", () => {
    expect(shouldCheckOnFocus(null, 1_000)).toBe(true);
    expect(shouldCheckOnFocus(1_000, 1_000 + 9 * 60_000)).toBe(false);
    expect(shouldCheckOnFocus(1_000, 1_000 + 10 * 60_000)).toBe(true);
  });
});
