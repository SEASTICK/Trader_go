// Låtsas-backend för att mäta Universes gränssnitt i en vanlig webbläsare. Ingen kod här går in i appen.
//   ?canvas=real   kartan i perf-utdatamappen (real.canvas, kopierad från appens datamapp)
//   ?n=3000        syntetisk karta med n filkort
type Payload = { payload: unknown };
const listeners = new Map<string, Set<(e: Payload) => void>>();
const params = new URLSearchParams(location.search);

function synthetic(n: number) {
  const nodes: Record<string, unknown>[] = [];
  const edges: Record<string, unknown>[] = [];
  const groups = 40;
  for (let g = 0; g < groups; g++) nodes.push({ id: `grp-${g}`, type: "group", label: `area${g}`, x: g * 1400, y: -50, width: 1300, height: Math.ceil(n / groups / 4) * 80 + 100 });
  for (let i = 0; i < n; i++) {
    const g = i % groups, k = Math.floor(i / groups);
    nodes.push({ id: `f-${i}`, type: "file", file: `area${g}/sub${k % 7}/n${i}.md`, x: g * 1400 + 30 + (k % 4) * 300, y: 50 * 0 + Math.floor(k / 4) * 80, width: 280, height: 60 });
  }
  for (let i = 0; i < n * 1.5; i++) {
    const a = i % n, b = (i * 7 + 13) % n, kind = ["g-e-", "g-d-", "g-i-"][i % 3];
    edges.push({ id: `${kind}${i}`, fromNode: `f-${a}`, toNode: `f-${b}`, label: kind === "g-e-" ? "länk" : kind === "g-d-" ? "import" : "nämner" });
  }
  return { nodes, edges };
}

let docPromise: Promise<unknown> = params.get("canvas") === "real"
  ? fetch("./real.canvas").then(r => r.json())
  : Promise.resolve(synthetic(Number(params.get("n") ?? 3000)));

const status = () => ({ state: "idle", root: "/perf", files: 0, edges: 0, unconnected: 0, last_run: Date.now(), by_kind: {}, broken: [] });
const calls: Record<string, number> = {};

(globalThis as Record<string, unknown>).__UNIVERSE_MOCK__ = {
  invoke: async (cmd: string) => {
    calls[cmd] = (calls[cmd] ?? 0) + 1;
    switch (cmd) {
      case "map_info": return { status: status(), canvas_path: "/perf/map.canvas", obsidian_installed: false };
      case "map_load": return { doc: await docPromise, hash: "h" };
      case "universe_discovery": return { root: "/perf", source: "found", tried: [] };
      case "map_preview": return { path: "x", size: 10, text: "preview", truncated: false, links: [] };
      default: return null;
    }
  },
  listen: (name: string, cb: (e: Payload) => void) => {
    if (!listeners.has(name)) listeners.set(name, new Set());
    listeners.get(name)!.add(cb);
    return () => listeners.get(name)!.delete(cb);
  },
};

/** Hjälp för mätskriptet: skicka händelser som Rust-sidan gör, och läs hur många anrop gränssnittet gjort. */
(globalThis as Record<string, unknown>).__perf = {
  emit: (name: string, payload: unknown) => listeners.get(name)?.forEach(cb => cb({ payload })),
  status,
  calls,
  listeners: () => Object.fromEntries([...listeners].map(([k, v]) => [k, v.size])),
  setDoc: (d: unknown) => { docPromise = Promise.resolve(d); },
};
