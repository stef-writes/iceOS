"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, type Connection, type OnConnect, type EdgeChange, type IsValidConnection, type NodeChange } from "reactflow";
import "reactflow/dist/style.css";
import { useSearchParams, useRouter } from "next/navigation";
import { mcp, workflows } from "@/modules/api/client";
import NodePalette from "@/modules/canvas/components/NodePalette";
import { nodeTypes } from "@/modules/canvas/components/nodes";
// Frosty chat and ExecutionDrawer removed to reduce UI surface area
import { useExecutionStore } from "@/modules/shell/useExecutionStore";
import { computeSimpleDagLayout } from "@/modules/canvas/utils/autolayout";
import InspectorPanel from "@/modules/canvas/components/inspector/InspectorPanel";
import { useCanvasStore } from "@/modules/canvas/state/useCanvasStore";
import { Dialog } from "@/modules/ui/primitives/Dialog";
import EdgeLinkWizard from "@/modules/canvas/components/EdgeLinkWizard";
import FrostyPanel from "@/modules/frosty/FrostyPanel";
import { useCopilotStore } from "@/modules/frosty/store/useCopilotStore";

type Blueprint = { nodes?: Array<{ id: string; type: string; dependencies?: string[] }> };

export default function CanvasView() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathBpId = typeof window !== "undefined" ? (window.location.pathname.match(/^\/workflows\/([^/?#]+)/)?.[1] || null) : null;
  const blueprintId = sp.get("blueprintId") || pathBpId;
  const projectId = sp.get("projectId");
  const bp = useCanvasStore((s) => s.blueprint) as any as Blueprint | null;
  const setBp = useCanvasStore((s) => s.setBlueprint) as any as (b: any) => void;
  const selected = useCanvasStore((s) => s.selected) as any as { id: string; type: string } | null;
  const setSelected = useCanvasStore((s) => s.setSelected) as any as (s: any) => void;
  const connectEdgeStore = useCanvasStore((s) => s.connectEdge);
  const removeEdgesStore = useCanvasStore((s) => s.removeEdgesByIds);
  const [err, setErr] = useState<string | null>(null);
  // Right pane removed; keep Canvas + Inspector only
  const [paletteOpen, setPaletteOpen] = useState<boolean>(false);
  const positions = useCanvasStore((s) => s.positions);
  const updatePositions = useCanvasStore((s) => s.updatePositions);
  const undo = useCanvasStore((s) => s.undo);
  const redo = useCanvasStore((s) => s.redo);
  const [versionLock, setVersionLock] = useState<string>("");
  const [title, setTitle] = useState<string>("");

  useEffect(() => {
    (async () => {
      setErr(null);
      try {
        // Canvas no longer auto-creates workflows; open with an explicit blueprintId
        if (!blueprintId) { setBp({ nodes: [] }); return; }
        const res = await workflows.get(blueprintId);
        try { setVersionLock(String((res as any).version_lock || "")); } catch {}
        const data = (res as any).data || { nodes: [] };
        setBp(data as any);
        try { setTitle(String((data?.metadata?.name) || "Untitled Workflow")); } catch { setTitle("Untitled Workflow"); }
      } catch (e: any) {
        setErr(String(e?.message || e));
      }
    })();
  }, [blueprintId, projectId]);

  // Debounced autosave on blueprint changes
  useEffect(() => {
    const id = blueprintId;
    const bpVal = bp as any;
    if (!id || !bpVal || !Array.isArray(bpVal.nodes)) return;
    const handle = setTimeout(async () => {
      try {
        if (!versionLock) {
          const res = await workflows.get(id);
          const lock = String((res as any).version_lock || "");
          setVersionLock(lock);
        }
        const payload = { nodes: bpVal.nodes, metadata: { name: title } } as any;
        const currentLock = versionLock || String(((await workflows.get(id)) as any).version_lock || "");
        await (workflows as any).patch(id, payload, currentLock);
        // After successful patch, refresh lock
        const next = await workflows.get(id);
        try { setVersionLock(String((next as any).version_lock || "")); } catch {}
      } catch (e) {
        // 409/conflict or validation errors: best-effort refresh lock; in future, merge
        try {
          const latest = await workflows.get(id);
          setVersionLock(String((latest as any).version_lock || ""));
        } catch {}
      }
    }, 600);
    return () => clearTimeout(handle);
  }, [bp, blueprintId]);

  // Debounced title save when changed
  useEffect(() => {
    const id = blueprintId;
    if (!id || !title) return;
    const handle = setTimeout(async () => {
      try {
        const res = await workflows.get(id);
        const data = (res as any).data || {};
        const lock = String((res as any).version_lock || "");
        data.metadata = { ...(data.metadata || {}), name: title };
        await (workflows as any).put(id, data, lock);
        const next = await workflows.get(id);
        setVersionLock(String((next as any).version_lock || ""));
      } catch {}
    }, 800);
    return () => clearTimeout(handle);
  }, [title, blueprintId]);

  // Handle node dropped from Studio via sessionStorage
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("studio:addNode");
      if (raw) {
        sessionStorage.removeItem("studio:addNode");
        const node = JSON.parse(raw);
        const nodesArr = Array.isArray(bp?.nodes) ? [...bp!.nodes] : [];
        const id = String(node.id || `n${Math.floor(Math.random()*1e6)}`);
        const safe = { id, type: String(node.type||"agent"), dependencies: Array.isArray(node.dependencies)?node.dependencies:[], ...node } as any;
        const exists = nodesArr.find((n:any)=>String(n.id)===id);
        if (!exists) nodesArr.push(safe);
        setBp({ nodes: nodesArr } as any);
      }
    } catch {}
  }, [bp]);

  // Right panel removed: no tab sync required

  // Initialize selection from URL param when present
  useEffect(() => {
    const sel = sp.get("sel");
    if (!sel) return;
    const n = (bp?.nodes || []).find((x: any) => String(x.id) === String(sel));
    if (n) setSelected({ id: String(n.id), type: String((n as any).type || "") });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sp, bp]);

  // Inspector opens as a modal now; keep right pane for console/step only

  const exec = useExecutionStore();

  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const dataNodes = Array.isArray(bp?.nodes) ? bp!.nodes! : [];
    const layout = Object.keys(positions).length ? positions : computeSimpleDagLayout(bp as any);
    dataNodes.forEach((n: any) => {
      const status = exec.nodeStatus[n.id as string] as any;
      const p = layout[n.id] || { x: 80, y: 60 };
      const t = String((n as any).type || "");
      let summary = "";
      if (t === "llm") {
        const prov = String((n as any).provider || (n as any).llm_config?.provider || "");
        const model = String((n as any).model || (n as any).llm_config?.model || "");
        if (prov || model) summary = `${prov}${prov && model ? "/" : ""}${model}`;
      } else if (t === "tool") {
        const name = String((n as any).tool_name || "");
        if (name) summary = name;
      } else if (t === "agent") {
        const prov = String((n as any).llm_config?.provider || "");
        const model = String((n as any).llm_config?.model || "");
        const toolsArr = Array.isArray((n as any).tools) ? (n as any).tools : [];
        const toolsInfo = toolsArr.length ? ` · ${toolsArr.length} tool${toolsArr.length>1?"s":""}` : "";
        if (prov || model) summary = `${prov}${prov && model ? "/" : ""}${model}${toolsInfo}`;
      }
      nodes.push({ id: n.id, type: t, position: p, data: { label: `${t}:${n.id}`, status, summary } as any });
    });
    const depOf: Record<string, string[]> = {};
    dataNodes.forEach((n) => {
      (n.dependencies || []).forEach((dep) => {
        depOf[n.id] = depOf[n.id] || [];
        depOf[n.id].push(dep);
      });
    });
    Object.entries(depOf).forEach(([to, fromList]) => {
      fromList.forEach((from, i) => {
        edges.push({ id: `${from}->${to}-${i}` , source: from, target: to });
      });
    });
    return { nodes, edges };
  }, [bp, exec.nodeStatus, positions]);

  function hasPath(from: string, to: string): boolean {
    const nodes = (bp?.nodes || []) as any[];
    const depsOf: Record<string, string[]> = {};
    nodes.forEach((n) => {
      const deps = Array.isArray(n.dependencies) ? n.dependencies : [];
      depsOf[n.id] = deps;
    });
    const stack = [from];
    const seen = new Set<string>();
    while (stack.length) {
      const cur = stack.pop()!;
      if (cur === to) return true;
      if (seen.has(cur)) continue;
      seen.add(cur);
      (depsOf[cur] || []).forEach((d) => stack.push(d));
    }
    return false;
  }

  const isValidConnection: IsValidConnection = useCallback((conn) => {
    const source = conn.source ?? undefined;
    const target = conn.target ?? undefined;
    if (!source || !target || source === target) return false;
    // prevent cycles: if target already reaches source, connecting would create a cycle
    if (hasPath(target, source)) return false;
    // allow multiple inputs by default; port-specific cardinality can be enforced later via schema
    return true;
  }, [bp]);

  const onConnect: OnConnect = useCallback((params: Connection) => {
    const source = params.source ?? undefined;
    const target = params.target ?? undefined;
    const targetHandle = (params.targetHandle ?? "in") as string;
    if (!source || !target) return;
    connectEdgeStore(source, target, targetHandle);
    // After connecting, prompt to link inputs from source to target
    setPendingLink({ sourceId: source, targetId: target });
  }, []);

  const onEdgesChange = useCallback((changes: EdgeChange[]) => {
    const removals = changes.filter((c) => c.type === "remove");
    if (removals.length === 0) return;
    const ids = removals.map((r: any) => r.id).filter(Boolean);
    removeEdgesStore(ids as string[]);
  }, []);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    const posUpdates: Record<string, { x: number; y: number }> = {};
    changes.forEach((c: any) => {
      if (c.type === "position" && c.position) {
        posUpdates[c.id] = { x: c.position.x, y: c.position.y };
      }
    });
    if (Object.keys(posUpdates).length) updatePositions(posUpdates);
  }, []);

  async function onRunGraph() {
    try {
      const blueprint = { nodes: (bp?.nodes || []).map((n: any) => ({ id: n.id, type: n.type, dependencies: n.dependencies || [], ...n })) } as any;
      const ack = await mcp.runs.start({ blueprint });
      useExecutionStore.getState().start(mcp.runs.eventsUrl(ack.run_id));
    } catch (e) {
      // no-op UI error surfacing for now
    }
  }

  async function onRunSelection() {
    if (!selected) return onRunGraph();
    const all = (bp?.nodes || []) as any[];
    const depsOf: Record<string, string[]> = {};
    all.forEach((n) => { depsOf[n.id] = Array.isArray(n.dependencies) ? n.dependencies : []; });
    const include = new Set<string>();
    const stack = [selected.id];
    while (stack.length) {
      const cur = stack.pop()!;
      if (include.has(cur)) continue;
      include.add(cur);
      (depsOf[cur] || []).forEach((d) => stack.push(d));
    }
    const nodes = all.filter((n) => include.has(n.id)).map((n) => ({ id: n.id, type: n.type, dependencies: n.dependencies || [], ...n }));
    try {
      const ack = await mcp.runs.start({ blueprint: { nodes } as any });
      useExecutionStore.getState().start(mcp.runs.eventsUrl(ack.run_id));
    } catch {}
  }

  function addNodeOfType(t: string) {
    const id = `n${Math.floor(Math.random() * 1e6)}`;
    const nodesArr = Array.isArray(bp?.nodes) ? [...bp!.nodes] : [];
    nodesArr.push({ id, type: t, dependencies: [] } as any);
    setBp({ nodes: nodesArr });
  }

  // Draft helpers exist in Studio; Canvas omits draft actions in this view to keep TS build strict.

  // Always use full center span (no right pane)
  const centerSpan = "col-span-5";
  const [pendingLink, setPendingLink] = useState<{ sourceId: string; targetId: string } | null>(null);
  const copilotOpen = (useCopilotStore as any).getState().open as boolean;

  return (
    <div className="grid grid-cols-6 gap-3">
      <div className="col-span-1">
        {!paletteOpen ? (
          <div className="h-[80vh] border border-neutral-800 rounded p-2 flex flex-col items-start justify-between">
            <div className="text-neutral-300 text-sm">Palette</div>
            <button onClick={() => setPaletteOpen(true)} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Add node</button>
          </div>
        ) : (
          <div className="relative">
            <div className="absolute right-2 top-2 z-10">
              <button onClick={() => setPaletteOpen(false)} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Close</button>
            </div>
            <NodePalette onAdd={(t) => { addNodeOfType(t); setPaletteOpen(false); }} />
          </div>
        )}
      </div>
      <div className={`${centerSpan} h-[80vh]`}>
        <div className="mb-2 flex items-center gap-2">
          <input value={title} onChange={(e)=>setTitle(e.target.value)} placeholder="Untitled Workflow" className="px-2 py-1 text-xs border border-neutral-700 rounded bg-neutral-900" />
          <button onClick={onRunGraph} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Run workflow</button>
          <button onClick={onRunSelection} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Run selected nodes</button>
          <span className="mx-2 h-4 w-px bg-neutral-800" />
          <button onClick={undo} title="Undo" className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Undo</button>
          <button onClick={redo} title="Redo" className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Redo</button>
          <span className="mx-2 h-4 w-px bg-neutral-800" />
          <button onClick={()=>{ try{ (useCopilotStore as any).getState().setOpen(!(useCopilotStore as any).getState().open);}catch{} }} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">{copilotOpen?"Hide Frosty":"Open Frosty"}</button>
        </div>
        {err && <div className="p-2 text-red-400 text-sm">{err}</div>}
        <ReactFlow
          nodeTypes={nodeTypes as any}
          nodes={nodes}
          edges={edges}
          fitView
          snapToGrid
          snapGrid={[12, 12]}
          defaultEdgeOptions={{ type: "smoothstep" as any }}
          connectionLineStyle={{ stroke: "#6b7280", strokeWidth: 1 }}
          onNodeClick={(_, n) => {
            const typ = String((bp?.nodes||[]).find(x=>x.id===n.id)?.type||"");
            setSelected({ id: n.id, type: typ });
            const params = new URLSearchParams(sp.toString());
            params.set("sel", n.id);
            router.replace(`/canvas?${params.toString()}`);
          }}
          onConnect={onConnect}
          onEdgesChange={onEdgesChange}
          onNodesChange={onNodesChange}
          isValidConnection={isValidConnection}
        >
          <MiniMap />
          <Controls />
          <Background gap={12} />
        </ReactFlow>
        {/* Copilot removed for now; keep Canvas focused */}
      </div>
      {/* Right pane removed (console/step) */}

      {/* Modal Node editor */}
      <Dialog
        open={!!selected}
        onOpenChange={(o) => {
          if (!o) {
            setSelected(null);
            const params = new URLSearchParams(sp.toString());
            params.delete("sel");
            router.replace(`/canvas?${params.toString()}`);
          }
        }}
        title={selected ? `Edit ${selected.type}:${selected.id}` : "Edit node"}
      >
        {selected && (
          <div className="space-y-2">
            <InspectorPanel bp={bp as any} nodeId={selected.id} nodeType={selected.type} onChange={(next) => setBp(next as any)} />
            <div className="text-right">
              <button onClick={() => {
                setSelected(null);
                const params = new URLSearchParams(sp.toString());
                params.delete("sel");
                router.replace(`/canvas?${params.toString()}`);
              }} className="mt-2 px-3 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Close</button>
            </div>
          </div>
        )}
      </Dialog>

      {/* Edge Link Wizard */}
      <button id="edge-link-wizard-open" className="hidden" />
      <Dialog
        open={!!pendingLink}
        onOpenChange={(o) => { if (!o) setPendingLink(null); }}
        title={pendingLink ? `Link inputs: ${pendingLink.sourceId} → ${pendingLink.targetId}` : "Link inputs"}
      >
        {pendingLink && (
          <EdgeLinkWizard
            bp={bp as any}
            sourceId={pendingLink.sourceId}
            targetId={pendingLink.targetId}
            onApply={({ replaceRoots }) => {
              // Replace unresolved roots in target's prompts/args with sourceId
              const all = Array.isArray(bp?.nodes) ? [...(bp!.nodes as any[])] : [];
              const idx = all.findIndex((n) => String(n.id) === String(pendingLink.targetId));
              if (idx >= 0) {
                const t = { ...(all[idx] as any) };
                const replacements = new Set(replaceRoots);
                function swap(text: any) {
                  if (typeof text !== "string") return text;
                  let out = text;
                  if (pendingLink) {
                    replacements.forEach((root) => {
                      const re = new RegExp(`\\{\\{\\s*${root}(?=[\\.\\[]|\\s*\\}})`, "g");
                      out = out.replace(re, `{{ ${pendingLink.sourceId}`);
                    });
                  }
                  return out;
                }
                if (typeof t.prompt === "string") t.prompt = swap(t.prompt);
                if (typeof t.system_prompt === "string") t.system_prompt = swap(t.system_prompt);
                if (typeof t.user_prompt === "string") t.user_prompt = swap(t.user_prompt);
                if (t && typeof t.tool_args === "object" && t.tool_args !== null) {
                  const nextArgs: Record<string, any> = {};
                  Object.entries(t.tool_args).forEach(([k, v]) => { nextArgs[k] = swap(v as any); });
                  t.tool_args = nextArgs;
                }
                // Ensure dependency from target to source exists
                const deps = Array.isArray(t.dependencies) ? Array.from(new Set([...(t.dependencies as string[]), pendingLink.sourceId])) : [pendingLink.sourceId];
                t.dependencies = deps;
                all[idx] = t;
                setBp({ nodes: all as any });
              }
              setPendingLink(null);
            }}
            onClose={() => setPendingLink(null)}
          />
        )}
      </Dialog>
      <FrostyPanel />
    </div>
  );
}
