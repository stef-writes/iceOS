import { Suspense } from "react";
import StudioView from "@/modules/studio/StudioView";

export default function StudioPage() {
  return (
    <Suspense fallback={<div className="p-3 text-sm text-neutral-400">Loading…</div>}>
      <StudioView />
    </Suspense>
  );
}
