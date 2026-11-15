"""Audit orchestrator. Runs the allowlisted stages in order and reports progress through a callback."""

import platform
import time
import uuid
from datetime import datetime, timezone
from importlib import metadata
from typing import Callable, Optional

import pandas as pd

from labmirror import __version__, config
from labmirror.engine import EngineError
from labmirror.engine.pipelines import MODEL_LABELS, MODEL_SETTINGS, PREPROCESSING_SETTINGS
from labmirror.engine import llm
from labmirror.engine import verdict as verdict_rules
from labmirror.engine.diagnostics import run_diagnostics
from labmirror.engine.registry import initial_stages
from labmirror.engine.report_md import build_narrative
from labmirror.engine.tests_default import run_default_split
from labmirror.engine.tests_noise import noise_config, run_noise
from labmirror.engine.tests_seeds import run_seed_sensitivity
from labmirror.engine.validation import prepare
from labmirror.schemas import (
    AuditConfig,
    AuditReport,
    AuditRequest,
    ClaimSpec,
    DatasetInfo,
    Narrative,
    Stage,
    TraceEntry,
)

OnUpdate = Callable[[list[Stage], Optional[AuditReport]], None]

LIMITATIONS = [
    config.DISCLOSURE,
    "Only binary classification on tabular CSV data with the two listed scikit-learn models is supported.",
    "Hyperparameters are fixed and untuned; a tuned model could behave differently.",
    "The model random_state is held fixed across splits, so this measures split-seed sensitivity, "
    "not sensitivity to model initialization.",
    "Leakage checks are heuristics and cannot establish the absence of leakage.",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": metadata.version("numpy"),
        "pandas": metadata.version("pandas"),
        "scikit_learn": metadata.version("scikit-learn"),
        "labmirror": __version__,
    }


def claim_sentence(claim: ClaimSpec) -> str:
    return (
        f"Audit whether {MODEL_LABELS[claim.candidate]} exceeds {MODEL_LABELS[claim.baseline]} by at least "
        f"{claim.threshold_pp:.1f} percentage points of test-set accuracy on this dataset."
    )


class _Tracker:
    def __init__(self, on_update: Optional[OnUpdate]):
        self.stages = initial_stages()
        self.on_update = on_update
        self.report: Optional[AuditReport] = None

    def _get(self, stage_id: str) -> Stage:
        return next(s for s in self.stages if s.id == stage_id)

    def emit(self) -> None:
        if self.on_update:
            self.on_update(self.stages, self.report)

    def start(self, stage_id: str) -> None:
        stage = self._get(stage_id)
        stage.status, stage.started_at = "running", now_iso()
        self.emit()

    def finish(self, stage_id: str, message: Optional[str] = None) -> None:
        stage = self._get(stage_id)
        stage.status, stage.finished_at, stage.message = "done", now_iso(), message
        self.emit()

    def skip(self, stage_id: str, message: str) -> None:
        stage = self._get(stage_id)
        stage.status, stage.message = "skipped", message
        self.emit()

    def fail(self, stage_id: str, message: str) -> None:
        stage = self._get(stage_id)
        stage.status, stage.finished_at, stage.message = "failed", now_iso(), message
        self.emit()

    def running(self) -> Optional[str]:
        return next((s.id for s in self.stages if s.status == "running"), None)


