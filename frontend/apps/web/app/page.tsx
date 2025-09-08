"use client";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  return (
    <div className="p-8 max-w-5xl">
      <div className="text-2xl font-semibold mb-2">iceOS Studio</div>
      <div className="text-neutral-400 mb-6">Design and run AI workflows on the Canvas.</div>
      <div className="flex gap-3 text-sm">
        <button
          className="px-3 py-2 border border-neutral-700 rounded hover:bg-neutral-800"
          onClick={() => router.push("/workspaces")}
        >Workspaces</button>
        <button
          className="px-3 py-2 border border-neutral-700 rounded hover:bg-neutral-800"
          onClick={() => router.push("/workspaces")}
        >Projects</button>
      </div>
      <div className="mt-8 grid grid-cols-3 gap-4 text-xs">
        <div className="border border-neutral-800 rounded p-3">
          <div className="font-medium mb-1">Professional UX</div>
          <div className="text-neutral-400">Clean navigation, fast actions, and clear status. Focus on building, not wiring.</div>
        </div>
        <div className="border border-neutral-800 rounded p-3">
          <div className="font-medium mb-1">Zero Setup</div>
          <div className="text-neutral-400">Built-in templates load automatically. Add workflows to a project and start running.</div>
        </div>
        <div className="border border-neutral-800 rounded p-3">
          <div className="font-medium mb-1">Bring Your Repo</div>
          <div className="text-neutral-400">Mount a repo and register its manifests to use your tools and workflows.</div>
        </div>
      </div>
    </div>
  );
}
