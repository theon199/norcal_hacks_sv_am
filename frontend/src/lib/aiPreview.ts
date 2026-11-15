// AI preview for the demo: Skeptical Auditor and Evidence Writer output, written ahead of time.
//
// The live LLM path (plan §7, Phase 4) is not built. For the sensor-fault demo only, this file holds
// the output those two agents would produce, written ahead of time with Claude and labelled that way
// in the UI. It never changes a score or the verdict. Every "finding" shown next to a skeptic
// decision is read from the live report, and the narrative is shown only if every number in it
// matches a value in that report (the A4.2 verifier, run in the browser).

import type { AuditReport } from "./types";

export interface SkepticStep {
  /** Registry stage id (backend/labmirror/engine/registry.py). */
  test_id: "seed_sensitivity" | "noise_robustness" | "leakage_diagnostics";
  rationale: string;
}

export interface AiPreview {
  /** Applies only to this exact file and claim. */
  sha256: string;
  claim: { target: string; candidate: string; baseline: string; metric: string; threshold_pp: number };
  skeptic: SkepticStep[];
  narrative: string;
}

const SENSOR_FAULT: AiPreview = {
  sha256: "12db1061fe7ce69f47e4676c8d8d8953f3c8b4bf9c59ce301dbb9098bba9f6e3",
  claim: {
    target: "machine_fault",
    candidate: "random_forest",
    baseline: "logistic_regression",
    metric: "accuracy",
    threshold_pp: 5,
  },
  skeptic: [
    {
      test_id: "seed_sensitivity",
      rationale:
        "Only 80 machines are held back for testing, so one lucky or unlucky draw can make either model look good. Reshuffle which machines are tested and repeat, first.",
    },
    {
      test_id: "noise_robustness",
      rationale:
        "Real gauges drift and read a little off. Check whether the advantage survives small errors in the temperature, vibration and other readings.",
    },
    {
      test_id: "leakage_diagnostics",
      rationale:
        "If the same machine shows up in both the practice data and the test, the test is too easy. Look for copied rows and ID-like columns.",
    },
  ],
  narrative:
    "The claim: Random Forest predicts machine breakdowns at least 5 points more accurately than Logistic Regression. " +
    "On the usual single test it does, scoring 91.3% against 83.8%, a gap of 7.5 points. " +
    "But that test uses only 80 machines, so luck matters. When LabMirror reshuffled which machines were tested and ran it five more times, " +
    "Random Forest reached the promised 5-point gap on only 3 of 5 tries. On those three it landed exactly on the line, " +
    "and on one try the two models tied. Adding small errors to the readings, like a slightly miscalibrated gauge, barely changed " +
    "the result (a gap of 6.9 points instead of 7.5), and no signs of data leakage were found. " +
    "Bottom line: Random Forest is usually a little better here, but \"at least 5 points better\" depends on which machines " +
    "happen to be in the test. The verdict is Mixed.",
};

const PREVIEWS = [SENSOR_FAULT];

export function findAiPreview(report: AuditReport): AiPreview | null {
  const c = report.claim;
  return (
    PREVIEWS.find(
      (p) =>
        p.sha256 === report.dataset.sha256 &&
        p.claim.target === c.target &&
        p.claim.candidate === c.candidate &&
        p.claim.baseline === c.baseline &&
        p.claim.metric === (c.metric ?? "accuracy") &&
        p.claim.threshold_pp === c.threshold_pp,
    ) ?? null
  );
}

function collectNumbers(value: unknown, out: number[]): void {
  if (typeof value === "number" && Number.isFinite(value)) out.push(value);
  else if (Array.isArray(value)) value.forEach((v) => collectNumbers(v, out));
  else if (value && typeof value === "object") Object.values(value).forEach((v) => collectNumbers(v, out));
}

/**
 * Returns the numbers in `text` that cannot be found in the report. A number matches if some report value,
 * as is or ×100 (fractions shown as percentages), rounds to it at the precision it is written with.
 */
export function unverifiedNumbers(text: string, report: AuditReport): string[] {
  const values: number[] = [];
  collectNumbers(report, values);
  const tokens = text.match(/\d+(?:\.\d+)?/g) ?? [];
  return tokens.filter((tok) => {
    const n = Number(tok);
    const digits = tok.includes(".") ? tok.split(".")[1].length : 0;
    // Integers (counts, thresholds) must match exactly; decimals within half a unit of their last digit.
    const tol = digits === 0 ? 1e-9 : 0.5 * 10 ** -digits + 1e-9;
    return !values.some((v) => Math.abs(v - n) <= tol || Math.abs(v * 100 - n) <= tol);
  });
}
