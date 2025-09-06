export type Cardinality = "one" | "many";

export type PortSpec = {
  inputs: Array<{ name: string; max: Cardinality }>;
  outputs: Array<{ name: string; max: Cardinality }>;
};

export function derivePortSpec(nodeType: string): PortSpec {
  const t = String(nodeType).toLowerCase();
  if (t === "condition") {
    return { inputs: [{ name: "in", max: "one" }], outputs: [{ name: "true", max: "one" }, { name: "false", max: "one" }] };
  }
  if (t === "parallel") {
    return { inputs: [{ name: "in", max: "many" }], outputs: [{ name: "out", max: "one" }] };
  }
  // default single in/out
  return { inputs: [{ name: "in", max: "one" }], outputs: [{ name: "out", max: "many" }] };
}
