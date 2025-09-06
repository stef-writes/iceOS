"use client";
import * as React from "react";

type Variant = "default" | "outline" | "ghost" | "danger";
type Size = "sm" | "md";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

function classes(variant: Variant, size: Size, extra?: string) {
  const base = "inline-flex items-center justify-center rounded border transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const v = {
    default: "bg-surface text-text border-border hover:bg-neutral-900",
    outline: "bg-transparent text-text border-border hover:bg-neutral-900",
    ghost: "bg-transparent text-muted border-transparent hover:bg-neutral-900",
    danger: "bg-transparent text-danger border-danger hover:bg-danger/10",
  }[variant];
  const s = size === "sm" ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm";
  return [base, v, s, extra ?? ""].join(" ");
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "outline", size = "sm", className, ...props }, ref
) {
  return <button ref={ref} className={classes(variant, size, className)} {...props} />;
});
