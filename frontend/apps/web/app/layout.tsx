import "./styles/globals.css";
import type { Metadata } from "next";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";
import { AppShell } from "@/modules/shell/AppShell";
import { ToastProvider } from "@/modules/ui/primitives/Toast";

export const metadata: Metadata = {
  title: "iceOS Studio",
  description: "Canvas, Studio, Repo, Library",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full bg-neutral-950 text-neutral-100">
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}
