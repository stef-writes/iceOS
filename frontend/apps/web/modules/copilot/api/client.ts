import { api } from "@/modules/api/client";

export async function suggestV2(payload: {
  text: string;
  selection?: string | null;
  canvas_state?: Record<string, unknown>;
  provider?: string | null;
  model?: string | null;
  temperature?: number | null;
}) {
  const r = await fetch(`${(api as any).baseUrl || ""}/api/v1/frosty/suggest_v2`, {
    method: "POST",
    headers: (api as any).headers ? (api as any).headers() : { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: payload.text,
      selection: payload.selection ?? undefined,
      canvas_state: payload.canvas_state ?? {},
      provider: payload.provider ?? undefined,
      model: payload.model ?? undefined,
      temperature: payload.temperature ?? undefined,
    }),
  });
  if (!r.ok) throw new Error(`suggest_v2 failed: ${r.status}`);
  return r.json();
}
