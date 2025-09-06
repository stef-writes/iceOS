"use client";
import { useQuery } from "@tanstack/react-query";
import { library as api } from "@/modules/api/client";
import { useRouter } from "next/navigation";
import RepoFilters, { useRepoQuery } from "@/modules/library/components/RepoFilters";
import NodeCard from "@/modules/library/components/NodeCard";
import { useState } from "react";
import RepoPreviewDrawer from "@/modules/library/components/RepoPreviewDrawer";
import { Button } from "@/modules/ui/primitives/Button";
import { VirtualList } from "@/modules/ui/primitives/VirtualList";

function useRepo(kind?: "component" | "blueprint", limit?: number, q?: string) {
  return useQuery({
    queryKey: ["library", "index", kind ?? "all", limit ?? 30, q ?? ""],
    queryFn: () => api.index({ kind, limit: limit ?? 30, q }),
    staleTime: 10_000,
  });
}

export default function RepoIndex() {
  const router = useRouter();
  const [previewJson, setPreviewJson] = useState<string | null>(null);
  const [compLimit, setCompLimit] = useState<number>(30);
  const [bpLimit, setBpLimit] = useState<number>(30);
  const { q, kind, ctype, sort } = useRepoQuery();
  const comps = useRepo("component", compLimit, q);
  const bps = useRepo("blueprint", bpLimit, q);
  const emptyRepo = !comps.isLoading && !bps.isLoading && (comps.data?.items?.length ?? 0) === 0 && (bps.data?.items?.length ?? 0) === 0;
  const showDevHint = process.env.NEXT_PUBLIC_SHOW_DEV_HINTS === "1";
  return (
    <div>
      <RepoFilters />
      <RepoPreviewDrawer json={previewJson} onClose={() => setPreviewJson(null)} />
      {emptyRepo && showDevHint && (
        <div className="mb-3 text-xs text-amber-300 bg-amber-950/30 border border-amber-800 rounded p-2">
          No components or blueprints found. If you expect built-ins, set the server env var <span className="font-mono">ICEOS_PLUGIN_MANIFESTS</span> to load plugin manifests at startup. See <span className="font-mono">docs/PLUGINS_MANIFEST_CONTRACT.md</span>.
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-neutral-300 mb-1">Components</div>
          {comps.isLoading ? (
            <div className="text-neutral-500 text-sm">Loading…</div>
          ) : (
            <div>
              <VirtualList
                items={(comps.data?.items ?? [])
                .filter((it: any) => (kind === "all" || kind === "components"))
                .filter((it: any) => (ctype === "all" ? true : String(it.type) === ctype))
                .filter((it: any) => (q ? String(it.name).toLowerCase().includes(q.toLowerCase()) : true))
                .sort((a: any, b: any) => {
                  if (sort === "name_asc") return String(a.name).localeCompare(String(b.name));
                  if (sort === "name_desc") return String(b.name).localeCompare(String(a.name));
                  return 0;
                })}
                height={480}
                estimateSize={92}
                render={(it: any) => (
                  <div className="px-1">
                    <NodeCard
                      key={`c:${it.name}`}
                      title={String(it.name)}
                      subtitle={String(it.type ?? "")}
                      badges={[
                        ...(Array.isArray(it.tags) ? (it.tags as string[]) : []),
                        ...(it.status ? [String(it.status)] : []),
                      ]}
                      onOpen={() => router.push(`/studio?type=${encodeURIComponent(String(it.type))}&name=${encodeURIComponent(String(it.name))}`)}
                      onOpenCanvas={() => router.push(`/canvas?componentType=${encodeURIComponent(String(it.type))}&name=${encodeURIComponent(String(it.name))}`)}
                      onCopyId={() => navigator.clipboard.writeText(String(it.name))}
                      onPreview={() => setPreviewJson(JSON.stringify(it, null, 2))}
                    />
                  </div>
                )}
              />
              {(!comps.data || (comps.data.items ?? []).length === 0) && (
                <div className="text-neutral-500 text-sm">No components</div>
              )}
              <div className="mt-2">
                <Button size="sm" className="mt-2" onClick={() => setCompLimit((n) => n + 30)}>Load more</Button>
              </div>
            </div>
          )}
        </div>
        <div>
          <div className="text-neutral-300 mb-1">Blueprints</div>
          {bps.isLoading ? (
            <div className="text-neutral-500 text-sm">Loading…</div>
          ) : (
            <div>
              <VirtualList
                items={(bps.data?.items ?? [])
                .filter((it: any) => (kind === "all" || kind === "blueprints"))
                .filter((it: any) => (q ? String(it.name).toLowerCase().includes(q.toLowerCase()) : true))
                .sort((a: any, b: any) => {
                  if (sort === "name_asc") return String(a.name).localeCompare(String(b.name));
                  if (sort === "name_desc") return String(b.name).localeCompare(String(a.name));
                  return 0;
                })}
                height={480}
                estimateSize={88}
                render={(it: any) => (
                  <div className="px-1">
                    <NodeCard
                      key={`b:${it.name}`}
                      title={String(it.name)}
                      badges={Array.isArray(it.tags) ? (it.tags as string[]) : []}
                      onOpen={() => router.push(`/studio?blueprintId=${encodeURIComponent(String(it.name))}`)}
                      onOpenCanvas={() => router.push(`/canvas?blueprintId=${encodeURIComponent(String(it.name))}`)}
                      onCopyId={() => navigator.clipboard.writeText(String(it.name))}
                      onPreview={() => setPreviewJson(JSON.stringify(it, null, 2))}
                    />
                  </div>
                )}
              />
              {(!bps.data || (bps.data.items ?? []).length === 0) && (
                <div className="text-neutral-500 text-sm">No blueprints</div>
              )}
              <div className="mt-2">
                <Button size="sm" className="mt-2" onClick={() => setBpLimit((n) => n + 30)}>Load more</Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
