"use client";
import { NavSidebar } from "@/modules/shell/NavSidebar";
import { Topbar } from "@/modules/shell/Topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-full flex">
      <aside className="w-56 border-r border-neutral-800 bg-neutral-950">
        <NavSidebar />
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-auto min-w-0">{children}</main>
      </div>
    </div>
  );
}
