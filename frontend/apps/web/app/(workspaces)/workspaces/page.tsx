"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { workspaces, workflows, projects as projectsApi, library } from "@/modules/api/client";
import { useProjectContext } from "@/modules/context/ProjectContext";

export default function WorkspacesPage() {
  const router = useRouter();
  const { setProjectId } = useProjectContext();
  const [ws, setWs] = useState<Array<{ id: string; name: string }>>([]);
  const [projects, setProjects] = useState<Record<string, Array<{ id: string; name: string }>>>({});

  useEffect(() => {
    (async () => {
      try {
        const rows = await workspaces.list();
        setWs(rows);
        rows.forEach((w) => {
          workspaces.projects(w.id).then((r) => setProjects((p) => ({ ...p, [w.id]: r.map((x: any) => ({ id: x.id, name: x.name })) }))).catch(()=>{});
        });
      } catch {}
    })();
  }, []);

  async function loadProjects(id: string) {
    const rows = await workspaces.projects(id).catch(() => []);
    setProjects((p) => ({ ...p, [id]: rows.map((r: any) => ({ id: r.id, name: r.name })) }));
  }

  return (
    <div className="p-3 text-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="text-neutral-300">Workspaces</div>
        <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={async () => {
          try {
            const id = `ws-${Date.now()}`;
            await workspaces.create({ id, name: `Workspace ${new Date().toLocaleString()}` });
            const rows = await workspaces.list();
            setWs(rows);
          } catch {}
        }}>New Workspace</button>
      </div>
      <div className="space-y-3">
        {ws.map((w) => (
          <div key={w.id} className="border border-neutral-800 rounded p-2">
            <div className="flex items-center justify-between">
              <div className="text-neutral-200">{w.name}</div>
              <div className="flex items-center gap-2">
                <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={() => loadProjects(w.id)}>Refresh</button>
                <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={async () => {
                  try {
                    const id = `pr-${Date.now()}`;
                    await workspaces.createProject({ id, workspace_id: w.id, name: `Project ${new Date().toLocaleString()}` });
                    await loadProjects(w.id);
                  } catch {}
                }}>New Project</button>
              </div>
            </div>
            <div className="mt-2 grid gap-2">
              {(projects[w.id] || []).map((p) => (
                <div key={p.id} className="border border-neutral-800 rounded p-2 flex items-center justify-between">
                  <span className="text-neutral-300">{p.name}</span>
                  <div className="flex items-center gap-2">
                    <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={() => { setProjectId(p.id); router.push(`/canvas?projectId=${encodeURIComponent(p.id)}`); }}>Open</button>
                    <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={async () => {
                      try {
                        setProjectId(p.id);
                        const initial = { schema_version: "1.2.0", metadata: { name: `Workflow ${new Date().toLocaleString()}`, project_id: p.id }, nodes: [] } as any;
                        const created = await workflows.create(initial);
                        await projectsApi.attach(p.id, created.id);
                        router.push(`/canvas?projectId=${encodeURIComponent(p.id)}&blueprintId=${encodeURIComponent(created.id)}`);
                      } catch {}
                    }}>New Workflow</button>
                    <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={async () => {
                      try {
                        setProjectId(p.id);
                        const t = await library.templates.list();
                        const preferred = (t.templates || []).find((x:any)=>x.id.includes("library_assistant")) || (t.templates || [])[0];
                        if (!preferred) return;
                        const created = await library.templates.addToProject(p.id, { workflow_id: preferred.id });
                        router.push(`/canvas?projectId=${encodeURIComponent(p.id)}&blueprintId=${encodeURIComponent(created.id)}`);
                      } catch {}
                    }}>Add Starter</button>
                  </div>
                </div>
              ))}
              {(!projects[w.id] || projects[w.id].length === 0) && (
                <div className="text-neutral-500 text-xs">No projects yet. Use "New Project" to add one.</div>
              )}
            </div>
          </div>
        ))}
        {ws.length === 0 && <div className="text-neutral-500 text-xs">No workspaces yet. Click "New Workspace" to get started.</div>}
      </div>
    </div>
  );
}
