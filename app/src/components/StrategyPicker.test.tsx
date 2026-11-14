// @vitest-environment happy-dom
// Strategiväljaren: alla registrerade strategier går att välja, med lättbegripligt namn, id och utfall ur registret.
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import registryMd from "../../../research/registry.md?raw";
import { groupRegistry, parseRegistry } from "../lib/registry";
import { STRATEGY_NAMES } from "../lib/strategyNames";
import { StrategyPicker, verdict } from "./StrategyPicker";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
beforeEach(() => { localStorage.clear(); host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); });

const all = groupRegistry(parseRegistry(registryMd));

describe("StrategyPicker", () => {
  it("listar varje registrerad hypotes en gång, med namn och id", () => {
    act(() => root.render(<StrategyPicker />));
    const opts = [...host.querySelectorAll("option")].map((o) => o.value);
    expect(new Set(opts).size).toBe(all.length);
    expect(opts.sort()).toEqual(all.map((h) => h.id).sort());
    for (const h of all) if (STRATEGY_NAMES[h.id]) expect([...host.querySelectorAll("option")].map((o) => o.textContent)).toContain(STRATEGY_NAMES[h.id].name);
    expect(host.textContent).not.toMatch(/\bREJECT\b|H-00\d\d|t-värde/);                // enkel svenska i första vyn
  });

  it("visar utfallet för vald strategi och kommer ihåg valet", () => {
    act(() => root.render(<StrategyPicker />));
    const select = host.querySelector("select")!;
    const target = all.find((h) => h.decision === "REJECT" && h.t !== null)!;
    act(() => { select.value = target.id; select.dispatchEvent(new Event("change", { bubbles: true })); });
    expect(host.textContent).toContain(STRATEGY_NAMES[target.id].name);
    expect(host.textContent).toContain("Klarade inte kraven");
    expect(host.textContent).toMatch(/under kravet|över kravet/);
    expect(localStorage.getItem("valdStrategi")).toBe(target.id);
    expect(host.querySelector("[data-id]")!.getAttribute("data-id")).toBe(target.id);   // spårbart till registret
  });

  it("läser t och krav även med beskrivning emellan (Pelosi, altcoins version B)", () => {
    const byId = Object.fromEntries(all.map((h) => [h.id, h]));
    expect([byId["H-0017"].t, byId["H-0017"].krav]).toEqual([1.43, 2.75]);
    expect([byId["H-0023"].t, byId["H-0023"].krav]).toEqual([1.37, 3.45]);
  });

  it("ogiltiga försök visas aldrig som godkända", () => {
    for (const h of all.filter((x) => x.invalid)) expect(verdict(h).label).toBe("Kunde inte avgöras");
    for (const h of all.filter((x) => x.decision === "REJECT")) expect(verdict(h).label).not.toMatch(/klarade testkraven/i);
  });

  it("knappen till resultaten anropar navigeringen", () => {
    let opened = 0;
    act(() => root.render(<StrategyPicker onOpenResults={() => { opened += 1; }} />));
    const btn = [...host.querySelectorAll("button")].find((b) => b.textContent === "Se alla resultat")!;
    act(() => btn.click());
    expect(opened).toBe(1);
  });
});
