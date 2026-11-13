// @vitest-environment happy-dom
// Navigeringen: högst fyra huvudval, resten under "Mer". Startsidan visar bara riktig status och döljer inga fel.
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App, { MORE, NAV } from "./App";
import Overview from "./pages/Overview";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
Object.assign(globalThis, { __APP_VERSION__: "0.0.0", __COMMIT__: "abc1234", __COMMIT_MSG__: "", __BUILT_AT__: new Date().toISOString(), __UPDATE_FEED__: "", __UPDATE_CHANNEL__: "stable" });
let host: HTMLDivElement; let root: Root;
beforeEach(() => {
  host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host);
  vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("reduce"), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }));
});
afterEach(() => { act(() => root.unmount()); host.remove(); vi.unstubAllGlobals(); });
const text = () => host.textContent ?? "";

describe("navigering", () => {
  it("har högst fyra huvudval och lägger avancerat under Mer", () => {
    expect(NAV.map((n) => n.id)).toEqual(["Hem", "Resultat", "Papper", "Marknad"]);
    expect(NAV.length).toBeLessThanOrEqual(4);
    expect(MORE.map((m) => m.id)).toEqual(["Research Lab", "Status"]);
  });
  it("visar fyra huvudval plus Mer, och Mer öppnar Research Lab, Status och inställningar", async () => {
    await act(async () => { root.render(<App />); });
    const navButtons = [...host.querySelectorAll("nav button")].map((b) => b.textContent?.trim());
    expect(navButtons.length).toBe(4);
    const mer = [...host.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Mer") as HTMLButtonElement;
    expect(mer).toBeTruthy();
    await act(async () => { mer.click(); });
    const items = [...host.querySelectorAll('[role="menuitem"]')].map((b) => b.textContent?.trim());
    expect(items).toEqual(expect.arrayContaining(["Research Lab", "Status"]));
    expect(text()).toContain("Inställningar");
  });
  it("visar inte byggcommit i den globala toppraden, men alltid att inga riktiga pengar används", async () => {
    await act(async () => { root.render(<App />); });
    const top = host.querySelector(".topbar")?.textContent ?? "";
    expect(top).toContain("inga riktiga pengar");
    expect(top).not.toContain("abc1234");
  });
});

describe("startsidan", () => {
  const render = async (now: Date) => { await act(async () => { root.render(<Overview go={() => {}} now={now} />); }); };
  it("svarar med tre mått och en huvudhandling, och säger REJECT på enkel svenska", async () => {
    await render(new Date("2026-11-10T12:00:00Z"));
    expect(host.querySelectorAll(".stat").length).toBe(3);
    expect(host.querySelectorAll(".btn.accent").length).toBe(1);
    expect(text()).toContain("klarade inte kraven");
    // Utanför "Visa detaljer" finns varken registerord, hypotes-id eller t-värden.
    const visible = (host.cloneNode(true) as HTMLElement); visible.querySelector("details")?.remove();
    expect(visible.textContent).not.toMatch(/\bREJECT\b|H-00\d\d|t-värde|commit/i);
  });
  it("visar ogiltiga försök öppet och räknar dem aldrig som godkända", async () => {
    await render(new Date("2026-11-10T12:00:00Z"));
    expect(host.querySelector(".note.warn")?.textContent).toMatch(/kunde inte avgöras/);
    expect(host.querySelector(".note.warn")?.textContent).toMatch(/aldrig som godkända/);
  });
  it("varnar tydligt när papperdatan är gammal och visar annars att den är aktuell med datum", async () => {
    await render(new Date("2026-11-10T12:00:00Z"));
    expect(text()).toContain("Aktuell"); expect(text()).toContain("2026-11-09");
    await render(new Date("2026-12-20T12:00:00Z"));
    expect(host.querySelector('[role="alert"]')?.textContent).toMatch(/gammal/);
    expect(text()).toContain("Gammal");
  });
  it("lägger metod, livscykel och krav bakom Visa detaljer", async () => {
    await render(new Date("2026-11-10T12:00:00Z"));
    const more = host.querySelector("details.more") as HTMLDetailsElement;
    expect(more.open).toBe(false);
    expect(more.textContent).toContain("Så arbetar vi");
    expect(more.textContent).toContain("Krav på t-värde");
  });
});
