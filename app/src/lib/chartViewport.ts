/** Keep canvases sized and repaint when an offscreen chart first enters the viewport.
 * Own sizing (chart autoSize must be false), so there is only one resize owner.
 * Re-entry repaints without changing a zoom chosen by the user.
 */
export function observeChartViewport(
  element: HTMLElement,
  chart: { resize(width: number, height: number, forceRepaint?: boolean): void; timeScale(): { fitContent(): void; setVisibleLogicalRange(range: {from:number;to:number}): void } },
) {
  let visible = false;
  let pendingView: (() => void) | undefined;
  let frame: number | undefined;
  let closed = false;
  const schedule = () => {
    if (closed || frame !== undefined) return;
    frame = requestAnimationFrame(() => {
      frame = undefined;
      if (closed || !visible) return;
      const { width, height } = element.getBoundingClientRect();
      if (width < 1 || height < 1) return;
      chart.resize(Math.floor(width), Math.floor(height), true);
      if (pendingView) { pendingView(); pendingView = undefined; }
    });
  };
  const size = new ResizeObserver(schedule);
  const intersection = new IntersectionObserver(entries => {
    visible = entries.some(entry => entry.isIntersecting);
    if (visible) schedule();
  });
  size.observe(element);
  intersection.observe(element);
  return {
    fitWhenVisible() { pendingView = () => chart.timeScale().fitContent(); schedule(); },
    latestWhenVisible(count: number) {
      pendingView = () => chart.timeScale().setVisibleLogicalRange({from:Math.max(0,count-120),to:count+4});
      schedule();
    },
    close() {
      closed = true;
      size.disconnect();
      intersection.disconnect();
      if (frame !== undefined) cancelAnimationFrame(frame);
    },
  };
}
