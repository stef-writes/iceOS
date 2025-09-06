"use client";
import { useState } from "react";
import { suggest as svcSuggest, applyPatches as svcApply } from "@/modules/canvas/services/builderApi";
import { useCanvasStore } from "@/modules/canvas/state/useCanvasStore";

type Blueprint = { nodes?: Array<Record<string, unknown>> };

export default function ComposeBar({ bp, onApplyBlueprint }: { bp: Blueprint | null; onApplyBlueprint: (next: Blueprint) => void }) {
  // Deprecated in favor of CopilotChat; keep file temporarily to avoid breaking imports
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [patches, setPatches] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [questions, setQuestions] = useState<string[]>([]);
  const [missing, setMissing] = useState<Record<string, unknown>>({});
  const [info, setInfo] = useState<string | null>(null);
  const [cost, setCost] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const selected = useCanvasStore((s) => s.selected) as any as { id: string; type: string } | null;
  const [urlInput, setUrlInput] = useState("");
  const [urls, setUrls] = useState<string[]>([]);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState("");

  function summarizePatch(p: any): string {
    try {
      const op = String((p?.op ?? p?.operation ?? (p?.add ? "add" : p?.remove ? "remove" : p?.update ? "update" : "edit"))).toLowerCase();
      const id = String(p?.id ?? p?.node_id ?? p?.target_id ?? "");
      const ntype = String(p?.type ?? p?.node_type ?? "");
      let details = "";
      if (p?.changes && typeof p.changes === "object") {
        const keys = Object.keys(p.changes);
        if (keys.length) details = ` changes: ${keys.slice(0, 3).join(", ")}${keys.length > 3 ? "…" : ""}`;
      } else if (p?.node && typeof p.node === "object") {
        details = " new node";
      }
      const idPart = id ? id : "(graph)";
      const typePart = ntype ? ` · ${ntype}` : "";
      return `[${op}] ${idPart}${typePart}${details}`;
    } catch {
      return "[edit] (unrecognized patch)";
    }
  }

  function tryQuickCommand(input: string): boolean {
    // 1) add <type> [args] [after selected] [; connect to <nodeId|selected>]
    const addRe = /add\s+(llm|tool|agent|condition|parallel|loop|code|swarm|recursive|human|monitor)(?:\s+([^;]+))?(?:\s+after\s+selected)?(?:\s*;\s*connect\s+to\s+(\w+|selected))?/i;
    const mAdd = input.match(addRe);
    if (mAdd) {
      const [, rawType, argStr, rawTarget] = mAdd;
      const type = String(rawType).toLowerCase();
      const newId = `n${Math.floor(Math.random() * 1e6)}`;
      const next: Blueprint = { nodes: Array.isArray(bp?.nodes) ? [...(bp!.nodes!)] : [] } as any;
      const node: any = { id: newId, type, dependencies: [] as string[] };
      if (type === "tool" && argStr) node.tool_name = argStr.trim();
      if (type === "llm" && argStr) node.model = argStr.trim();
      next.nodes = [...(next.nodes || []), node];
      let targetId = rawTarget;
      if ((!targetId || String(targetId).toLowerCase() === "selected") && selected?.id) targetId = selected.id;
      if (targetId) {
        const idx = (next.nodes || []).findIndex((n: any) => String(n.id) === String(targetId));
        if (idx >= 0) {
          const tgt = { ...(next.nodes as any)[idx] };
          const deps: string[] = Array.isArray(tgt.dependencies) ? [...tgt.dependencies] : [];
          if (!deps.includes(newId)) deps.push(newId);
          tgt.dependencies = deps;
          (next.nodes as any)[idx] = tgt;
        }
      }
      onApplyBlueprint(next);
      setInfo(`Added ${type} ${newId}${targetId ? ` and connected to ${targetId}` : ""}.`);
      setPatches([]); setQuestions([]); setMissing({}); setText("");
      return true;
    }

    // 2) connect selected to <nodeId>
    const mConn = input.match(/^connect\s+selected\s+to\s+(\w+)/i);
    if (mConn && selected?.id) {
      const targetId = mConn[1];
      const next: Blueprint = { nodes: Array.isArray(bp?.nodes) ? [...(bp!.nodes!)] : [] } as any;
      const idx = (next.nodes || []).findIndex((n: any) => String(n.id) === String(targetId));
      if (idx >= 0) {
        const tgt = { ...(next.nodes as any)[idx] };
        const deps: string[] = Array.isArray(tgt.dependencies) ? [...tgt.dependencies] : [];
        if (!deps.includes(selected.id)) deps.push(selected.id);
        tgt.dependencies = deps;
        (next.nodes as any)[idx] = tgt;
        onApplyBlueprint(next);
        setInfo(`Connected ${selected.id} → ${targetId}.`);
        setPatches([]); setQuestions([]); setMissing({}); setText("");
        return true;
      }
    }

    // 3) set <field> <value> on selected|<nodeId>
    const mSet = input.match(/^set\s+([a-zA-Z0-9_\.]+)\s+(.+?)(?:\s+on\s+(\w+|selected))?$/i);
    if (mSet) {
      const [, field, valueRaw, targetRaw] = mSet;
      const targetId = (!targetRaw || String(targetRaw).toLowerCase()==="selected") ? selected?.id : targetRaw;
      if (!targetId) return false;
      const next: Blueprint = { nodes: Array.isArray(bp?.nodes) ? [...(bp!.nodes!)] : [] } as any;
      const idx = (next.nodes || []).findIndex((n: any) => String(n.id) === String(targetId));
      if (idx >= 0) {
        const node = { ...(next.nodes as any)[idx] } as any;
        // simple top-level assignment (no dotted path expansion here)
        const v = valueRaw.trim();
        node[field] = /^\d+(\.\d+)?$/.test(v) ? Number(v) : (v.toLowerCase()==="true"?true:(v.toLowerCase()==="false"?false:v));
        (next.nodes as any)[idx] = node;
        onApplyBlueprint(next);
        setInfo(`Set ${field} on ${targetId}.`);
        setPatches([]); setQuestions([]); setMissing({}); setText("");
        return true;
      }
    }
    return false;
  }

  async function onSuggest() {
    setError(null);
    setLoading(true);
    try {
      // Handle quick commands locally when matched
      if (text.trim().toLowerCase().startsWith("add ")) {
        const handled = tryQuickCommand(text.trim());
        if (handled) { setLoading(false); return; }
      }
      const ctx: Record<string, unknown> = {};
      if (urls.length || noteText.trim()) ctx.attachments = { urls, notes: noteText.trim() ? [noteText] : [] } as any;
      const canvas_state = { blueprint: bp ?? { nodes: [] }, context: ctx } as Record<string, unknown>;
      const r = await svcSuggest(text, canvas_state);
      setPatches((r as any)?.patches ?? []);
      setQuestions(Array.isArray((r as any)?.questions) ? (r as any).questions : []);
      setMissing(typeof (r as any)?.missing_fields === "object" && (r as any)?.missing_fields !== null ? (r as any).missing_fields : {});
      const ce = (r as any)?.cost_estimate_usd;
      setCost(typeof ce === "number" ? ce : null);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }


  async function onApply() {
    setError(null);
    if (!patches.length) { setError("No patches to apply"); return; }
    try {
      const base = (bp ?? { nodes: [] }) as Record<string, unknown>;
      const r = await svcApply(base, patches);
      const next = { blueprint: (r as any).blueprint } as any;
      onApplyBlueprint(next.blueprint);
      // Auto-layout after applying patches
      try { useCanvasStore.getState().autoLayout(); } catch {}
      setPatches([]);
      setQuestions([]);
      setMissing({});
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  async function onApplyOne(idx: number) {
    setError(null);
    try {
      const single = patches[idx];
      if (!single) return;
      const base = (bp ?? { nodes: [] }) as Record<string, unknown>;
      const r = await svcApply(base, [single]);
      const next = { blueprint: (r as any).blueprint } as any;
      onApplyBlueprint(next.blueprint);
      // Auto-layout after applying a single patch
      try { useCanvasStore.getState().autoLayout(); } catch {}
      setPatches((old) => old.filter((_, i) => i !== idx));
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  return (
    <div className="mt-3 border-t border-neutral-800 pt-3">
      <div className="flex items-center gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Suggest an edit (e.g., add an LLM node and connect to tool:writer)"
          className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-3 py-2 text-sm"
        />
        <button onClick={onSuggest} className="px-3 py-2 text-sm border border-neutral-700 rounded hover:bg-neutral-800">{loading ? "Thinking…" : "Suggest"}</button>
        <button onClick={onApply} className="px-3 py-2 text-sm border border-neutral-700 rounded hover:bg-neutral-800">Apply</button>
      </div>
      <div className="mt-2 flex items-center gap-2 text-xs text-neutral-400">
        <input value={urlInput} onChange={(e) => setUrlInput(e.target.value)} placeholder="Add URL context" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
        <button onClick={() => { if (urlInput.trim()) { setUrls((u) => [...u, urlInput.trim()]); setUrlInput(""); } }} className="px-2 py-0.5 border border-neutral-700 rounded hover:bg-neutral-800">Add URL</button>
        {urls.length > 0 && <span className="text-neutral-500">URLs: {urls.length}</span>}
        <button onClick={() => setNoteOpen((o) => !o)} className="px-2 py-0.5 border border-neutral-700 rounded hover:bg-neutral-800">{noteOpen?"Hide note":"Add note"}</button>
      </div>
      {noteOpen && (
        <div className="mt-2">
          <textarea value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Optional context note (used by co‑creator)" className="w-full h-16 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs" />
        </div>
      )}
      {!!patches.length && (
        <div className="mt-2">
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs text-neutral-400">Proposed changes: {patches.length}{cost != null && <span className="ml-2">· est. cost ≈ ${cost.toFixed(4)}</span>}</div>
            <button onClick={onApply} className="text-xs px-2 py-0.5 border border-neutral-700 rounded hover:bg-neutral-800">Apply all</button>
          </div>
          <div className="space-y-2 max-h-48 overflow-auto">
            {patches.map((p, i) => {
              const summary = summarizePatch(p as any);
              const isOpen = !!expanded[i];
              return (
                <div key={i} className="border border-neutral-800 rounded p-2 text-xs bg-neutral-900">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-neutral-300">Patch {i + 1}</div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => setExpanded((old) => ({ ...old, [i]: !isOpen }))} className="px-2 py-0.5 border border-neutral-700 rounded hover:bg-neutral-800">{isOpen ? "Hide" : "Details"}</button>
                      <button onClick={() => onApplyOne(i)} className="px-2 py-0.5 border border-neutral-700 rounded hover:bg-neutral-800">Apply</button>
                    </div>
                  </div>
                  <div className="mb-1 text-neutral-400">{summary}</div>
                  {isOpen && (
                    <pre className="text-[11px] whitespace-pre-wrap break-words">{JSON.stringify(p, null, 2)}</pre>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
      {questions.length > 0 && (
        <div className="mt-2">
          <div className="text-neutral-300 text-xs mb-1">Questions</div>
          <div className="flex flex-wrap gap-2">
            {questions.map((q, i) => (
              <span key={i} className="text-xs px-2 py-1 border border-neutral-800 rounded bg-neutral-900 text-neutral-200">{q}</span>
            ))}
          </div>
        </div>
      )}
      {Object.keys(missing).length > 0 && (
        <div className="mt-2">
          <div className="text-neutral-300 text-xs mb-1">Missing fields</div>
          <pre className="text-xs bg-neutral-900 border border-neutral-800 rounded p-2 overflow-auto max-h-40">{JSON.stringify(missing, null, 2)}</pre>
        </div>
      )}
      {info && <div className="mt-2 text-xs text-green-400">{info}</div>}
      {error && <div className="mt-2 text-xs text-red-400">{error}</div>}
    </div>
  );
}
