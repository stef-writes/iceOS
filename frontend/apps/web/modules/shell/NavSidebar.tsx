"use client";
import Link from "next/link";
import { emit } from "@/modules/core/events";
import { useEffect, useState } from "react";
import { workspaces, projects as projectsApi, workflows as workflowsApi } from "@/modules/api/client";

export function NavSidebar() {
  const [tree, setTree] = useState<Array<{ id: string; name: string; projects: Array<{ id: string; name: string; workflows: Array<{ id: string; name: string }> }> }>>([]);
  async function fetchTree() {
    try {
      const ws = await workspaces.list();
      const out: Array<any> = [];
      for (const w of ws) {
        const projs = await workspaces.projects(w.id);
        const projOut: Array<any> = [];
        for (const p of projs) {
          try {
            const bps = await projectsApi.blueprints(p.id);
            const ids: string[] = Array.isArray((bps as any).blueprint_ids) ? (bps as any).blueprint_ids : [];
            const wf = [] as Array<{ id: string; name: string }>;
            for (const id of ids) {
              try {
                const d = await workflowsApi.get(id);
                const name = String(((d as any).data?.metadata?.name) || id);
                wf.push({ id, name });
              } catch {
                wf.push({ id, name: id });
              }
            }
            projOut.push({ id: p.id, name: p.name, workflows: wf });
          } catch {
            projOut.push({ id: p.id, name: p.name, workflows: [] });
          }
        }
        out.push({ id: w.id, name: w.name, projects: projOut });
      }
      setTree(out);
    } catch {}
  }
  useEffect(() => { void fetchTree(); }, []);
  return (
    <div className="p-2 text-sm space-y-2">
      <div className="font-semibold">Explorer</div>
      <div className="space-y-1">
        {tree.map((w) => (
          <div key={w.id}>
            <div className="text-neutral-300">{w.name}</div>
            <div className="pl-2 space-y-1">
              {w.projects.map((p) => (
                <div key={p.id}>
                  <div className="text-neutral-400">{p.name}</div>
                  <div className="pl-2 grid">
                    {p.workflows.map((bp) => (
                      <div key={bp.id} className="flex items-center justify-between gap-2">
                        <Link href={`/workflows/${bp.id}`} className="text-neutral-500 hover:text-white truncate">{bp.name}</Link>
                        <div className="flex gap-1">
                          <button
                            title="Duplicate"
                            className="px-1 py-0.5 text-[10px] border border-neutral-700 rounded hover:bg-neutral-800"
                            onClick={async (e) => {
                              e.preventDefault();
                              try {
                                const src = await workflowsApi.get(bp.id);
                                const data = (src as any).data || { nodes: [] };
                                const copy = { ...data, metadata: { ...(data.metadata||{}), name: String((data.metadata?.name||bp.name) + " copy") } };
                                const created = await (workflowsApi as any).create({ data: copy });
                                await projectsApi.attach(p.id, created.id);
                                await fetchTree();
                                const url = new URL(window.location.origin + "/workflows/" + String(created.id));
                                window.open(url.toString(), "_blank");
                              } catch {}
                            }}
                          >Dup</button>
                          <button
                            title="Delete"
                            className="px-1 py-0.5 text-[10px] border border-red-800 text-red-300 rounded hover:bg-red-950"
                            onClick={async (e) => {
                              e.preventDefault();
                              try {
                                const res = await workflowsApi.get(bp.id);
                                const lock = String((res as any).version_lock || "");
                                await (workflowsApi as any).delete(bp.id, lock);
                                await fetchTree();
                              } catch {}
                            }}
                          >Del</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="pt-2 border-t border-neutral-900" />
      <nav className="grid gap-1">
        <Link href="/workspaces" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.projects" })}>Projects</Link>
        <Link href="/workflows" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.workflows" })}>Workflows</Link>
        <Link href="/library" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.library" })}>Library</Link>
      </nav>
    </div>
  );
}
