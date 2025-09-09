"use client";
import { useEffect, useMemo, useState } from "react";
import { meta } from "@/modules/api/client";

export default function LLMInspector({ node, setField }: { node: any; setField: (path: string, value: unknown) => void }) {
  const [providers, setProviders] = useState<Array<{ id: string; label: string }>>([]);
  const [models, setModels] = useState<Array<{ id: string; provider: string; label: string }>>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const provider = String(node.provider || node?.llm_config?.provider || "");
  const model = String(node.model || node?.llm_config?.model || "");

  useEffect(() => {
    setLoading(true);
    meta.models()
      .then((cat: { providers: Array<{ id: string; label: string }>; models: Array<{ id: string; provider: string; label: string }>; defaults?: Record<string,string> }) => {
        setProviders(cat.providers || []);
        setModels((cat.models || []).map((m: any) => ({ id: m.id, provider: m.provider, label: m.label })));
        if (!provider && cat.defaults?.provider) setField("provider", cat.defaults.provider);
        if (!model && cat.defaults?.model) setField("model", cat.defaults.model);
      })
      .finally(() => setLoading(false));
  }, []);

  const providerModels = useMemo(() => models.filter((m) => m.provider === provider), [models, provider]);

  return (
    <div className="space-y-2">
      <div className="text-neutral-300">LLM</div>
      <div className="flex items-center gap-2">
        <select value={provider} onChange={(e) => setField("provider", e.target.value)} className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm">
          <option value="" disabled>{loading?"loading…":"select provider"}</option>
          {providers.map((p) => (<option key={p.id} value={p.id}>{p.label}</option>))}
        </select>
        <select value={model} onChange={(e) => setField("model", e.target.value)} className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm">
          <option value="" disabled>{provider? (loading?"loading…":"select model") : "select provider first"}</option>
          {providerModels.map((m) => (<option key={m.id} value={m.id}>{m.label}</option>))}
        </select>
      </div>
      <div className="flex items-center gap-2">
        <input type="number" step="0.01" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="temperature" defaultValue={node.temperature ?? ""} onChange={(e) => setField("temperature", parseFloat(e.target.value))} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="max_tokens" defaultValue={node.max_tokens ?? ""} onChange={(e) => setField("max_tokens", parseInt(e.target.value||"0",10) || undefined)} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="timeout_s" defaultValue={node.timeout_seconds ?? ""} onChange={(e) => setField("timeout_seconds", parseInt(e.target.value||"0",10) || undefined)} />
      </div>
      <textarea className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs font-mono" placeholder="system_prompt" defaultValue={node.system_prompt || ""} onChange={(e) => setField("system_prompt", e.target.value)} />
      <textarea className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs font-mono" placeholder="user_prompt (optional)" defaultValue={node.user_prompt || ""} onChange={(e) => setField("user_prompt", e.target.value)} />
      <div className="text-[11px] text-neutral-400">Provider/model are selected from approved lists. Prompts are saved with the node.</div>
    </div>
  );
}
