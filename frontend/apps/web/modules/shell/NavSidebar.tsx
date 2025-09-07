"use client";
import Link from "next/link";
import { emit } from "@/modules/core/events";
// (no state/hooks needed – simplified nav only)

export function NavSidebar() {
  return (
    <div className="p-2 text-sm space-y-2">
      <div className="font-semibold">Navigation</div>
      <nav className="grid gap-1">
        <Link href="/canvas" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.canvas" })}>Canvas</Link>
        <Link href="/workspaces" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.workspaces" })}>Workspaces</Link>
      </nav>
    </div>
  );
}
