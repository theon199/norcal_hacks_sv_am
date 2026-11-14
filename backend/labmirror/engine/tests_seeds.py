"""Required test 2: split-seed sensitivity. Descriptive robustness evidence, not independent trials."""

import statistics

from labmirror import config
from labmirror.engine.splits import run_paired_split
from labmirror.engine.validation import PreparedData
from labmirror.schemas import ClaimSpec, SeedSummary, SplitResult


def run_seed_sensitivity(data: PreparedData, claim: ClaimSpec) -> tuple[list[SplitResult], SeedSummary]:
    runs = [run_paired_split(data, claim, seed).result for seed in config.SENSITIVITY_SEEDS]
    return runs, summarize(runs)


def _accuracy(run: SplitResult, role: str) -> float:
    return next(s.accuracy for s in run.scores if s.model == role)


def summarize(runs: list[SplitResult]) -> SeedSummary:
    lifts = [r.lift_pp for r in runs]
    cand = [_accuracy(r, "candidate") for r in runs]
    base = [_accuracy(r, "baseline") for r in runs]
    return SeedSummary(
        n_seeds=len(runs),
        n_candidate_wins=sum(r.candidate_wins for r in runs),
        n_meets_threshold=sum(r.meets_threshold for r in runs),
        median_lift_pp=float(statistics.median(lifts)),
        min_lift_pp=float(min(lifts)),
        max_lift_pp=float(max(lifts)),
        candidate_accuracy_range=(float(min(cand)), float(max(cand))),
        baseline_accuracy_range=(float(min(base)), float(max(base))),
    )
