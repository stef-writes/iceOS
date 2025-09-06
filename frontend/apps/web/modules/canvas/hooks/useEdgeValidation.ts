"use client";
import { useCallback } from "react";
import type { Connection } from "reactflow";
import { derivePortSpec } from "@/modules/canvas/utils/ports";

export function useEdgeValidation(getNodeType: (id: string) => string, getInputs: (id: string) => Record<string, string | string[] | undefined>) {
  const isValid = useCallback((conn: Connection) => {
    const source = conn.source ?? undefined;
    const target = conn.target ?? undefined;
    if (!source || !target || source === target) return false;
    const tgtType = getNodeType(target);
    const spec = derivePortSpec(tgtType);
    // enforce single input by default
    const inputs = getInputs(target) || {};
    const current = inputs["in"];
    if (spec.inputs.find((p) => p.name === "in" && p.max === "one")) {
      if (current && current !== source) return false;
    }
    return true;
  }, [getNodeType, getInputs]);
  return isValid;
}
