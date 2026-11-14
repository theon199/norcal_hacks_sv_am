// Display helpers. The frontend never computes a lift; it only formats values the backend measured.

import type { ModelKey } from "./types";

/** Fraction in [0, 1] → "97.4%". */
export function pct(fraction: number, digits = 1): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

/** Percentage points → "+5.0 pp" (always signed). */
export function pp(points: number, digits = 1): string {
  const rounded = Number(points.toFixed(digits));
  const sign = rounded > 0 ? "+" : rounded < 0 ? "−" : "";
  return `${sign}${Math.abs(rounded).toFixed(digits)} pp`;
}

export const MODEL_LABELS: Record<ModelKey, string> = {
  random_forest: "Random Forest",
  logistic_regression: "Logistic Regression",
};

export function otherModel(model: ModelKey): ModelKey {
  return model === "random_forest" ? "logistic_regression" : "random_forest";
}

export function claimSentence(candidate: ModelKey, thresholdPp: number): string {
  const t = Number.isFinite(thresholdPp) ? thresholdPp.toFixed(1) : "?";
  return `Audit whether ${MODEL_LABELS[candidate]} exceeds ${MODEL_LABELS[otherModel(candidate)]} by at least ${t} percentage points of test-set accuracy on this dataset.`;
}
