"use client";
import { useSearchParams, useRouter } from "next/navigation";

export type TabKey = "repo" | "knowledge";

export function LibraryTabs({ children }: { children: React.ReactNode }) {
  const sp = useSearchParams();
  const router = useRouter();
  const tab = (sp.get("tab") as TabKey) || "repo";
  function setTab(next: TabKey) {
    const qs = new URLSearchParams(sp.toString());
    qs.set("tab", next);
    router.push(`/library?${qs.toString()}`);
  }
  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <button onClick={() => setTab("repo")} className={`text-sm px-2 py-1 rounded border ${tab === "repo" ? "border-neutral-500 bg-neutral-800" : "border-neutral-800 hover:bg-neutral-900"}`}>Repo</button>
        <button onClick={() => setTab("knowledge")} className={`text-sm px-2 py-1 rounded border ${tab === "knowledge" ? "border-neutral-500 bg-neutral-800" : "border-neutral-800 hover:bg-neutral-900"}`}>Knowledge</button>
      </div>
      <div>{children}</div>
    </div>
  );
}
