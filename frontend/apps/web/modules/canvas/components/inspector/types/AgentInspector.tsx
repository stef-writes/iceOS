"use client";
export default function AgentInspector({ node, setField }: { node: any; setField: (path: string, value: unknown) => void }) {
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
        <select defaultValue={node.llm_config?.provider || ""} onChange={(e) => setField("llm_config", { ...(node.llm_config||{}), provider: e.target.value })} className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm">
          <option value="">provider</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="google">Google</option>
        </select>
        <input className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="model" defaultValue={node.llm_config?.model || ""} onChange={(e) => setField("llm_config", { ...(node.llm_config||{}), model: e.target.value })} />
      </div>
      <div className="flex items-center gap-2">
        <input type="number" step="0.01" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="temperature" defaultValue={node.llm_config?.temperature ?? ""} onChange={(e) => setField("llm_config", { ...(node.llm_config||{}), temperature: parseFloat(e.target.value) })} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="max_tokens" defaultValue={node.llm_config?.max_tokens ?? ""} onChange={(e) => setField("llm_config", { ...(node.llm_config||{}), max_tokens: parseInt(e.target.value||"0",10) || undefined })} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="timeout_s" defaultValue={node.llm_config?.timeout_seconds ?? ""} onChange={(e) => setField("llm_config", { ...(node.llm_config||{}), timeout_seconds: parseInt(e.target.value||"0",10) || undefined })} />
      </div>
      <div className="text-[11px] text-neutral-400">Provider and model are required.</div>
    </div>
  );
}
