"use client";
import { useState } from "react";

export function Topbar() {
  const [orgId, setOrgId] = useState("");
  const [userId, setUserId] = useState("");
  const [sessionId, setSessionId] = useState("");
  return (
    <div className="border-b border-neutral-800 px-3 py-2 flex items-center justify-between">
      <div className="text-sm text-neutral-300">iceOS Studio</div>
      <div className="flex items-center gap-2 text-xs">
        <input value={orgId} onChange={(e)=>setOrgId(e.target.value)} placeholder="org_id" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
        <input value={userId} onChange={(e)=>setUserId(e.target.value)} placeholder="user_id" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
        <input value={sessionId} onChange={(e)=>setSessionId(e.target.value)} placeholder="session_id" className="w-28 bg-neutral-900 border border-neutral-800 rounded px-2 py-1" />
        <button className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Run</button>
      </div>
    </div>
  );
}
