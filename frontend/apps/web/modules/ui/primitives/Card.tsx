"use client";
import * as React from "react";

export function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  const cls = ["bg-surface border border-border rounded p-3", className ?? ""].join(" ");
  return <div className={cls}>{children}</div>;
}
