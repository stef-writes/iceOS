"use client";
import { useMemo, useState } from "react";
import { useAssetsList, useDeleteAsset } from "@/modules/library/hooks/useLibrary";

export default function AssetList() {
  const [prefix, setPrefix] = useState<string>("");
  const params = useMemo(() => ({ prefix, limit: 50 }), [prefix]);
  const { data, isLoading, isError, refetch } = useAssetsList(params);
  const del = useDeleteAsset();

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <input
          value={prefix}
          onChange={(e) => setPrefix(e.target.value)}
          placeholder="Filter by label prefix"
          className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm w-64"
        />
        <button onClick={() => refetch()} className="text-sm px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800">Search</button>
      </div>
      {isLoading && <div className="text-neutral-400 text-sm">Loading…</div>}
      {isError && <div className="text-red-400 text-sm">Error loading assets</div>}
      <ul className="divide-y divide-neutral-800 border border-neutral-800 rounded">
        {(data?.items ?? []).map((it: any) => {
          const key = String(it.key ?? it.name ?? "");
          const createdAt = String(it.created_at ?? "");
          const copy = () => navigator.clipboard.writeText(key);
          const label = key.includes(":") ? key.split(":").slice(-1)[0] : key;
          return (
            <li key={key} className="flex items-center justify-between px-3 py-2 text-sm">
              <div className="truncate">
                <div className="font-mono text-neutral-200 truncate">{key}</div>
                <div className="text-neutral-500 truncate">{String(it.scope ?? "library")} {createdAt && <span className="ml-2">· {createdAt}</span>}</div>
              </div>
              <div className="flex items-center gap-2">
                <button className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800" onClick={copy}>Copy key</button>
                <button
                  className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800"
                  onClick={() => del.mutate({ label, params: { user_id: it.user_id, org_id: it.org_id } })}
                >
                  Delete
                </button>
              </div>
            </li>
          );
        })}
        {(!data || (data.items ?? []).length === 0) && !isLoading && (
          <li className="px-3 py-2 text-neutral-500 text-sm">No assets</li>
        )}
      </ul>
    </div>
  );
}
