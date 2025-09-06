"use client";
import dynamic from "next/dynamic";
import type { editor as MonacoTypes } from "monaco-editor";

const Monaco = dynamic(() => import("@monaco-editor/react"), { ssr: false });

export type MonacoEditorProps = {
  language?: string;
  value: string;
  onChange?: (value: string) => void;
  height?: string | number;
  readOnly?: boolean;
  options?: MonacoTypes.IStandaloneEditorConstructionOptions;
};

export default function MonacoEditor({
  language = "typescript",
  value,
  onChange,
  height = "60vh",
  readOnly = false,
  options,
}: MonacoEditorProps) {
  return (
    <Monaco
      height={height}
      defaultLanguage={language}
      value={value}
      onChange={(v) => onChange?.(v ?? "")}
      options={{
        minimap: { enabled: false },
        wordWrap: "on",
        readOnly,
        automaticLayout: true,
        scrollBeyondLastLine: false,
        tabSize: 2,
        ...options,
      }}
      theme="vs-dark"
    />
  );
}
