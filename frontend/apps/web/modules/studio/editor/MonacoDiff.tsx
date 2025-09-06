"use client";
import dynamic from "next/dynamic";

const DiffEditor = dynamic(() => import("@monaco-editor/react").then(m => m.DiffEditor), { ssr: false });

export function MonacoDiff({ original, modified, height = "40vh", language = "json" }: { original: string; modified: string; height?: string | number; language?: string }) {
  return (
    <DiffEditor
      original={original}
      modified={modified}
      height={height}
      language={language}
      theme="vs-dark"
      options={{
        readOnly: true,
        renderSideBySide: true,
        automaticLayout: true,
        renderIndicators: false,
        minimap: { enabled: false },
      }}
    />
  );
}
