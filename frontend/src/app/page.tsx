"use client";

import { useEffect, useState } from "react";

import { ClaimBuilder, validateDraft, type ClaimDraft } from "@/components/ClaimBuilder";
import { DatasetHealth } from "@/components/DatasetHealth";
import { UploadDropzone } from "@/components/UploadDropzone";
import { ApiError, getDemos, getHealth, loadDemo, uploadDataset } from "@/lib/api";
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

  useEffect(() => {
    getHealth()
      .then(() => {
        setServer("ok");
        return getDemos().then(setDemos);
      })
      .catch(() => setServer("down"));
  }, []);

  async function load(action: () => Promise<DatasetSummary>, suggested?: ClaimSpec) {
    setBusy(true);
    setError(null);
    try {
      const next = await action();
      setSummary(next);
      setDraft(draftFor(next, suggested));
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

  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:py-14">
      <header>
        <p className="font-mono text-sm text-accent">LabMirror</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-5xl">
          Don&apos;t just trust the research. Test it.
        </h1>
        <p className="mt-4 max-w-2xl text-muted">
          State a machine-learning claim, such as &ldquo;Random Forest beats Logistic Regression by 5 points&rdquo;. LabMirror
          reruns the comparison on your data, challenges it with other splits and stress tests, and reports which
          conclusions still hold.
        </p>
        <p className="mt-3 text-xs text-muted">
          Scope: binary classification · CSV tabular data · scikit-learn models. This is an independent
          re-evaluation, not a reproduction of a published study.
        </p>
      </header>

      {server !== "ok" && (
        <p className="mt-6 rounded-md border border-line bg-surface px-4 py-3 text-sm" role="status">
          {server === "waking"
            ? "Waking the compute server. This can take up to a minute after a quiet period…"
            : "The compute server is unreachable right now. Reload the page in a minute."}
        </p>
      )}

      <section className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="flex flex-col gap-3 rounded-lg border border-line p-5">
          <h3 className="font-medium">Try an example</h3>
          {demos.length === 0 && <p className="text-sm text-muted">Examples appear once the server is awake.</p>}
          {demos.map((d) => (
            <div key={d.id} className="flex flex-1 flex-col justify-between gap-3">
              <div>
                <p className="text-sm font-medium">{d.title}</p>
                <p className="mt-1 text-sm text-muted">{d.description}</p>
                <p className="mt-2 text-xs text-muted">{d.provenance_note}</p>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => load(() => loadDemo(d.id), d.suggested_claim)}
                className="self-start rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
              >
                Try this example
              </button>
            </div>
          ))}
        </div>
        <UploadDropzone busy={busy || server !== "ok"} onFile={(file) => load(() => uploadDataset(file))} />
      </section>

      {busy && <p className="mt-4 text-sm text-muted">Reading and profiling the dataset…</p>}
      {error && (
        <p className="mt-4 rounded-md border border-bad bg-bad-soft px-4 py-3 text-sm text-bad" role="alert">
          {error}
        </p>
      )}

      {summary && draft && (
        <div className="mt-8 flex flex-col gap-6">
          <DatasetHealth summary={summary} />
          <ClaimBuilder summary={summary} draft={draft} onChange={changeDraft} />
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              disabled
              className="rounded-md bg-accent px-5 py-2.5 font-medium text-white disabled:opacity-40"
            >
              Run stress test
            </button>
            <p className="text-sm text-muted">
              {problem ?? "The claim is valid. Running audits from this page is not wired up in this build yet."}
            </p>
          </div>
        </div>
      )}
    </main>
  );
}
