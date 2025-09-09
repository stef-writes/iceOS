"use client";
import { useEffect, useState } from "react";
import { library } from "@/modules/api/client";

export default function LibraryPage() {
  const [assets, setAssets] = useState<Array<{ label: string; mime?: string }>>([]);
  const [busy, setBusy] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const res = await library.assets.list({ user_id: "demo_user", limit: 20 });
      const items = Array.isArray((res as any).items) ? (res as any).items : [];
      setAssets(items as any);
    } catch (e: any) {
      setError(String(e?.message || e));
    }
  }

  useEffect(() => { refresh(); }, []);

  async function onDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setError(null);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const text = await file.text();
      await library.assets.create({ label: file.name, content: text, mime: file.type || "text/plain", org_id: "demo_org", user_id: "demo_user" });
      await refresh();
    } catch (er: any) {
      setError(String(er?.message || er));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 text-sm">
      <div className="text-xl font-semibold mb-3">Library</div>
      {error && <div className="mb-3 text-red-400">{error}</div>}
      <div
        onDragOver={(e)=>{e.preventDefault();}}
        onDrop={onDrop}
        className="mb-4 h-28 border border-dashed border-neutral-700 rounded flex items-center justify-center text-neutral-400"
      >{busy?"Uploading…":"Drag & drop a file to upload"}</div>
      <div className="grid grid-cols-2 gap-2">
        {assets.map((a) => (
          <div key={a.label} className="border border-neutral-800 rounded p-2 flex items-center justify-between">
            <div>
              <div className="font-medium">{a.label}</div>
              <div className="text-neutral-500 text-xs">{a.mime || "text/plain"}</div>
            </div>
            <button onClick={async()=>{ try{ await library.assets.delete(a.label, { user_id: "demo_user" }); await refresh(); }catch(e:any){ setError(String(e?.message||e)); } }} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Delete</button>
          </div>
        ))}
      </div>
    </div>
  );
}
