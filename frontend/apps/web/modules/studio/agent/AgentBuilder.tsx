"use client";
import { useEffect, useMemo, useState } from "react";
import { mcp, library } from "@/modules/api/client";

type AgentSpec = {
  id: string;
  type: "agent";
  dependencies: string[];
  name?: string;
  system_prompt?: string;
  user_prompt?: string;
  llm_config: {
    provider?: string;
    model?: string;
    temperature?: number;
    max_tokens?: number;
    timeout_seconds?: number;
  };
  memory_enabled?: boolean;
  memory_instructions?: string;
  tools?: string[];
  per_tool_instructions?: Record<string, string>;
};

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

function getRoot(key: string): string {
  const dot = key.indexOf(".");
  const bracket = key.indexOf("[");
  const idx = [dot, bracket].filter((n) => n >= 0).sort((a, b) => a - b)[0];
  return idx >= 0 ? key.slice(0, idx) : key;
}

const MEMORY_PRESETS: Array<{ id: string; label: string; instructions: string }> = [
  { id: "none", label: "No memory", instructions: "" },
  { id: "scratchpad", label: "Short-term scratchpad", instructions: "Maintain a short-term scratchpad of recent steps to keep continuity within the current task." },
  { id: "session", label: "Session memory", instructions: "Remember the user's preferences and constraints during this session and reuse them to improve responses." },
  { id: "knowledge", label: "Long-term knowledge", instructions: "Persist new facts, glossaries, and definitions for future sessions. Keep entries concise and factual." },
];

