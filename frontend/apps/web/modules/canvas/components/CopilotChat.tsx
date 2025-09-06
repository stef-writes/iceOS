"use client";
import { useRef, useState } from "react";
import { suggest as svcSuggest, applyPatches as svcApply } from "@/modules/canvas/services/builderApi";
import { useCanvasStore } from "@/modules/canvas/state/useCanvasStore";

type Blueprint = { nodes?: Array<Record<string, unknown>> };
type Msg = { role: "user" | "assistant"; content: string };

export default function CopilotChat({ bp, onApplyBlueprint }: { bp: Blueprint | null; onApplyBlueprint: (next: Blueprint) => void }) {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "assistant", content: "Describe changes. Try: Add an LLM node and connect to tool:writer." },
  ]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [patches, setPatches] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  function append(m: Msg) {
    setMessages((old) => [...old, m]);
    setTimeout(() => scrollRef.current?.scrollTo({ top: 1e6, behavior: "smooth" }), 0);
  }

  async function onSend() {
    if (!text.trim()) return;
    const prompt = text.trim();
    setText("");
    append({ role: "user", content: prompt });
    setLoading(true);
    setError(null);
    try {
      const canvas_state = { blueprint: bp ?? { nodes: [] } } as Record<string, unknown>;
      const r: any = await svcSuggest(prompt, canvas_state);
      const nextPatches = Array.isArray(r?.patches) ? r.patches : [];
      const questions = Array.isArray(r?.questions) ? r.questions : [];
      const missing = (typeof r?.missing_fields === "object" && r?.missing_fields !== null) ? r.missing_fields : {};
      setPatches(nextPatches);
      const lines: string[] = [];
      lines.push(`Proposed patches: ${nextPatches.length}`);
      if (questions.length) lines.push(`Questions: ${questions.join(" • ")}`);
      const missingKeys = Object.keys(missing);
      if (missingKeys.length) lines.push(`Missing: ${missingKeys.join(", ")}`);
      append({ role: "assistant", content: lines.join("\n") || "No changes proposed." });
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  }

  async function proposePlan() {
    // Minimal local planner: converts the last user message into a skeleton plan
    const lastUser = [...messages].reverse().find(m => m.role === "user");
    const goal = lastUser?.content || "Build a simple workflow";
    const planLines: string[] = [
      `Plan for: ${goal}`,
      "1) Ingest (tool:fetch or upload) → 2) Process (LLM summarize/classify) → 3) Output (tool:export)",
      "Nodes:" ,
      "- tool:fetch (notes: set URL or attach asset)",
      "- llm:summarize (notes: write system prompt, pick provider/model)",
      "- tool:export (notes: choose output format)",
    ];
    append({ role: "assistant", content: planLines.join("\n") });
  }

  async function onApplyAll() {
    if (!patches.length) return;
    setError(null);
    try {
      const base = (bp ?? { nodes: [] }) as Record<string, unknown>;
      const r: any = await svcApply(base, patches);
      const next = { blueprint: r.blueprint } as any;
      onApplyBlueprint(next.blueprint);
      try { useCanvasStore.getState().autoLayout(); } catch {}
      setPatches([]);
      append({ role: "assistant", content: "Applied all patches and refreshed layout." });
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  return (
    <div className="border-t border-neutral-800 pt-3">
      <div ref={scrollRef} className="max-h-48 overflow-auto space-y-2">
        {messages.map((m, i) => (
          <div key={i} className={`text-xs ${m.role==="assistant"?"text-neutral-300":"text-blue-300"}`}>
            {m.content.split("\n").map((line, j) => (<div key={j}>{line}</div>))}
          </div>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <button onClick={proposePlan} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Propose plan</button>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e)=>{ if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); onSend(); }}}
          placeholder="Chat with your copilot (Enter to send, Shift+Enter newline)"
          className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-3 py-2 text-sm"
        />
        <button onClick={onSend} className="px-3 py-2 text-sm border border-neutral-700 rounded hover:bg-neutral-800">{loading?"Thinking…":"Send"}</button>
        <button onClick={onApplyAll} disabled={!patches.length} className="px-3 py-2 text-sm border border-neutral-700 rounded hover:bg-neutral-800">Apply all</button>
      </div>
      {error && <div className="mt-2 text-xs text-red-400">{error}</div>}
    </div>
  );
}
