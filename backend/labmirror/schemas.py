"""API and report contract. Mirrors docs/IMPLEMENTATION_PLAN.md §3.2 and frontend/src/lib/types.ts.

Accuracies are fractions in [0, 1]. Lifts are percentage points and carry the suffix `_pp`.
Change this file and types.ts together, in one commit.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ModelKey = Literal["random_forest", "logistic_regression"]
ColumnKind = Literal["numeric", "categorical", "unusable"]
ColumnFlag = Literal["identifier_like", "leakage_name", "high_cardinality", "constant", "free_text"]
StageId = Literal[
    "validate",
    "default_split",
    "seed_sensitivity",
    "noise_robustness",
    "leakage_diagnostics",
    "verdict",
    "report",
]
StageStatus = Literal["pending", "running", "done", "failed", "skipped"]
JobStatus = Literal["queued", "running", "succeeded", "failed", "timeout"]


class ClaimSpec(BaseModel):
    target: str
    candidate: ModelKey
    baseline: ModelKey
    metric: Literal["accuracy"] = "accuracy"
    threshold_pp: float = Field(gt=0, le=100)
    reported_candidate_accuracy: Optional[float] = Field(default=None, ge=0, le=1)
    reported_baseline_accuracy: Optional[float] = Field(default=None, ge=0, le=1)
    source_note: Optional[str] = Field(default=None, max_length=500)


class DemoDescriptor(BaseModel):
    id: str
    title: str
    description: str
    suggested_claim: ClaimSpec
    provenance_note: str


class ColumnInfo(BaseModel):
    name: str
    kind: ColumnKind
    n_unique: int
    missing_fraction: float
    flags: list[ColumnFlag] = []


class Preview(BaseModel):
    columns: list[str]
    rows: list[list[str]]


class DatasetSummary(BaseModel):
    dataset_id: str
    sha256: str
    filename: str
    is_demo: bool = False
    n_rows: int
    n_columns: int
    columns: list[ColumnInfo]
    duplicate_row_count: int
    binary_target_candidates: list[str]
    preview: Preview


class AuditRequest(BaseModel):
    dataset_id: str
    claim: ClaimSpec
    excluded_columns: list[str] = []


class Stage(BaseModel):
    id: StageId
    label: str
    why: str
    status: StageStatus = "pending"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    message: Optional[str] = None


class ModelScore(BaseModel):
    model: Literal["candidate", "baseline", "dummy"]
    estimator: str
    accuracy: float
    balanced_accuracy: float
    f1: float


class SplitResult(BaseModel):
    seed: int
    n_train: int
    n_test: int
    test_class_counts: dict[str, int]
    scores: list[ModelScore]
    lift_pp: float
    candidate_wins: bool
    meets_threshold: bool


class SeedSummary(BaseModel):
    n_seeds: int
    n_candidate_wins: int
    n_meets_threshold: int
    median_lift_pp: float
    min_lift_pp: float
    max_lift_pp: float
    candidate_accuracy_range: tuple[float, float]
    baseline_accuracy_range: tuple[float, float]


class NoiseModelResult(BaseModel):
    model: Literal["candidate", "baseline"]
    clean_accuracy: float
    noisy_mean_accuracy: float
    noisy_min: float
    noisy_max: float
    delta_pp: float


class NoiseResult(BaseModel):
    noise_scale: float
    n_draws: int
    rng_seed: int
    perturbed_features: list[str]
    skipped_features: list[str]
    per_model: list[NoiseModelResult]
    clean_lift_pp: float
    noisy_mean_lift_pp: float


class DiagnosticFinding(BaseModel):
    check: Literal[
        "cross_split_duplicates",
        "conflicting_label_duplicates",
        "identifier_like",
        "leakage_name",
        "class_imbalance",
        "small_test_class",
    ]
    severity: Literal["info", "warning", "critical"]
    description: str
    evidence: dict[str, Any]
    caveat: str


class AuditVerdict(BaseModel):
    label: Literal["consistent", "mixed", "not_reproduced", "inconclusive"]
    headline: str
    rule_text: str
    triggered_rules: list[str]
    reasons: list[str]


class TraceEntry(BaseModel):
    step: str
    actor: Literal["engine", "skeptic", "writer"] = "engine"
    decision: str
    rationale: str
    evidence_ref: Optional[str] = None


class DatasetInfo(BaseModel):
    sha256: str
    filename: str
    n_rows: int
    features_used: list[str]
    excluded_columns: list[str]
    numeric_features: list[str]
    categorical_features: list[str]
    class_counts: dict[str, int]
    positive_class: str


class AuditConfig(BaseModel):
    test_size: float
    default_seed: int
    seeds: list[int]
    preprocessing: dict[str, Any]
    models: dict[str, Any]
    noise: Optional[dict[str, Any]] = None


class Narrative(BaseModel):
    source: Literal["template", "llm"]
    text: str


class AuditReport(BaseModel):
    schema_version: str
    audit_id: str
    created_at: str
    dataset: DatasetInfo
    claim: ClaimSpec
    claim_sentence: str
    config: AuditConfig
    environment: dict[str, str]
    default_split: Optional[SplitResult] = None
    seed_runs: Optional[list[SplitResult]] = None
    seed_summary: Optional[SeedSummary] = None
    noise: Optional[NoiseResult] = None
    diagnostics: Optional[list[DiagnosticFinding]] = None
    no_issue_statement: Optional[str] = None
    verdict: Optional[AuditVerdict] = None
    trace: list[TraceEntry] = []
    narrative: Optional[Narrative] = None
    limitations: list[str] = []
    runtime_seconds: Optional[float] = None


class JobError(BaseModel):
    code: str
    message: str


class AuditJob(BaseModel):
    audit_id: str
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    stages: list[Stage]
    error: Optional[JobError] = None
    report: Optional[AuditReport] = None
