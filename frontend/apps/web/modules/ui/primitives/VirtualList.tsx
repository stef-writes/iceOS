"use client";
import * as React from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

export function VirtualList<T>({ items, estimateSize, overscan = 8, height = 480, render }: { items: T[]; estimateSize?: number; overscan?: number; height?: number; render: (item: T, index: number) => React.ReactNode }) {
  const parentRef = React.useRef<HTMLDivElement | null>(null);
  const rowVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize ?? 80,
    overscan,
  });

  return (
    <div ref={parentRef} className="border border-border rounded" style={{ height, overflow: "auto" }}>
      <div style={{ height: rowVirtualizer.getTotalSize(), width: "100%", position: "relative" }}>
        {rowVirtualizer.getVirtualItems().map((vi) => (
          <div key={vi.key} className="absolute left-0 top-0 w-full" style={{ transform: `translateY(${vi.start}px)`, height: vi.size }}>
            {render(items[vi.index], vi.index)}
          </div>
        ))}
      </div>
    </div>
  );
}
