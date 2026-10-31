import { ReactNode } from "react";

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: T[]; onChange: (v: T) => void }) {
  return (
    <div className="segmented" role="tablist">
      {options.map((o) => (
        <button key={o} role="tab" aria-selected={o === value} className={o === value ? "on" : ""} onClick={() => onChange(o)}>{o}</button>
      ))}
    </div>
  );
}

export function StatusDot({ status }: { status: string }) {
  const tone = status === "REJECT" ? "bad" : status === "READY_FOR_PAPER" ? "good" : status === "Pågår" || status === "MORE_RESEARCH" ? "warn" : "idle";
  return <span className={`status ${tone}`}><i />{status}</span>;
}

export function Page({ title, sub, actions, children }: { title: string; sub?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <div className="page">
      <div className="page-head">
        <div><h1>{title}</h1>{sub && <p className="sub">{sub}</p>}</div>
        {actions && <div className="actions">{actions}</div>}
      </div>
      {children}
    </div>
  );
}

export function SimChip() {
  return <span className="chip-sim" title="Påhittad data som visar hur ett resultat kommer att se ut. Inget är verkligt.">SIMULERAD DATA</span>;
}
