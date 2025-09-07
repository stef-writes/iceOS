"use client";
import { createContext, useContext, useMemo, useState, useEffect } from "react";
import { setProjectIdGlobal } from "@/modules/context/projectIdGlobal";

type ProjectCtx = {
  projectId: string | null;
  setProjectId: (id: string | null) => void;
};

const Ctx = createContext<ProjectCtx>({ projectId: null, setProjectId: () => {} });

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [projectId, setProjectId] = useState<string | null>(null);
  useEffect(() => { setProjectIdGlobal(projectId); }, [projectId]);
  const value = useMemo(() => ({ projectId, setProjectId }), [projectId]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useProjectContext(): ProjectCtx {
  return useContext(Ctx);
}
