"use client";
import { useEffect, useMemo, useState } from "react";
import { derivePortSpec, type PortSpec } from "@/modules/canvas/utils/ports";
import { env } from "@/lib/env";

const PORT_CACHE: Map<string, PortSpec> = new Map();

export function getPortSpecFromCacheOrDefault(nodeType: string): PortSpec {
  return PORT_CACHE.get(nodeType) || derivePortSpec(nodeType);
}

export function useSchemaPorts(nodeType: string): PortSpec {
  const [spec, setSpec] = useState<PortSpec>(() => getPortSpecFromCacheOrDefault(nodeType));
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const base = env.API_URL?.trim() || "/api";
        const url = `${base}/v1/meta/nodes/${encodeURIComponent(nodeType)}/schema`;
        const r = await fetch(url, { headers: { "Authorization": `Bearer ${env.API_TOKEN}` } });
        if (!r.ok) throw new Error(String(r.status));
        const data = await r.json();
        const ports = (data?.ports as any) || null;
        if (ports && Array.isArray(ports.inputs) && Array.isArray(ports.outputs)) {
          const ps: PortSpec = { inputs: ports.inputs, outputs: ports.outputs };
          PORT_CACHE.set(nodeType, ps);
          if (!cancelled) setSpec(ps);
          return;
        }
      } catch {}
      const fallback = derivePortSpec(nodeType);
      PORT_CACHE.set(nodeType, fallback);
      if (!cancelled) setSpec(fallback);
    })();
    return () => { cancelled = true; };
  }, [nodeType]);
  return useMemo(() => spec, [spec]);
}
