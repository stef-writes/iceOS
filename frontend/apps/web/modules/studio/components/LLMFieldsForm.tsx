"use client";
import { useState } from "react";
import { z } from "zod";

const llmSchema = z.object({
  model: z.string().min(1, "Model is required").default("gpt-4o"),
  prompt: z.string().min(1, "Prompt is required"),
  temperature: z.number().min(0).max(2).default(0.7),
  top_p: z.number().min(0).max(1).optional(),
  max_tokens: z.number().int().positive().optional(),
  stop_sequences: z.array(z.string()).optional(),
});

export type LLMFields = z.infer<typeof llmSchema>;

export function LLMFieldsForm({ value, onChange }: { value: Partial<LLMFields>; onChange: (v: LLMFields) => void }) {
  const [local, setLocal] = useState<Partial<LLMFields>>({
    model: value.model ?? "gpt-4o",
    prompt: value.prompt ?? "",
    temperature: value.temperature ?? 0.7,
    top_p: value.top_p,
    max_tokens: value.max_tokens,
    stop_sequences: value.stop_sequences ?? [],
  });
  const [error, setError] = useState<string | null>(null);

  function commit<K extends keyof LLMFields>(key: K, raw: unknown) {
    const next = { ...local, [key]: raw };
    setLocal(next);
    try {
      const parsed = llmSchema.parse({
        model: String(next.model ?? "gpt-4o"),
        prompt: String(next.prompt ?? ""),
        temperature: Number(next.temperature ?? 0.7),
        top_p: next.top_p != null && String(next.top_p).length > 0 ? Number(next.top_p) : undefined,
        max_tokens: next.max_tokens != null && String(next.max_tokens).length > 0 ? Number(next.max_tokens) : undefined,
        stop_sequences: Array.isArray(next.stop_sequences) ? next.stop_sequences.filter(Boolean) : undefined,
      });
      setError(null);
      onChange(parsed);
    } catch (e: any) {
      setError(String(e?.errors?.[0]?.message || e?.message || e));
    }
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        <div className="col-span-2">
          <div className="text-xs text-neutral-400 mb-1">Model</div>
          <input
            placeholder="gpt-4o"
            className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs"
            value={local.model ?? ""}
            onChange={(e) => commit("model", e.target.value)}
          />
        </div>
        <div>
          <div className="text-xs text-neutral-400 mb-1">Max Tokens</div>
          <input
            type="number"
            min={1}
            step={1}
            className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs"
            value={local.max_tokens ?? ""}
            onChange={(e) => commit("max_tokens", e.target.value === "" ? undefined : parseInt(e.target.value))}
          />
        </div>
      </div>
      <div>
        <div className="text-xs text-neutral-400 mb-1">Prompt</div>
        <textarea
          className="w-full h-24 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs"
          value={local.prompt ?? ""}
          onChange={(e) => commit("prompt", e.target.value)}
        />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <div>
          <div className="text-xs text-neutral-400 mb-1">Temperature</div>
          <input
            type="number"
            min={0}
            max={2}
            step={0.1}
            className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs"
            value={Number(local.temperature ?? 0.7)}
            onChange={(e) => commit("temperature", parseFloat(e.target.value))}
          />
        </div>
        <div>
          <div className="text-xs text-neutral-400 mb-1">Top P</div>
          <input
            type="number"
            min={0}
            max={1}
            step={0.01}
            className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs"
            value={local.top_p ?? ""}
            onChange={(e) => commit("top_p", e.target.value === "" ? undefined : parseFloat(e.target.value))}
          />
        </div>
        <div>
          <div className="text-xs text-neutral-400 mb-1">Stop sequences (comma-separated)</div>
          <input
            type="text"
            className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs"
            value={(local.stop_sequences ?? []).join(", ")}
            onChange={(e) => commit("stop_sequences", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
          />
        </div>
      </div>
      {error && <div className="text-red-400 text-xs">{error}</div>}
    </div>
  );
}
