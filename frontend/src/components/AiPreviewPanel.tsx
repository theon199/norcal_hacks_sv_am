import { findAiPreview, unverifiedNumbers } from "@/lib/aiPreview";
import type { AuditReport } from "@/lib/types";

const TEST_LABELS: Record<string, string> = {
  seed_sensitivity: "Repeat on five other splits",
  noise_robustness: "Stress-test with feature noise",
  leakage_diagnostics: "Check for leakage signs",
};

function AiBadge() {
  return (
    <span className="rounded bg-warn-soft px-1.5 py-0.5 text-xs font-normal text-warn">
      AI-suggested · pre-generated
    </span>
  );
}

/** Shown only for a report that matches a pre-generated preview (currently the sensor-fault demo). */
export function AiPreviewPanel({ report }: { report: AuditReport }) {
  const preview = findAiPreview(report);
  if (!preview) return null;

  const findingFor = (step: string) => report.trace.find((t) => t.step === step && t.actor === "engine")?.decision;
  const bad = unverifiedNumbers(preview.narrative, report);
  const narrativeOk = bad.length === 0;
  const def = report.default_split;

  return (
    <section className="rounded-lg border border-dashed border-warn p-5">
      <h3 className="flex flex-wrap items-center gap-2 font-medium">
        AI auditor <AiBadge />
      </h3>
      <p className="mt-1 text-xs text-muted">
        Preview of LabMirror&apos;s planned AI layer. This output was written ahead of time with Claude for this example
        dataset and claim. It was not generated live by this app. The AI picks tests and writes prose only. Every
        measurement and the verdict come from the Python engine above, and each finding below is read from this run.
      </p>

      <h4 className="mt-4 text-sm font-medium">Skeptical Auditor: which tests to run next</h4>
      <p className="mt-1 text-xs text-muted">
        Input: the claim, column names and types, and the default-split result
        {def ? ` (${def.n_test} test rows)` : ""}. No raw rows.
      </p>
      <ol className="mt-3 flex flex-col gap-3">
        {preview.skeptic.map((s, i) => (
          <li key={s.test_id} className="grid gap-1 rounded-md bg-surface p-3 text-sm sm:grid-cols-[8rem_1fr]">
            <span className="text-xs text-muted">Proposed test {i + 1}</span>
            <span>
              {TEST_LABELS[s.test_id]} <span className="font-mono text-xs text-muted">({s.test_id})</span>
            </span>
            <span className="text-xs text-muted">Why</span>
            <span className="text-xs">{s.rationale}</span>
            <span className="text-xs text-muted">Finding</span>
            <span className="text-xs font-medium">{findingFor(s.test_id) ?? "Not run in this audit."}</span>
          </li>
        ))}
      </ol>

      <h4 className="mt-5 text-sm font-medium">Evidence Writer: plain-language summary</h4>
      {narrativeOk ? (
        <>
          <p className="mt-2 text-sm">{preview.narrative}</p>
          <p className="mt-2 text-xs text-good">
            ✓ Number check passed: every number in this summary matches a value in this run&apos;s report.
          </p>
        </>
      ) : (
        <p className="mt-2 text-sm text-bad">
          Summary hidden: {bad.length} number(s) ({bad.join(", ")}) do not match this run&apos;s report, so the template
          summary above stands.
        </p>
      )}
    </section>
  );
}
