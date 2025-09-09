"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { workspaces, workflows, projects as projectsApi, library } from "@/modules/api/client";
import { useProjectContext } from "@/modules/context/ProjectContext";

export default function ProjectsPage() {
  const router = useRouter();
  const { setProjectId } = useProjectContext();
  const [defaultWsId, setDefaultWsId] = useState<string>("");
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    (async () => {
      try {
        // Ensure default workspace/project exist; prefer 'default'
        try { await workspaces.bootstrap(); } catch {}
        const rows = await workspaces.list();
        const def = rows.find((w:any)=>w.id==='default') || rows[0];
        if (!def) return;
        setDefaultWsId(def.id);
        const prows = await workspaces.projects(def.id).catch(()=>[]);
        setProjects(prows.map((x:any)=>({ id: x.id, name: x.name })));
      } catch {}
    })();
  }, []);

  async function reloadProjects() {
    if (!defaultWsId) return;
    const rows = await workspaces.projects(defaultWsId).catch(() => []);
    setProjects(rows.map((r: any) => ({ id: r.id, name: r.name })));
  }

  return (
    <div className="p-3 text-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="text-neutral-300">Projects</div>
        <div className="flex items-center gap-2">
          <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={reloadProjects}>Refresh</button>
          <button className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800" onClick={async () => {
            try {
              const id = `pr-${Date.now()}`;
              if (!defaultWsId) return;
              await workspaces.createProject({ id, workspace_id: defaultWsId, name: `Project ${new Date().toLocaleString()}` });
              await reloadProjects();
            } catch {}
          }}>New Project</button>
        </div>
      </div>
      <div className="mt-2 grid gap-2">
        {projects.map((p) => (
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
        {projects.length === 0 && (
          <div className="text-neutral-500 text-xs">No projects yet. Click "New Project" to create one.</div>
        )}
      </div>
    </div>
  );
}
