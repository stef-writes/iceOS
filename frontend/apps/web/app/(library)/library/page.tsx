import { Suspense } from "react";
import LibraryView from "@/modules/library/LibraryView";

export default function LibraryPage() {
  return (
    <Suspense fallback={<div className="p-3 text-sm text-neutral-400">Loading…</div>}>
      <LibraryView />
    </Suspense>
  );
}
