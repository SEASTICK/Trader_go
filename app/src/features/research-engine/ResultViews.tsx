import { LineChart } from "../../components/Charts";
import type { Result } from "./api";

export function number(value: unknown, percent = false) {
  return typeof value === "number" && Number.isFinite(value)
    ? (percent ? (value * 100).toLocaleString("sv-SE", {minimumFractionDigits:2,maximumFractionDigits:2}) + " %" : value.toLocaleString("sv-SE", { maximumFractionDigits: 2 })) : "—";
}
export function Chart({ curve, baseline, drawdown = false }: { curve: Result["curves"]; baseline?: Result["curves"]; drawdown?: boolean }) {
  const data = drawdown ? curve.drawdown.map(v => v * 100) : curve.equity.map(v => v * 100000);
  const other = baseline?.equity.map(v => v * 100000);
  const all = [...data, ...(other ?? [])];
  if (data.length < 2 || !all.every(Number.isFinite)) return <p>Diagramdata saknas.</p>;
  if (Math.max(...all) === Math.min(...all)) return <p>Oförändrad kurva: {number(data[0])}{drawdown ? " %" : ""}</p>;
  return <LineChart labels={curve.t.map(t => t.slice(0, 10))} watermark={null}
    series={[{ name: drawdown ? "Drawdown (%)" : "Kapital (start 100 000)", data, cls: "s1" },
      ...(other && other.length === data.length ? [{ name: "Köp och behåll", data: other, cls: "s2" }] : [])]} />;
}

