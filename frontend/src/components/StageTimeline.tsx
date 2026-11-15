"use client";

import { useEffect, useState } from "react";

import type { AuditJob, Stage } from "@/lib/types";

const MARK: Record<Stage["status"], { symbol: string; dot: string; tone: string; word: string }> = {
  pending: { symbol: "", dot: "border border-line bg-card", tone: "text-muted", word: "Waiting" },
  running: { symbol: "", dot: "border-2 border-accent border-t-transparent animate-spin motion-reduce:animate-none", tone: "text-accent", word: "Running" },
  done: { symbol: "✓", dot: "bg-good text-card", tone: "text-good", word: "Done" },
  failed: { symbol: "✕", dot: "bg-bad text-card", tone: "text-bad", word: "Failed" },
  skipped: { symbol: "–", dot: "border border-line bg-card text-muted", tone: "text-muted", word: "Skipped" },
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
  const settled = job.stages.filter((s) => s.status !== "pending" && s.status !== "running").length;

  return (
    <section className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold tracking-tight">Audit plan</h2>
        <p className="text-sm text-muted">
          {job.status === "queued" && "Queued: waiting for the compute server"}
          {job.status === "running" && `Running${total ? `, ${total} elapsed` : ""}`}
          {job.status === "succeeded" && `Finished${total ? ` in ${total}` : ""}`}
          {job.status === "failed" && "Stopped on an error"}
          {job.status === "timeout" && "Stopped: time limit reached"}
        </p>
      </div>
      {active && (
        <div
          className="mt-4 h-1.5 overflow-hidden rounded-full bg-surface"
          role="progressbar"
          aria-label="Stages finished"
          aria-valuemin={0}
          aria-valuemax={job.stages.length}
          aria-valuenow={settled}
        >
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-500"
            style={{ width: `${(settled / Math.max(1, job.stages.length)) * 100}%` }}
          />
        </div>
      )}
      <ol className="mt-5">
        {job.stages.map((stage, i) => {
          const mark = MARK[stage.status];
          return (
            <li key={stage.id} className="relative flex gap-3 pb-5 last:pb-0">
              {i < job.stages.length - 1 && (
                <span className="absolute bottom-0 left-[9.5px] top-6 w-px bg-line" aria-hidden="true" />
              )}
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold leading-none ${mark.dot}`}
                aria-hidden="true"
              >
                {mark.symbol}
              </span>
              <div className="min-w-0">
                <p className={`text-sm font-semibold ${stage.status === "pending" ? "text-muted" : ""}`}>
                  {stage.label}
                  <span className={`ml-2 text-xs font-normal ${mark.tone}`}>
                    {mark.word}
                    {stage.status === "done" && seconds(stage.started_at, stage.finished_at)
                      ? `, ${seconds(stage.started_at, stage.finished_at)}`
                      : ""}
                  </span>
                </p>
                <p className="mt-0.5 text-sm text-muted">{stage.why}</p>
                {stage.message && <p className={`mt-0.5 text-sm ${mark.tone}`}>{stage.message}</p>}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
