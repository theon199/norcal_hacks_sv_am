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
  sha256: "e9e379043ccc5bd9c03561defabef08a481897560f19fd82deea0f37fccfe966",
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
        "400 rows leaves only 80 in the test set, so a single split can swing the lift by several points. Check whether the margin survives other splits first.",
    },
    {
      test_id: "noise_robustness",
      rationale:
        "All eight features are continuous sensor readings. Real sensors drift, so check whether the advantage depends on exact values.",
    },
    {
      test_id: "leakage_diagnostics",
      rationale:
        "Repeated readings from the same machine could appear on both sides of the split and inflate either model. Look for duplicates and ID-like columns.",
    },
  ],
  narrative:
    "The claim is that Random Forest beats Logistic Regression by at least 5 pp of accuracy at predicting machine faults. " +
    "On the default split it does: 91.3% against 83.8%, a lift of +7.50 pp. But that split was one of the more favorable ones. " +
    "Refitted on other splits, Random Forest stayed ahead on 5 of 5, yet the lift reached the claimed margin on only 2 of 5, " +
    "ranging from +1.25 pp to +5.00 pp with a median of +3.75 pp. Noise on the sensor readings barely moved the default-split lift " +
    "(+7.06 pp against +7.50 pp clean), and the leakage checks found nothing. So the direction holds, but the size of the advantage " +
    "depends on which rows land in the test set. Under the fixed rule, the verdict is Mixed.",
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
