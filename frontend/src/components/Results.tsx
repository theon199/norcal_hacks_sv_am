import Link from "next/link";

import { AccuracyChart, LiftChart, NoiseChart } from "@/components/charts";
import { reportJsonUrl, reportMdUrl } from "@/lib/api";
import { MODEL_LABELS, pct, pp } from "@/lib/format";
import type { AuditReport, AuditVerdict, DiagnosticFinding, SplitResult } from "@/lib/types";

const VERDICT_TONE: Record<AuditVerdict["label"], { box: string; text: string; icon: string }> = {
  consistent: { box: "border-good bg-good-soft", text: "text-good", icon: "✓" },
  mixed: { box: "border-warn bg-warn-soft", text: "text-warn", icon: "≈" },
  not_reproduced: { box: "border-bad bg-bad-soft", text: "text-bad", icon: "✕" },
  inconclusive: { box: "border-line bg-surface", text: "text-foreground", icon: "?" },
};

const SEVERITY_TONE: Record<DiagnosticFinding["severity"], string> = {
  info: "bg-surface text-muted",
  warning: "bg-warn-soft text-warn",
  critical: "bg-bad-soft text-bad",
};

function Measured() {
  return (
    <span className="rounded bg-accent-soft px-1.5 py-0.5 text-xs font-normal text-accent">measured by LabMirror</span>
  );
}

function score(run: SplitResult, role: "candidate" | "baseline" | "dummy") {
  return run.scores.find((s) => s.model === role)!;
}

function evidenceText(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "number" && value > 0 && value < 1) return pct(value, 1);
  return String(value);
}

