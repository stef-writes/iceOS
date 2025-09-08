export type AppEventName =
  | "ui.commandExecuted"
  | "canvas.nodeSelected"
  | "builder.suggestRequested"
  | "frosty.suggestRequested"
  | "frosty.actionsApplied"
  | "frosty.runRequested"
  | "drafts.conflictDetected"
  | "preview.sandboxError";

export type AppEventPayload = Record<string, unknown>;

export type AppEvent = {
  name: AppEventName;
  payload?: AppEventPayload;
  ts: number;
};

const listeners = new Map<AppEventName, Set<(e: AppEvent) => void>>();

export function emit(name: AppEventName, payload?: AppEventPayload) {
  const evt: AppEvent = { name, payload, ts: Date.now() };
  const subs = listeners.get(name);
  if (!subs) return;
  subs.forEach((fn) => {
    try {
      fn(evt);
    } catch {}
  });
}

export function on(name: AppEventName, handler: (e: AppEvent) => void) {
  const set = listeners.get(name) ?? new Set();
  set.add(handler);
  listeners.set(name, set);
  return () => off(name, handler);
}

export function off(name: AppEventName, handler: (e: AppEvent) => void) {
  const set = listeners.get(name);
  if (!set) return;
  set.delete(handler);
}
