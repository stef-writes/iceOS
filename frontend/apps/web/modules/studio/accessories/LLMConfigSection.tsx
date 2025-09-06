"use client";
import { useState, useEffect } from "react";
import { Input } from "@/modules/ui/primitives/Input";

export function LLMConfigSection({ code, setCode }: { code: string; setCode: (v: string) => void }) {
  const [model, setModel] = useState<string>("");
  const [temperature, setTemperature] = useState<string>("");
  const [maxTokens, setMaxTokens] = useState<string>("");

  useEffect(() => {
    try {
      const obj = JSON.parse(code || "{}");
      const n = Array.isArray(obj.nodes) ? obj.nodes.find((x: any) => x?.type === "llm") : obj;
      if (n) {
        setModel(String(n.model ?? n?.llm_config?.model ?? ""));
        setTemperature(n.temperature != null ? String(n.temperature) : "");
        setMaxTokens(n.max_tokens != null ? String(n.max_tokens) : "");
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function apply() {
    try {
      const obj = JSON.parse(code || "{}");
      const nodes = Array.isArray(obj.nodes) ? obj.nodes : [];
      const idx = nodes.findIndex((x: any) => x?.type === "llm");
      if (idx >= 0) {
        nodes[idx] = {
          ...nodes[idx],
          model: model || nodes[idx].model,
          temperature: temperature ? Number(temperature) : nodes[idx].temperature,
          max_tokens: maxTokens ? Number(maxTokens) : nodes[idx].max_tokens,
          llm_config: { ...(nodes[idx].llm_config || {}), model: model || nodes[idx]?.llm_config?.model },
        };
        obj.nodes = nodes;
        setCode(JSON.stringify(obj, null, 2));
      }
    } catch {}
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        <Input placeholder="model" value={model} onChange={(e) => setModel(e.target.value)} />
        <Input placeholder="temperature" value={temperature} onChange={(e) => setTemperature(e.target.value)} />
        <Input placeholder="max_tokens" value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} />
      </div>
      <button className="text-xs px-2 py-1 border border-border rounded hover:bg-neutral-900" onClick={apply}>Apply</button>
    </div>
  );
}
