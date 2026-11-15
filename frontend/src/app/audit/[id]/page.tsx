"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Results } from "@/components/Results";
import { StageTimeline } from "@/components/StageTimeline";
import { ApiError, getAudit } from "@/lib/api";
import type { AuditJob } from "@/lib/types";

const TERMINAL = new Set(["succeeded", "failed", "timeout"]);
const POLL_MS = 1000;

function AuditView() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<AuditJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let misses = 0;

    async function poll() {
      try {
        const next = await getAudit(id);
        if (stopped) return;
        misses = 0;
        setJob(next);
        setError(null);
        if (TERMINAL.has(next.status)) return;
      } catch (e) {
        if (stopped) return;
        if (e instanceof ApiError && e.code === "unknown_audit") {
          setError(e.message);
          return;
        }
        misses += 1;
        if (misses >= 5) setError("Lost contact with the compute server. Still retrying…");
      }
      timer = setTimeout(poll, POLL_MS);
    }
    poll();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  const done = job?.status === "succeeded" && job.report;

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:py-10">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <Link href="/" className="font-mono text-sm text-accent">
          ← LabMirror
        </Link>
        <p className="font-mono text-xs text-muted">audit {id}</p>
      </header>

      {error && (
        <p className="mt-6 rounded-md border border-bad bg-bad-soft px-4 py-3 text-sm text-bad" role="alert">
          {error}
        </p>
      )}
      {!job && !error && <p className="mt-6 text-sm text-muted">Loading the audit…</p>}

      {job && (
        <div className="mt-6 flex flex-col gap-6">
          {job.error && (
            <div className="rounded-md border border-bad bg-bad-soft px-4 py-3 text-sm text-bad" role="alert">
              <p className="font-medium">{job.status === "timeout" ? "The audit ran out of time." : "The audit could not finish."}</p>
              <p className="mt-1">{job.error.message}</p>
              <p className="mt-2">
                No results are shown because none were completed.{" "}
                <Link href="/" className="underline">
                  Start a new audit
                </Link>
                .
              </p>
            </div>
          )}
          {done ? (
            <>
              <Results report={job.report!} />
              <details>
                <summary className="cursor-pointer text-sm font-medium">What was run, step by step</summary>
                <div className="mt-3">
                  <StageTimeline job={job} />
                </div>
              </details>
            </>
          ) : (
            <StageTimeline job={job} />
          )}
        </div>
      )}
    </main>
  );
}

// The audit id is only known at request time, so the view suspends during prerendering.
export default function AuditPage() {
  return (
    <Suspense fallback={<main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 text-sm text-muted">Loading the audit…</main>}>
      <AuditView />
    </Suspense>
  );
}
