"use client";
import { useEffect, useState } from "react";
// Fetch schemas directly to avoid double "/api" in base URL when NEXT_PUBLIC_API_URL is "/api"
import { updateNode, type CanvasBlueprint } from "@/modules/canvas/utils/blueprint";
import { mcp } from "@/modules/api/client";
import { useExecutionStore } from "@/modules/shell/useExecutionStore";
import { suggest as svcSuggest, applyPatches as svcApply } from "@/modules/canvas/services/builderApi";
import LLMInspector from "@/modules/canvas/components/inspector/types/LLMInspector";
import ToolInspector from "@/modules/canvas/components/inspector/types/ToolInspector";
import AgentInspector from "@/modules/canvas/components/inspector/types/AgentInspector";
import { useCanvasStore } from "@/modules/canvas/state/useCanvasStore";
import { env } from "@/lib/env";

type Props = {
  bp: CanvasBlueprint | null;
  nodeId: string;
  nodeType: string;
  onChange: (next: CanvasBlueprint) => void;
};

export default function InspectorPanel({ bp, nodeId, nodeType, onChange }: Props) {
  const [schema, setSchema] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nodeText, setNodeText] = useState<string>("");
  const [pendingPatches, setPendingPatches] = useState<Array<Record<string, unknown>>>([]);
  const execStore = useExecutionStore();
  const [toolInfo, setToolInfo] = useState<Record<string, any> | null>(null);
  const [toolErr, setToolErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const base = env.API_URL?.trim() || "/api";
        const nodeTypeLower = String(nodeType || "").toLowerCase();
        const url = `${base}/v1/meta/nodes/${encodeURIComponent(nodeTypeLower)}/schema`;
        const r = await fetch(url, { headers: { "Authorization": `Bearer ${env.API_TOKEN}` } });
        if (!r.ok) throw new Error(`get node schema failed: ${r.status}`);
        const s = await r.json();
        setSchema((s as any)?.json_schema || {});
      } catch (e: any) {
        setError(String(e?.message || e));
      }
    })();
  }, [nodeType]);

  // Load selected tool's IO schema for linting tool args
  useEffect(() => {
    (async () => {
      try {
        setToolErr(null);
        setToolInfo(null);
        if (nodeType !== "tool") return;
        const nodeObj = ((bp?.nodes || []) as any[]).find((n) => n.id === nodeId) || {};
        const toolName = String(nodeObj.tool_name || "").trim();
        if (!toolName) return;
        const base = env.API_URL?.trim() || "/api";
        const url = `${base}/v1/meta/nodes/tool/${encodeURIComponent(toolName)}`;
        const r = await fetch(url, { headers: { "Authorization": `Bearer ${env.API_TOKEN}` } });
        if (!r.ok) throw new Error(`get tool details failed: ${r.status}`);
        const info = await r.json();
        setToolInfo(info as any);
      } catch (e: any) {
        setToolErr(String(e?.message || e));
      }
    })();
  }, [nodeType, bp, nodeId]);

  function setField(path: string, value: unknown) {
    const current = ((bp?.nodes || []) as any[]).find((n) => n.id === nodeId) || {};
    const next = { ...current } as any;
    next[path] = value;
    const updated = updateNode(bp as any, nodeId, next) as any;
    if (updated) onChange(updated);
  }

  // ---------------- Prompt placeholder lint (frontend) -----------------
  function extractPlaceholders(tmpl: string): string[] {
    const out: string[] = [];
    if (!tmpl) return out;
    const re = /\{\{\s*([^}]+?)\s*\}\}/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(tmpl)) !== null) {
      const key = String(m[1] || "").trim();
      if (key) out.push(key);
    }
    return out;
  }

  function getPlaceholderRoots(keys: string[]): string[] {
    return keys.map((k) => {
      const dot = k.indexOf(".");
      const bracket = k.indexOf("[");
      const idx = [dot, bracket].filter((n) => n >= 0).sort((a, b) => a - b)[0];
      return idx >= 0 ? k.slice(0, idx) : k;
    });
  }

  async function runNode() {
    try {
      if (!bp) return;
      // Simple required-field gate using fetched schema
      if (missingRequired.length > 0) {
        setError(`Missing required: ${missingRequired.join(", ")}`);
        return;
      }
      // Build subset blueprint containing the node and its dependencies
      const all = (bp.nodes || []) as any[];
      const depsOf: Record<string, string[]> = {};
      all.forEach((n) => { depsOf[n.id] = Array.isArray(n.dependencies) ? n.dependencies : []; });
      const include = new Set<string>();
      const stack = [nodeId];
      while (stack.length) {
        const cur = stack.pop()!;
        if (include.has(cur)) continue;
        include.add(cur);
        (depsOf[cur] || []).forEach((d) => stack.push(d));
      }
      const nodes = all
        .filter((n) => include.has(n.id))
        .map((n) => ({ id: n.id, type: n.type, dependencies: n.dependencies || [], ...n }));
      const ack = await mcp.runs.start({ blueprint: { nodes } as any });
      execStore.start(mcp.runs.eventsUrl(ack.run_id));
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  async function suggestNodeEdit() {
    try {
      const canvas_state = { blueprint: bp ?? { nodes: [] } } as Record<string, unknown>;
      const r = await svcSuggest(nodeText, canvas_state);
      const all = (r as any)?.patches ?? [];
      const filtered = Array.isArray(all) ? all.filter((p: any) => {
        // Best-effort: keep patches that target this node id when present
        if (p && typeof p === "object") {
          if (p.id && String(p.id) === nodeId) return true;
          if (p.node_id && String(p.node_id) === nodeId) return true;
        }
        return false;
      }) : [];
      setPendingPatches(filtered.length > 0 ? filtered : all);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  async function applyNodePatches() {
    try {
      const base = (bp ?? { nodes: [] }) as Record<string, unknown>;
      const r = await svcApply(base, pendingPatches);
      const next = { blueprint: (r as any).blueprint } as any;
      onChange(next.blueprint);
      // Auto-layout after applying node patches
      try { useCanvasStore.getState().autoLayout(); } catch {}
      setPendingPatches([]);
      setNodeText("");
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  // Schema is best-effort; render editor even if schema fails to load
  const errorBanner = error ? (
    <div className="mb-2 border border-red-900 bg-red-950/40 text-red-300 rounded p-2 text-xs">{error}</div>
  ) : null;

  // Best-effort schema-driven validation hints (required fields missing)
  const nodeObj = ((bp?.nodes || []) as any[]).find((n) => n.id === nodeId) || {};
  const required = schema && Array.isArray((schema as any)?.required) ? (schema as any).required as string[] : [];
  const missingRequired = required.filter((key) => {
    const v = (nodeObj as any)?.[key];
    if (v === undefined || v === null) return true;
    if (typeof v === "string" && v.trim() === "") return true;
    if (Array.isArray(v) && v.length === 0) return true;
    return false;
  });

  // Available roots in node context: upstream dependency IDs + 'inputs'
  const deps: string[] = Array.isArray((nodeObj as any)?.dependencies)
    ? ((nodeObj as any).dependencies as string[])
    : [];
  const availableRoots = new Set<string>(["inputs", ...deps]);

  // Lint prompts (llm) for unresolved roots
  const promptsToScan: string[] = [
    String((nodeObj as any)?.prompt || (nodeObj as any)?.system_prompt || ""),
    String((nodeObj as any)?.user_prompt || ""),
  ].filter((s) => !!s.trim());
  const allPlaceholders = promptsToScan.flatMap((t) => extractPlaceholders(t));
  const placeholderRoots = new Set(getPlaceholderRoots(allPlaceholders));
  const unresolvedRoots = Array.from(placeholderRoots).filter((r) => !availableRoots.has(r));

  // Tool required args lint (based on discovered input_schema.required)
  let toolMissing: string[] = [];
  if (nodeType === "tool" && toolInfo && typeof toolInfo === "object") {
    try {
      const req = Array.isArray((toolInfo as any)?.input_schema?.required)
        ? ((toolInfo as any).input_schema.required as string[])
        : [];
      const args = ((nodeObj as any)?.tool_args || {}) as Record<string, any>;
      toolMissing = req.filter((k) => {
        const v = (args as any)[k];
        if (v === undefined || v === null) return true;
        if (typeof v === "string" && v.trim() === "") return true;
        if (Array.isArray(v) && v.length === 0) return true;
        return false;
      });
    } catch {}
  }

  // Controls inlined per-node type below to avoid unused symbol

  if (nodeType === "llm") return (
    <div className="space-y-2">
      {errorBanner}
      {missingRequired.length > 0 && (
        <div className="border border-amber-700/40 bg-amber-900/10 text-amber-300 rounded p-2 text-xs">
          Missing required: {missingRequired.join(", ")}
        </div>
      )}
      {unresolvedRoots.length > 0 && (
        <div className="border border-amber-700/40 bg-amber-900/10 text-amber-300 rounded p-2 text-xs">
          Unresolved context in prompt: {unresolvedRoots.join(", ")}. Available roots: {Array.from(availableRoots).join(", ")}
        </div>
      )}
      <div className="border border-neutral-800 rounded p-2 text-xs text-neutral-400">
        <div className="mb-1 text-neutral-300">Context preview (roots)</div>
        <div className="flex flex-wrap gap-2">
          {Array.from(availableRoots).map((k) => (
            <span key={k} className="px-2 py-0.5 border border-neutral-700 rounded bg-neutral-900">{k}</span>
          ))}
        </div>
      </div>
      <LLMInspector node={nodeObj || {}} setField={setField} />
      <div className="text-[11px] text-neutral-500">System and user prompts can be edited anytime; provider/model are required.</div>
      <div className="mt-2 flex items-center gap-2">
        <button onClick={suggestNodeEdit} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Validate</button>
        <button onClick={applyNodePatches} disabled={pendingPatches.length === 0} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Apply</button>
        <button onClick={runNode} disabled={missingRequired.length > 0 || unresolvedRoots.length > 0} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Run node</button>
      </div>
    </div>
  );
  if (nodeType === "tool") return (
    <div className="space-y-2">
      {errorBanner}
      {toolErr && <div className="border border-red-900 bg-red-950/40 text-red-300 rounded p-2 text-xs">{toolErr}</div>}
      {toolMissing.length > 0 && (
        <div className="border border-amber-700/40 bg-amber-900/10 text-amber-300 rounded p-2 text-xs">
          Missing required tool args: {toolMissing.join(", ")}
        </div>
      )}
      <div className="border border-neutral-800 rounded p-2 text-xs text-neutral-400">
        <div className="mb-1 text-neutral-300">Context preview (roots)</div>
        <div className="flex flex-wrap gap-2">
          {Array.from(availableRoots).map((k) => (
            <span key={k} className="px-2 py-0.5 border border-neutral-700 rounded bg-neutral-900">{k}</span>
          ))}
        </div>
      </div>
      <ToolInspector node={nodeObj || {}} setField={setField} />
      <div className="mt-2 flex items-center gap-2">
        <button onClick={suggestNodeEdit} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Validate</button>
        <button onClick={applyNodePatches} disabled={pendingPatches.length === 0} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Apply</button>
        <button onClick={runNode} disabled={toolMissing.length > 0} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Run node</button>
      </div>
    </div>
  );
  if (nodeType === "agent") return (
    <div className="space-y-2">
      {errorBanner}
      {missingRequired.length > 0 && (
        <div className="border border-amber-700/40 bg-amber-900/10 text-amber-300 rounded p-2 text-xs">
          Missing required: {missingRequired.join(", ")}
        </div>
      )}
      {unresolvedRoots.length > 0 && (
        <div className="border border-amber-700/40 bg-amber-900/10 text-amber-300 rounded p-2 text-xs">
          Unresolved context in prompt: {unresolvedRoots.join(", ")}. Available roots: {Array.from(availableRoots).join(", ")}
        </div>
      )}
      <div className="border border-neutral-800 rounded p-2 text-xs text-neutral-400">
        <div className="mb-1 text-neutral-300">Context preview (roots)</div>
        <div className="flex flex-wrap gap-2">
          {Array.from(availableRoots).map((k) => (
            <span key={k} className="px-2 py-0.5 border border-neutral-700 rounded bg-neutral-900">{k}</span>
          ))}
        </div>
      </div>
      <AgentInspector node={nodeObj || {}} setField={setField} />
      <div className="text-[11px] text-neutral-500">Enable memory only if you provide clear memory instructions. Attach tools intentionally.</div>
      <div className="mt-2 flex items-center gap-2">
        <button onClick={suggestNodeEdit} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Validate</button>
        <button onClick={applyNodePatches} disabled={pendingPatches.length === 0} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Apply</button>
        <button onClick={runNode} disabled={missingRequired.length > 0 || unresolvedRoots.length > 0} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Run node</button>
      </div>
    </div>
  );

  return (
    <div className="space-y-3">
      {errorBanner}
      {missingRequired.length > 0 && (
        <div className="border border-amber-700/40 bg-amber-900/10 text-amber-300 rounded p-2 text-xs">Missing required: {missingRequired.join(", ")}</div>
      )}
      <div className="text-neutral-500 text-xs">No custom inspector yet for {nodeType}.</div>
      <div className="border-t border-neutral-800 pt-2">
        <div className="text-neutral-300 text-xs mb-1">Suggest a node edit</div>
        <div className="flex items-center gap-2">
          <input value={nodeText} onChange={(e) => setNodeText(e.target.value)} placeholder="Describe a change to this node" className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" />
          <button onClick={suggestNodeEdit} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Suggest</button>
          <button onClick={applyNodePatches} disabled={pendingPatches.length === 0} className="text-xs px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Apply</button>
        </div>
        {pendingPatches.length > 0 && (
          <div className="mt-2 text-xs text-neutral-400">Patches ready: {pendingPatches.length}</div>
        )}
      </div>
    </div>
  );
}
