import Link from "next/link";

import { AiPreviewPanel } from "@/components/AiPreviewPanel";
import { AccuracyChart, LiftChart, NoiseChart } from "@/components/charts";
import { reportJsonUrl, reportMdUrl } from "@/lib/api";
import { MODEL_LABELS, pct, pp } from "@/lib/format";
import type { AuditReport, AuditVerdict, DiagnosticFinding, SplitResult } from "@/lib/types";

const VERDICT_TONE: Record<AuditVerdict["label"], { box: string; text: string; icon: string }> = {
  consistent: { box: "border-good/40 bg-good-soft", text: "text-good", icon: "✓" },
  mixed: { box: "border-warn/40 bg-warn-soft", text: "text-warn", icon: "≈" },
  not_reproduced: { box: "border-bad/40 bg-bad-soft", text: "text-bad", icon: "✕" },
  inconclusive: { box: "border-line bg-surface", text: "text-foreground", icon: "?" },
};

const SEVERITY_TONE: Record<DiagnosticFinding["severity"], string> = {
  info: "tag-quiet",
  warning: "tag-warn",
  critical: "tag-bad",
};

function Measured() {
  return (
<span className="tag">measured by LabMirror</span>
  );
}

const METRIC = "mt-0.5 text-3xl font-semibold tracking-tight";

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
        <section className={`rounded-[18px] border p-6 sm:p-9 ${tone.box}`}>
          <p className="text-sm text-muted">Audit verdict, under the tested conditions</p>
          <h1 className={`mt-3 flex items-start gap-3 text-3xl font-bold leading-[1.1] tracking-tight sm:gap-4 sm:text-5xl ${tone.text}`}>
            <span
              className="mt-[0.08em] flex h-[1em] w-[1em] shrink-0 items-center justify-center rounded-full border-2 border-current"
              aria-hidden="true"
            >
              <span className="text-[0.55em] leading-none">{tone.icon}</span>
            </span>
            {verdict.headline}
          </h1>
          <p className="mt-4 max-w-2xl text-base sm:text-lg">{verdict.reasons[0]}</p>
          <figure className="mt-6 border-t border-foreground/15 pt-4">
            <figcaption className="text-xs text-muted">The claim that was tested</figcaption>
            <blockquote className="mt-1 max-w-3xl font-serif text-lg leading-snug sm:text-xl">{report.claim_sentence}</blockquote>
          </figure>
        </section>
      )}

      {def && summary && (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="card p-5 sm:p-6 md:col-span-2">
            <h2 className="flex flex-wrap items-center gap-2 font-semibold">
              Default split (seed {def.seed}) <Measured />
            </h2>
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-4 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted">{candidate}</dt>
                <dd className={METRIC}>{pct(score(def, "candidate").accuracy)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted">{baseline}</dt>
                <dd className={METRIC}>{pct(score(def, "baseline").accuracy)}</dd>
              </div>
              <div className="col-span-2 border-t border-line pt-4 sm:col-span-1 sm:border-l sm:border-t-0 sm:pl-4 sm:pt-0">
                <dt className="text-xs text-muted">Lift (claimed ≥ {pp(claim.threshold_pp)})</dt>
                <dd className={METRIC}>{pp(def.lift_pp)}</dd>
              </div>
            </dl>
            <p className="mt-4 text-xs text-muted">
              Accuracy on {def.n_test} held-out rows after training on {def.n_train}. Always predicting the larger
              class scores {pct(score(def, "dummy").accuracy)}.
            </p>
            {reported && (
              <p className="mt-4 rounded-[10px] bg-surface px-3 py-2.5 text-xs leading-relaxed">
                <span className="tag tag-warn whitespace-normal">reported context, not verified by LabMirror</span>{" "}
                {claim.reported_candidate_accuracy != null && `Reported ${candidate}: ${pct(claim.reported_candidate_accuracy)}. `}
                {claim.reported_baseline_accuracy != null && `Reported ${baseline}: ${pct(claim.reported_baseline_accuracy)}. `}
                {claim.source_note}
              </p>
            )}
          </div>
          <div className="card p-5 sm:p-6">
            <h2 className="font-semibold">Across five other splits</h2>
            <p className="mt-4 text-5xl font-semibold tracking-tight">
              {summary.n_meets_threshold}
              <span className="text-2xl font-normal text-muted"> / {summary.n_seeds}</span>
            </p>
            {/* One pip per split, same encoding as the lift chart: filled meets the claim, outlined does not. */}
            {seeds && (
              <ul className="mt-3 flex gap-1.5" aria-hidden="true">
                {seeds.map((run) => (
                  <li
                    key={run.seed}
                    title={`Seed ${run.seed}: ${pp(run.lift_pp)}`}
                    className={`h-2.5 flex-1 rounded-full ${run.meets_threshold ? "bg-series-1" : "border-[1.5px] border-muted"}`}
                  />
                ))}
              </ul>
            )}
            <p className="mt-3 text-sm">splits met the claimed {pp(claim.threshold_pp)}.</p>
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
          <details className="card p-4 text-sm sm:px-6">
            <summary className="cursor-pointer font-semibold">Table of every split</summary>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-left text-xs tabular-nums">
                <thead className="text-muted">
                  <tr>
                    {["Split", `${candidate} acc.`, `${baseline} acc.`, "Lift", "Meets claim", "Bal. acc. (cand.)", "F1 (cand.)", "Test rows"].map((h) => (
                      <th key={h} className="whitespace-nowrap px-2 py-1.5 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[def, ...seeds].map((run, i) => (
                    <tr key={run.seed} className="border-t border-line">
                      <td className="whitespace-nowrap px-2 py-1.5 font-medium">{i === 0 ? `Default (${run.seed})` : `Seed ${run.seed}`}</td>
                      <td className="px-2 py-1.5">{pct(score(run, "candidate").accuracy, 2)}</td>
                      <td className="px-2 py-1.5">{pct(score(run, "baseline").accuracy, 2)}</td>
                      <td className="px-2 py-1.5">{pp(run.lift_pp, 2)}</td>
                      <td className="px-2 py-1.5">{run.meets_threshold ? "yes" : "no"}</td>
                      <td className="px-2 py-1.5">{pct(score(run, "candidate").balanced_accuracy, 2)}</td>
                      <td className="px-2 py-1.5">{score(run, "candidate").f1.toFixed(3)}</td>
                      <td className="px-2 py-1.5">{run.n_test}</td>
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
        <p className="card p-4 text-sm text-muted">
          The noise test did not produce a result for this audit. See the audit plan above for the reason.
        </p>
      )}

      <section className="card p-5 sm:p-6">
        <h2 className="font-semibold">Validity warnings</h2>
        {diagnostics == null && <p className="mt-2 text-sm text-bad">Diagnostics failed to run; no findings are reported.</p>}
        {diagnostics?.length === 0 && <p className="mt-2 text-sm">{report.no_issue_statement}</p>}
        <ul className="mt-3 flex flex-col gap-4">
          {diagnostics?.map((d, i) => (
            <li key={i} className="max-w-3xl text-sm">
              <span className={`tag mr-2 ${SEVERITY_TONE[d.severity]}`}>{d.severity}</span>
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
        <section className="card p-5 sm:p-6">
          <h2 className="font-semibold">Why this verdict</h2>
          {report.narrative && (
            <p className="mt-2 max-w-3xl text-sm">
              {report.narrative.text}{" "}
              <span className="text-xs text-muted">(Template summary of the measurements above; no AI involved.)</span>
            </p>
          )}
          <ul className="mt-3 max-w-3xl list-disc pl-5 text-sm">
            {verdict.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          <h3 className="mt-5 border-t border-line pt-4 text-sm font-semibold">The fixed rule</h3>
          <pre className="mt-1 max-w-3xl whitespace-pre-wrap font-sans text-xs leading-relaxed text-muted">{verdict.rule_text}</pre>
        </section>
      )}

      <AiPreviewPanel report={report} />

      <section className="card p-5 sm:p-6">
        <h2 className="font-semibold">Audit trace</h2>
        <ol className="mt-3 flex flex-col text-sm">
          {report.trace.map((t, i) => (
            <li key={i} className="grid gap-x-4 gap-y-0.5 border-t border-line py-2.5 first:border-t-0 sm:grid-cols-[11rem_1fr]">
              <span className="break-all font-mono text-xs text-muted sm:pt-0.5">{t.step}</span>
              <div>
                {t.decision}
                <p className="mt-0.5 text-xs text-muted">{t.rationale}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <details className="card p-5 text-sm sm:px-6">
        <summary className="cursor-pointer font-semibold">Reproducibility details</summary>
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
        <h2 className="text-sm font-semibold text-foreground">Limitations</h2>
        <ul className="mt-2 flex max-w-3xl list-disc flex-col gap-1 pl-5">
          {report.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap gap-3">
        <a href={reportJsonUrl(report.audit_id)} className="btn">
          Download report (JSON)
        </a>
        <a href={reportMdUrl(report.audit_id)} className="btn">
          Download report (Markdown)
        </a>
        <Link href="/" className="btn btn-primary">
          Run new audit
        </Link>
      </div>
    </div>
  );
}
