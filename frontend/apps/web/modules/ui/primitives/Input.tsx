"use client";
import * as React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...props }, ref
) {
  const cls = [
    "w-full bg-neutral-900 text-text border border-border rounded",
    "px-2 py-1 text-sm",
    className ?? "",
  ].join(" ");
  return <input ref={ref} className={cls} {...props} />;
});
