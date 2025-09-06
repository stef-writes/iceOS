"use client";
export default function LLMInspector({ node, setField }: { node: any; setField: (path: string, value: unknown) => void }) {
  return (
    <div className="space-y-2">
      <div className="text-neutral-300">LLM</div>
      <div className="flex items-center gap-2">
        <select defaultValue={node.provider || ""} onChange={(e) => setField("provider", e.target.value)} className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm">
          <option value="">provider</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="google">Google</option>
        </select>
        <input className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="model" defaultValue={node.model || ""} onChange={(e) => setField("model", e.target.value)} />
      </div>
      <div className="flex items-center gap-2">
        <input type="number" step="0.01" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="temperature" defaultValue={node.temperature ?? ""} onChange={(e) => setField("temperature", parseFloat(e.target.value))} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="max_tokens" defaultValue={node.max_tokens ?? ""} onChange={(e) => setField("max_tokens", parseInt(e.target.value||"0",10) || undefined)} />
        <input type="number" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="timeout_s" defaultValue={node.timeout_seconds ?? ""} onChange={(e) => setField("timeout_seconds", parseInt(e.target.value||"0",10) || undefined)} />
      </div>
      <textarea className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs font-mono" placeholder="system_prompt" defaultValue={node.system_prompt || ""} onChange={(e) => setField("system_prompt", e.target.value)} />
      <textarea className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs font-mono" placeholder="user_prompt (optional)" defaultValue={node.user_prompt || ""} onChange={(e) => setField("user_prompt", e.target.value)} />
      <div className="text-[11px] text-neutral-400">Provider and model are required. Prompts are saved with the node.</div>
    </div>
  );
}
