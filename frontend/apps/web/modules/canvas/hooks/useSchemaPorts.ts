"use client";
import { useMemo } from "react";
import { derivePortSpec, type PortSpec } from "@/modules/canvas/utils/ports";

export function useSchemaPorts(nodeType: string): PortSpec {
  return useMemo(() => derivePortSpec(nodeType), [nodeType]);
}
