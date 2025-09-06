"use client";
import { useState, useEffect } from "react";
import MonacoEditor from "@/modules/studio/editor/MonacoEditor";
import { useSearchParams } from "next/navigation";
import { mcp } from "@/modules/api/client";
import ComponentEditor from "@/modules/studio/components/ComponentEditor";
import BlueprintEditor from "@/modules/studio/components/BlueprintEditor";
import { AccessoryDock } from "@/modules/studio/accessories/AccessoryDock";
import { ExecutionDrawer } from "@/modules/shell/ExecutionDrawer";
import CopilotChat from "@/modules/canvas/components/CopilotChat";
import AgentBuilder from "@/modules/studio/agent/AgentBuilder";
import ToolBuilder from "@/modules/studio/tool/ToolBuilder";
// ComposePanel is not used in single-column Studio; keep builder in Canvas

type Blueprint = { nodes?: Array<Record<string, unknown>> };

export default function StudioView() {
  const [code, setCode] = useState<string>("// Start here\n");
  const [runOpen, setRunOpen] = useState<boolean>(false);
  const sp = useSearchParams();
  // router reserved for future navigation
  // no router in single-column view
  const [bp, setBp] = useState<Blueprint | null>(null);
  // Single-column editor: no tabs; execution opens as slide-over panel
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        const form = document.querySelector("button[data-action=save]") as HTMLButtonElement | null;
        form?.click();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        const runBtn = document.querySelector("button[data-action=validate]") as HTMLButtonElement | null;
        runBtn?.click();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => {
    const t = sp.get("type");
    const name = sp.get("name");
    const bp = sp.get("blueprintId");
    (async () => {
      if (t && name) {
        try {
          const res: any = await mcp.components.get(t, name);
          const def = res?.definition ?? res?.data ?? res;
          const pretty = JSON.stringify(def, null, 2);
          setCode(pretty);
        } catch {}
      } else if (bp) {
        try {
          const obj = await mcp.blueprints.get(bp);
          setCode(JSON.stringify(obj, null, 2));
        } catch {}
      }
    })();
  }, [sp]);
  return (
    <div className="relative p-3 text-sm">
      <div className="mb-3 flex items-center justify-end">
        <button onClick={() => setRunOpen(true)} className="px-3 py-1 rounded border border-neutral-700 hover:bg-neutral-800">Run</button>
      </div>
      <StudioBody code={code} setCode={setCode} bp={bp} setBp={setBp} />

      {runOpen && (
        <div className="absolute inset-0 z-20">
          <div className="absolute inset-0 bg-black/50" onClick={() => setRunOpen(false)} />
          <div className="absolute right-0 top-0 h-full w-[420px] bg-neutral-950 border-l border-neutral-800 p-3 overflow-auto">
            <div className="flex items-center justify-between mb-2">
              <div className="text-neutral-300">Execution</div>
              <button onClick={() => setRunOpen(false)} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Close</button>
            </div>
            <ExecutionDrawer />
          </div>
        </div>
      )}
    </div>
  );
}

