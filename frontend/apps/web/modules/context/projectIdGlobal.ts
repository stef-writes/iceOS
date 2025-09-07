let _projectId: string | null = null;

export function setProjectIdGlobal(id: string | null) {
  _projectId = id;
}

export function getProjectId(): string | null {
  if (_projectId) return _projectId;
  try {
    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      return sp.get("projectId");
    }
  } catch {}
  return null;
}
