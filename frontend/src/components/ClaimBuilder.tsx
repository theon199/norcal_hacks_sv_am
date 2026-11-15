"use client";

import { claimSentence, MODEL_LABELS, otherModel } from "@/lib/format";
import type { ColumnFlag, DatasetSummary, ModelKey } from "@/lib/types";

export interface ClaimDraft {
  target: string;
  candidate: ModelKey;
  threshold: string; // raw input text, percentage points
  reportedCandidate: string; // raw input text, percent
  reportedBaseline: string;
  sourceNote: string;
  excluded: string[];
}

const FLAG_LABELS: Record<ColumnFlag, string> = {
  identifier_like: "looks like an ID",
  leakage_name: "name suggests the outcome",
  high_cardinality: "too many categories",
  constant: "constant",
  free_text: "free text",
};

const MIN_FEATURES = 2;
const MAX_FEATURES = 50;
const MAX_CELLS = 100_000; // rows × selected features; mirrors backend config.MAX_CELLS

export function validateDraft(summary: DatasetSummary, draft: ClaimDraft): string | null {
  if (!draft.target) return "Choose the target column.";
  const threshold = Number(draft.threshold);
  if (draft.threshold.trim() === "" || !Number.isFinite(threshold) || threshold <= 0 || threshold > 100)
    return "The claimed improvement must be greater than 0 and at most 100 percentage points.";
  for (const raw of [draft.reportedCandidate, draft.reportedBaseline]) {
    if (raw.trim() === "") continue;
    const v = Number(raw);
    if (!Number.isFinite(v) || v < 0 || v > 100) return "Reported accuracies must be between 0 and 100%.";
  }
  const features = summary.columns.filter((c) => c.name !== draft.target && !draft.excluded.includes(c.name));
  const unusable = features.find((c) => c.kind === "unusable");
  if (unusable) return `Column “${unusable.name}” cannot be used as a feature. Exclude it to continue.`;
  if (features.length < MIN_FEATURES) return `Keep at least ${MIN_FEATURES} feature columns.`;
  if (features.length > MAX_FEATURES) return `At most ${MAX_FEATURES} feature columns are supported. Exclude some.`;
  if (summary.n_rows * features.length > MAX_CELLS)
    return `${summary.n_rows.toLocaleString()} rows × ${features.length} features is over the ${MAX_CELLS.toLocaleString()}-value limit that keeps audits fast. Keep at most ${Math.floor(MAX_CELLS / summary.n_rows)} feature columns.`;
  return null;
}

const field = "field";
const label = "block text-sm font-medium";

export function ClaimBuilder({
  summary,
  draft,
  onChange,
}: {
  summary: DatasetSummary;
  draft: ClaimDraft;
  onChange: (next: ClaimDraft) => void;
}) {
  const set = (patch: Partial<ClaimDraft>) => onChange({ ...draft, ...patch });
  const toggle = (name: string) =>
    set({ excluded: draft.excluded.includes(name) ? draft.excluded.filter((c) => c !== name) : [...draft.excluded, name] });
  const featureColumns = summary.columns.filter((c) => c.name !== draft.target);
  const usedCount = featureColumns.filter((c) => !draft.excluded.includes(c.name)).length;

  return (
    <section className="card p-5 sm:p-6">
      <figure className="border-l-2 border-accent pl-4">
        <figcaption className="text-xs text-muted">The claim under test</figcaption>
        <blockquote className="mt-1 max-w-3xl font-serif text-xl leading-snug sm:text-2xl">
          {claimSentence(draft.candidate, Number(draft.threshold))}
        </blockquote>
        <p className="mt-2 text-xs text-muted">
          Primary metric: accuracy. Balanced accuracy and F1 are reported alongside.
        </p>
      </figure>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <label className={label}>
          Target column
          <select className={field} value={draft.target} onChange={(e) => set({ target: e.target.value })}>
            <option value="">Choose…</option>
            {summary.binary_target_candidates.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className={label}>
          Candidate model
          <select
            className={field}
            value={draft.candidate}
            onChange={(e) => set({ candidate: e.target.value as ModelKey })}
          >
            {(Object.keys(MODEL_LABELS) as ModelKey[]).map((m) => (
              <option key={m} value={m}>
                {MODEL_LABELS[m]}
              </option>
            ))}
          </select>
        </label>
        <div className={label}>
          Baseline model
          <p className={`${field} bg-surface text-muted`} title="The baseline is always the other model">
            {MODEL_LABELS[otherModel(draft.candidate)]}
          </p>
        </div>
        <label className={label}>
          Claimed improvement (pp)
          <input
            className={field}
            type="number"
            inputMode="decimal"
            min={0}
            max={100}
            step={0.5}
            value={draft.threshold}
            onChange={(e) => set({ threshold: e.target.value })}
          />
        </label>
      </div>
      {summary.binary_target_candidates.length === 0 && (
        <p className="mt-3 text-sm text-warn">
          No column has exactly two values and no missing entries, so there is no valid binary target in this file.
        </p>
      )}

      <details className="mt-6 border-t border-line pt-4">
        <summary className="cursor-pointer text-sm font-semibold">
          Originally reported result <span className="font-normal text-muted">(optional, shown for context only)</span>
        </summary>
        <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className={label}>
            Reported candidate accuracy (%)
            <input
              className={field}
              type="number"
              min={0}
              max={100}
              value={draft.reportedCandidate}
              onChange={(e) => set({ reportedCandidate: e.target.value })}
            />
          </label>
          <label className={label}>
            Reported baseline accuracy (%)
            <input
              className={field}
              type="number"
              min={0}
              max={100}
              value={draft.reportedBaseline}
              onChange={(e) => set({ reportedBaseline: e.target.value })}
            />
          </label>
          <label className={`${label} sm:col-span-2`}>
            Source or note
            <input
              className={field}
              type="text"
              maxLength={500}
              value={draft.sourceNote}
              onChange={(e) => set({ sourceNote: e.target.value })}
            />
          </label>
        </div>
        <p className="mt-2 text-xs text-muted">LabMirror does not verify these values; it measures its own.</p>
      </details>

      {draft.target && (
        <div className="mt-4 border-t border-line pt-4">
          <h3 className="text-sm font-semibold">
            Features <span className="font-normal text-muted">({usedCount} used; untick to exclude)</span>
          </h3>
          <ul className="mt-2 grid gap-x-4 sm:grid-cols-2 lg:grid-cols-3">
            {featureColumns.map((c) => {
              const used = !draft.excluded.includes(c.name);
              return (
                <li key={c.name}>
                  <label className="-mx-2 flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-surface">
                    <input type="checkbox" className="mt-1" checked={used} onChange={() => toggle(c.name)} />
                    <span className="min-w-0">
                      <span className={`break-all font-mono text-xs ${used ? "" : "text-muted line-through"}`}>{c.name}</span>{" "}
                      <span className="text-xs text-muted">{c.kind}</span>
                      {c.flags.map((f) => (
                        <span key={f} className="tag tag-warn ml-1">
                          {FLAG_LABELS[f]}
                        </span>
                      ))}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </section>
  );
}