export function Results({ report }: { report: AuditReport }) {
  const { claim, default_split: def, seed_runs: seeds, seed_summary: summary, noise, diagnostics, verdict } = report;
  const candidate = MODEL_LABELS[claim.candidate];
  const baseline = MODEL_LABELS[claim.baseline];
  const tone = verdict ? VERDICT_TONE[verdict.label] : VERDICT_TONE.inconclusive;
  const reported =
    claim.reported_candidate_accuracy != null || claim.reported_baseline_accuracy != null || claim.source_note;

  return (
    <div className="flex flex-col gap-6">
      {/* Above the fold: verdict, claim, default split, N/5 */}
      {verdict && (
        <section className={`rounded-lg border-l-4 p-5 ${tone.box}`}>
          <p className="text-xs uppercase tracking-wide text-muted">Audit verdict · under tested conditions</p>
          <h2 className={`mt-1 text-2xl font-semibold sm:text-3xl ${tone.text}`}>
            <span aria-hidden="true">{tone.icon} </span>
            {verdict.headline}
          </h2>
          <p className="mt-2 text-sm">{verdict.reasons[0]}</p>
          <blockquote className="mt-3 border-l-2 border-line pl-3 text-sm text-muted">{report.claim_sentence}</blockquote>
        </section>
      )}

      {def && summary && (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-line p-5 md:col-span-2">
            <h3 className="flex flex-wrap items-center gap-2 font-medium">
              Default split (seed {def.seed}) <Measured />
            </h3>
            <dl className="mt-3 grid grid-cols-3 gap-4">
              <div>
                <dt className="text-xs text-muted">{candidate}</dt>
                <dd className="font-mono text-2xl">{pct(score(def, "candidate").accuracy)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">{baseline}</dt>
                <dd className="font-mono text-2xl">{pct(score(def, "baseline").accuracy)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Lift (claimed ≥ {pp(claim.threshold_pp)})</dt>
                <dd className="font-mono text-2xl">{pp(def.lift_pp)}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-muted">
              Accuracy on {def.n_test} held-out rows after training on {def.n_train}. Always predicting the larger
              class scores {pct(score(def, "dummy").accuracy)}.
            </p>
            {reported && (
              <p className="mt-3 rounded-md bg-surface px-3 py-2 text-xs">
                <span className="rounded bg-warn-soft px-1.5 py-0.5 text-warn">reported context, not verified by LabMirror</span>{" "}
                {claim.reported_candidate_accuracy != null && `Reported ${candidate}: ${pct(claim.reported_candidate_accuracy)}. `}
                {claim.reported_baseline_accuracy != null && `Reported ${baseline}: ${pct(claim.reported_baseline_accuracy)}. `}
                {claim.source_note}
              </p>
            )}
          </div>
          <div className="rounded-lg border border-line p-5">
            <h3 className="font-medium">Across five other splits</h3>
            <p className="mt-3 font-mono text-4xl">
              {summary.n_meets_threshold}
              <span className="text-xl text-muted"> / {summary.n_seeds}</span>
            </p>
            <p className="mt-1 text-sm">splits met the claimed {pp(claim.threshold_pp)}.</p>
            <p className="mt-3 text-xs text-muted">
              {candidate} was ahead at all on {summary.n_candidate_wins} of {summary.n_seeds}. Lift ranged from{" "}
              {pp(summary.min_lift_pp)} to {pp(summary.max_lift_pp)}. This count describes these splits; it is not a
              probability.
            </p>
          </div>
        </section>
      )}

      {def && seeds && (
        <>
          <LiftChart defaultSplit={def} seedRuns={seeds} thresholdPp={claim.threshold_pp} />
          <AccuracyChart defaultSplit={def} seedRuns={seeds} candidateLabel={candidate} baselineLabel={baseline} />
          <details className="rounded-lg border border-line p-4 text-sm">
            <summary className="cursor-pointer font-medium">Table of every split</summary>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-left font-mono text-xs">
                <thead className="text-muted">
                  <tr>
                    {["Split", `${candidate} acc.`, `${baseline} acc.`, "Lift", "Meets claim", "Bal. acc. (cand.)", "F1 (cand.)", "Test rows"].map((h) => (
                      <th key={h} className="whitespace-nowrap px-2 py-1 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[def, ...seeds].map((run, i) => (
                    <tr key={run.seed} className="border-t border-line">
                      <td className="whitespace-nowrap px-2 py-1">{i === 0 ? `Default (${run.seed})` : `Seed ${run.seed}`}</td>
                      <td className="px-2 py-1">{pct(score(run, "candidate").accuracy, 2)}</td>
                      <td className="px-2 py-1">{pct(score(run, "baseline").accuracy, 2)}</td>
                      <td className="px-2 py-1">{pp(run.lift_pp, 2)}</td>
                      <td className="px-2 py-1">{run.meets_threshold ? "yes" : "no"}</td>
                      <td className="px-2 py-1">{pct(score(run, "candidate").balanced_accuracy, 2)}</td>
                      <td className="px-2 py-1">{score(run, "candidate").f1.toFixed(3)}</td>
                      <td className="px-2 py-1">{run.n_test}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-muted">F1 treats “{report.dataset.positive_class}” (the smaller class) as positive.</p>
          </details>
        </>
      )}

      {noise ? (
        <NoiseChart noise={noise} candidateLabel={candidate} baselineLabel={baseline} />
      ) : (
        <p className="rounded-lg border border-line p-4 text-sm text-muted">
          The noise test did not produce a result for this audit. See the audit plan above for the reason.
        </p>
      )}

      <section className="rounded-lg border border-line p-5">
        <h3 className="font-medium">Validity warnings</h3>
        {diagnostics == null && <p className="mt-2 text-sm text-bad">Diagnostics failed to run; no findings are reported.</p>}
        {diagnostics?.length === 0 && <p className="mt-2 text-sm">{report.no_issue_statement}</p>}
        <ul className="mt-2 flex flex-col gap-3">
          {diagnostics?.map((d, i) => (
            <li key={i} className="text-sm">
              <span className={`mr-2 rounded px-1.5 py-0.5 text-xs ${SEVERITY_TONE[d.severity]}`}>{d.severity}</span>
              {d.description}
              <p className="mt-1 break-words font-mono text-xs text-muted">
                {Object.entries(d.evidence).map(([k, v]) => `${k}: ${evidenceText(v)}`).join(" · ")}
              </p>
            </li>
          ))}
        </ul>
        {diagnostics && diagnostics.length > 0 && <p className="mt-3 text-xs text-muted">{diagnostics[0].caveat}</p>}
      </section>

      {verdict && (
        <section className="rounded-lg border border-line p-5">
          <h3 className="font-medium">Why this verdict</h3>
          {report.narrative && (
            <p className="mt-2 text-sm">
              {report.narrative.text}{" "}
              <span className="text-xs text-muted">(Template summary of the measurements above; no AI involved.)</span>
            </p>
          )}
          <ul className="mt-2 list-disc pl-5 text-sm">
            {verdict.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <p className="mt-3 text-xs uppercase tracking-wide text-muted">The fixed rule</p>
          <pre className="mt-1 whitespace-pre-wrap font-sans text-xs text-muted">{verdict.rule_text}</pre>
        </section>
      )}

      <section className="rounded-lg border border-line p-5">
        <h3 className="font-medium">Audit trace</h3>
        <ol className="mt-2 flex flex-col gap-2 text-sm">
          {report.trace.map((t, i) => (
            <li key={i}>
              <span className="font-mono text-xs text-muted">{t.step}</span> · {t.decision}
              <p className="text-xs text-muted">{t.rationale}</p>
            </li>
          ))}
        </ol>
      </section>

      <details className="rounded-lg border border-line p-5 text-sm">
        <summary className="cursor-pointer font-medium">Reproducibility details</summary>
        <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-[max-content_1fr]">
          {(
            [
              ["Dataset", `${report.dataset.filename} · ${report.dataset.n_rows} rows`],
              ["SHA-256", report.dataset.sha256],
              ["Class counts", Object.entries(report.dataset.class_counts).map(([k, v]) => `${k}: ${v}`).join(", ")],
              ["Features used", `${report.dataset.features_used.length} (${report.dataset.numeric_features.length} numeric, ${report.dataset.categorical_features.length} categorical)`],
              ["Excluded columns", report.dataset.excluded_columns.join(", ") || "none"],
              ["Split", `stratified ${Math.round((1 - report.config.test_size) * 100)}/${Math.round(report.config.test_size * 100)}; default seed ${report.config.default_seed}; repeat seeds ${report.config.seeds.join(", ")}`],
              ["Preprocessing", JSON.stringify(report.config.preprocessing)],
              ["Models", JSON.stringify(report.config.models)],
              ["Noise test", JSON.stringify(report.config.noise ?? "not run")],
              ["Versions", Object.entries(report.environment).map(([k, v]) => `${k} ${v}`).join(" · ")],
              ["Run", `${report.audit_id} · ${report.created_at} · ${report.runtime_seconds ?? "?"} s`],
            ] as [string, string][]
          ).map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-muted">{k}</dt>
              <dd className="break-all font-mono text-xs">{v}</dd>
            </div>
          ))}
        </dl>
      </details>

      <section className="text-xs text-muted">
        <h3 className="font-medium text-foreground">Limitations</h3>
        <ul className="mt-1 list-disc pl-5">
          {report.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap gap-3">
        <a href={reportJsonUrl(report.audit_id)} className="rounded-md border border-line px-4 py-2 text-sm font-medium hover:bg-surface">
          Download report (JSON)
        </a>
        <a href={reportMdUrl(report.audit_id)} className="rounded-md border border-line px-4 py-2 text-sm font-medium hover:bg-surface">
          Download report (Markdown)
        </a>
        <Link href="/" className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90">
          Run new audit
        </Link>
      </div>
    </div>
  );
}
