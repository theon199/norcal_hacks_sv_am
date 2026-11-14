"use client";

import { useEffect, useState } from "react";

import type { AuditJob, Stage } from "@/lib/types";

const MARK: Record<Stage["status"], { symbol: string; tone: string; word: string }> = {
  pending: { symbol: "○", tone: "text-muted", word: "Waiting" },
  running: { symbol: "◐", tone: "text-accent", word: "Running" },
  done: { symbol: "●", tone: "text-good", word: "Done" },
  failed: { symbol: "✕", tone: "text-bad", word: "Failed" },
  skipped: { symbol: "–", tone: "text-muted", word: "Skipped" },
};

function seconds(from?: string | null, to?: string | null, now?: number): string | null {
  if (!from) return null;
  const end = to ? Date.parse(to) : now;
  if (!end) return null;
  return `${Math.max(0, Math.round((end - Date.parse(from)) / 1000))} s`;
}

export function StageTimeline({ job }: { job: AuditJob }) {
  const active = job.status === "queued" || job.status === "running";
  const [now, setNow] = useState<number | undefined>(undefined);
  useEffect(() => {
    if (!active) return;
    const tick = () => setNow(Date.now());
    const id = setInterval(tick, 1000);
    const first = setTimeout(tick, 0);
    return () => {
      clearInterval(id);
      clearTimeout(first);
    };
  }, [active]);

  const total = seconds(job.started_at, job.finished_at, now);

  return (
    <section className="rounded-lg border border-line p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-medium">Audit plan</h2>
        <p className="font-mono text-xs text-muted">
          {job.status === "queued" && "Queued: waiting for the compute server"}
          {job.status === "running" && `Running${total ? ` · ${total} elapsed` : ""}`}
          {job.status === "succeeded" && `Finished${total ? ` in ${total}` : ""}`}
          {job.status === "failed" && "Stopped on an error"}
          {job.status === "timeout" && "Stopped: time limit reached"}
        </p>
      </div>
      <ol className="mt-4 flex flex-col gap-3">
        {job.stages.map((stage) => {
          const mark = MARK[stage.status];
          return (
            <li key={stage.id} className="flex gap-3">
              <span className={`w-4 shrink-0 text-center font-mono ${mark.tone}`} aria-hidden="true">
                {mark.symbol}
              </span>
              <div className="min-w-0">
                <p className="text-sm font-medium">
                  {stage.label}
                  <span className={`ml-2 text-xs font-normal ${mark.tone}`}>
                    {mark.word}
                    {stage.status === "done" && seconds(stage.started_at, stage.finished_at)
                      ? ` · ${seconds(stage.started_at, stage.finished_at)}`
                      : ""}
                  </span>
                </p>
                <p className="text-sm text-muted">{stage.why}</p>
                {stage.message && <p className={`mt-0.5 text-sm ${mark.tone}`}>{stage.message}</p>}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
