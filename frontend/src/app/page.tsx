"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Health = { status: string; version: string; llm_enabled: boolean };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setHealth)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 px-4">
      <h1 className="text-4xl font-semibold tracking-tight">LabMirror</h1>
      <p className="text-lg text-zinc-600 dark:text-zinc-400">
        Don&apos;t just trust the research. Test it.
      </p>
      <p className="rounded-md border border-zinc-300 px-4 py-3 font-mono text-sm dark:border-zinc-700">
        {health
          ? `backend: ${health.status} (v${health.version})`
          : error
            ? `backend: unreachable (${error})`
            : "backend: waking the compute server…"}
      </p>
    </main>
  );
}