export default function AgentBuilder() {
  const [spec, setSpec] = useState<AgentSpec>({
    id: "agent1",
    type: "agent",
    dependencies: [],
    name: "my_agent",
    system_prompt: "You are a helpful agent.",
    user_prompt: "{{ inputs.text }}",
    llm_config: {},
    memory_enabled: false,
    memory_instructions: "",
    tools: [],
    per_tool_instructions: {},
  });
  const [toolQuery, setToolQuery] = useState("");
  const [toolOptions, setToolOptions] = useState<Array<{ name: string; type: string }>>([]);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res: any = await library.index({ kind: "component" });
        const items = Array.isArray(res?.items) ? res.items : Array.isArray(res) ? res : [];
        const tools = items.filter((it: any) => String(it.type || "").toLowerCase() === "tool");
        const simple = tools.map((t: any) => ({ name: String(t.name), type: String(t.type || "tool") }));
        setToolOptions(simple);
      } catch {}
    })();
  }, []);

  function setField(path: string, value: any) {
    setSpec((old) => {
      const next = { ...old } as any;
      if (path.startsWith("llm_config.")) {
        const k = path.split(".")[1];
        next.llm_config = { ...(next.llm_config || {}), [k]: value };
      } else if (path.startsWith("per_tool_instructions.")) {
        const k = path.split(".")[1];
        next.per_tool_instructions = { ...(next.per_tool_instructions || {}), [k]: value };
      } else {
        next[path] = value;
      }
      return next as AgentSpec;
    });
  }

  // Validation
  const requiredMissing: string[] = useMemo(() => {
    const miss: string[] = [];
    if (!spec.llm_config.provider) miss.push("llm_config.provider");
    if (!spec.llm_config.model) miss.push("llm_config.model");
    return miss;
  }, [spec.llm_config]);

  const unresolvedPlaceholders: string[] = useMemo(() => {
    const texts = [spec.system_prompt || "", spec.user_prompt || ""];
    const keys = texts.flatMap((t) => extractPlaceholders(t));
    const roots = Array.from(new Set(keys.map(getRoot)));
    const available = new Set<string>(["inputs"]);
    return roots.filter((r) => !available.has(r));
  }, [spec.system_prompt, spec.user_prompt]);

  const canRun = requiredMissing.length === 0 && unresolvedPlaceholders.length === 0;

  async function runSandbox() {
    if (!canRun) return;
    setRunning(true);
    setError(null);
    try {
      const bp = { nodes: [spec] } as any;
      await mcp.runs.start({ blueprint: bp });
      // Fire-and-forget; user can watch Console on Canvas page
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setRunning(false);
    }
  }

  function addTool(name: string) {
    if (!name) return;
    setSpec((old) => {
      const tools = Array.isArray(old.tools) ? Array.from(new Set([...old.tools, name])) : [name];
      return { ...old, tools };
    });
  }

  return (
    <div className="space-y-3">
      {error && <div className="border border-red-900 bg-red-950/40 text-red-300 rounded p-2 text-xs">{error}</div>}

      <div className="grid grid-cols-2 gap-3">
        <div className="border border-neutral-800 rounded p-2">
          <div className="text-neutral-300 text-sm mb-2">LLM Config</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <input value={spec.llm_config.provider || ""} onChange={(e)=>setField("llm_config.provider", e.target.value)} placeholder="Provider" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <input value={spec.llm_config.model || ""} onChange={(e)=>setField("llm_config.model", e.target.value)} placeholder="Model" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <input value={spec.llm_config.temperature ?? ""} onChange={(e)=>setField("llm_config.temperature", Number(e.target.value))} placeholder="Temperature" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <input value={spec.llm_config.max_tokens ?? ""} onChange={(e)=>setField("llm_config.max_tokens", Number(e.target.value))} placeholder="Max tokens" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <input value={spec.llm_config.timeout_seconds ?? ""} onChange={(e)=>setField("llm_config.timeout_seconds", Number(e.target.value))} placeholder="Timeout (s)" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
          </div>
        </div>

        <div className="border border-neutral-800 rounded p-2">
          <div className="text-neutral-300 text-sm mb-2">Memory</div>
          <div className="flex items-center gap-2 text-xs mb-2">
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={!!spec.memory_enabled} onChange={(e)=>setField("memory_enabled", e.target.checked)} />
              Enable memory
            </label>
            <select value={spec.memory_enabled ? (MEMORY_PRESETS.find(p=>p.instructions===spec.memory_instructions)?.id || "none") : "none"} onChange={(e)=>{
              const preset = MEMORY_PRESETS.find((p)=>p.id===e.target.value);
              if (!preset) return;
              setField("memory_enabled", preset.id !== "none");
              setField("memory_instructions", preset.instructions);
            }} className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1">
              {MEMORY_PRESETS.map((p)=>(<option key={p.id} value={p.id}>{p.label}</option>))}
            </select>
          </div>
          <textarea value={spec.memory_instructions || ""} onChange={(e)=>setField("memory_instructions", e.target.value)} placeholder="Memory instructions" className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs" />
        </div>

        <div className="border border-neutral-800 rounded p-2 col-span-2">
          <div className="text-neutral-300 text-sm mb-2">Prompts</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <textarea value={spec.system_prompt || ""} onChange={(e)=>setField("system_prompt", e.target.value)} placeholder="System prompt" className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <textarea value={spec.user_prompt || ""} onChange={(e)=>setField("user_prompt", e.target.value)} placeholder="User prompt" className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
          </div>
          {unresolvedPlaceholders.length > 0 && (
            <div className="mt-2 text-xs text-amber-300">Unresolved placeholders: {unresolvedPlaceholders.join(", ")}. Available: inputs</div>
          )}
        </div>

        <div className="border border-neutral-800 rounded p-2 col-span-2">
          <div className="text-neutral-300 text-sm mb-2">Tools</div>
          <div className="flex items-center gap-2 text-xs mb-2">
            <input value={toolQuery} onChange={(e)=>setToolQuery(e.target.value)} placeholder="Search tools" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <button onClick={()=>{ const t = toolOptions.find(o=>o.name.includes(toolQuery)); if (t) addTool(t.name); }} className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Add</button>
          </div>
          {Array.isArray(spec.tools) && spec.tools.length > 0 ? (
            <div className="space-y-2 text-xs">
              {spec.tools.map((t) => (
                <div key={t} className="border border-neutral-800 rounded p-2">
                  <div className="flex items-center justify-between">
                    <div className="text-neutral-300">{t}</div>
                    <button onClick={()=> setSpec((old)=> ({...old, tools: (old.tools||[]).filter((x)=>x!==t)}))} className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Remove</button>
                  </div>
                  <textarea value={spec.per_tool_instructions?.[t] || ""} onChange={(e)=>setField(`per_tool_instructions.${t}`, e.target.value)} placeholder="Per-tool instructions" className="mt-2 w-full h-16 bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-neutral-500">No tools selected.</div>
          )}
        </div>
      </div>

      {/* Status & Actions */}
      <div className="flex items-center justify-between">
        <div className="text-xs">
          {requiredMissing.length > 0 && <span className="text-amber-300">Missing: {requiredMissing.join(", ")}</span>}
          {requiredMissing.length === 0 && unresolvedPlaceholders.length === 0 && <span className="text-green-300">Ready</span>}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={runSandbox} disabled={!canRun || running} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">{running?"Running…":"Run sandbox"}</button>
          <button onClick={async()=>{
            setError(null);
            try {
              const component = { type: "agent", name: spec.name || "agent", definition: spec } as any;
              await mcp.components.register(component);
              alert("Published agent component.");
            } catch(e: any){ setError(String(e?.message || e)); }
          }} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Publish</button>
          <button onClick={()=>{
            try {
              sessionStorage.setItem("studio:addNode", JSON.stringify(spec));
              window.location.href = "/canvas";
            } catch(e) {}
          }} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Add to Canvas</button>
          <button onClick={()=>navigator.clipboard.writeText(JSON.stringify(spec, null, 2))} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Copy JSON</button>
          <a href="/canvas" className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Open Canvas</a>
        </div>
      </div>
    </div>
  );
}
