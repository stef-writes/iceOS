"use client";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { library } from "@/modules/api/client";
import { Button } from "@/modules/ui/primitives/Button";
import { Input } from "@/modules/ui/primitives/Input";
import { Dialog, DialogTrigger, DialogClose } from "@/modules/ui/primitives/Dialog";

type RagConfig = { enabled?: boolean; assets?: string[]; top_k?: number; min_score?: number };

export function AttachAssetsSection({ code, setCode }: { code: string; setCode: (v: string) => void }) {
  const q = useQuery({ queryKey: ["assets", 50], queryFn: () => library.assets.list({ limit: 50 }) });

  const current: RagConfig = useMemo(() => {
    try {
      const obj = JSON.parse(code || "{}");
      const lc = obj?.llm_config ?? {};
      return { enabled: lc?.rag?.enabled ?? false, assets: lc?.rag?.assets ?? [], top_k: lc?.rag?.top_k ?? 4, min_score: lc?.rag?.min_score ?? 0.0 };
    } catch {
      return { enabled: false, assets: [], top_k: 4, min_score: 0.0 };
    }
  }, [code]);

  const [topK, setTopK] = useState<string>(String(current.top_k ?? 4));
  const [minScore, setMinScore] = useState<string>(String(current.min_score ?? 0.0));

  function write(next: RagConfig) {
    try {
      const obj = JSON.parse(code || "{}");
      obj.llm_config = obj.llm_config || {};
      obj.llm_config.rag = {
        enabled: next.enabled ?? current.enabled ?? true,
        assets: next.assets ?? (current.assets ?? []),
        top_k: next.top_k ?? (Number(topK) || 4),
        min_score: next.min_score ?? (Number(minScore) || 0.0),
      };
      setCode(JSON.stringify(obj, null, 2));
    } catch {}
  }

  function attach(label: string) {
    const set = new Set(current.assets ?? []);
    set.add(label);
    write({ assets: Array.from(set), enabled: true });
  }
  function remove(label: string) {
    const arr = (current.assets ?? []).filter((x) => x !== label);
    write({ assets: arr });
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Dialog title="Add text asset">
          <DialogTrigger asChild>
            <Button size="sm">Add text</Button>
          </DialogTrigger>
          <AddTextAsset onAdded={(label) => attach(label)} />
        </Dialog>
        <Button size="sm" disabled title="File upload coming soon">Add file</Button>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <label className="flex items-center gap-1"><input type="checkbox" checked={!!current.enabled} onChange={(e) => write({ enabled: e.target.checked })} /> Enable RAG</label>
        <span>top_k</span>
        <Input className="w-16" value={topK} onChange={(e) => { setTopK(e.target.value); write({ top_k: Number(e.target.value) || 4 }); }} />
        <span>min_score</span>
        <Input className="w-16" value={minScore} onChange={(e) => { setMinScore(e.target.value); write({ min_score: Number(e.target.value) || 0 }); }} />
      </div>
      <div className="flex flex-wrap gap-1 text-xs">
        {(current.assets ?? []).map((lab) => (
          <span key={lab} className="px-2 py-0.5 border border-border rounded">{lab} <button className="ml-1 text-muted" onClick={() => remove(lab)}>×</button></span>
        ))}
        {(current.assets ?? []).length === 0 && <span className="text-neutral-500">No assets attached</span>}
      </div>
      {q.isLoading ? (
        <div className="text-xs text-neutral-500">Loading…</div>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          {(q.data?.items ?? []).map((it: any) => (
            <div key={String(it.label)} className="flex items-center justify-between border border-border rounded px-2 py-1 text-xs">
              <span className="truncate">{String(it.label)}</span>
              <div className="flex items-center gap-1">
                <Button size="sm" onClick={() => attach(String(it.label))}>Attach</Button>
                <Button size="sm" onClick={() => remove(String(it.label))}>Remove</Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AddTextAsset({ onAdded }: { onAdded: (label: string) => void }) {
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const [orgId, setOrgId] = useState("");
  const [userId, setUserId] = useState("");
  const [saving, setSaving] = useState(false);
  async function save() {
    if (!label.trim() || !content.trim()) return;
    setSaving(true);
    try {
      await library.assets.create({ label: label.trim(), content, mime: "text/plain", org_id: orgId || undefined, user_id: userId || undefined });
      onAdded(label.trim());
    } finally { setSaving(false); }
  }
  return (
    <div className="space-y-2">
      <Input placeholder="label" value={label} onChange={(e) => setLabel(e.target.value)} />
      <textarea placeholder="content" className="w-full h-32 bg-neutral-900 border border-border rounded p-2 text-xs" value={content} onChange={(e) => setContent(e.target.value)} />
      <div className="flex items-center gap-2">
        <Input placeholder="org_id (optional)" className="w-40" value={orgId} onChange={(e) => setOrgId(e.target.value)} />
        <Input placeholder="user_id (optional)" className="w-40" value={userId} onChange={(e) => setUserId(e.target.value)} />
      </div>
      <div className="flex items-center gap-2">
        <DialogClose asChild><Button size="sm">Cancel</Button></DialogClose>
        <DialogClose asChild><Button size="sm" onClick={save} disabled={saving || !label || !content}>Save</Button></DialogClose>
      </div>
    </div>
  );
}
