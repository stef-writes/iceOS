"use client";
import { Suspense } from "react";
import CanvasView from "@/modules/canvas/CanvasView";

export default function CanvasPage() {
  return (
    <Suspense fallback={<div className="p-3 text-sm text-neutral-400">Loading canvas…</div>}>
      <CanvasView />
    </Suspense>
  );
}
