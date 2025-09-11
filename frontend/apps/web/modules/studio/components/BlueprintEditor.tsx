"use client";
import { useEffect, useState } from "react";
import { mcp } from "@/modules/api/client";
import { useExecutionStore } from "@/modules/shell/useExecutionStore";
// Removed local LLMFieldsForm; Studio should rely on node inspectors or JSON editing
import MonacoEditor from "@/modules/studio/editor/MonacoEditor";
import { Button } from "@/modules/ui/primitives/Button";

export default function BlueprintEditor({ blueprintId }: { blueprintId: string }) {
  const [fullJson, setFullJson] = useState<string>("{}");
  const [partialId, setPartialId] = useState<string>("");
  const [lock, setLock] = useState<string | null>(null);
  const [updateJson, setUpdateJson] = useState<string>(
    '{"action":"add_node","node":{"id":"n1","type":"llm","model":"gpt-4o","prompt":"Say hi"}}'
  );
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  // Simplify: remove bespoke LLMFieldsForm state – use JSON editor and Inspector elsewhere

  useEffect(() => {
    (async () => {
      try {
        setStatus("loading blueprint...");
        const bp = await mcp.blueprints.get(blueprintId);
        setFullJson(JSON.stringify(bp, null, 2));
        setStatus("");
      } catch (e: any) {
        const msg = String(e?.message || e || "error");
        // 404-safe: prefill minimal blueprint template so user can author and finalize
        if (msg.toLowerCase().includes("404") || msg.toLowerCase().includes("not found")) {
          const minimal = {
            schema_version: "mcp.v1",
            blueprint_id: blueprintId,
            nodes: [],
          } as any;
          setFullJson(JSON.stringify(minimal, null, 2));
          setStatus("new blueprint (not registered)");
          setError(null);
        } else {
          setError(String(e?.message || e));
          setStatus("");
        }
      }
    })();
  }, [blueprintId]);

  async function createPartial() {
    setError(null);
    try {
      const resp = await mcp.blueprints.partial.create();
      const id = String((resp as any)?.blueprint_id || (resp as any)?.id || (resp as any)?.blueprintId || "");
      setPartialId(id);
      setStatus(`partial created: ${id}`);
      const got = await mcp.blueprints.partial.get(id);
      setLock(got.versionLock ?? null);
    } catch (e: any) { setError(String(e?.message || e)); }
  }

  async function loadPartial() {
    if (!partialId) { setError("partial id required"); return; }
    setError(null);
    try {
      const got = await mcp.blueprints.partial.get(partialId);
      setLock(got.versionLock ?? null);
      setFullJson(JSON.stringify(got.data, null, 2));
      setStatus("partial loaded");
    } catch (e: any) { setError(String(e?.message || e)); }
  }

  async function updatePartial() {
    if (!partialId || !lock) { setError("partial id and lock required"); return; }
    setError(null);
    try {
      const upd = JSON.parse(updateJson || "{}");
      const resp = await mcp.blueprints.partial.update(partialId, upd, lock);
      setFullJson(JSON.stringify(resp, null, 2));
      const got = await mcp.blueprints.partial.get(partialId);
      setLock(got.versionLock ?? null);
      setStatus("partial updated");
    } catch (e: any) { setError(String(e?.message || e)); }
  }

  async function finalizePartial() {
    if (!partialId || !lock) { setError("partial id and lock required"); return; }
    setError(null);
    try {
      if (!confirm("Finalize this partial into an executable blueprint? This will register it and make it immutable.")) return;
      const resp = await mcp.blueprints.partial.finalize(partialId, lock);
      setStatus("finalized → " + JSON.stringify(resp));
    } catch (e: any) { setError(String(e?.message || e)); }
  }

  async function runBlueprint() {
    try {
      const obj = JSON.parse(fullJson || "{}");
      const ack = await mcp.runs.start({ blueprint: obj as any });
      useExecutionStore.getState().start(mcp.runs.eventsUrl(ack.run_id));
      setStatus("run started: " + ack.run_id);
    } catch (e: any) { setError(String(e?.message || e)); }
  }

  return (
    <div className="space-y-2 text-sm">
      <div className="text-neutral-300">Blueprint: {blueprintId}</div>
      <div className="text-neutral-500 text-xs">partial: {partialId || "-"} lock: {lock || "-"} {status}</div>
      {/* LLM field helper removed to avoid drift; edit JSON or use Canvas Inspector */}
      <MonacoEditor
        language="json"
        value={fullJson}
        height={"50vh"}
        onChange={(v) => setFullJson(v)}
        options={{
          formatOnPaste: true,
          formatOnType: true,
        }}
      />
      <div className="flex items-center gap-2">
        <Button data-action="run-blueprint" onClick={runBlueprint}>Run</Button>
        <Button onClick={createPartial}>Create Partial</Button>
        <Button onClick={async () => {
          setError(null);
          try {
            const obj = JSON.parse(fullJson || "{}");
            const resp = await mcp.blueprints.partial.create(obj as any);
            const id = String((resp as any)?.blueprint_id || (resp as any)?.id || (resp as any)?.blueprintId || "");
            setPartialId(id);
            setStatus(`partial created from JSON: ${id}`);
            const got = await mcp.blueprints.partial.get(id);
            setLock(got.versionLock ?? null);
          } catch (e: any) { setError(String(e?.message || e)); }
        }}>Create from current JSON</Button>
        <Button onClick={loadPartial}>Load Partial</Button>
        <Button onClick={updatePartial}>Update Partial</Button>
        <Button onClick={finalizePartial}>Finalize</Button>
      </div>
      <div>
        <div className="text-neutral-400 text-xs mb-1">Partial Update JSON</div>
        <MonacoEditor
          language="json"
          value={updateJson}
          height={"24vh"}
          onChange={(v) => setUpdateJson(v)}
        />
      </div>
      {error && <div className="text-red-400 text-xs">{error}</div>}
    </div>
  );
}
