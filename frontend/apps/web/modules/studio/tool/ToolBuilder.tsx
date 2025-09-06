"use client";
import { useEffect, useMemo, useState } from "react";
import { builder, mcp } from "@/modules/api/client";

type JsonSchema = { properties?: Record<string, { type?: string; description?: string }>; required?: string[] };

type ToolSpec = {
  type: "tool";
  name: string;
  description?: string;
  input_schema: JsonSchema;
  output_schema?: JsonSchema;
  implementation: { kind: string; code: string };
};

export default function ToolBuilder() {
  const [spec, setSpec] = useState<ToolSpec>({
    type: "tool",
    name: "my_tool",
    description: "",
    input_schema: { properties: {}, required: [] },
    output_schema: { properties: {}, required: [] },
    implementation: { kind: "python", code: "# TODO: implement\n" },
  });
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown | null>(null);

  const requiredMissing = useMemo(() => {
    const req = Array.isArray(spec.input_schema?.required) ? spec.input_schema!.required! : [];
    return req.filter((k) => {
      const v = inputs[k];
      return v == null || String(v).trim() === "";
    });
  }, [spec.input_schema, inputs]);

  useEffect(() => {
    // Sync inputs keys from schema
    const props = spec.input_schema?.properties || {};
    const base: Record<string, string> = {};
    Object.keys(props).forEach((k) => { base[k] = inputs[k] ?? ""; });
    setInputs(base);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spec.input_schema]);

  async function runPreview() {
    setRunning(true); setError(null); setResult(null);
    try {
      if (spec.implementation?.code?.trim()) {
        const r: any = await builder.previewTool({ language: spec.implementation.kind, code: spec.implementation.code, inputs });
        if (!r?.success) throw new Error(String(r?.error || "preview failed"));
        setResult(r.output ?? null);
      } else {
        // Fallback: run via MCP as a tool node if no code is provided (requires registered tool)
        const node = { id: "tool1", type: "tool", tool_name: spec.name, tool_args: inputs, dependencies: [] } as any;
        await mcp.runs.start({ blueprint: { nodes: [node] } as any });
      }
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setRunning(false);
    }
  }

  function setSchemaText(kind: "input" | "output", text: string) {
    try {
      const obj = JSON.parse(text || "{}");
      if (kind === "input") setSpec((s) => ({ ...s, input_schema: obj }));
      else setSpec((s) => ({ ...s, output_schema: obj }));
    } catch (e) {
      // ignore parse errors while typing
    }
  }

  return (
    <div className="space-y-3">
      {error && <div className="border border-red-900 bg-red-950/40 text-red-300 rounded p-2 text-xs">{error}</div>}

      <div className="grid grid-cols-2 gap-3">
        <div className="border border-neutral-800 rounded p-2">
          <div className="text-neutral-300 text-sm mb-2">Meta</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <input value={spec.name} onChange={(e)=>setSpec((s)=>({...s, name: e.target.value}))} placeholder="Name" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <input value={spec.description || ""} onChange={(e)=>setSpec((s)=>({...s, description: e.target.value}))} placeholder="Description" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 col-span-1" />
          </div>
        </div>

        <div className="border border-neutral-800 rounded p-2">
          <div className="text-neutral-300 text-sm mb-2">Implementation</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <input value={spec.implementation.kind} onChange={(e)=>setSpec((s)=>({...s, implementation:{...s.implementation, kind: e.target.value}}))} placeholder="Language (python)" className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
            <span className="text-neutral-500 text-[11px] self-center">Leave code empty to run registered tool</span>
          </div>
          <textarea value={spec.implementation.code} onChange={(e)=>setSpec((s)=>({...s, implementation:{...s.implementation, code: e.target.value}}))} placeholder="# Code" className="w-full h-20 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs mt-2" />
        </div>

        <div className="border border-neutral-800 rounded p-2 col-span-2">
          <div className="text-neutral-300 text-sm mb-2">Input Schema (JSON)</div>
          <textarea defaultValue={JSON.stringify(spec.input_schema, null, 2)} onChange={(e)=>setSchemaText("input", e.target.value)} className="w-full h-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs font-mono" />
          <div className="mt-2 text-xs text-neutral-400">Form</div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            {Object.entries(spec.input_schema.properties || {}).map(([key, meta]) => (
              <div key={key} className="border border-neutral-800 rounded p-2">
                <div className="text-neutral-300 mb-1">{key}</div>
                <input value={inputs[key] || ""} onChange={(e)=>setInputs((old)=>({...old, [key]: e.target.value}))} placeholder={meta.description || meta.type || "string"} className="w-full bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
              </div>
            ))}
            {Object.keys(spec.input_schema.properties || {}).length === 0 && (
              <div className="text-neutral-500">No schema properties</div>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-xs">
          {requiredMissing.length > 0 ? (<span className="text-amber-300">Missing inputs: {requiredMissing.join(", ")}</span>) : (<span className="text-green-300">Ready</span>)}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={runPreview} disabled={running || requiredMissing.length>0} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">{running?"Running…":"Run"}</button>
          <button onClick={async()=>{
            setError(null);
            try {
              await mcp.components.register(spec as any);
              alert("Published tool component.");
            } catch(e:any){ setError(String(e?.message || e)); }
          }} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Publish</button>
          <button onClick={()=>{
            try {
              const node = { id: spec.name, type: "tool", tool_name: spec.name, tool_args: {}, dependencies: [] };
              sessionStorage.setItem("studio:addNode", JSON.stringify(node));
              window.location.href = "/canvas";
            } catch(e){}
          }} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Add to Canvas</button>
        </div>
      </div>

      {result != null && (
        <div className="border border-neutral-800 rounded p-2 text-xs">
          <div className="text-neutral-300 mb-1">Result</div>
          <pre className="whitespace-pre-wrap break-words">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
