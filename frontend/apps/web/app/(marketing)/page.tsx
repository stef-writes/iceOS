"use client";
import Link from "next/link";
export const dynamic = "force-dynamic";

export default function Landing() {
  return (
    <div className="p-10 mx-auto max-w-5xl text-sm">
      <div className="text-3xl font-semibold mb-3">Welcome to iceOS</div>
      <div className="text-neutral-400 mb-6">An AI-native workflow studio. Sign up with your maker kit, then jump into Workspaces.</div>
      <div className="flex gap-3">
        <Link href="/workspaces" className="px-3 py-2 border border-neutral-700 rounded hover:bg-neutral-800">Open Workspaces</Link>
      </div>
      <div className="mt-10 grid grid-cols-3 gap-4">
        <div className="border border-neutral-800 rounded p-3">
          <div className="font-medium mb-1">Build Workflows</div>
          <div className="text-neutral-400">Use ready-made templates or design your own in the Canvas.</div>
        </div>
        <div className="border border-neutral-800 rounded p-3">
          <div className="font-medium mb-1">Bring Knowledge</div>
          <div className="text-neutral-400">Upload documents to your Library and use them in RAG flows.</div>
        </div>
        <div className="border border-neutral-800 rounded p-3">
          <div className="font-medium mb-1">Preview & Run</div>
          <div className="text-neutral-400">See plan and cost, then execute with live providers.</div>
        </div>
      </div>
    </div>
  );
}
