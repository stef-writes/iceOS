"use client";
import { useEffect, useState } from "react";
import { executions, mcp } from "@/modules/api/client";
import { Button } from "@/modules/ui/primitives/Button";
import { useExecutionStore } from "@/modules/shell/useExecutionStore";

type ExecItem = { execution_id: string; status: string; blueprint_id: string };

export function RunHistoryPanel() {
  const [items, setItems] = useState<ExecItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Access store methods via static accessors where needed; avoid unused instance

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await executions.list(50);
      setItems(r.executions);
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const openEvents = async (id: string) => {
    // Use MCP SSE if available for active blueprint runs; for historical executions we show status polling
    try {
      // Attempt to resolve a matching mcp run events URL is not possible here; we just poll status as a fallback
      const status = await executions.status(id);
      // Emit a synthetic event snapshot to the drawer
      if (status.events && status.events.length > 0) {
        // No direct SSE URL for executions; append events to drawer
        status.events.forEach((ev) => {
          // append each event
          // eslint-disable-next-line @typescript-eslint/no-unused-expressions
          useExecutionStore.setState((s) => ({ events: [...s.events, ev as any] }));
        });
      }
    } catch {}
  };

  const rerun = async (bp: string) => {
    try {
      const ack = await mcp.runs.start({ blueprint_id: bp });
      useExecutionStore.getState().start(mcp.runs.eventsUrl(ack.run_id));
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  };

  return (
    <div data-testid="run-history">
      <div className="font-semibold mb-1">Run history</div>
      <div className="flex items-center gap-2 mb-2">
        <Button onClick={() => void refresh()} disabled={loading}>{loading ? "Loading..." : "Refresh"}</Button>
        {error && <span className="text-red-400 text-xs">{error}</span>}
      </div>
      {items.length === 0 ? (
        <div className="text-neutral-400">No runs yet.</div>
      ) : (
        <div className="space-y-1">
          {items.map((it) => (
            <div key={it.execution_id} className="flex items-center justify-between text-xs text-neutral-300" data-testid="run-row">
              <div className="truncate">
                <span className="text-neutral-400 mr-1">{it.status}</span>
                <span className="font-mono">{it.execution_id}</span>
                <span className="text-neutral-500 ml-1">({it.blueprint_id})</span>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" data-testid="run-open" onClick={() => void openEvents(it.execution_id)}>Open</Button>
                <Button size="sm" data-testid="run-rerun" onClick={() => void rerun(it.blueprint_id)}>Re-run</Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
