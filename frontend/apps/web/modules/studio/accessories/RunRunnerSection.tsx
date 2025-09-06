"use client";
import { useState } from "react";
import { mcp } from "@/modules/api/client";
import { Button } from "@/modules/ui/primitives/Button";
import { Input } from "@/modules/ui/primitives/Input";
import { useExecutionStore } from "@/modules/shell/useExecutionStore";

export function RunRunnerSection({ blueprintId }: { blueprintId?: string }) {
  const [inputs, setInputs] = useState<string>("{}");
  const [orgId, setOrgId] = useState<string>("");
  const [userId, setUserId] = useState<string>("");
  const [sessionId, setSessionId] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  async function run() {
    setErr(null);
    try {
      if (!blueprintId) { setErr("blueprintId required"); return; }
      const payload = JSON.parse(inputs || "{}");
      payload.org_id = payload.org_id ?? orgId;
      payload.user_id = payload.user_id ?? userId;
      payload.session_id = payload.session_id ?? sessionId;
      const ack = await mcp.runs.start({ blueprint_id: blueprintId, options: { max_parallel: 1 } });
      useExecutionStore.getState().start(mcp.runs.eventsUrl(ack.run_id));
    } catch (e: any) { setErr(String(e?.message || e)); }
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs">
        <Input className="w-28" placeholder="org_id" value={orgId} onChange={(e) => setOrgId(e.target.value)} />
        <Input className="w-28" placeholder="user_id" value={userId} onChange={(e) => setUserId(e.target.value)} />
        <Input className="w-28" placeholder="session_id" value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
      </div>
      <Input placeholder="inputs JSON" value={inputs} onChange={(e) => setInputs(e.target.value)} />
      <Button size="sm" onClick={run}>Run blueprint</Button>
      {err && <div className="text-xs text-danger">{err}</div>}
    </div>
  );
}
