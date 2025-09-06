export type PositionMap = Record<string, { x: number; y: number }>;

type BpNode = { id: string; type: string; dependencies?: string[] };
type Blueprint = { nodes?: BpNode[] };

export function computeSimpleDagLayout(bp: Blueprint | null): PositionMap {
  const nodes = (bp?.nodes || []) as BpNode[];
  if (nodes.length === 0) return {};
  const depsOf: Record<string, string[]> = {};
  const incoming: Record<string, number> = {};
  nodes.forEach((n) => {
    const deps = Array.isArray(n.dependencies) ? n.dependencies : [];
    depsOf[n.id] = deps;
    incoming[n.id] = deps.length;
    deps.forEach((d) => { if (!(d in incoming)) incoming[d] = incoming[d] ?? 0; });
  });
  const layers: string[][] = [];
  let frontier = Object.keys(incoming).filter((k) => incoming[k] === 0);
  const seen = new Set<string>();
  while (frontier.length) {
    layers.push(frontier);
    frontier.forEach((id) => seen.add(id));
    const next: string[] = [];
    nodes.forEach((n) => {
      if (seen.has(n.id)) return;
      const deps = depsOf[n.id] || [];
      if (deps.every((d) => seen.has(d))) next.push(n.id);
    });
    frontier = next.filter((v, i, a) => a.indexOf(v) === i);
  }
  // position
  const pos: PositionMap = {};
  const xGap = 220; const yGap = 120;
  layers.forEach((layer, li) => {
    layer.forEach((id, idx) => {
      pos[id] = { x: 80 + idx * xGap, y: 60 + li * yGap };
    });
  });
  return pos;
}
