import { invoke as tauriInvoke } from "@tauri-apps/api/core";
import { listen as tauriListen } from "@tauri-apps/api/event";

// Bara för prestandamätningen i perf/ (webbläsare utan Tauri): en låtsas-backend kan sättas på window.
// I appen finns den aldrig, och då används Tauri som vanligt.
type Mock = { invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown>; listen: (name: string, cb: (e: { payload: unknown }) => void) => () => void };
const mock = (): Mock | undefined => (globalThis as { __UNIVERSE_MOCK__?: Mock }).__UNIVERSE_MOCK__;

export const invoke = <T,>(cmd: string, args?: Record<string, unknown>) => {
  const m = mock();
  return m ? (m.invoke(cmd, args) as Promise<T>) : tauriInvoke<T>(cmd, args);
};
export const listen = <T,>(name: string, cb: (e: { payload: T }) => void) => {
  const m = mock();
  return m ? Promise.resolve(m.listen(name, cb as (e: { payload: unknown }) => void)) : tauriListen<T>(name, cb);
};
