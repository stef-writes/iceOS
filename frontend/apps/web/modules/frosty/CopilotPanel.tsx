"use client";
import { useEffect, useRef, useState } from "react";
import { useCopilotStore } from "@/modules/frosty/store/useCopilotStore";
import { suggestV2 } from "@/modules/frosty/api/client";
import { useCanvasStore } from "@/modules/canvas/state/useCanvasStore";
import { builder, mcp } from "@/modules/api/client";
import { emit } from "@/modules/core/events";

export default function CopilotPanel() {
  const { open, widthPct, setOpen, loading, setLoading, provider, model, temperature, includeSelection, includeCanvas, setModelControls, setContextToggles, messages, pushMessage } = useCopilotStore();
  const [text, setText] = useState("");
  const selected = useCanvasStore((s) => s.selected) as any as { id: string; type: string } | null;
  const bp = useCanvasStore((s) => s.blueprint) as any;
  const setBp = useCanvasStore((s) => s.setBlueprint) as any;
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === ".") { e.preventDefault(); setOpen(!open); }
      if (e.key === "Escape" && open) { setOpen(false); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  const w = `${widthPct}%`;
  if (!open) return null;

  async function onSuggest() {
    if (!text.trim()) return;
    setLoading(true);
    pushMessage({ id: `m${Date.now()}`, role: "user", text, created_at: Date.now() });
    try {
      emit("frosty.suggestRequested", { text_length: text.length });
      const canvas_state = includeCanvas ? { blueprint: bp ?? { nodes: [] } } : {};
      const r = await suggestV2({
        text,
        selection: includeSelection ? selected?.id ?? null : null,
        canvas_state,
        provider: provider ?? null,
        model: model ?? null,
        temperature: temperature ?? null,
      });
      pushMessage({ id: `a${Date.now()}`, role: "assistant", text: undefined, actions: r.actions || [], costs: r.costs || {}, risks: r.risks || {}, created_at: Date.now() });
      setText("");
    } catch (e: any) {
      pushMessage({ id: `e${Date.now()}`, role: "assistant", text: `Error: ${String(e?.message||e)}`, created_at: Date.now() });
    } finally {
      setLoading(false);
    }
  }

  async function onApplyPatches(patches: any[]) {
    if (!patches || patches.length === 0) return;
    const base = (bp ?? { nodes: [] }) as Record<string, unknown>;
    const r = await builder.apply({ blueprint: base as any, patches });
    const next = (r as any)?.blueprint ?? null;
    if (next) {
      try { setBp(next); (useCanvasStore as any).getState().autoLayout(); } catch {}
    }
    emit("frosty.actionsApplied", { count: Array.isArray(patches) ? patches.length : 0 });
  }

  async function onRun() {
    const blueprint = { nodes: (bp?.nodes || []).map((n: any) => ({ id: n.id, type: n.type, dependencies: n.dependencies || [], ...n })) } as any;
    emit("frosty.runRequested", { node_count: Array.isArray((bp?.nodes||[])) ? (bp!.nodes as any[]).length : 0 });
    const ack = await mcp.runs.start({ blueprint });
    try { (useCanvasStore as any).getState(); } catch {}
    return ack;
  }

  return (
    <div ref={panelRef} className="fixed right-2 top-14 bottom-2 z-40 border border-neutral-800 rounded bg-neutral-950 flex flex-col" style={{ width: w, minWidth: 280 }}>
      <div className="px-2 py-1 border-b border-neutral-800 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <span className="text-neutral-300">Frosty</span>
          <select className="bg-neutral-900 border border-neutral-800 rounded px-1 py-0.5" value={provider||""} onChange={(e)=>setModelControls(e.target.value||null, model, temperature)} aria-label="Provider">
            <option value="">provider</option>
            <option value="openai">openai</option>
            <option value="anthropic">anthropic</option>
            <option value="deepseek">deepseek</option>
          </select>
          <input placeholder="model" value={model||""} onChange={(e)=>setModelControls(provider, e.target.value||null, temperature)} className="w-28 bg-neutral-900 border border-neutral-800 rounded px-1 py-0.5" />
          <input placeholder="temp" value={temperature??""} onChange={(e)=>setModelControls(provider, model, e.target.value?Number(e.target.value):null)} className="w-14 bg-neutral-900 border border-neutral-800 rounded px-1 py-0.5" />
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-1"><input type="checkbox" checked={includeSelection} onChange={(e)=>setContextToggles(e.target.checked, includeCanvas)} /> <span className="text-neutral-400">selection</span></label>
          <label className="flex items-center gap-1"><input type="checkbox" checked={includeCanvas} onChange={(e)=>setContextToggles(includeSelection, e.target.checked)} /> <span className="text-neutral-400">canvas</span></label>
          <button className="px-2 py-0.5 border border-neutral-700 rounded hover:bg-neutral-800" onClick={()=>setOpen(false)}>Close</button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-2 text-xs">
        {messages.map((m)=> (
          <div key={m.id} className="border border-neutral-800 rounded p-2 bg-neutral-900">
            {m.role==="user" && <div className="text-neutral-200 whitespace-pre-wrap">{m.text}</div>}
            {m.role==="assistant" && (
              <div className="space-y-1">
                {m.text && <div className="text-neutral-300">{m.text}</div>}
                {Array.isArray(m.actions) && m.actions.length>0 && (
                  <div className="space-y-1">
                    {m.actions.map((a)=> {
                      const label = a.kind==="link"?"Connect":a.kind==="run"?"Run":"Apply";
                      return (
                        <div key={a.id} className="flex items-center justify-between border border-neutral-800 rounded px-2 py-1">
                          <div className="text-neutral-300">{a.kind}{a.target?`: ${a.target}`:""}</div>
                          <button className="px-2 py-0.5 border border-neutral-700 rounded hover:bg-neutral-800" onClick={async ()=>{
                            try {
                              if (a.kind === "run") { await onRun(); }
                              else { await onApplyPatches(a.patches || []); }
                            } catch (e) {
                              console.error(e);
                            }
                          }}>{label}</button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="p-2 border-t border-neutral-800 flex items-center gap-2">
        <input value={text} onChange={(e)=>setText(e.target.value)} onKeyDown={(e)=>{ if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); onSuggest(); } }} placeholder="Ask to add/edit/connect/run…" className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" />
        <button onClick={onSuggest} className="px-3 py-1 text-sm border border-neutral-700 rounded hover:bg-neutral-800">{loading?"Thinking…":"Send"}</button>
        <div className="w-1.5 h-[calc(100%-16px)] cursor-col-resize" onMouseDown={(e)=>{
          const startX=e.clientX; const startW=widthPct; function mm(ev:MouseEvent){ const dx=ev.clientX-startX; const pct=startW - (dx/window.innerWidth*100); useCopilotStore.getState().setWidth(pct); } function mu(){ window.removeEventListener("mousemove",mm); window.removeEventListener("mouseup",mu);} window.addEventListener("mousemove",mm); window.addEventListener("mouseup",mu);
        }} />
      </div>
    </div>
  );
}
