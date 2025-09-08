"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { workspaces } from "@/modules/api/client";
import { useProjectContext } from "@/modules/context/ProjectContext";

export default function WorkspacesPage() {
  const router = useRouter();
  const { setProjectId } = useProjectContext();
  const [ws, setWs] = useState<Array<{ id: string; name: string }>>([]);
  const [projects, setProjects] = useState<Record<string, Array<{ id: string; name: string }>>>({});
  useEffect(() => {
    workspaces.list().then((rows) => setWs(rows)).catch(() => {});
  }, []);
  async function loadProjects(id: string) {
    const rows = await workspaces.projects(id).catch(() => []);
    setProjects((p) => ({ ...p, [id]: rows.map((r: any) => ({ id: r.id, name: r.name })) }));
  }
  return (
    <div className="p-3 text-sm">
      <div className="text-neutral-300 mb-2">Workspaces</div>
      <div className="mb-3">
        <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={async () => {
          try {
            const { project_id } = await workspaces.bootstrap();
            setProjectId(project_id);
            router.push(`/canvas?projectId=${encodeURIComponent(project_id)}`);
          } catch {}
        }}>Create Default Project</button>
      </div>
      <div className="space-y-3">
        {ws.map((w) => (
          <div key={w.id} className="border border-neutral-800 rounded p-2">
            <div className="flex items-center justify-between">
              <div className="text-neutral-200">{w.name}</div>
              <div className="flex items-center gap-2">
                <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={() => loadProjects(w.id)}>Refresh</button>
              </div>
            </div>
            <div className="mt-2 grid gap-2">
              {(projects[w.id] || []).map((p) => (
                <div key={p.id} className="border border-neutral-800 rounded p-2 flex items-center justify-between">
                  <span className="text-neutral-300">{p.name}</span>
                  <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={() => { setProjectId(p.id); router.push(`/canvas?projectId=${encodeURIComponent(p.id)}`); }}>Open Canvas</button>
                </div>
              ))}
              {(!projects[w.id] || projects[w.id].length === 0) && (
                <div className="text-neutral-500 text-xs">No projects loaded</div>
              )}
            </div>
          </div>
        ))}
        {ws.length === 0 && <div className="text-neutral-500 text-xs">No workspaces yet. Use "Create Default Project" to get started.</div>}
      </div>
    </div>
  );
}



// Pruned non-essential panels to focus on Canvas
