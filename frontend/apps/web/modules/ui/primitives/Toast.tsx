"use client";
import * as React from "react";
import * as RT from "@radix-ui/react-toast";

export function ToastProvider({ children }: { children: React.ReactNode }) {
  return <RT.Provider swipeDirection="right">{children}<RT.Viewport className="fixed bottom-2 right-2 w-[360px] flex flex-col gap-2" /></RT.Provider>;
}

export function Toast({ title, description, open, onOpenChange }: { title?: string; description?: string; open?: boolean; onOpenChange?: (o: boolean) => void }) {
  return (
    <RT.Root open={open} onOpenChange={onOpenChange} className="bg-surface text-text border border-border rounded p-2 shadow">
      {title && <RT.Title className="text-sm font-semibold">{title}</RT.Title>}
      {description && <RT.Description className="text-xs text-muted">{description}</RT.Description>}
    </RT.Root>
  );
}
