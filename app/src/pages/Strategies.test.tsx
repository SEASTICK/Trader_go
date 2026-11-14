// @vitest-environment happy-dom
// Strategiväljaren i Resultat: välj en strategi, se detaljer, valet sparas och appen erbjuder aldrig en order.
import { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import experiments from "../../data/experiments.json";
import results from "../../data/results.json";
import { fromResult, type Experiment, type RealResult } from "../lib/experiments";
import Strategies from "./Strategies";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const real = results as unknown as Record<string, RealResult>;
const computed = (experiments as Experiment[]).filter((e) => real[e.id]?.source === "HISTORIK").map((e) => fromResult(e, real[e.id]));
let host: HTMLDivElement; let root: Root;
beforeEach(() => { localStorage.clear(); host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host); });
afterEach(() => { act(() => root.unmount()); host.remove(); vi.restoreAllMocks(); });
const item = (id: string) => [...host.querySelectorAll<HTMLButtonElement>(".strat-item")].find((b) => b.textContent?.startsWith(id))!;
const detail = () => host.querySelector(".strat-detail")?.textContent ?? "";

describe("Strategier", () => {
  it("listar strategierna och visar den valda", async () => {
    const open = vi.fn();
    await act(async () => { root.render(<Strategies results={computed} onOpenResult={open} />); });
    expect(host.querySelectorAll(".strat-item").length).toBeGreaterThan(20);
    await act(async () => { item("H-0001").click(); });
    expect(item("H-0001").getAttribute("aria-pressed")).toBe("true");
    expect(detail()).toContain("BTC 4h");
    expect(detail()).toContain("Körs inte på papper");
    expect(localStorage.getItem("strategy")).toBe("H-0001");
    const btn = [...host.querySelectorAll("button")].find((b) => b.textContent === "Öppna hela resultatet")!;
    await act(async () => { btn.click(); });
    expect(open).toHaveBeenCalledWith("E-01");
  });
  it("minns valet och visar 13F-observationen med länk till Papper", async () => {
    localStorage.setItem("strategy", "H-0016");
    const goPaper = vi.fn();
    await act(async () => { root.render(<Strategies results={computed} onOpenResult={() => {}} goPaper={goPaper} />); });
    expect(detail()).toContain("Följs på papper");
    expect(detail()).toContain("inte som ett godkänt test");
    const btn = [...host.querySelectorAll("button")].find((b) => b.textContent === "Visa på Papper")!;
    await act(async () => { btn.click(); });
    expect(goPaper).toHaveBeenCalled();
  });
  it("har ingen knapp som köper, säljer eller startar handel", async () => {
    await act(async () => { root.render(<Strategies results={computed} onOpenResult={() => {}} />); });
    const labels = [...host.querySelectorAll("button:not(.strat-item)")].map((b) => b.textContent?.toLowerCase() ?? "");
    expect(labels.some((l) => /köp|sälj|order|starta handel|live/.test(l))).toBe(false);
  });
});
