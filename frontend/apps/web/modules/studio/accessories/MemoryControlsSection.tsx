"use client";
import { useState } from "react";
import { Input } from "@/modules/ui/primitives/Input";
import { Button } from "@/modules/ui/primitives/Button";

export function MemoryControlsSection({ code, setCode }: { code: string; setCode: (v: string) => void }) {
  const [scope, setScope] = useState<string>("");
  function applyScope() {
    try {
      const obj = JSON.parse(code || "{}");
      obj.memory_scope = scope || obj.memory_scope;
      setCode(JSON.stringify(obj, null, 2));
    } catch {}
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Input placeholder="memory scope (e.g., session:chat_demo)" value={scope} onChange={(e) => setScope(e.target.value)} />
        <Button size="sm" onClick={applyScope}>Apply</Button>
      </div>
      <div className="text-xs text-neutral-500">List/Clear actions will be wired when memory endpoints are exposed.</div>
    </div>
  );
}
