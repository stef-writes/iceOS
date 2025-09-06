"use client";
import { useEffect, useState } from "react";
import { mcp } from "@/modules/api/client";
import { Button } from "@/modules/ui/primitives/Button";
import { Dialog, DialogTrigger, DialogClose } from "@/modules/ui/primitives/Dialog";
import { useState as useClientState } from "react";
import { Toast } from "@/modules/ui/primitives/Toast";

export default function ComponentEditor({ type, name }: { type: string; name: string }) {
  const [toastOpen, setToastOpen] = useClientState(false);
  const [toastText, setToastText] = useClientState<string>("");
  const [jsonText, setJsonText] = useState<string>("{}");
  const [lock, setLock] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setStatus("loading...");
        const res: any = await mcp.components.get(type, name);
        const versionLock = (res as any).versionLock || null;
        setLock(versionLock);
        const body = res?.definition ?? res?.data ?? res;
        setJsonText(JSON.stringify(body, null, 2));
        setStatus("");
      } catch (e: any) {
        // If not found, prefill a minimal definition template so the user can validate/register
        const msg = String(e?.message || e || "error");
        if (msg.toLowerCase().includes("404") || msg.toLowerCase().includes("not found")) {
          const minimal: Record<string, unknown> = { type, name, description: "" };
          setJsonText(JSON.stringify(minimal, null, 2));
          setStatus("new (not registered)");
          setError("Component not found. Start from this template and Validate/Register.");
        } else {
          setError(msg);
          setStatus("");
        }
      }
    })();
    return () => {};
  }, [type, name]);

  async function onValidate() {
    setError(null);
    try {
      const obj = JSON.parse(jsonText || "{}");
      const r = await mcp.components.validate(obj);
      setStatus("validated" + (r?.valid ? ": ok" : ": with warnings"));
      setToastText("Validated"); setToastOpen(true);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  async function onRegister() {
    setError(null);
    try {
      const obj = JSON.parse(jsonText || "{}");
      const r = await mcp.components.register(obj);
      setStatus("registered");
      if ((r as any)?.version_lock) setLock(String((r as any).version_lock));
      setToastText("Registered"); setToastOpen(true);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  async function onSave() {
    setError(null);
    try {
      if (!lock) { setError("Missing X-Version-Lock. Reload or register first."); return; }
      const obj = JSON.parse(jsonText || "{}");
      let r: any;
      try {
        r = await mcp.components.update(type, name, obj, lock);
      } catch (e: any) {
        const msg = String(e?.message || e || "error");
        if (msg.includes("409")) {
          const choice = window.confirm("This component changed on the server (409). Overwrite with your version? Click Cancel to reload server version.");
          if (choice) {
            // Optimistic overwrite: fetch latest lock first to avoid blind write
            try {
              const latest: any = await mcp.components.get(type, name);
              const latestLock = latest?.versionLock;
              if (latestLock) r = await mcp.components.update(type, name, obj, latestLock);
            } catch (e2) {
              throw e2;
            }
          } else {
            // Reload current server definition
            const latest: any = await mcp.components.get(type, name);
            const versionLock = latest?.versionLock || null;
            setLock(versionLock);
            const body = latest?.definition ?? latest?.data ?? latest;
            setJsonText(JSON.stringify(body, null, 2));
            setStatus("reloaded server version");
            return;
          }
        } else {
          throw e;
        }
      }
      const newLock = (r as any)?.version_lock;
      if (newLock) setLock(String(newLock));
      setStatus("saved"); setToastText("Saved"); setToastOpen(true);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  async function onDelete() {
    setError(null);
    try {
      await mcp.components.delete(type, name);
      setStatus("deleted");
      setToastText("Deleted"); setToastOpen(true);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  return (
    <div className="space-y-2 text-sm">
      <div className="text-neutral-300">Component: {type}/{name}</div>
      <div className="text-neutral-500 text-xs flex items-center gap-2">
        <span className="text-neutral-400">X-Version-Lock:</span>
        <span className="font-mono text-[10px] px-1 py-0.5 bg-neutral-900 border border-neutral-800 rounded max-w-[50%] truncate" title={lock ?? "-"}>{lock ?? "-"}</span>
        <span>{status}</span>
      </div>
      <textarea value={jsonText} onChange={(e) => setJsonText(e.target.value)} className="w-full h-64 bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs font-mono" />
      <div className="text-xs text-neutral-500">Shortcuts: Cmd+S Save, Cmd+Enter Validate</div>
      <div className="flex items-center gap-2">
        <Button data-action="validate" onClick={onValidate}>Validate</Button>
        <Button onClick={onRegister}>Register</Button>
        <Button data-action="save" onClick={onSave}>Save</Button>
        <Dialog title="Confirm delete">
          <DialogTrigger asChild>
            <Button variant="danger">Delete</Button>
          </DialogTrigger>
          <div className="text-sm text-neutral-300 space-y-2">
            <div>Delete {type}/{name}? This cannot be undone.</div>
            <div className="flex items-center gap-2">
              <DialogClose asChild><Button>Cancel</Button></DialogClose>
              <DialogClose asChild><Button variant="danger" onClick={onDelete}>Delete</Button></DialogClose>
            </div>
          </div>
        </Dialog>
      </div>
      {error && <div className="text-red-400 text-xs">{error}</div>}
      <Toast title={toastText} open={toastOpen} onOpenChange={setToastOpen} />
    </div>
  );
}
