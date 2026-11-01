import { invoke as tauriInvoke } from "@tauri-apps/api/core";
import { listen as tauriListen } from "@tauri-apps/api/event";

export const invoke = <T,>(cmd: string, args?: Record<string, unknown>) => tauriInvoke<T>(cmd, args);
export const listen = <T,>(name: string, cb: (e: { payload: T }) => void) => tauriListen<T>(name, cb);
