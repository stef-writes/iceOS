"use client";
import { NavSidebar } from "@/modules/shell/NavSidebar";
import { Topbar } from "@/modules/shell/Topbar";
import { useUiStore } from "@/modules/shell/useUiStore";

export function AppShell({ children }: { children: React.ReactNode }) {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  return (
    <div className="h-full flex">
      {sidebarOpen && (
        <aside className="w-56 border-r border-neutral-800 bg-neutral-950">
          <NavSidebar />
        </aside>
      )}
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-auto min-w-0">{children}</main>
      </div>
    </div>
  );
}
