import { useEffect, useState } from "react";
import type { LaunchKind } from "../lib/launch";

// Dekorativ kurva i introt. Den är en symbol, inte data: inga axlar, siffror eller procent.
const LINE = "M0,72 L28,64 L52,68 L80,50 L104,56 L134,38 L158,44 L188,26 L212,32 L242,14 L280,18";
const AREA = `${LINE} L280,90 L0,90 Z`;

type Props = { kind: LaunchKind; version: string; previous: string | null; reduced: boolean; onDone: () => void };

/** Startbild när appen öppnas, och en bekräftelse när den just har uppdaterats. Klick eller Esc hoppar över. */
export function Intro({ kind, version, previous, reduced, onDone }: Props) {
  const [leaving, setLeaving] = useState(false);
  const update = kind === "update";

  useEffect(() => {
    const leave = () => setLeaving(true);
    const t = window.setTimeout(leave, reduced ? (update ? 2500 : 0) : update ? 4200 : 1900);
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" || e.key === "Enter") leave(); };
    window.addEventListener("keydown", onKey);
    return () => { window.clearTimeout(t); window.removeEventListener("keydown", onKey); };
  }, [reduced, update]);

  useEffect(() => {
    if (!leaving) return;
    const t = window.setTimeout(onDone, reduced ? 0 : 380);
    return () => window.clearTimeout(t);
  }, [leaving, reduced, onDone]);

  return (
    <div className={`intro${leaving ? " leaving" : ""}${update ? " is-update" : ""}`} role="status" aria-live="polite"
      onClick={() => setLeaving(true)}>
      <div className="intro-card">
        {update ? (
          <svg className="intro-check" viewBox="0 0 64 64" aria-hidden="true">
            <circle cx="32" cy="32" r="28" pathLength={1} />
            <path d="M20 33 L29 42 L45 24" pathLength={1} />
          </svg>
        ) : (
          <img src="/logo.svg" className="intro-logo" alt="" />
        )}
        <svg className="intro-chart" viewBox="0 0 280 90" aria-hidden="true">
          <defs>
            <linearGradient id="intro-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="var(--accent)" stopOpacity=".28" />
              <stop offset="1" stopColor="var(--accent)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path className="intro-area" d={AREA} fill="url(#intro-fill)" />
          <path className="intro-line" d={LINE} pathLength={1} />
          <circle className="intro-dot" cx="280" cy="18" r="4" />
        </svg>
        {update ? (
          <>
            <h1 className="intro-title">Uppdaterad till <span className="intro-version">v{version}</span></h1>
            <p className="intro-sub">{previous ? `Från v${previous}. ` : ""}Trader_go är redo. Fortfarande bara papper, inga riktiga pengar.</p>
            <button type="button" className="btn accent intro-btn" onClick={(e) => { e.stopPropagation(); setLeaving(true); }}>Fortsätt</button>
          </>
        ) : (
          <>
            <h1 className="intro-title">Trader_go</h1>
            <p className="intro-sub">Papper · inga riktiga pengar</p>
          </>
        )}
      </div>
    </div>
  );
}
