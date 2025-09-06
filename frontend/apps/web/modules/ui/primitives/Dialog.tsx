"use client";
import * as React from "react";
import * as RD from "@radix-ui/react-dialog";

export function Dialog({ open, onOpenChange, title, children }: { open?: boolean; onOpenChange?: (o: boolean) => void; title?: string; children: React.ReactNode }) {
  return (
    <RD.Root open={open} onOpenChange={onOpenChange}>
      <RD.Portal>
        <RD.Overlay className="fixed inset-0 bg-black/40" />
        <RD.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-surface border border-border rounded p-3 w-[520px] shadow-xl">
          {title && <div className="text-sm font-semibold mb-2">{title}</div>}
          {children}
        </RD.Content>
      </RD.Portal>
    </RD.Root>
  );
}

export const DialogTrigger = RD.Trigger;
export const DialogClose = RD.Close;
