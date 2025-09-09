"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useProjectContext } from "@/modules/context/ProjectContext";
import { workspaces, workflows, projects as projectsApi } from "@/modules/api/client";
import { useUiStore } from "@/modules/shell/useUiStore";

export function Topbar() {
  const { projectId, setProjectId } = useProjectContext();
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const [ws, setWs] = useState<Array<{ id: string; name: string }>>([]);
  const [projects, setProjects] = useState<Record<string, Array<{ id: string; name: string }>>>({});
  const [wsId, setWsId] = useState<string>("");
  useEffect(() => {
    workspaces
      .list()
      .then((rows) => {
        setWs(rows);
        if (rows.length > 0 && !wsId) setWsId(rows[0].id);
      })
      .catch(() => {});
  }, []);
  useEffect(() => {
    if (!wsId) return;
    workspaces
      .projects(wsId)
      .then((rows) => {
        setProjects((p) => ({ ...p, [wsId]: rows.map((r: any) => ({ id: r.id, name: r.name })) }));
      })
      .catch(() => {});
  }, [wsId]);
  const pr = projects[wsId] || [];
  return (
    <div className="border-b border-neutral-800 px-3 py-2 flex items-center justify-between">
      <div className="flex items-center gap-3 text-sm">
        <button onClick={toggleSidebar} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Toggle</button>
        <Link href="/" className="text-neutral-200 font-medium">
          iceOS Studio
        </Link>
        <div className="flex items-center gap-2">
          <select
            className="bg-neutral-900 border border-neutral-800 rounded px-2 py-1 text-xs"
            value={wsId}
            onChange={(e) => setWsId(e.target.value)}
            aria-label="Workspace"
          >
            <option value="">Workspace</option>
            {ws.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
          <select
            className={`bg-neutral-900 border ${wsId?"border-neutral-800":"border-neutral-900 opacity-50"} rounded px-2 py-1 text-xs min-w-[12rem]`}
            value={projectId || ""}
            onChange={(e) => {
              const nextId = e.target.value;
              setProjectId(nextId);
              try {
                const u = new URL(window.location.href);
                if (nextId) u.searchParams.set("projectId", nextId);
                else u.searchParams.delete("projectId");
                window.history.replaceState({}, "", u.toString());
              } catch {}
            }}
            aria-label="Project"
            disabled={!wsId}
          >
            <option value="">Project</option>
            {pr.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <button
            className={`px-2 py-1 border ${wsId?"border-neutral-700":"border-neutral-900 opacity-50"} rounded text-xs hover:bg-neutral-800`}
            onClick={async () => {
              try {
                const { project_id } = await workspaces.bootstrap();
                setProjectId(project_id);
                try {
                  const u = new URL(window.location.href);
                  u.searchParams.set("projectId", project_id);
                  window.history.replaceState({}, "", u.toString());
                } catch {}
              } catch {}
            }}
            disabled={!wsId}
          >
            New Project
          </button>
          <button
            className="px-2 py-1 border border-neutral-700 rounded text-xs hover:bg-neutral-800 disabled:opacity-50"
            disabled={!projectId}
            onClick={async () => {
              if (!projectId) return;
              try {
                const initial = { schema_version: "1.2.0", metadata: { name: `Workflow ${new Date().toLocaleString()}`, project_id: projectId }, nodes: [] } as any;
                const created = await workflows.create(initial);
                await projectsApi.attach(projectId, created.id);
                const url = new URL(window.location.origin + "/canvas");
                url.searchParams.set("projectId", projectId);
                url.searchParams.set("blueprintId", String(created.id));
                window.open(url.toString(), "_blank");
              } catch {}
            }}
          >
            New Workflow
          </button>
        </div>
      </div>
      <div />
    </div>
  );
}
