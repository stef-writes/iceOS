"use client";
import { useEffect, useState } from "react";
import { library } from "@/modules/api/client";
import { useProjectContext } from "@/modules/context/ProjectContext";

export default function WorkflowsPage() {
  const { projectId } = useProjectContext();
  const [templates, setTemplates] = useState<Array<{ id: string; bundle: string; path: string; description?: string }>>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const t = await library.templates.list();
        setTemplates(t.templates || []);
      } catch (e: any) {
        setError(String(e?.message || e));
      }
    })();
  }, []);

  async function addToProject(templateId: string) {
    if (!projectId) { setError("Select a Project first (top-right)." ); return; }
    setBusy(templateId);
    setError(null);
    try {
      const res = await library.templates.addToProject(projectId, { workflow_id: templateId });
      const url = new URL(window.location.origin + "/workflows/" + String(res.id));
      url.searchParams.set("projectId", projectId);
      window.location.href = url.toString();
    } catch (e: any) {
      setError(String(e?.message || e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="p-6 text-sm">
      <div className="text-xl font-semibold mb-3">Workflows</div>
      {error && <div className="mb-3 text-red-400">{error}</div>}
      <div className="mb-4 text-neutral-400">Materialize a starter and open it in Canvas. Requires a selected Project.</div>
      <div className="grid grid-cols-3 gap-3">
        {templates.map((t) => (
          <div key={t.id} className="border border-neutral-800 rounded p-3">
            <div className="font-medium">{t.id}</div>
            <div className="text-neutral-500 text-xs mb-2">{t.description || t.path}</div>
            <div className="flex gap-2">
              <button disabled={!!busy} onClick={() => addToProject(t.id)} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800 disabled:opacity-50">{busy===t.id?"Adding…":"Add to Project"}</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
