"use client";
import { useState } from "react";
import { useCreateAsset } from "@/modules/library/hooks/useLibrary";

export default function CreateAssetForm() {
  const [label, setLabel] = useState("");
  const [content, setContent] = useState("");
  const [mime, setMime] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const create = useCreateAsset();

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!label.trim()) { setError("Label required"); return; }
    create.mutate({ label: label.trim(), content, mime });
    setContent("");
  }

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    const f = e.target.files?.[0];
    if (!f) return;
    // Backend limit ~1MB (bytes). Guard here for UX.
    if (f.size > 950_000) { setError("File too large (> ~950 KB)"); return; }
    try {
      const text = await f.text();
      setContent(text);
      setMime(f.type || undefined);
      if (!label.trim()) {
        const inferred = (f.name || "").replace(/\.[^.]+$/, "");
        setLabel(inferred);
      }
    } catch (err: any) {
      setError(String(err?.message || err));
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-2">
      <div className="flex items-center gap-2">
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Label"
          className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm w-64"
        />
        <input type="file" onChange={onFileChange} className="text-xs" />
        <button type="submit" className="text-sm px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">
          {create.isPending ? "Creating…" : "Create"}
        </button>
      </div>
      <div className="text-neutral-500 text-xs">MIME: {mime || "(auto)"}</div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Content"
        className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm w-full h-24"
      />
      {error && <div className="text-red-400 text-xs">{error}</div>}
    </form>
  );
}
