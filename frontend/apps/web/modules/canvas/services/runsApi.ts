import { mcp } from "@/modules/api/client";

export async function startRun(blueprint: Record<string, unknown>) {
  return mcp.runs.start({ blueprint });
}

export function eventsUrl(runId: string) {
  return mcp.runs.eventsUrl(runId);
}