def run_audit(
    df: pd.DataFrame,
    *,
    sha256: str,
    filename: str,
    request: AuditRequest,
    audit_id: Optional[str] = None,
    on_update: Optional[OnUpdate] = None,
) -> tuple[AuditReport, list[Stage]]:
    """Run every implemented stage. Raises EngineError on a validation failure (the failing stage is marked)."""
    started = time.perf_counter()
    tracker = _Tracker(on_update)
    claim = request.claim
    try:
        tracker.start("validate")
        data = prepare(df, claim, request.excluded_columns)
        report = AuditReport(
            schema_version=config.SCHEMA_VERSION,
            audit_id=audit_id or uuid.uuid4().hex[:12],
            created_at=now_iso(),
            dataset=DatasetInfo(
                sha256=sha256,
                filename=filename,
                n_rows=int(len(df)),
                features_used=data.numeric_features + data.categorical_features,
                excluded_columns=data.excluded_columns,
                numeric_features=data.numeric_features,
                categorical_features=data.categorical_features,
                class_counts=data.class_counts,
                positive_class=data.positive_class,
            ),
            claim=claim,
            claim_sentence=claim_sentence(claim),
            config=AuditConfig(
                test_size=config.TEST_SIZE,
                default_seed=config.DEFAULT_SEED,
                seeds=config.SENSITIVITY_SEEDS,
                preprocessing=PREPROCESSING_SETTINGS,
                models={
                    "candidate": {"key": claim.candidate, **MODEL_SETTINGS[claim.candidate]},
                    "baseline": {"key": claim.baseline, **MODEL_SETTINGS[claim.baseline]},
                    "dummy": {"key": "dummy", **MODEL_SETTINGS["dummy"]},
                },
            ),
            environment=environment(),
            limitations=LIMITATIONS,
        )
        tracker.report = report
        report.trace.append(
            TraceEntry(
                step="validate",
                decision=f"Accepted {len(report.dataset.features_used)} features and a binary target",
                rationale=f"Positive class for F1 is the minority class '{data.positive_class}'.",
                evidence_ref="dataset",
            )
        )
        tracker.finish("validate")

        tracker.start("default_split")
        default = run_default_split(data, claim)
        report.default_split = default.result
        report.trace.append(
            TraceEntry(
                step="default_split",
                decision=f"Measured a lift of {default.result.lift_pp:+.2f} pp on the default split",
                rationale="One stratified 80/20 split with seed 42; all models share the same rows.",
                evidence_ref="default_split",
            )
        )
        tracker.finish("default_split")

        # A4.1: the Skeptical Auditor may reorder the stress tests. All of them always run; scores never change.
        order: list[str] = list(llm.STRESS_TESTS)
        if config.LLM_ENABLED:
            picks = llm.plan_tests(report)
            if picks is None:
                report.trace.append(
                    TraceEntry(
                        step="skeptic",
                        decision="Skeptical Auditor unavailable; ran the stress tests in the fixed order",
                        rationale="The AI call failed or returned no usable test IDs. Nothing else changes.",
                    )
                )
            else:
                order = [test_id for test_id, _ in picks]
                for rank, (test_id, why) in enumerate(picks, start=1):
                    report.trace.append(
                        TraceEntry(
                            step=test_id,
                            actor="skeptic",
                            decision=f"AI-suggested (Skeptical Auditor): run {test_id} as test {rank} of {len(picks)}",
                            rationale=why or "Not picked by the AI; required test, run anyway.",
                            evidence_ref="default_split",
                        )
                    )

        # Stress and diagnostic stages are non-fatal: a failure is recorded, never replaced by a made-up result.
        # Seed sensitivity is the exception: the verdict needs it, so its errors propagate as before.
        failed: set[str] = set()

        def stage_seeds() -> None:
            tracker.start("seed_sensitivity")
            report.seed_runs, report.seed_summary = run_seed_sensitivity(data, claim)
            report.trace.append(
                TraceEntry(
                    step="seed_sensitivity",
                    decision=(
                        f"The claimed threshold was met on {report.seed_summary.n_meets_threshold} of "
                        f"{report.seed_summary.n_seeds} evaluated splits"
                    ),
                    rationale="Same pipelines and hyperparameters refitted on five other stratified splits.",
                    evidence_ref="seed_runs",
                )
            )
            tracker.finish("seed_sensitivity")

        def stage_noise() -> None:
            tracker.start("noise_robustness")
            try:
                report.config.noise = noise_config()
                report.noise = run_noise(data, default)
                if report.noise is None:
                    tracker.skip("noise_robustness", "Skipped: there are no numeric features with variation to perturb.")
                    report.trace.append(
                        TraceEntry(
                            step="noise_robustness",
                            decision="Skipped the noise test",
                            rationale="The noise model only applies to numeric features; none were usable.",
                        )
                    )
                else:
                    report.trace.append(
                        TraceEntry(
                            step="noise_robustness",
                            decision=(
                                f"Under noise the mean lift was {report.noise.noisy_mean_lift_pp:+.2f} pp "
                                f"(clean {report.noise.clean_lift_pp:+.2f} pp)"
                            ),
                            rationale=(
                                f"{report.noise.n_draws} seeded draws of Gaussian noise at "
                                f"{report.noise.noise_scale:.0%} of each feature's training standard deviation."
                            ),
                            evidence_ref="noise",
                        )
                    )
                    tracker.finish("noise_robustness")
            except Exception as exc:
                failed.add("noise_robustness")
                report.noise = None
                tracker.fail("noise_robustness", f"The noise test failed ({type(exc).__name__}); no result is reported.")

        def stage_diagnostics() -> None:
            tracker.start("leakage_diagnostics")
            try:
                report.diagnostics = run_diagnostics(data, default, claim.target)
                if not report.diagnostics:
                    report.no_issue_statement = config.NO_ISSUE_STATEMENT
                report.trace.append(
                    TraceEntry(
                        step="leakage_diagnostics",
                        decision=(
                            f"Raised {len(report.diagnostics)} finding(s)"
                            if report.diagnostics
                            else "Found no issues in the checks performed"
                        ),
                        rationale="Duplicate rows across the split, identifier-like columns, suspicious names, class balance.",
                        evidence_ref="diagnostics",
                    )
                )
                tracker.finish("leakage_diagnostics")
            except Exception as exc:
                failed.add("leakage_diagnostics")
                report.diagnostics = None
                tracker.fail("leakage_diagnostics", f"Diagnostics failed ({type(exc).__name__}); no findings are reported.")

        stages = {
            "seed_sensitivity": stage_seeds,
            "noise_robustness": stage_noise,
            "leakage_diagnostics": stage_diagnostics,
        }
        for test_id in order:
            stages[test_id]()

        tracker.start("verdict")
        report.verdict = verdict_rules.decide(
            threshold_pp=claim.threshold_pp,
            default_split=report.default_split,
            seed_summary=report.seed_summary,
            noise=report.noise,
            diagnostics=report.diagnostics,
            failed_stages=failed,
        )
        report.trace.append(
            TraceEntry(
                step="verdict",
                decision=report.verdict.headline,
                rationale=f"Fixed rule applied to the measurements: {report.verdict.triggered_rules[0]}.",
                evidence_ref="verdict",
            )
        )
        tracker.finish("verdict")

        tracker.start("report")
        report.narrative = Narrative(source="template", text=build_narrative(report))
        if config.LLM_ENABLED:
            # A4.2: the Evidence Writer replaces the template only if every number it uses is in the report.
            text, reason = llm.write_narrative(report)
            if text:
                report.narrative = Narrative(source="llm", text=text)
            report.trace.append(
                TraceEntry(
                    step="report",
                    actor="writer",
                    decision=(
                        "AI-written summary (Evidence Writer) accepted"
                        if text
                        else "AI-written summary not used; kept the template summary"
                    ),
                    rationale=f"Numeric check: {reason}.",
                    evidence_ref="narrative",
                )
            )
        report.runtime_seconds = round(time.perf_counter() - started, 3)
        tracker.finish("report")
        return report, tracker.stages
    except EngineError as exc:
        running = tracker.running()
        if running:
            tracker.fail(running, exc.message)
        raise
    except Exception as exc:
        running = tracker.running()
        if running:
            tracker.fail(running, f"Unexpected error: {type(exc).__name__}")
        raise
