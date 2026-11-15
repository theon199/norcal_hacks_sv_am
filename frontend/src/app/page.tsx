"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ClaimBuilder, validateDraft, type ClaimDraft } from "@/components/ClaimBuilder";
import { DatasetHealth } from "@/components/DatasetHealth";
import { UploadDropzone } from "@/components/UploadDropzone";
import { ApiError, createAudit, getDemos, getHealth, loadDemo, uploadDataset } from "@/lib/api";
import { otherModel } from "@/lib/format";
import type { ClaimSpec, DatasetSummary, DemoDescriptor } from "@/lib/types";

type Server = "waking" | "ok" | "down";

function defaultExclusions(summary: DatasetSummary, target: string): string[] {
  return summary.columns
    .filter((c) => c.name !== target && (c.kind === "unusable" || c.flags.includes("identifier_like")))
    .map((c) => c.name);
}

function draftFor(summary: DatasetSummary, suggested?: ClaimSpec): ClaimDraft {
  const target =
    suggested && summary.binary_target_candidates.includes(suggested.target)
      ? suggested.target
      : summary.binary_target_candidates.length === 1
        ? summary.binary_target_candidates[0]
        : "";
  return {
    target,
    candidate: suggested?.candidate ?? "random_forest",
    threshold: String(suggested?.threshold_pp ?? 5),
    reportedCandidate: "",
    reportedBaseline: "",
    sourceNote: suggested?.source_note ?? "",
    excluded: defaultExclusions(summary, target),
  };
}

