// Projektkarta i TraderGO Universe: visar Project Map.canvas (JSON Canvas) och håller den i synk via Rust-sidan.
// Allt innehåll från filer visas som ren text; ingen HTML från projektet renderas.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background, Controls, Edge, Handle, MarkerType, MiniMap, Node, NodeProps, OnConnect, OnNodesChange,
  Position, ReactFlow, ReactFlowProvider, applyNodeChanges, useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { invoke, listen } from "./tauri";

type CanvasNode = { id: string; type: string; x: number; y: number; width: number; height: number;
  file?: string; text?: string; url?: string; label?: string; [k: string]: unknown };
type CanvasEdge = { id: string; fromNode: string; toNode: string; label?: string; [k: string]: unknown };
type CanvasDoc = { nodes?: CanvasNode[]; edges?: CanvasEdge[]; [k: string]: unknown };
export type Status = { state: "unconfigured" | "indexing" | "idle" | "error"; root?: string; message?: string;
  files: number; edges: number; unconnected: number; last_run: number;
  by_kind: Record<string, number>; broken: { from: string; target: string }[] };
type Info = { status: Status; canvas_path?: string; obsidian_installed: boolean; obsidian_vault?: string };
type Preview = { path: string; size: number; text?: string; truncated: boolean;
  links: { path: string; kind: "Explicit" | "Dependency" | "Inferred"; label: string; outgoing: boolean }[] };

type EdgeKind = "explicit" | "dependency" | "inferred" | "user";
const KIND_OF = (id: string): EdgeKind =>
  id.startsWith("g-e-") ? "explicit" : id.startsWith("g-d-") ? "dependency" : id.startsWith("g-i-") ? "inferred" : "user";
const KIND_LABEL: Record<EdgeKind, string> = { explicit: "Länkar", dependency: "Beroenden", inferred: "Härledda", user: "Egna pilar" };
const KIND_STYLE: Record<EdgeKind, React.CSSProperties> = {
  explicit: { stroke: "#2e9e5b", strokeWidth: 1.5 },
  dependency: { stroke: "#2b7bd6", strokeWidth: 1.5 },
  inferred: { stroke: "#c99a06", strokeWidth: 1.2, strokeDasharray: "6 4" },
  user: { stroke: "#e0661b", strokeWidth: 2.4 },
};

// Handles let arrows attach and let you drag a new arrow from one card to another.
const Ports = () => (<><Handle type="target" position={Position.Left} /><Handle type="source" position={Position.Right} /></>);

const base = (p: string) => p.split("/").pop() ?? p;
const dir = (p: string) => p.split("/").slice(0, -1).join("/");

function FileCard({ data, selected }: NodeProps) {
  const d = data as { path: string; dim: boolean };
  return (
    <div className={`pm-card${selected ? " sel" : ""}${d.dim ? " dim" : ""}`} title={d.path}>
      <Ports />
      <strong>{base(d.path)}</strong>
      <span>{dir(d.path) || "/"}</span>
    </div>
  );
}

function TextCard({ data, selected }: NodeProps) {
  const d = data as { text: string; dim: boolean };
  return <div className={`pm-card pm-text${selected ? " sel" : ""}${d.dim ? " dim" : ""}`}><Ports />{d.text}</div>;
}

function GroupFrame({ data }: NodeProps) {
  const d = data as { label: string; collapsed: boolean; count: number; toggle: () => void };
  return (
    <div className={`pm-group${d.collapsed ? " collapsed" : ""}`}>
      <button className="pm-group-head nodrag" onClick={d.toggle}>
        {d.collapsed ? "▸" : "▾"} {d.label} <span>({d.count})</span>
      </button>
    </div>
  );
}

type MapProps = { onStatus?: (s: Status) => void; searching?: boolean };

const nodeTypes = { file: FileCard, text: TextCard, frame: GroupFrame };

function inside(n: CanvasNode, g: CanvasNode) {
  const cx = n.x + n.width / 2, cy = n.y + n.height / 2;
  return cx >= g.x && cx <= g.x + g.width && cy >= g.y && cy <= g.y + g.height;
}