function StudioBody({ code, setCode, bp, setBp }: { code: string; setCode: (s: string) => void; bp: Blueprint | null; setBp: (b: Blueprint | null) => void }) {
  const sp = useSearchParams();
  const [advanced, setAdvanced] = useState(false);
  const [queue, setQueue] = useState<Array<{ id: string; kind: string; status: "ready"|"missing"|"unresolved"; detail: string }>>([]);

  function recomputeQueue(nextBp: Blueprint | null) {
    const items: Array<{ id: string; kind: string; status: "ready"|"missing"|"unresolved"; detail: string }> = [];
    const nodes = Array.isArray(nextBp?.nodes) ? (nextBp!.nodes as any[]) : [];
    nodes.forEach((n) => {
      const kind = String(n.type || "");
      // Required minimal checks
      const missing: string[] = [];
      if (kind === "llm") {
        if (!n.provider && !n.llm_config?.provider) missing.push("provider");
        if (!n.model && !n.llm_config?.model) missing.push("model");
      }
      if (kind === "agent") {
        if (!n.llm_config?.provider) missing.push("llm_config.provider");
        if (!n.llm_config?.model) missing.push("llm_config.model");
      }
      // Placeholder roots
      const texts: string[] = [];
      if (typeof n.prompt === "string") texts.push(n.prompt);
      if (typeof n.system_prompt === "string") texts.push(n.system_prompt);
      if (typeof n.user_prompt === "string") texts.push(n.user_prompt);
      if (n && typeof n.tool_args === "object" && n.tool_args !== null) {
        Object.values(n.tool_args).forEach((v: any) => { if (typeof v === "string") texts.push(v); });
      }
      const re = /\{\{\s*([^}]+?)\s*\}\}/g;
      const roots = new Set<string>();
      texts.forEach((t) => {
        let m: RegExpExecArray | null;
        while ((m = re.exec(String(t))) !== null) {
          const key = String(m[1] || "").trim();
          const dot = key.indexOf(".");
          const bracket = key.indexOf("[");
          const idx = [dot, bracket].filter((x) => x >= 0).sort((a,b)=>a-b)[0];
          const root = idx >= 0 ? key.slice(0, idx) : key;
          roots.add(root);
        }
      });
      const deps: string[] = Array.isArray(n.dependencies) ? (n.dependencies as string[]) : [];
      const available = new Set<string>(["inputs", ...deps]);
      const unresolved = Array.from(roots).filter((r) => !available.has(r));
      if (missing.length > 0) {
        items.push({ id: String(n.id), kind, status: "missing", detail: missing.join(", ") });
      } else if (unresolved.length > 0) {
        items.push({ id: String(n.id), kind, status: "unresolved", detail: unresolved.join(", ") });
      } else {
        items.push({ id: String(n.id), kind, status: "ready", detail: "" });
      }
    });
    setQueue(items);
  }

  // Recompute when blueprint changes
  useEffect(() => { recomputeQueue(bp); }, [bp]);

  if (sp.get("type") && sp.get("name")) {
    return <ComponentEditor type={sp.get("type") as string} name={sp.get("name") as string} />;
  }
  if (sp.get("blueprintId")) {
    return <BlueprintEditor blueprintId={sp.get("blueprintId") as string} />;
  }

  return (
    <div>
      <div className="mb-2 flex items-center gap-2 text-xs">
        <span className="text-neutral-400">Mode</span>
        <button onClick={() => setAdvanced(false)} className={`px-2 py-1 border rounded ${!advanced?"border-neutral-500 bg-neutral-800":"border-neutral-800 hover:bg-neutral-900"}`}>Simple</button>
        <button onClick={() => setAdvanced(true)} className={`px-2 py-1 border rounded ${advanced?"border-neutral-500 bg-neutral-800":"border-neutral-800 hover:bg-neutral-900"}`}>Advanced</button>
        <span className="ml-4 text-neutral-400">Builder</span>
        <a className={`px-2 py-1 border rounded ${sp.get("builder")==="agent"?"border-neutral-500 bg-neutral-800":"border-neutral-800 hover:bg-neutral-900"}`} href="/studio?builder=agent">Agent</a>
        <a className={`px-2 py-1 border rounded ${sp.get("builder")==="tool"?"border-neutral-500 bg-neutral-800":"border-neutral-800 hover:bg-neutral-900"}`} href="/studio?builder=tool">Tool</a>
      </div>

      {!advanced ? (
        <div className="space-y-3">
          <div className="border border-neutral-800 rounded p-3">
            <div className="text-neutral-300 mb-2">Studio Copilot</div>
            <CopilotChat bp={bp} onApplyBlueprint={(next) => setBp(next as any)} />
          </div>
          {sp.get("builder") === "agent" && (
            <div className="border border-neutral-800 rounded p-3">
              <div className="text-neutral-300 mb-2">Agent Builder</div>
              <AgentBuilder />
            </div>
          )}
          {sp.get("builder") === "tool" && (
            <div className="border border-neutral-800 rounded p-3">
              <div className="text-neutral-300 mb-2">Tool Builder</div>
              <ToolBuilder />
            </div>
          )}
          <div className="border border-neutral-800 rounded p-3">
            <div className="text-neutral-300 mb-2">Validation Queue</div>
            {queue.length === 0 ? (
              <div className="text-xs text-neutral-500">No nodes yet.</div>
            ) : (
              <div className="space-y-1">
                {queue.map((q) => (
                  <div key={q.id} className="flex items-center justify-between text-xs border border-neutral-800 rounded px-2 py-1">
                    <div>
                      <span className="text-neutral-300 mr-2">{q.kind}:{q.id}</span>
                      {q.status === "ready" && <span className="px-1.5 py-0.5 border border-green-900/50 rounded text-green-300">Ready</span>}
                      {q.status === "missing" && <span className="px-1.5 py-0.5 border border-amber-900/50 rounded text-amber-300">Missing: {q.detail}</span>}
                      {q.status === "unresolved" && <span className="px-1.5 py-0.5 border border-red-900/50 rounded text-red-300">Unresolved: {q.detail}</span>}
                    </div>
                    <div className="flex items-center gap-2">
                      <a className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800" href={`/canvas?sel=${encodeURIComponent(q.id)}`}>Open in Canvas</a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          {bp && (
            <div className="text-xs text-neutral-400">Blueprint nodes: {Array.isArray(bp.nodes) ? bp.nodes.length : 0}</div>
          )}
        </div>
      ) : (
        <div>
          <div className="mb-2 text-neutral-300">Studio (IDE) – Monaco editor</div>
          <MonacoEditor value={code} onChange={setCode} language="typescript" height="60vh" />
          <div className="mt-3">
            <AccessoryDock code={code} setCode={setCode} />
          </div>
        </div>
      )}
    </div>
  );
}
