"use client";
import { useSearchParams } from "next/navigation";
// Pruned sections to simplify MVP
import { RunRunnerSection } from "@/modules/studio/accessories/RunRunnerSection";
import { LLMConfigSection } from "@/modules/studio/accessories/LLMConfigSection";
import { accessoriesByKind, inferStudioKind } from "@/modules/studio/accessories/registry";
import { AttachAssetsSection } from "@/modules/studio/accessories/AttachAssetsSection";
import { MemoryControlsSection } from "@/modules/studio/accessories/MemoryControlsSection";
import { useStudioUiStore } from "@/modules/studio/state/useStudioUiStore";
// StudioBuilderSection pruned from MVP

export function AccessoryDock({ code, setCode }: { code: string; setCode: (v: string) => void }) {
  const sp = useSearchParams();
  const kind = inferStudioKind(sp as unknown as URLSearchParams);
  const blueprintId = sp.get("blueprintId") || undefined;
  const items = accessoriesByKind[kind];

  const ui = useStudioUiStore();
  return (
    <div className="space-y-3">
      {items.includes("llmConfig") && (
        <div className="border border-border rounded p-2">
          <div className="flex items-center justify-between mb-1">
            <div className="text-neutral-300 text-sm">LLM Config</div>
            <button className="text-xs text-muted" onClick={() => ui.toggle("llmConfig")}>{ui.collapsed["llmConfig"] ? "Expand" : "Collapse"}</button>
          </div>
          {!ui.collapsed["llmConfig"] && <LLMConfigSection code={code} setCode={setCode} />}
        </div>
      )}
      {/* Pruned: prompt assistant, drafts, wasm tool preview, builder actions */}
      <div className="border border-border rounded p-2">
        <div className="flex items-center justify-between mb-1">
          <div className="text-neutral-300 text-sm">Attach Assets</div>
          <button className="text-xs text-muted" onClick={() => ui.toggle("attachAssets")}>{ui.collapsed["attachAssets"] ? "Expand" : "Collapse"}</button>
        </div>
        {!ui.collapsed["attachAssets"] && <AttachAssetsSection code={code} setCode={setCode} />}
      </div>
      <div className="border border-border rounded p-2">
        <div className="flex items-center justify-between mb-1">
          <div className="text-neutral-300 text-sm">Memory Controls</div>
          <button className="text-xs text-muted" onClick={() => ui.toggle("memoryControls")}>{ui.collapsed["memoryControls"] ? "Expand" : "Collapse"}</button>
        </div>
        {!ui.collapsed["memoryControls"] && <MemoryControlsSection code={code} setCode={setCode} />}
      </div>
      {items.includes("run") && (
        <div className="border border-border rounded p-2">
          <div className="text-neutral-300 text-sm mb-1">Run</div>
          <RunRunnerSection blueprintId={blueprintId} />
        </div>
      )}
    </div>
  );
}
