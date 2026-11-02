import { afterEach, expect, it, vi } from "vitest";
import { observeChartViewport } from "./chartViewport";

afterEach(() => vi.unstubAllGlobals());
function setup() {
  let resized: () => void = () => {};
  let intersected: (entries: { isIntersecting: boolean }[]) => void = () => {};
  const frames = new Map<number, () => void>();
  let id = 0;
  const disconnectSize = vi.fn(), disconnectIntersection = vi.fn();
  vi.stubGlobal("ResizeObserver", class {
    constructor(cb: () => void) { resized = cb; }
    observe() {} disconnect = disconnectSize;
  });
  vi.stubGlobal("IntersectionObserver", class {
    constructor(cb: typeof intersected) { intersected = cb; }
    observe() {} disconnect = disconnectIntersection;
  });
  vi.stubGlobal("requestAnimationFrame", (cb: () => void) => { frames.set(++id, cb); return id; });
  vi.stubGlobal("cancelAnimationFrame", (key: number) => frames.delete(key));
  const bounds = { width: 800, height: 420 };
  const element = { getBoundingClientRect: () => bounds } as HTMLElement;
  const fitContent = vi.fn(), resize = vi.fn();
  const controller = observeChartViewport(element, { resize, timeScale: () => ({ fitContent }) });
  return { controller, bounds, resize, fitContent, disconnectSize, disconnectIntersection,
    size: () => resized(), visible: (isIntersecting: boolean) => intersected([{ isIntersecting }]),
    flush: () => { const work = [...frames.values()]; frames.clear(); work.forEach(cb => cb()); } };
}

it("waits for visible nonzero layout before fitting historical data", () => {
  const t = setup();
  t.controller.fitWhenVisible(); t.size(); t.flush();
  expect(t.resize).not.toHaveBeenCalled();
  t.bounds.width = 0; t.visible(true); t.flush();
  expect(t.fitContent).not.toHaveBeenCalled();
  t.bounds.width = 800; t.size(); t.flush();
  expect(t.resize).toHaveBeenCalledWith(800, 420, true);
  expect(t.fitContent).toHaveBeenCalledTimes(1);
});

it("repaints on re-entry and resize while preserving the user's chosen range", () => {
  const t = setup();
  t.controller.fitWhenVisible(); t.visible(true); t.flush();
  t.visible(false); t.flush(); t.visible(true); t.flush();
  t.bounds.width = 640; t.size(); t.flush();
  expect(t.resize).toHaveBeenLastCalledWith(640, 420, true);
  expect(t.fitContent).toHaveBeenCalledTimes(1);
});

it("disconnects observers and cancels pending work before chart removal", () => {
  const t = setup();
  t.visible(true); t.controller.close(); t.flush(); t.size(); t.flush();
  expect(t.disconnectSize).toHaveBeenCalledOnce();
  expect(t.disconnectIntersection).toHaveBeenCalledOnce();
  expect(t.resize).not.toHaveBeenCalled();
});
