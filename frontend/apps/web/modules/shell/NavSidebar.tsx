"use client";
import Link from "next/link";
import { emit } from "@/modules/core/events";

export function NavSidebar() {
  return (
    <div className="p-2 text-sm space-y-1">
      <div className="font-semibold mb-2">Surfaces</div>
      <nav className="grid gap-1">
        <Link href="/canvas" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.canvas" })}>Canvas</Link>
        <Link href="/studio" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.studio" })}>Studio</Link>
        <Link href="/repo" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.repo" })}>Repo</Link>
        <Link href="/library" className="hover:text-white text-neutral-300" onClick={() => emit("ui.commandExecuted", { command: "nav.library" })}>Library</Link>
      </nav>
    </div>
  );
}
