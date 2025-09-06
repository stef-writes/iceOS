"use client";
import { useEffect, useMemo, useState } from "react";

type ToolInfo = {
  name?: string;
  input_schema?: any;
  output_schema?: any;
};

export default function RepoPreviewDrawer({ json, onClose }: { json: string | null; onClose: () => void }) {
  const [open, setOpen] = useState<boolean>(false);
  useEffect(() => { setOpen(!!json); }, [json]);
  const parsed = useMemo(() => {
    try { return json ? JSON.parse(json) : null; } catch { return null; }
  }, [json]);
  const isTool = parsed && String(parsed.type || "").toLowerCase() === "tool";
  const toolName = isTool ? String(parsed.name || "") : "";
  const [toolInfo, setToolInfo] = useState<ToolInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setToolInfo(null); setErr(null);
      if (!open || !isTool || !toolName) return;
      try {
        const base = (process.env.NEXT_PUBLIC_API_URL || "/api").toString();
        const r = await fetch(`${base}/v1/meta/nodes/tool/${encodeURIComponent(toolName)}`, {
          headers: { "Authorization": `Bearer ${process.env.NEXT_PUBLIC_API_TOKEN || ""}` }
        });
        if (!r.ok) throw new Error(`tool details ${r.status}`);
        const info = await r.json();
        setToolInfo(info as ToolInfo);
      } catch (e: any) {
        setErr(String(e?.message || e));
      }
    })();
  }, [open, isTool, toolName]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-30">
      <div className="absolute inset-0 bg-black/60" onClick={() => { setOpen(false); onClose(); }} />
      <div className="absolute right-0 top-0 h-full w-[560px] bg-neutral-950 border-l border-neutral-800 p-3 overflow-auto">
        <div className="flex items-center justify-between mb-2">
          <div className="text-sm text-neutral-300">Details</div>
          <button onClick={() => { setOpen(false); onClose(); }} className="text-sm px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Close</button>
        </div>
        {!parsed && <div className="text-neutral-500 text-xs">No details</div>}
        {parsed && (
          <div className="space-y-3">
            <div>
              <div className="text-neutral-400 text-xs">Raw</div>
              <pre className="text-[11px] whitespace-pre-wrap break-words border border-neutral-800 rounded p-2">{json}</pre>
            </div>
            {isTool && (
              <div className="border border-neutral-800 rounded p-2">
                <div className="text-neutral-300 text-sm mb-1">Tool IO Schemas</div>
                {err && <div className="text-xs text-red-400">{err}</div>}
                {!err && !toolInfo && <div className="text-xs text-neutral-500">Loading…</div>}
                {toolInfo && (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <div className="text-neutral-400 mb-1">Input schema</div>
                      <pre className="text-[11px] whitespace-pre-wrap break-words border border-neutral-800 rounded p-2">{JSON.stringify(toolInfo.input_schema ?? {}, null, 2)}</pre>
                    </div>
                    <div>
                      <div className="text-neutral-400 mb-1">Output schema</div>
                      <pre className="text-[11px] whitespace-pre-wrap break-words border border-neutral-800 rounded p-2">{JSON.stringify(toolInfo.output_schema ?? {}, null, 2)}</pre>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
