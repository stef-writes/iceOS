"use client";
export default function ToolInspector({ node, setField }: { node: any; setField: (path: string, value: unknown) => void }) {
  return (
    <div className="space-y-2">
      <div className="text-neutral-300">Tool</div>
      <input className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm" placeholder="tool_name" defaultValue={node.tool_name || ""} onChange={(e) => setField("tool_name", e.target.value)} />
      <textarea className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs font-mono" placeholder="inputs (JSON)" defaultValue={JSON.stringify(node.inputs_json || {}, null, 2)} onChange={(e) => {
        try { setField("inputs_json", JSON.parse(e.target.value || "{}")); } catch {}
      }} />
    </div>
  );
}
