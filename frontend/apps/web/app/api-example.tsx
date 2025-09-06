"use client";
import { useEffect, useState } from "react";
import { IceApiClient } from "@ice/api-client";

export default function ApiExample() {
  const [status, setStatus] = useState<string>("idle");
  const [result, setResult] = useState<any>(null);
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const token = process.env.NEXT_PUBLIC_API_TOKEN ?? "dev-token";
    const client = new IceApiClient({ baseUrl: base, token });
    (async () => {
      setStatus("calling");
      const s = await client.suggest({ text: "hello", canvas_state: {} });
      setResult(s);
      setStatus("done");
    })().catch((e) => {
      setStatus(String(e));
    });
  }, []);
  return (
    <div className="text-sm">
      <div>Status: {status}</div>
      <pre className="mt-2 whitespace-pre-wrap break-words">{JSON.stringify(result, null, 2)}</pre>
    </div>
  );
}
