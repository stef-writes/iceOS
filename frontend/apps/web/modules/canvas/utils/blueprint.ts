export type CanvasNode = { id: string; type: string; dependencies?: string[] } & Record<string, unknown>;
export type CanvasBlueprint = { nodes?: CanvasNode[] };

export function updateNode(bp: CanvasBlueprint | null, nodeId: string, changes: Record<string, unknown>): CanvasBlueprint | null {
  if (!bp) return bp;
  const nodes = [...(bp.nodes || [])];
  const idx = nodes.findIndex((n) => n.id === nodeId);
  if (idx < 0) return bp;
  nodes[idx] = { ...nodes[idx], ...changes } as CanvasNode;
  return { ...bp, nodes };
}
