"use client";
import { useEffect, useMemo, useState } from "react";
import { meta } from "@/modules/api/client";

export default function AgentInspector({ node, setField }: { node: any; setField: (path: string, value: unknown) => void }) {
  const [providers, setProviders] = useState<Array<{ id: string; label: string }>>([]);
  const [models, setModels] = useState<Array<{ id: string; provider: string; label: string }>>([]);
  const lc = (node?.llm_config && typeof node.llm_config === "object") ? node.llm_config : {};
  const provider = String(lc.provider || "");
  const model = String(lc.model || "");
  const providerModels = useMemo(() => models.filter((m)=>m.provider === provider), [models, provider]);
  useEffect(() => { meta.models().then((cat:any)=>{ setProviders(cat.providers||[]); setModels((cat.models||[]).map((m:any)=>({id:m.id, provider:m.provider, label:m.label}))); if(!provider && cat.defaults?.provider){ setField("llm_config", { ...(lc as any), provider: cat.defaults.provider }); } if(!model && cat.defaults?.model){ setField("llm_config", { ...(lc as any), provider: provider || cat.defaults?.provider || "", model: cat.defaults.model }); } }).catch(()=>{}); }, []);
  return (
    <div className="space-y-2">
      <div className="text-neutral-300">Agent</div>
      <input className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="name" defaultValue={node.name || ""} onChange={(e) => setField("name", e.target.value)} />
      <textarea className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs" placeholder="system_prompt" defaultValue={node.system_prompt || ""} onChange={(e) => setField("system_prompt", e.target.value)} />
      <input className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="tools (comma-separated)" defaultValue={(node.tools || []).join(",")} onChange={(e) => setField("tools", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} />
      <div className="flex items-center gap-2">
        <label className="text-xs text-neutral-400 flex items-center gap-1">
          <input type="checkbox" defaultChecked={!!node.memory_enabled} onChange={(e)=>setField("memory_enabled", e.target.checked)} />
          enable memory
        </label>
        <input className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="memory instructions (optional)" defaultValue={node.memory_instructions || ""} onChange={(e) => setField("memory_instructions", e.target.value)} />
      </div>
      <textarea className="w-full h-16 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs" placeholder="per-tool instructions (JSON: { tool_name: instructions })" defaultValue={JSON.stringify(node.tool_instructions || {}, null, 2)} onChange={(e) => {
        try {
          const obj = JSON.parse(e.target.value || "{}");
          setField("tool_instructions", obj);
        } catch {
          // ignore parse errors to avoid noisy UX; apply when valid
        }
      }} />
      <div className="flex items-center gap-2">
        <select value={provider} onChange={(e) => setField("llm_config", { ...(lc as any), provider: e.target.value })} className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm">
          <option value="">provider</option>
          {providers.map((p)=>(<option key={p.id} value={p.id}>{p.label}</option>))}
        </select>
        <select value={model} onChange={(e)=> setField("llm_config", { ...(lc as any), provider, model: e.target.value })} disabled={!provider} className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm">
          <option value="">{provider?"model":"select provider first"}</option>
          {providerModels.map((m)=>(<option key={m.id} value={m.id}>{m.label}</option>))}
        </select>
      </div>
      <div className="flex items-center gap-2">
        <input type="number" step="0.01" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="temperature" defaultValue={lc?.temperature ?? ""} onChange={(e) => setField("llm_config", { ...(lc as any), temperature: parseFloat(e.target.value) })} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="max_tokens" defaultValue={lc?.max_tokens ?? ""} onChange={(e) => setField("llm_config", { ...(lc as any), max_tokens: parseInt(e.target.value||"0",10) || undefined })} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="timeout_s" defaultValue={lc?.timeout_seconds ?? ""} onChange={(e) => setField("llm_config", { ...(lc as any), timeout_seconds: parseInt(e.target.value||"0",10) || undefined })} />
      </div>
      <div className="text-[11px] text-neutral-400">Provider and model are required.</div>
    </div>
  );
}
