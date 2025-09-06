export type StudioKind = "tool" | "llm" | "agent" | "blueprint";
export type AccessoryId = "llmConfig" | "run" | "attachAssets" | "memoryControls";

export const accessoriesByKind: Record<StudioKind, AccessoryId[]> = {
  tool: ["llmConfig", "attachAssets", "memoryControls", "run"],
  llm: ["llmConfig", "attachAssets", "memoryControls", "run"],
  agent: ["llmConfig", "attachAssets", "memoryControls", "run"],
  blueprint: ["attachAssets", "run"],
};

export function inferStudioKind(params: URLSearchParams): StudioKind {
  const bp = params.get("blueprintId");
  if (bp) return "blueprint";
  const t = params.get("type");
  if (!t) return "blueprint";
  const tl = t.toLowerCase();
  if (tl === "llm") return "llm";
  if (tl === "agent") return "agent";
  return "tool";
}
