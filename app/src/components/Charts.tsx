import { useEffect, useRef, useState } from "react";

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((e) => setW(Math.max(200, Math.floor(e[0].contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

export function Sparkline({ data, w = 84, h = 26 }: { data: number[]; w?: number; h?: number }) {
  const min = Math.min(...data), max = Math.max(...data);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - 2 - ((v - min) / (max - min || 1)) * (h - 4)}`);
  return (
    <svg width={w} height={h} className="spark" aria-hidden="true">
      <polyline points={pts.join(" ")} fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 2" strokeLinejoin="round" />
    </svg>
  );
}

/** Liten yta-kurva för kort (inga axlar). Huvudserien som fylld yta, jämförelseserien streckad. Beskrivs för skärmläsare via `label`. */
export function AreaSpark({ main, other, label, h = 72 }: { main: number[]; other?: number[]; label: string; h?: number }) {
  const all = [...main, ...(other ?? [])].filter(Number.isFinite);
  if (main.length < 2 || !all.length) return null;
  const w = 320, lo = Math.min(...all), hi = Math.max(...all), span = hi - lo || 1;
  const X = (i: number, n: number) => (i / (n - 1)) * w;
  const Y = (v: number) => 4 + (1 - (v - lo) / span) * (h - 8);
  const line = (d: number[]) => d.map((v, i) => `${i ? "L" : "M"}${X(i, d.length).toFixed(1)},${Y(v).toFixed(1)}`).join("");
  return (
    <svg className="area-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="img" aria-label={label}>
      <defs><linearGradient id="spark-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="var(--accent)" stopOpacity="0.22" /><stop offset="100%" stopColor="var(--accent)" stopOpacity="0" /></linearGradient></defs>
      <path d={`${line(main)}L${w},${h}L0,${h}Z`} fill="url(#spark-fill)" />
      {other && other.length > 1 && <path d={line(other)} className="spark-other" vectorEffect="non-scaling-stroke" />}
      <path d={line(main)} className="spark-main" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

type Series = { name: string; data: number[]; cls: string };

/** Y-axelns domän. En konstant serie (platt kapital, drawdown som alltid är noll) får ett eget intervall runt
 *  värdet, så att linjen ritas med ändliga koordinater i stället för att dela med noll. */
export function chartDomain(values: number[]): [number, number] {
  const finite = values.filter(Number.isFinite);
  if (!finite.length) return [0, 1];
  const min = Math.min(...finite), max = Math.max(...finite);
  const pad = max > min ? (max - min) * 0.08 : Math.max(Math.abs(max) * 0.05, 1);
  const lo = min >= 0 ? Math.max(0, min - pad) : min - pad;  // kapital kan inte bli negativt
  return [lo, max + pad];
}

export function LineChart({ series, labels, height = 280, watermark = null }: { series: Series[]; labels: string[]; height?: number; watermark?: string | null }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const padL = 8, padR = 52, padT = 12, padB = 26;
  const [lo, hi] = chartDomain(series.flatMap((s) => s.data));
  const n = series[0].data.length;
  const x = (i: number) => padL + (n > 1 ? i / (n - 1) : 0) * (width - padL - padR);
  const y = (v: number) => padT + (1 - (v - lo) / (hi - lo)) * (height - padT - padB);
  const path = (d: number[]) => d.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const ticks = [0, 1, 2, 3].map((k) => lo + ((hi - lo) * k) / 3);
  const xt = [0, 0.25, 0.5, 0.75, 1].map((f) => Math.round(f * (n - 1)));
  const main = series[0];
  return (
    <div ref={ref} className="chart" style={{ height }}>
      <svg width={width} height={height}
        onMouseMove={(e) => {
          const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const f = (e.clientX - r.left - padL) / (width - padL - padR);
          setHover(Math.min(n - 1, Math.max(0, Math.round(f * (n - 1)))));
        }}
        onMouseLeave={() => setHover(null)}>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={padL} x2={width - padR} y1={y(t)} y2={y(t)} className="grid" />
            <text x={width - padR + 8} y={y(t) + 4} className="axis">{t.toFixed(0)}</text>
          </g>
        ))}
        {xt.map((i, k) => <text key={k} x={x(i)} y={height - 6} textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"} className="axis">{labels[i]}</text>)}
        <defs>
          <linearGradient id="fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.18" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${path(main.data)}L${x(n - 1)},${height - padB}L${x(0)},${height - padB}Z`} fill="url(#fill)" />
        {series.slice().reverse().map((s) => <path key={s.name} d={path(s.data)} className={`line ${s.cls}`} />)}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={padT} y2={height - padB} className="cross" />
            {series.map((s) => <circle key={s.name} cx={x(hover)} cy={y(s.data[hover])} r="4" className={`dot ${s.cls}`} />)}
          </g>
        )}
      </svg>
      {watermark && <div className="watermark">{watermark}</div>}
      {hover !== null && (
        <div className="tip" style={{ left: Math.min(width - 170, Math.max(0, x(hover) + 12)) }}>
          <div className="tip-date">{labels[hover]}</div>
          {series.map((s) => (
            <div key={s.name} className="tip-row"><span className={`swatch ${s.cls}`} />{s.name}<b>{s.data[hover].toFixed(1)}</b></div>
          ))}
        </div>
      )}
    </div>
  );
}
