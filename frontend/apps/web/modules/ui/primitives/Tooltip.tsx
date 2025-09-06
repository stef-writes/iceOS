"use client";
import * as React from "react";
import * as RT from "@radix-ui/react-tooltip";

export function Tooltip({ content, children }: { content: React.ReactNode; children: React.ReactNode }) {
  return (
    <RT.Provider delayDuration={250}>
      <RT.Root>
        <RT.Trigger asChild>{children}</RT.Trigger>
        <RT.Portal>
          <RT.Content className="bg-neutral-900 text-text border border-border rounded px-2 py-1 text-xs shadow">
            {content}
            <RT.Arrow className="fill-neutral-900" />
          </RT.Content>
        </RT.Portal>
      </RT.Root>
    </RT.Provider>
  );
}
