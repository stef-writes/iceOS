import { builder } from "@/modules/api/client";

export async function suggest(text: string, canvas_state: Record<string, unknown>) {
  return builder.suggest({ text, canvas_state });
}

export async function applyPatches(blueprint: Record<string, unknown>, patches: Array<Record<string, unknown>>) {
  return builder.apply({ blueprint, patches });
}

export async function suggestWithOverrides(
  text: string,
  canvas_state: Record<string, unknown>,
  opts?: { provider?: string | null; model?: string | null; temperature?: number | null }
) {
  return builder.suggest({ text, canvas_state, provider: opts?.provider ?? null, model: opts?.model ?? null, temperature: opts?.temperature ?? null });
}
