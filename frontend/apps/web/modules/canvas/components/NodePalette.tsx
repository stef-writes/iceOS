"use client";
type Props = {
  onAdd: (type: string) => void;
};

const TYPES: Array<{ key: string; label: string }> = [
  { key: "llm", label: "LLM" },
  { key: "tool", label: "Tool" },
  { key: "agent", label: "Agent" },
  { key: "aggregator", label: "Aggregator (concat)" },
];

export default function NodePalette({ onAdd }: Props) {
  return (
    <div className="h-[80vh] overflow-auto border border-neutral-800 rounded p-2 text-sm">
      <div className="text-neutral-300 mb-2">Palette</div>
      <div className="grid grid-cols-2 gap-2">
        {TYPES.map((t) => (
          <button
            key={t.key}
            className="px-2 py-1 border border-neutral-700 rounded hover:bg-neutral-800 text-xs"
            onClick={() => onAdd(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}
