// API and report contract. Mirrors backend/labmirror/schemas.py and docs/IMPLEMENTATION_PLAN.md §3.2.
// Accuracies are fractions in [0, 1]. Lifts are percentage points and carry the suffix `_pp`.
// Change this file and schemas.py together, in one commit.

export type ModelKey = "random_forest" | "logistic_regression";
export type ColumnKind = "numeric" | "categorical" | "unusable";
export type ColumnFlag = "identifier_like" | "leakage_name" | "high_cardinality" | "constant" | "free_text";
export type StageId =
  | "validate"
  | "default_split"
  | "seed_sensitivity"
  | "noise_robustness"
  | "leakage_diagnostics"
  | "verdict"
  | "report";
export type StageStatus = "pending" | "running" | "done" | "failed" | "skipped";
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "timeout";

export interface Health {
  status: string;
  version: string;
  llm_enabled: boolean;
}

export interface ClaimSpec {
  target: string;
  candidate: ModelKey;
  baseline: ModelKey;
  metric: "accuracy";
  threshold_pp: number;
  reported_candidate_accuracy?: number | null;
  reported_baseline_accuracy?: number | null;
  source_note?: string | null;
}

export interface DemoDescriptor {
  id: string;
  title: string;
  description: string;
  suggested_claim: ClaimSpec;
  provenance_note: string;
}

export interface ColumnInfo {
  name: string;
  kind: ColumnKind;
  n_unique: number;
  missing_fraction: number;
  flags: ColumnFlag[];
}

export interface DatasetSummary {
  dataset_id: string;
  sha256: string;
  filename: string;
  is_demo: boolean;
  n_rows: number;
  n_columns: number;
  columns: ColumnInfo[];
  duplicate_row_count: number;
  binary_target_candidates: string[];
  preview: { columns: string[]; rows: string[][] };
}

export interface AuditRequest {
  dataset_id: string;
  claim: ClaimSpec;
  excluded_columns: string[];
}

export interface Stage {
  id: StageId;
  label: string;
  why: string;
  status: StageStatus;
  started_at?: string | null;
  finished_at?: string | null;
  message?: string | null;
}

export interface ModelScore {
  model: "candidate" | "baseline" | "dummy";
  estimator: string;
  accuracy: number;
  balanced_accuracy: number;
  f1: number;
}

export interface SplitResult {
  seed: number;
  n_train: number;
  n_test: number;
  test_class_counts: Record<string, number>;
  scores: ModelScore[];
  lift_pp: number;
  candidate_wins: boolean;
  meets_threshold: boolean;
}

export interface SeedSummary {
  n_seeds: number;
  n_candidate_wins: number;
  n_meets_threshold: number;
  median_lift_pp: number;
  min_lift_pp: number;
  max_lift_pp: number;
  candidate_accuracy_range: [number, number];
  baseline_accuracy_range: [number, number];
}

export interface NoiseResult {
  noise_scale: number;
  n_draws: number;
  rng_seed: number;
  perturbed_features: string[];
  skipped_features: string[];
  per_model: {
    model: "candidate" | "baseline";
    clean_accuracy: number;
    noisy_mean_accuracy: number;
    noisy_min: number;
    noisy_max: number;
    delta_pp: number;
  }[];
  clean_lift_pp: number;
  noisy_mean_lift_pp: number;
}

export interface DiagnosticFinding {
  check:
    | "cross_split_duplicates"
    | "conflicting_label_duplicates"
    | "identifier_like"
    | "leakage_name"
    | "class_imbalance"
    | "small_test_class";
  severity: "info" | "warning" | "critical";
  description: string;
  evidence: Record<string, unknown>;
  caveat: string;
}

export interface AuditVerdict {
  label: "consistent" | "mixed" | "not_reproduced" | "inconclusive";
  headline: string;
  rule_text: string;
  triggered_rules: string[];
  reasons: string[];
}

export interface TraceEntry {
  step: string;
  actor: "engine" | "skeptic" | "writer";
  decision: string;
  rationale: string;
  evidence_ref?: string | null;
}

export interface AuditReport {
  schema_version: string;
  audit_id: string;
  created_at: string;
  dataset: {
    sha256: string;
    filename: string;
    n_rows: number;
    features_used: string[];
    excluded_columns: string[];
    numeric_features: string[];
    categorical_features: string[];
    class_counts: Record<string, number>;
    positive_class: string;
  };
  claim: ClaimSpec;
  claim_sentence: string;
  config: {
    test_size: number;
    default_seed: number;
    seeds: number[];
    preprocessing: Record<string, unknown>;
    models: Record<string, unknown>;
    noise?: Record<string, unknown> | null;
  };
  environment: Record<string, string>;
  default_split?: SplitResult | null;
  seed_runs?: SplitResult[] | null;
  seed_summary?: SeedSummary | null;
  noise?: NoiseResult | null;
  diagnostics?: DiagnosticFinding[] | null;
  no_issue_statement?: string | null;
  verdict?: AuditVerdict | null;
  trace: TraceEntry[];
  narrative?: { source: "template" | "llm"; text: string } | null;
  limitations: string[];
  runtime_seconds?: number | null;
}

export interface AuditJob {
  audit_id: string;
  status: JobStatus;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  stages: Stage[];
  error?: { code: string; message: string } | null;
  report?: AuditReport | null;
}

export interface ApiErrorBody {
  error: { code: string; message: string; field?: string };
}
