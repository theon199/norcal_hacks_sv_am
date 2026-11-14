"""Unit conversions. Accuracies are fractions; lifts are percentage points (pp)."""

from labmirror.config import THRESHOLD_EPSILON


def to_percent(fraction: float) -> float:
    return fraction * 100.0


def lift_pp(candidate_accuracy: float, baseline_accuracy: float) -> float:
    """Candidate minus baseline, in percentage points. Never a relative percent change."""
    return (candidate_accuracy - baseline_accuracy) * 100.0


def meets_threshold(lift: float, threshold_pp: float) -> bool:
    return lift >= threshold_pp - THRESHOLD_EPSILON
