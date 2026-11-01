// Projektkarta i TraderGO Universe: visar Project Map.canvas (JSON Canvas) och håller den i synk via Rust-sidan.
// Allt innehåll från filer visas som ren text; ingen HTML från projektet renderas.
import { memo, useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import {
  Background, Controls, Edge, Handle, MarkerType, MiniMap, Node, NodeProps, OnConnect, OnNodesChange,
  Position, ReactFlow, ReactFlowProvider, applyNodeChanges, useReactFlow, useStore,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { invoke, listen } from "./tauri";

type CanvasNode = { id: string; type: string; x: number; y: number; width: number; height: number;
  file?: string; text?: string; url?: string; label?: string; [k: string]: unknown };
type CanvasEdge = { id: string; fromNode: string; toNode: string; label?: string; [k: string]: unknown };
type CanvasDoc = { nodes?: CanvasNode[]; edges?: CanvasEdge[]; [k: string]: unknown };
export type Status = { state: "unconfigured" | "indexing" | "idle" | "error"; root?: string; message?: string;
  files: number; edges: number; unconnected: number; last_run: number; last_duration_ms?: number;
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
  const d = data as { path: string };
  return (
    <div className={`pm-card${selected ? " sel" : ""}`} title={d.path}>
      <Ports />
      <strong>{base(d.path)}</strong>
      <span>{dir(d.path) || "/"}</span>
    </div>
  );
}

function TextCard({ data, selected }: NodeProps) {
  const d = data as { text: string };
  return <div className={`pm-card pm-text${selected ? " sel" : ""}`}><Ports />{d.text}</div>;
}

function GroupFrame({ id, data }: NodeProps) {
  const d = data as { label: string; collapsed: boolean; count: number; toggle: (id: string) => void };
  return (
    <div className={`pm-group${d.collapsed ? " collapsed" : ""}`}>
      <button className="pm-group-head nodrag" onClick={() => d.toggle(id)}>
        {d.collapsed ? "▸" : "▾"} {d.label} <span>({d.count})</span>
      </button>
    </div>
  );
}

type MapProps = { onStatus?: (s: Status) => void; searching?: boolean };

// memo: ett kort renderas bara om när dess egna data ändras (inte vid varje sökning eller status).
const nodeTypes = { file: memo(FileCard), text: memo(TextCard), frame: memo(GroupFrame) };
/** Över så här många kort ritas ingen minikarta: den ritar alla kort vid varje rörelse. */
const MINIMAP_MAX = 1500;
/** Under den här zoomnivån döljs pilarnas etiketter (färre detaljer utzoomat). */
const LABEL_ZOOM = 0.6;
const SEARCH_LIST = 12;
/** Fler träffar än så markeras inte på kartan (listan räcker); annars ändras tusentals kort per tangent. */
const HIGHLIGHT_MAX = 500;
/** Kartor med fler pilar än så visar genererade pilar först från EDGE_ZOOM (för många för att läsa utzoomat). */
const EDGE_HEAVY = 1000;
const EDGE_ZOOM = 0.3;

type CanvasProps = {
  nodes: Node[]; edges: Edge[]; minimap: boolean; highlighting: boolean;
  onNodesChange: OnNodesChange; onNodeDragStop: (e: unknown, n: Node, dragged: Node[]) => void; onConnect: OnConnect;
  onNodeClick: (id: string) => void; onEdgeClick: (id: string) => void; onPaneClick: () => void; onDeleteEdges: (ids: string[]) => void;
};

/**
 * Själva kartan. Egen komponent med memo, så att status, sökfält och sidopanel kan uppdateras utan att
 * React Flow och alla kort renderas om. Etiketter på pilar visas bara inzoomat.
 */
const MapCanvas = memo(function MapCanvas(p: CanvasProps) {
  const showLabels = useStore((st) => st.transform[2] >= LABEL_ZOOM);
  const heavy = p.edges.length > EDGE_HEAVY;
  const showGenerated = useStore((st) => !heavy || st.transform[2] >= EDGE_ZOOM);
  const edges = useMemo(() => {
    const visible = showGenerated ? p.edges : p.edges.filter((e) => KIND_OF(e.id) === "user");
    return showLabels ? visible : visible.map((e) => (e.label ? { ...e, label: undefined } : e));
  }, [p.edges, showLabels, showGenerated]);
  return (
    <div className={`pm-flow${p.highlighting ? " pm-searching" : ""}`}>
    {!showGenerated && <span className="pm-note pm-note-top muted">{p.edges.length} pilar visas när du zoomar in (för många att läsa utzoomat). Egna pilar visas alltid.</span>}
    <ReactFlow nodes={p.nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={p.onNodesChange}
      onNodeDragStop={p.onNodeDragStop} onConnect={p.onConnect} onlyRenderVisibleElements fitView minZoom={0.05}
      onNodeClick={(_, n) => p.onNodeClick(n.id)} onEdgeClick={(_, e) => p.onEdgeClick(e.id)} onPaneClick={p.onPaneClick}
      onBeforeDelete={async ({ edges: es }) => { p.onDeleteEdges(es.map((e) => e.id)); return false; }}>
      <Background />
      {p.minimap && <MiniMap pannable zoomable />}
      <Controls />
    </ReactFlow>
    </div>
  );
});

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

  const loading = useRef(false);
  const again = useRef(false);
  // Täta ändringar ger en laddning i taget plus högst en till efteråt, och en oförändrad karta
  // (samma hash) ritas inte om.
  const load = useCallback(async () => {
    if (loading.current) { again.current = true; return; }
    loading.current = true;
    try {
      do {
        again.current = false;
        const r = await invoke<{ doc: CanvasDoc; hash: string }>("map_load");
        const same = r.hash !== "" && r.hash === hash.current;
        hash.current = r.hash;
        dirty.current = false;
        if (!same) setDoc(r.doc);
        setConflict(false);
        setError("");
      } while (again.current);
    } catch (e) { setError(String(e)); }
    finally { loading.current = false; }
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

  const nodes = useMemo(() => doc.nodes ?? [], [doc]);
  const edges = useMemo(() => doc.edges ?? [], [doc]);
  // Sökningen räknas i bakgrunden (useDeferredValue) så att det går att skriva utan att vänta på kartan.
  const q = useDeferredValue(query.trim().toLowerCase());
  const found = useMemo(
    () => (q ? nodes.filter((n) => n.type !== "group" && (n.file ?? n.text ?? n.label ?? "").toLowerCase().includes(q)) : []),
    [nodes, q],
  );
  const matches = useMemo(() => new Set(found.map((n) => n.id)), [found]);

  // Vilka kort som ligger i varje grupp, räknat en gång per kartversion (inte per grupp och render).
  const members = useMemo(() => {
    const groups = nodes.filter((n) => n.type === "group");
    const m = new Map<string, string[]>();
    for (const g of groups) m.set(g.id, nodes.filter((n) => n.type !== "group" && inside(n, g)).map((n) => n.id));
    return m;
  }, [nodes]);
  const toggleGroup = useCallback((id: string) => setCollapsed((s) => { const t = new Set(s); if (t.has(id)) t.delete(id); else t.add(id); return t; }), []);

  // Grundnoderna ändras bara när kartan eller hopfällda grupper ändras.
  const baseNodes = useMemo(() => {
    const hidden = new Set<string>();
    for (const id of collapsed) for (const m of members.get(id) ?? []) hidden.add(m);
    return nodes.map((n): Node => {
      const common = { id: n.id, position: { x: n.x, y: n.y }, width: n.width, height: n.height, hidden: hidden.has(n.id) };
      if (n.type === "group") {
        const isC = collapsed.has(n.id);
        return { ...common, type: "frame", zIndex: -1, selectable: false, height: isC ? 44 : n.height,
          data: { label: n.label ?? "", collapsed: isC, count: members.get(n.id)?.length ?? 0, toggle: toggleGroup } };
      }
      if (n.type === "file") return { ...common, type: "file", data: { path: n.file ?? "" } };
      return { ...common, type: "text", data: { text: n.text ?? n.url ?? n.file ?? "" } };
    });
  }, [nodes, collapsed, members, toggleGroup]);

  // Sökmarkering: bara träffar får klassen pm-hit. Ett kort återanvänds så länge dess grunddata och
  // träffläge är desamma, också efter att React Flow uppdaterat det med sina mått (onNodesChange).
  // Annars byggs alla kort om, React Flow mäter om dem, och kortelementen flyttas i DOM vid varje tangent.
  const highlighting = q !== "" && found.length <= HIGHLIGHT_MAX;
  const builtFrom = useRef(new Map<string, { base: Node; hit: boolean }>());
  useEffect(() => {
    setRfNodes((prev) => {
      const byId = new Map(prev.map((n) => [n.id, n]));
      const next = baseNodes.map((b) => {
        const hit = highlighting && matches.has(b.id);
        const old = byId.get(b.id);
        const from = builtFrom.current.get(b.id);
        if (old && from && from.base === b && from.hit === hit) return old;
        builtFrom.current.set(b.id, { base: b, hit });
        return { ...b, measured: old?.measured, selected: old?.selected, className: hit ? "pm-hit" : undefined };
      });
      if (builtFrom.current.size > next.length * 2) {
        const live = new Set(next.map((n) => n.id));
        for (const id of builtFrom.current.keys()) if (!live.has(id)) builtFrom.current.delete(id);
      }
      // Ingen ändring: behåll samma lista, så att React Flow inte går igenom alla kort i onödan.
      return next.length === prev.length && next.every((n, i) => n === prev[i]) ? prev : next;
    });
  }, [baseNodes, matches, highlighting]);

  const rfEdges: Edge[] = useMemo(() => edges
    .filter((e) => kinds[KIND_OF(e.id)])
    .map((e) => {
      const k = KIND_OF(e.id);
      return { id: e.id, source: e.fromNode, target: e.toNode, label: e.label, style: KIND_STYLE[k],
        markerEnd: { type: MarkerType.ArrowClosed, color: KIND_STYLE[k].stroke as string },
        deletable: k === "user" };
    }), [edges, kinds]);

  const docRef = useRef(doc);
  docRef.current = doc;
  const onNodesChange: OnNodesChange = useCallback((changes) => setRfNodes((ns) => applyNodeChanges(changes, ns)), []);

  // Positioner sparas först när man släpper, aldrig för varje rörelse eller zoom.
  const onNodeDragStop = useCallback((_: unknown, n: Node, dragged: Node[]) => {
    const d = docRef.current;
    const moved = new Map((dragged.length ? dragged : [n]).map((x) => [x.id, x.position]));
    persist({ ...d, nodes: (d.nodes ?? []).map((c) => moved.has(c.id)
      ? { ...c, x: Math.round(moved.get(c.id)!.x), y: Math.round(moved.get(c.id)!.y) } : c) });
  }, [persist]);

  const onConnect: OnConnect = useCallback((c) => {
    if (!c.source || !c.target || c.source === c.target) return;
    const d = docRef.current;
    const id = `u-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
    persist({ ...d, edges: [...(d.edges ?? []), { id, fromNode: c.source, toNode: c.target }] });
  }, [persist]);

  const deleteUserEdges = useCallback((ids: string[]) => {
    const d = docRef.current;
    persist({ ...d, edges: (d.edges ?? []).filter((e) => !(ids.includes(e.id) && KIND_OF(e.id) === "user")) });
  }, [persist]);

  const selectNode = useCallback((id: string) => {
    const n = (docRef.current.nodes ?? []).find((x) => x.id === id);
    setSelected({ node: n });
    setPreview(undefined);
    if (n?.type === "file" && n.file) invoke<Preview>("map_preview", { path: n.file }).then(setPreview, (e) => setError(String(e)));
  }, []);
  const selectEdge = useCallback((id: string) => { setSelected({ edge: (docRef.current.edges ?? []).find((x) => x.id === id) }); setPreview(undefined); }, []);
  const clearSelection = useCallback(() => { setSelected({}); setPreview(undefined); }, []);

  const focusNode = (n: CanvasNode) => {
    selectNode(n.id);
    flow.setCenter(n.x + n.width / 2, n.y + n.height / 2, { zoom: 1.1, duration: 300 });
  };
  const focusFile = (path: string) => {
    const n = nodes.find((x) => x.file === path);
    if (n) focusNode(n);
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
            : `${status.files} filer · ${status.edges} kopplingar · ${status.unconnected} utan koppling · uppdaterad ${new Date(status.last_run).toLocaleTimeString("sv-SE")}${status.last_duration_ms != null ? ` (${status.last_duration_ms} ms)` : ""}`}
        </span>
      </div>
      <div className="actions pm-bar">
        <span className="pm-search">
          <input placeholder="Sök fil…" value={query} onChange={(e) => setQuery(e.target.value)} autoComplete="off" spellCheck={false}
            onKeyDown={(e) => { if (e.key === "Enter" && found.length) flow.fitView({ nodes: found.map((n) => ({ id: n.id })), duration: 300, maxZoom: 1.2 }); }} />
          {q && (
            <span className="pm-results">
              <span className="muted">{found.length} träffar{found.length > SEARCH_LIST ? ` (visar ${SEARCH_LIST}, Enter visar alla)` : ""}{found.length > HIGHLIGHT_MAX ? ". För många för att markera på kartan; skriv mer." : ""}</span>
              {found.slice(0, SEARCH_LIST).map((n) => (
                <button key={n.id} className="link" onClick={() => focusNode(n)}>{n.file ?? n.text ?? n.label}</button>
              ))}
            </span>
          )}
        </span>
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
          <MapCanvas nodes={rfNodes} edges={rfEdges} minimap={nodes.length <= MINIMAP_MAX} highlighting={highlighting}
            onNodesChange={onNodesChange} onNodeDragStop={onNodeDragStop} onConnect={onConnect}
            onNodeClick={selectNode} onEdgeClick={selectEdge} onPaneClick={clearSelection} onDeleteEdges={deleteUserEdges} />
          {nodes.length > MINIMAP_MAX && <span className="pm-note muted">Minikartan är avstängd för kartor med fler än {MINIMAP_MAX} kort.</span>}
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