export default function Home() {
  const [server, setServer] = useState<Server>("waking");
  const [demos, setDemos] = useState<DemoDescriptor[]>([]);
  const [summary, setSummary] = useState<DatasetSummary | null>(null);
  const [draft, setDraft] = useState<ClaimDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [source, setSource] = useState<string | null>(null); // demo id, or "upload"
  const dataRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    getHealth()
      .then(() => {
        setServer("ok");
        return getDemos().then(setDemos);
      })
      .catch(() => setServer("down"));
  }, []);

  async function load(action: () => Promise<DatasetSummary>, from: string, suggested?: ClaimSpec) {
    setBusy(true);
    setError(null);
    try {
      const next = await action();
      setSource(from);
      setSummary(next);
      setDraft(draftFor(next, suggested));
      // The dataset appears below the fold; bring it into view so the click visibly did something.
      requestAnimationFrame(() => dataRef.current?.scrollIntoView({ block: "start" }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong while loading the dataset.");
    } finally {
      setBusy(false);
    }
  }

  function changeDraft(next: ClaimDraft) {
    if (summary && draft && next.target !== draft.target) next = { ...next, excluded: defaultExclusions(summary, next.target) };
    setDraft(next);
  }

  const problem = summary && draft ? validateDraft(summary, draft) : null;

  async function run() {
    if (!summary || !draft || problem) return;
    setStarting(true);
    setError(null);
    const fraction = (raw: string) => (raw.trim() === "" ? null : Number(raw) / 100);
    try {
      const job = await createAudit({
        dataset_id: summary.dataset_id,
        claim: {
          target: draft.target,
          candidate: draft.candidate,
          baseline: otherModel(draft.candidate),
          metric: "accuracy",
          threshold_pp: Number(draft.threshold),
          reported_candidate_accuracy: fraction(draft.reportedCandidate),
          reported_baseline_accuracy: fraction(draft.reportedBaseline),
          source_note: draft.sourceNote.trim() || null,
        },
        excluded_columns: draft.excluded,
      });
      router.push(`/audit/${job.audit_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong while starting the audit.");
      setStarting(false);
    }
  }

  const errorBox = error && (
    <p className="mt-4 rounded-[10px] border border-bad/40 bg-bad-soft px-4 py-3 text-sm text-bad" role="alert">
      {error}
    </p>
  );

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-24 pt-10 sm:pt-16">
      <section>
        <h1 className="max-w-3xl text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
          Don&apos;t just trust the research. Test it.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted">
          State a machine-learning claim, such as &ldquo;Random Forest beats Logistic Regression by 5 points&rdquo;. LabMirror
          reruns the comparison on your data, challenges it with other splits and stress tests, and reports which
          conclusions still hold.
        </p>
        <ul className="mt-5 flex flex-wrap gap-2" aria-label="Scope">
          {["Binary classification", "CSV tabular data", "scikit-learn models"].map((s) => (
            <li key={s} className="tag tag-quiet">
              {s}
            </li>
          ))}
        </ul>
        <p className="mt-2 max-w-2xl text-sm text-muted">
          This is an independent re-evaluation, not a reproduction of a published study.
        </p>
      </section>

      {server !== "ok" && (
        <p className="card mt-8 flex items-center gap-3 px-4 py-3 text-sm" role="status">
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${server === "waking" ? "animate-pulse bg-warn motion-reduce:animate-none" : "bg-bad"}`}
            aria-hidden="true"
          />
          {server === "waking"
            ? "Waking the compute server. This can take up to a minute after a quiet period…"
            : "The compute server is unreachable right now. Reload the page in a minute."}
        </p>
      )}

      <Step n={1} title="Choose a dataset" done={Boolean(summary)}>
        <div className="grid gap-4 md:grid-cols-2">
          {demos.length === 0 && (
            <p className="card p-5 text-sm text-muted md:col-span-2">Examples appear once the server is awake.</p>
          )}
          {demos.map((d) => {
            const loaded = source === d.id && Boolean(summary);
            return (
              <article
                key={d.id}
                className={`card flex flex-col gap-3 p-5 ${loaded ? "border-accent outline outline-1 outline-accent" : ""}`}
              >
                <h3 className="flex flex-wrap items-center gap-2 font-semibold">
                  {d.title}
                  {loaded && <span className="tag">loaded</span>}
                </h3>
                <p className="text-sm">{d.description}</p>
                <p className="text-xs text-muted">{d.provenance_note}</p>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => load(() => loadDemo(d.id), d.id, d.suggested_claim)}
                  className="btn btn-primary mt-auto self-start"
                >
                  Try this example
                </button>
              </article>
            );
          })}
          <div className="md:col-span-2">
            <UploadDropzone busy={busy || server !== "ok"} onFile={(file) => load(() => uploadDataset(file), "upload")} />
          </div>
        </div>
        {busy && (
          <p className="mt-4 flex items-center gap-2 text-sm text-muted" role="status">
            <span
              className="h-4 w-4 animate-spin rounded-full border-2 border-accent border-t-transparent motion-reduce:animate-none"
              aria-hidden="true"
            />
            Reading and profiling the dataset…
          </p>
        )}
        {!summary && errorBox}
      </Step>

      <div ref={dataRef} className="scroll-mt-4">
        <Step n={2} title="Check the data" done={Boolean(summary)}>
          {summary ? (
            <DatasetHealth summary={summary} />
          ) : (
            <Placeholder>Row counts, column types, missing values and a preview appear here once a dataset is loaded.</Placeholder>
          )}
        </Step>
      </div>

      <Step n={3} title="State the claim and run">
        {summary && draft ? (
          <>
            <ClaimBuilder summary={summary} draft={draft} onChange={changeDraft} />
            <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3">
              <button
                type="button"
                disabled={Boolean(problem) || starting}
                onClick={run}
                className="btn btn-primary px-6 py-3 text-base"
              >
                {starting ? "Starting…" : "Run stress test"}
              </button>
              <p className={`max-w-xl text-sm ${problem ? "text-warn" : "text-muted"}`}>
                {problem ??
                  "Runs a default split, five other splits, a noise test and leakage checks. Usually under a minute."}
              </p>
            </div>
            {errorBox}
          </>
        ) : (
          <Placeholder>
            Pick the target column, the model that is claimed to win and by how many points. Then run the stress test.
          </Placeholder>
        )}
      </Step>
    </main>
  );
}

// The setup really is a sequence, so the steps are numbered; a finished step fills in.
function Step({ n, title, done, children }: { n: number; title: string; done?: boolean; children: ReactNode }) {
  return (
    <section className="mt-12">
      <h2 className="flex items-center gap-3 text-xl font-semibold tracking-tight">
        <span
          className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-sm tabular-nums ${
            done ? "border-accent bg-accent text-on-accent" : "border-line text-muted"
          }`}
        >
          <span className="sr-only">Step </span>
          {n}
        </span>
        {title}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Placeholder({ children }: { children: ReactNode }) {
  return <p className="rounded-[14px] border border-dashed border-line px-5 py-6 text-sm text-muted">{children}</p>;
}
