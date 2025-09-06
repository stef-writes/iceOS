"use client";
import { useSearchParams, useRouter } from "next/navigation";
import { useMemo } from "react";
import { Button } from "@/modules/ui/primitives/Button";
import { Select } from "@/modules/ui/primitives/Select";
import { Input } from "@/modules/ui/primitives/Input";

export type RepoKind = "all" | "components" | "blueprints";
export type ComponentType = "all" | "tool" | "agent" | "workflow" | "code";

export function useRepoQuery() {
  const sp = useSearchParams();
  const router = useRouter();
  const q = sp.get("q") ?? "";
  const kind = (sp.get("rk") as RepoKind) || "all";
  const ctype = (sp.get("ct") as ComponentType) || "all";
  const sort = sp.get("sort") || "updated_desc";

  function set(next: Partial<{ q: string; kind: RepoKind; ctype: ComponentType; sort: string }>) {
    const params = new URLSearchParams(sp.toString());
    if (next.q !== undefined) params.set("q", next.q);
    if (next.kind) params.set("rk", next.kind);
    if (next.ctype) params.set("ct", next.ctype);
    if (next.sort) params.set("sort", next.sort);
    router.push(`/library?tab=repo&${params.toString()}`);
  }

  return useMemo(() => ({ q, kind, ctype, sort, set }), [q, kind, ctype, sort, router, sp]);
}

export default function RepoFilters() {
  const { q, kind, ctype, sort, set } = useRepoQuery();
  return (
    <div className="flex flex-wrap items-center gap-2 mb-3">
      <div className="flex items-center gap-1">
        <Button variant={kind === "all" ? "default" : "outline"} onClick={() => set({ kind: "all" })}>All</Button>
        <Button variant={kind === "components" ? "default" : "outline"} onClick={() => set({ kind: "components" })}>Components</Button>
        <Button variant={kind === "blueprints" ? "default" : "outline"} onClick={() => set({ kind: "blueprints" })}>Blueprints</Button>
      </div>
      <div className="flex items-center gap-1">
        <Select
          value={ctype}
          onChange={(e) => set({ ctype: e.target.value as ComponentType })}
        >
          <option value="all">All Types</option>
          <option value="tool">Tools</option>
          <option value="agent">Agents</option>
          <option value="workflow">Workflows</option>
          <option value="code">Code</option>
        </Select>
        <Select
          value={sort}
          onChange={(e) => set({ sort: e.target.value })}
        >
          <option value="updated_desc">Newest first</option>
          <option value="updated_asc">Oldest first</option>
          <option value="name_asc">Name A→Z</option>
          <option value="name_desc">Name Z→A</option>
        </Select>
      </div>
      <Input
        value={q}
        onChange={(e) => set({ q: e.target.value })}
        placeholder="Search"
        className="min-w-[240px]"
      />
    </div>
  );
}
