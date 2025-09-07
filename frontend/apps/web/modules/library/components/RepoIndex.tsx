"use client";
import { useQuery } from "@tanstack/react-query";
import { library as api, workspaces } from "@/modules/api/client";
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
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>("");
  const [selectedProject, setSelectedProject] = useState<string>("");
  // Note: workspace/project selectors are rendered inside TemplatesPanel to avoid unused warnings here
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
      {/* Templates panel */}
      <div className="mb-4 p-3 border border-neutral-800 rounded">
        <div className="text-neutral-300 mb-2">Templates</div>
        <TemplatesPanel
          onAdd={(tplId: string) => {
            if (!selectedProject) return;
            api.templates
              .addToProject(selectedProject, { workflow_id: tplId })
              .then((res: any) => router.push(`/studio?blueprintId=${encodeURIComponent(String(res.id))}&projectId=${encodeURIComponent(String(selectedProject))}`));
          }}
          workspaceId={selectedWorkspace}
          projectId={selectedProject}
          onWorkspaceChange={setSelectedWorkspace}
          onProjectChange={setSelectedProject}
        />
      </div>
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

function TemplatesPanel(props: {
  workspaceId?: string;
  projectId?: string;
  onWorkspaceChange: (id: string) => void;
  onProjectChange: (id: string) => void;
  onAdd: (templateId: string) => void;
}) {
  const { onWorkspaceChange, onProjectChange, workspaceId, projectId, onAdd } = props;
  const { data: tpls } = useQuery({ queryKey: ["templates"], queryFn: () => api.templates.list(), staleTime: 10_000 });
  const wsQuery = useQuery({ queryKey: ["ws-for-tpl"], queryFn: () => workspaces.list(), staleTime: 10_000 });
  const prQuery = useQuery({
    queryKey: ["pr-for-tpl", workspaceId],
    queryFn: () => (workspaceId ? workspaces.projects(workspaceId) : Promise.resolve([])),
    enabled: !!workspaceId,
    staleTime: 10_000,
  });
  const wsEmpty = (wsQuery.data ?? []).length === 0;
  const prEmpty = (prQuery.data ?? []).length === 0;
  return (
    <div className="space-y-3">
      <div className="flex items-end gap-2">
      <div>
        <div className="text-xs text-neutral-400 mb-1">Workspace</div>
        <select className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm"
          value={workspaceId ?? ""}
          onChange={(e) => onWorkspaceChange(e.target.value)}>
          <option value="">{wsEmpty ? "No workspaces found" : "Select workspace"}</option>
          {(wsQuery.data ?? []).map((w: any) => (
            <option key={w.id} value={w.id}>{w.name}</option>
          ))}
        </select>
      </div>
      <div>
        <div className="text-xs text-neutral-400 mb-1">Project</div>
        <select className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-sm"
          value={projectId ?? ""}
          onChange={(e) => onProjectChange(e.target.value)}
          disabled={!workspaceId}>
          <option value="">{prEmpty ? "No projects found" : "Select project"}</option>
          {(prQuery.data ?? []).map((p: any) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>
        <div className="flex-1" />
      </div>
      <TemplateCardGrid templates={((tpls as any)?.templates ?? [])} onAdd={onAdd} disabled={!projectId} />
    </div>
  );
}

function TemplateCardGrid({ templates, onAdd, disabled }: { templates: Array<any>; onAdd: (id: string)=>void; disabled: boolean }) {
  if ((templates ?? []).length === 0) {
    return <div className="text-neutral-500 text-sm">No templates found</div>;
  }
  return (
    <div className="grid grid-cols-3 gap-3">
      {templates.map((t: any) => (
        <div key={t.id} className="border border-neutral-800 rounded p-2">
          <div className="text-neutral-200 text-sm mb-1">{t.id}</div>
          <div className="text-neutral-500 text-xs mb-2">Workflow: {t.id.split(".")[0]}</div>
          <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800 disabled:opacity-50" disabled={disabled} onClick={()=>onAdd(t.id)}>Add to Project</button>
        </div>
      ))}
    </div>
  );
}
