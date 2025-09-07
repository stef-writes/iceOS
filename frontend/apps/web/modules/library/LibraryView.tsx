"use client";
import AssetList from "@/modules/library/components/AssetList";
import CreateAssetForm from "@/modules/library/components/CreateAssetForm";
import RepoIndex from "@/modules/library/components/RepoIndex";
import RepoPreviewDrawer from "@/modules/library/components/RepoPreviewDrawer";
import { useState } from "react";
import { LibraryTabs } from "@/modules/library/components/LibraryTabs";
import { useSearchParams } from "next/navigation";

export default function LibraryView() {
  const sp = useSearchParams();
  const tab = (sp.get("tab") as "repo" | "knowledge") || "knowledge";
  const [previewJson, setPreviewJson] = useState<string | null>(null);
  // Zero-setup: ensure projectId is present by calling /api/v1/bootstrap once on load
  if (typeof window !== "undefined") {
    const pid = sp.get("projectId");
    if (!pid) {
      import("@/modules/api/client").then(({ workspaces }) => {
        workspaces.bootstrap().then(({ project_id }) => {
          const next = new URL(window.location.href);
          next.searchParams.set("projectId", project_id);
          window.history.replaceState({}, "", next.toString());
        }).catch(() => {});
      });
    }
  }
  return (
    <div className="p-3 text-sm">
      <LibraryTabs>
        {tab === "repo" ? (
          <div>
            <RepoIndex />
            <RepoPreviewDrawer json={previewJson} onClose={() => setPreviewJson(null)} />
          </div>
        ) : (
          <div>
            <div className="mb-3">
              <div className="text-neutral-300 mb-1">Upload document or paste text</div>
              <CreateAssetForm />
            </div>
            <div className="mt-4">
              <div className="text-neutral-300 mb-1">Assets</div>
              <AssetList />
            </div>
          </div>
        )}
      </LibraryTabs>
    </div>
  );
}