function MapView({ onStatus, searching }: MapProps) {
  const flow = useReactFlow();
  const [info, setInfo] = useState<Info>();
  const [status, setStatus] = useState<Status>();
  const [doc, setDoc] = useState<CanvasDoc>({});
  const [rfNodes, setRfNodes] = useState<Node[]>([]);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [kinds, setKinds] = useState<Record<EdgeKind, boolean>>({ explicit: true, dependency: true, inferred: true, user: true });
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [selected, setSelected] = useState<{ node?: CanvasNode; edge?: CanvasEdge }>({});
  const [preview, setPreview] = useState<Preview>();
  const hash = useRef("");
  const dirty = useRef(false);
  const saveTimer = useRef<number>();

  const load = useCallback(async () => {
    try {
      const r = await invoke<{ doc: CanvasDoc; hash: string }>("map_load");
      hash.current = r.hash;
      dirty.current = false;
      setDoc(r.doc);
      setConflict(false);
      setError("");
    } catch (e) { setError(String(e)); }
  }, []);

  useEffect(() => { if (status) onStatus?.(status); }, [status, onStatus]);

  const refreshInfo = useCallback(() => invoke<Info>("map_info").then((i) => { setInfo(i); setStatus(i.status); }), []);

  useEffect(() => {
    const offs = [
      listen<Status>("map-status", (e) => setStatus(e.payload)),
      listen<{ external: boolean }>("map-changed", () => {
        if (dirty.current) setConflict(true);
        else load();
      }),
    ];
    // Read the current state only once both listeners are attached, so no update is missed.
    Promise.all(offs).then(() => refreshInfo()).then(load);
    return () => offs.forEach((o) => o.then((f) => f()));
  }, [load, refreshInfo]);

  useEffect(() => { if (status?.state === "idle" && !info?.canvas_path) refreshInfo().then(load); }, [status, info, load, refreshInfo]);

  // Saves after edits settle; a changed file on disk turns into a conflict, never an overwrite.
  const persist = useCallback((next: CanvasDoc) => {
    setDoc(next);
    dirty.current = true;
    window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      try {
        hash.current = await invoke<string>("map_save", { doc: next, baseHash: hash.current });
        dirty.current = false;
      } catch (e) {
        if (String(e).startsWith("CONFLICT")) setConflict(true);
        else setError(String(e));
      }
    }, 400);
  }, []);

  const nodes = doc.nodes ?? [];
  const edges = doc.edges ?? [];
  const q = query.trim().toLowerCase();
  const matches = useMemo(
    () => new Set(q ? nodes.filter((n) => (n.file ?? n.text ?? n.label ?? "").toLowerCase().includes(q)).map((n) => n.id) : []),
    [nodes, q],
  );

  useEffect(() => {
    const groups = nodes.filter((n) => n.type === "group");
    const hidden = new Set<string>();
    for (const g of groups) if (collapsed.has(g.id)) for (const n of nodes) if (n.type !== "group" && inside(n, g)) hidden.add(n.id);
    setRfNodes(nodes.map((n): Node => {
      const common = { id: n.id, position: { x: n.x, y: n.y }, width: n.width, height: n.height, hidden: hidden.has(n.id) };
      const dim = q !== "" && !matches.has(n.id);
      if (n.type === "group") {
        const isC = collapsed.has(n.id);
        const count = nodes.filter((m) => m.type !== "group" && inside(m, n)).length;
        return { ...common, type: "frame", zIndex: -1, selectable: false, height: isC ? 44 : n.height,
          data: { label: n.label ?? "", collapsed: isC, count,
            toggle: () => setCollapsed((s) => { const t = new Set(s); if (t.has(n.id)) t.delete(n.id); else t.add(n.id); return t; }) } };
      }
      if (n.type === "file") return { ...common, type: "file", data: { path: n.file ?? "", dim } };
      return { ...common, type: "text", data: { text: n.text ?? n.url ?? n.file ?? "", dim } };
    }));
  }, [nodes, collapsed, matches, q]);

  const rfEdges: Edge[] = useMemo(() => edges
    .filter((e) => kinds[KIND_OF(e.id)])
    .map((e) => {
      const k = KIND_OF(e.id);
      return { id: e.id, source: e.fromNode, target: e.toNode, label: e.label, style: KIND_STYLE[k],
        markerEnd: { type: MarkerType.ArrowClosed, color: KIND_STYLE[k].stroke as string },
        deletable: k === "user", selected: selected.edge?.id === e.id };
    }), [edges, kinds, selected.edge]);

  const onNodesChange: OnNodesChange = (changes) => setRfNodes((ns) => applyNodeChanges(changes, ns));

  const onNodeDragStop = (_: unknown, n: Node, dragged: Node[]) => {
    const moved = new Map((dragged.length ? dragged : [n]).map((d) => [d.id, d.position]));
    persist({ ...doc, nodes: nodes.map((c) => moved.has(c.id)
      ? { ...c, x: Math.round(moved.get(c.id)!.x), y: Math.round(moved.get(c.id)!.y) } : c) });
  };

  const onConnect: OnConnect = (c) => {
    if (!c.source || !c.target || c.source === c.target) return;
    const id = `u-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    persist({ ...doc, edges: [...edges, { id, fromNode: c.source, toNode: c.target }] });
  };

  const deleteUserEdges = (ids: string[]) =>
    persist({ ...doc, edges: edges.filter((e) => !(ids.includes(e.id) && KIND_OF(e.id) === "user")) });

  const selectNode = (id: string) => {
    const n = nodes.find((x) => x.id === id);
    setSelected({ node: n });
    setPreview(undefined);
    if (n?.type === "file" && n.file) invoke<Preview>("map_preview", { path: n.file }).then(setPreview, (e) => setError(String(e)));
  };

  const focusFile = (path: string) => {
    const n = nodes.find((x) => x.file === path);
    if (!n) return;
    selectNode(n.id);
    flow.setCenter(n.x + n.width / 2, n.y + n.height / 2, { zoom: 1.1, duration: 300 });
  };

  const run = (cmd: string, args?: Record<string, unknown>) => invoke(cmd, args).catch((e) => setError(String(e)));

  if (searching && (!status || status.state === "unconfigured")) {
    return (
      <section className="pm pm-empty">
        <h2>Letar efter projektmappen…</h2>
        <p className="muted">Om macOS frågar om TraderGO Universe får komma åt mappen <b>Dokument</b>, välj <b>Tillåt</b>. Universe behöver bara läsa projektet.</p>
      </section>
    );
  }

  if (!status || status.state === "unconfigured") {
    return (
      <section className="pm pm-empty">
        <h2>Hittade ingen projektmapp</h2>
        <p className="muted">Universe letar efter en TraderGO-mapp (med <code>CLAUDE.md</code> och <code>apps/trader-go-universe</code>) på vanliga ställen, t.ex. <code>~/Documents/GitHub/Trader_go</code>. Välj din kopia av repot. Universe läser bara mappen och ändrar ingenting i den.</p>
        <div className="actions"><button onClick={() => invoke<boolean>("map_choose_root").then(async (ok) => { if (ok) await refreshInfo(); }).catch((e) => setError(String(e)))}>Välj projektmapp…</button></div>
        {error && !error.includes("Ingen projektmapp") && <p className="error">{error}</p>}
      </section>
    );
  }

  const vaultOk = info?.obsidian_installed && info.obsidian_vault;
  const obsidianHint = !info?.obsidian_installed ? "Obsidian är inte installerat"
    : !info?.obsidian_vault ? "Öppna projektmappen som valv i Obsidian först" : "";

  return (
    <section className="pm">
      <div className="actions pm-bar">
        <span className="muted" title={status.root}>{status.root}</span>
        <button title="Välj en annan kopia av projektet" onClick={() => invoke<boolean>("map_choose_root").then(async (ok) => { if (ok) { await refreshInfo(); await load(); } }).catch((e) => setError(String(e)))}>Byt mapp…</button>
        <button onClick={() => run("map_refresh")}>Uppdatera</button>
        <button onClick={() => run("map_export", { doc })}>Exportera…</button>
        <span className={status.state === "error" ? "error" : "muted"}>
          {status.state === "indexing" ? "Indexerar…" : status.state === "error" ? status.message
            : `${status.files} filer · ${status.edges} kopplingar · ${status.unconnected} utan koppling · ${new Date(status.last_run).toLocaleTimeString("sv-SE")}`}
        </span>
      </div>
      <div className="actions pm-bar">
        <input placeholder="Sök fil…" value={query} onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && matches.size) flow.fitView({ nodes: [...matches].map((id) => ({ id })), duration: 300, maxZoom: 1.2 }); }} />
        {(Object.keys(KIND_LABEL) as EdgeKind[]).map((k) => (
          <label key={k} className="pm-kind">
            <input type="checkbox" checked={kinds[k]} onChange={(e) => setKinds({ ...kinds, [k]: e.target.checked })} />
            <i style={{ borderTop: `3px ${KIND_STYLE[k].strokeDasharray ? "dashed" : "solid"} ${KIND_STYLE[k].stroke}` }} /> {KIND_LABEL[k]}
          </label>
        ))}
      </div>
      {conflict && (
        <div className="pm-conflict">
          Kartfilen har ändrats på disken sedan den lästes in. Dina senaste ändringar av layouten är inte sparade.
          <button onClick={load}>Ladda om från disk</button>
          <button onClick={() => invoke<string>("map_save_copy", { doc }).then((name) => { setError(`Sparad som ${name}`); load(); }, (e) => setError(String(e)))}>Spara mina ändringar som kopia</button>
        </div>
      )}
      {error && <p className="error">{error}</p>}
      <div className="pm-body">
        <div className="pm-canvas">
          <ReactFlow nodes={rfNodes} edges={rfEdges} nodeTypes={nodeTypes} onNodesChange={onNodesChange}
            onNodeDragStop={onNodeDragStop} onConnect={onConnect} onlyRenderVisibleElements fitView minZoom={0.05}
            onNodeClick={(_, n) => selectNode(n.id)} onEdgeClick={(_, e) => { setSelected({ edge: edges.find((x) => x.id === e.id) }); setPreview(undefined); }}
            onPaneClick={() => { setSelected({}); setPreview(undefined); }}
            onBeforeDelete={async ({ edges: es }) => { deleteUserEdges(es.map((e) => e.id)); return false; }}>
            <Background />
            <MiniMap pannable zoomable />
            <Controls />
          </ReactFlow>
        </div>
        {(selected.node || selected.edge) && (
          <aside className="pm-side">
            {selected.edge && (() => {
              const e = selected.edge!;
              const k = KIND_OF(e.id);
              const name = (id: string) => { const n = nodes.find((x) => x.id === id); return n?.file ?? n?.text ?? id; };
              return (
                <>
                  <h3>{KIND_LABEL[k]}</h3>
                  <p className="muted">{name(e.fromNode)} → {name(e.toNode)}</p>
                  {k === "user" ? (
                    <>
                      <input placeholder="Etikett" defaultValue={e.label ?? ""} key={e.id}
                        onBlur={(ev) => persist({ ...doc, edges: edges.map((x) => x.id === e.id ? { ...x, label: ev.target.value || undefined } : x) })} />
                      <div className="actions"><button onClick={() => { deleteUserEdges([e.id]); setSelected({}); }}>Ta bort pil</button></div>
                    </>
                  ) : <p>{e.label}<br /><span className="muted">Skapad automatiskt. Ändras när filerna ändras.</span></p>}
                </>
              );
            })()}
            {selected.node && (
              <>
                <h3>{selected.node.file ? base(selected.node.file) : selected.node.label ?? "Kort"}</h3>
                {selected.node.file && <p className="muted">{selected.node.file}</p>}
                {selected.node.file && (
                  <div className="actions">
                    <button onClick={() => run("map_reveal", { path: selected.node!.file })}>Visa i mappen</button>
                    <button disabled={!vaultOk} title={obsidianHint} onClick={() => run("map_open_obsidian", { path: selected.node!.file })}>Öppna i Obsidian</button>
                  </div>
                )}
                {preview && (
                  <>
                    {preview.links.length > 0 && (
                      <ul className="pm-links">
                        {preview.links.map((l, i) => (
                          <li key={i}><button className="link" onClick={() => focusFile(l.path)}>{l.outgoing ? "→" : "←"} {l.path}</button>
                            <span className="muted"> {l.label}{l.kind === "Inferred" ? " (härledd)" : ""}</span></li>
                        ))}
                      </ul>
                    )}
                    {preview.text !== undefined && preview.text !== null
                      ? <pre className="pm-preview">{preview.text}{preview.truncated ? "\n…" : ""}</pre>
                      : <p className="muted">Binärfil ({(preview.size / 1024).toFixed(1)} kB). Visas inte.</p>}
                  </>
                )}
                {selected.node.type === "text" && <pre className="pm-preview">{selected.node.text}</pre>}
              </>
            )}
          </aside>
        )}
      </div>
    </section>
  );
}

export function ProjectMap(props: MapProps) {
  return <ReactFlowProvider><MapView {...props} /></ReactFlowProvider>;
}
