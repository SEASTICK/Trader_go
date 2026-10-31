import { useEffect, useRef, useState } from "react";
import type { UpdateNotice } from "./useUpdater";

type Props = { notice: UpdateNotice; currentVersion: string; onInstall: () => void; onLater: () => void; onDismissError: () => void };

/** "Ny version av Trader_go finns". Går inte att stänga mitt i en installation. */
export function UpdateDialog({ notice, currentVersion, onInstall, onLater, onDismissError }: Props) {
  const [showNotes, setShowNotes] = useState(false);
  const primary = useRef<HTMLButtonElement>(null);
  const visible = !!notice.promptOpen && !!notice.version && (notice.status === "available" || notice.status === "installing" || notice.status === "error");
  const installing = notice.status === "installing";
  const failed = notice.status === "error";

  useEffect(() => { if (visible) primary.current?.focus(); }, [visible, notice.status]);
  useEffect(() => {
    if (!visible || installing) return;
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") (failed ? onDismissError : onLater)(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [visible, installing, failed, onLater, onDismissError]);

  if (!visible) return null;
  const percent = notice.progress != null ? Math.round(notice.progress * 100) : null;

  return (
    <div className="overlay" role="presentation">
      <div className="modal update-dialog" role="dialog" aria-modal="true" aria-labelledby="update-title">
        <div className="update-body">
          <span className="k">Uppdatering</span>
          <h2 id="update-title">Ny version finns <span className="version-tag">v{notice.version}</span></h2>
          <p className="muted">
            {failed || installing ? notice.message : `Du kör v${currentVersion}. Programmet startar om efter installationen.`}
          </p>
          {installing && (
            <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent ?? undefined}>
              <i style={{ width: percent != null ? `${percent}%` : "35%" }} />
            </div>
          )}
          {!installing && !failed && showNotes && (
            <div className="notes">{notice.notes ? <pre>{notice.notes}</pre> : <p className="muted">Inga anteckningar för den här versionen.</p>}</div>
          )}
          <div className="update-actions">
            {failed ? (
              <>
                <button type="button" className="btn accent" ref={primary} onClick={onInstall}>Försök igen</button>
                <button type="button" className="btn" onClick={onDismissError}>Stäng</button>
              </>
            ) : (
              <>
                <button type="button" className="btn accent" ref={primary} disabled={installing} onClick={onInstall}>{installing ? "Uppdaterar…" : "Installera nu"}</button>
                <button type="button" className="btn" disabled={installing} onClick={onLater}>Senare</button>
                {!installing && <button type="button" className="link" aria-expanded={showNotes} onClick={() => setShowNotes(v => !v)}>Vad är nytt?</button>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
