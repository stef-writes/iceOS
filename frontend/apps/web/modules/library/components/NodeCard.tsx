"use client";
export default function NodeCard({ title, subtitle, badges, onOpen, onCopyId, onOpenCanvas, onPreview }: { title: string; subtitle?: string; badges?: string[]; onOpen?: () => void; onCopyId?: () => void; onOpenCanvas?: () => void; onPreview?: () => void }) {
  return (
    <div className="bg-surface border border-border rounded p-3 hover:border-neutral-700 transition-colors">
      <div className="font-mono text-neutral-100 truncate">{title}</div>
      {(subtitle || (badges && badges.length > 0)) && (
        <div className="mt-1 flex items-center gap-2">
          {subtitle && <div className="text-neutral-500 text-xs truncate">{subtitle}</div>}
          {Array.isArray(badges) && badges.map((b, i) => (
            <span key={i} className="text-[10px] px-1.5 py-0.5 border border-neutral-700 rounded bg-neutral-900 text-neutral-300">
              {b}
            </span>
          ))}
        </div>
      )}
      <div className="mt-2 flex items-center gap-2">
        {onOpen && (
          <button onClick={onOpen} className="text-xs px-2 py-1 border border-border rounded hover:bg-neutral-800">Open</button>
        )}
        {onOpenCanvas && (
          <button onClick={onOpenCanvas} className="text-xs px-2 py-1 border border-border rounded hover:bg-neutral-800">Canvas</button>
        )}
        {onCopyId && (
          <button onClick={onCopyId} className="text-xs px-2 py-1 border border-border rounded hover:bg-neutral-800">Copy ID</button>
        )}
        {onPreview && (
          <button onClick={onPreview} className="text-xs px-2 py-1 border border-border rounded hover:bg-neutral-800">Details</button>
        )}
      </div>
    </div>
  );
}
