"use client";
import { useEffect, useRef, useState } from "react";
import { useExecutionStore } from "@/modules/shell/useExecutionStore";
import { useCanvasStore } from "@/modules/canvas/state/useCanvasStore";

export function ExecutionDrawer() {
  const _es = useRef<EventSource | null>(null);
  useEffect(() => {
    return () => { try { _es.current?.close(); } catch {}; };
  }, []);
  const exec = useExecutionStore();
  const counts = exec.events.reduce((acc, e) => { acc[e.event] = (acc[e.event] || 0) + 1; return acc; }, {} as Record<string, number>);
  const [filter, setFilter] = useState<string>("all");
  const [query, setQuery] = useState<string>("");
  const [nodeFilter, setNodeFilter] = useState<string>("");
  const selected = useCanvasStore((s) => s.selected);
  const eventNames = Object.keys(counts);
  const listRef = useRef<HTMLDivElement | null>(null);
  const filtered = (exec.events ?? [])
    .filter((e) => (filter === "all" ? true : e.event === filter))
    .filter((e) => {
      if (!nodeFilter.trim()) return true;
      const pid = String(e.payload?.node_id ?? e.payload?.id ?? "");
      return pid === nodeFilter.trim();
    })
    .filter((e) => {
      if (!query.trim()) return true;
      const t = query.toLowerCase();
      return JSON.stringify(e.payload).toLowerCase().includes(t) || e.event.toLowerCase().includes(t);
    });
  return (
    <div className="text-sm" data-testid="execution-drawer">
      <div className="font-semibold mb-1">Execution</div>
      <div className="flex items-center gap-2 text-xs mb-2">
        <span className="text-neutral-400">Events:</span>
        {Object.entries(counts).map(([k, v]) => (
          <span key={k} className="px-2 py-0.5 border border-neutral-700 rounded bg-neutral-900 text-neutral-300">{k} {v}</span>
        ))}
      </div>
      <div className="flex items-center gap-2 text-xs mb-2">
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1">
          <option value="all">All</option>
          {eventNames.map((n) => (<option key={n} value={n}>{n}</option>))}
        </select>
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter text" className="flex-1 bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
      </div>
      <div className="flex items-center gap-2 text-xs mb-2">
        <input value={nodeFilter} onChange={(e) => setNodeFilter(e.target.value)} placeholder="Filter by node id" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
        <button disabled={!selected} onClick={() => selected && setNodeFilter(selected.id)} className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800 disabled:opacity-50">Use selected{selected ? ` (${selected.id})` : ""}</button>
        {nodeFilter && (
          <button onClick={() => setNodeFilter("")} className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Clear</button>
        )}
      </div>
      {exec.runId == null && (
        <div className="text-neutral-400 mb-2">No active run.</div>
      )}
      <div ref={listRef} className="max-h-56 overflow-auto space-y-1" data-testid="execution-events">
        {filtered.map((e, i) => {
          const isFail = e.event === "node.failed";
          return (
            <div key={i} className={`text-neutral-300 font-mono text-xs ${isFail?"bg-red-950/30 border border-red-800/50 rounded px-1 py-0.5":""}`}>
              {e.event}: {JSON.stringify(e.payload)}
            </div>
          );
        })}
      </div>
      {/* Auto-scroll to most recent failure */}
      <AutoScrollOnFail containerRef={listRef} />
    </div>
  );
}

function AutoScrollOnFail({ containerRef }: { containerRef: React.RefObject<HTMLDivElement> }) {
  const exec = useExecutionStore();
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const last = [...(exec.events||[])].reverse().find((e) => e.event === "node.failed");
    if (last) {
      try { el.scrollTop = el.scrollHeight; } catch {}
      const nodeId = String(last.payload?.node_id ?? last.payload?.id ?? "");
      if (nodeId) {
        try {
          // highlight on canvas via store status already handled; ensure visible selection
          const node = (useCanvasStore.getState().blueprint?.nodes || []).find((n: any) => String(n.id) === nodeId);
          if (node) useCanvasStore.getState().setSelected({ id: String(nodeId), type: String((node as any).type || "") });
        } catch {}
      }
    }
  }, [exec.events]);
  return null;
}
