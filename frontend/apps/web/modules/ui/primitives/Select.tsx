"use client";
import * as React from "react";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, children, ...props }, ref
) {
  const cls = [
    "bg-neutral-900 text-text border border-border rounded",
    "px-2 py-1 text-sm",
    className ?? "",
  ].join(" ");
  return (
    <select ref={ref} className={cls} {...props}>
      {children}
    </select>
  );
});
