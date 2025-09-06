"use client";
import { useMemo, useState } from "react";

type Blueprint = { nodes?: Array<Record<string, any>> };

function extractPlaceholders(tmpl: string): string[] {
  const out: string[] = [];
  if (!tmpl) return out;
  const re = /\{\{\s*([^}]+?)\s*\}\}/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(tmpl)) !== null) {
    const key = String(m[1] || "").trim();
    if (key) out.push(key);
  }
  return out;
}

function getRoot(key: string): string {
  const dot = key.indexOf(".");
  const bracket = key.indexOf("[");
  const idx = [dot, bracket].filter((n) => n >= 0).sort((a, b) => a - b)[0];
  return idx >= 0 ? key.slice(0, idx) : key;
}

export default function EdgeLinkWizard({ bp, sourceId, targetId, onApply, onClose }: { bp: Blueprint | null; sourceId: string; targetId: string; onApply: (mapping: { replaceRoots: string[] }) => void; onClose: () => void }) {
  const target = useMemo(() => (bp?.nodes || []).find((n: any) => n.id === targetId) || {}, [bp, targetId]);
  const deps: string[] = useMemo(() => Array.isArray((target as any).dependencies) ? (target as any).dependencies : [], [target]);
  const availableRoots = useMemo(() => new Set<string>(["inputs", ...deps, sourceId]), [deps, sourceId]);

  const textsToScan: string[] = useMemo(() => {
    const t = target as any;
    const out: string[] = [];
    if (typeof t.prompt === "string") out.push(t.prompt);
    if (typeof t.system_prompt === "string") out.push(t.system_prompt);
    if (typeof t.user_prompt === "string") out.push(t.user_prompt);
    if (t && typeof t.tool_args === "object" && t.tool_args !== null) {
      Object.values(t.tool_args).forEach((v: any) => { if (typeof v === "string") out.push(v); });
    }
    return out;
  }, [target]);

  const placeholderRoots = useMemo(() => {
    const keys = textsToScan.flatMap((t) => extractPlaceholders(String(t)));
    return Array.from(new Set(keys.map(getRoot)));
  }, [textsToScan]);

  const unresolved = useMemo(() => placeholderRoots.filter((r) => !availableRoots.has(r)), [placeholderRoots, availableRoots]);
  const [selected, setSelected] = useState<string[]>(unresolved);

  if (!targetId) return null;
  return (
    <div className="space-y-2">
      <div className="text-neutral-300 text-sm">Link inputs for {targetId}</div>
      {unresolved.length === 0 ? (
        <div className="text-xs text-neutral-500">No unresolved placeholders detected. You can close this wizard.</div>
      ) : (
        <div className="text-xs">
          <div className="mb-1">Unresolved roots found in prompts/args:</div>
          <div className="flex flex-wrap gap-2 mb-2">
            {unresolved.map((r) => (
              <label key={r} className={`px-2 py-1 border rounded cursor-pointer ${selected.includes(r)?"border-neutral-500 bg-neutral-800":"border-neutral-800 hover:bg-neutral-900"}`}>
                <input type="checkbox" className="mr-1" checked={selected.includes(r)} onChange={(e) => {
                  setSelected((old) => e.target.checked ? Array.from(new Set([...old, r])) : old.filter((x) => x !== r));
                }} />
                {r} → {sourceId}
              </label>
            ))}
          </div>
          <div className="text-neutral-500">Available roots now include: {Array.from(availableRoots).join(", ")}</div>
        </div>
      )}
      <div className="text-right flex items-center gap-2 justify-end">
        <button onClick={onClose} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Close</button>
        <button onClick={() => onApply({ replaceRoots: selected })} disabled={selected.length === 0} className="px-2 py-1 text-xs border border-neutral-700 rounded hover:bg-neutral-800">Apply replacements</button>
      </div>
    </div>
  );
}
