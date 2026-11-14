"""Deterministic verdict rules (plan §5.6). Product labels, not statistical significance results."""

from typing import Optional

from labmirror import config
from labmirror.schemas import AuditVerdict, DiagnosticFinding, NoiseResult, SeedSummary, SplitResult

RULES = {
    "rule_1_inconclusive": (
        "1. Inconclusive: a required test (default split, seed sensitivity or diagnostics) failed, "
        "or a critical diagnostic is present."
    ),
    "rule_2_not_reproduced": "2. Not reproduced in tested settings: the claimed threshold was met on 0 of 5 splits.",
    "rule_3_mixed_seeds": "3. Mixed / sensitive to conditions: the threshold was met on 1, 2 or 3 of 5 splits.",
    "rule_4_mixed_noise": (
        f"4. Mixed / sensitive to conditions: the threshold was met on at least {config.CONSISTENT_MIN_SEEDS} of 5 "
        "splits, but under feature noise the mean lift falls below the threshold and drops by at least "
        f"{config.NOISE_MATERIALITY_PP:.1f} pp."
    ),
    "rule_5_consistent": (
        f"5. Consistent with claim in tested settings: the threshold was met on at least "
        f"{config.CONSISTENT_MIN_SEEDS} of 5 splits and rule 4 did not apply."
    ),
}
RULE_TEXT = (
    "Rules are evaluated in order and the first match wins. They are product labels, not statistical tests.\n"
    + "\n".join(RULES.values())
)

HEADLINES = {
    "inconclusive": "Inconclusive: the audit is blocked",
    "not_reproduced": "Not reproduced in tested settings",
    "mixed": "Mixed: sensitive to conditions",
    "consistent": "Consistent with the claim in tested settings",
}


def decide(
    *,
    threshold_pp: float,
    default_split: Optional[SplitResult],
    seed_summary: Optional[SeedSummary],
    noise: Optional[NoiseResult],
    diagnostics: Optional[list[DiagnosticFinding]],
    failed_stages: set[str],
) -> AuditVerdict:
    def verdict(label: str, rule: str, reasons: list[str]) -> AuditVerdict:
        return AuditVerdict(
            label=label, headline=HEADLINES[label], rule_text=RULE_TEXT, triggered_rules=[rule], reasons=reasons
        )

    # Rule 1
    blockers: list[str] = []
    required = {"default_split", "seed_sensitivity", "leakage_diagnostics"}
    for stage in sorted(required & failed_stages):
        blockers.append(f"The required test '{stage}' failed, so its evidence is missing.")
    if default_split is None or seed_summary is None or diagnostics is None:
        if not blockers:
            blockers.append("A required test did not produce a result.")
    for finding in diagnostics or []:
        if finding.severity == "critical":
            blockers.append(f"Critical diagnostic: {finding.description}")
    if blockers:
        return verdict("inconclusive", "rule_1_inconclusive", blockers)

    k, n = seed_summary.n_meets_threshold, seed_summary.n_seeds
    reasons = [
        f"The claimed threshold of {threshold_pp:.1f} pp was met on {k} of {n} evaluated splits.",
        f"On the default split the measured lift was {default_split.lift_pp:+.2f} pp.",
        f"Across the {n} splits the lift ranged from {seed_summary.min_lift_pp:+.2f} to "
        f"{seed_summary.max_lift_pp:+.2f} pp (median {seed_summary.median_lift_pp:+.2f} pp).",
    ]
    if "noise_robustness" in failed_stages:
        reasons.append("The noise test failed to run, so noise sensitivity was not assessed.")
    elif noise is None:
        reasons.append("The noise test was skipped because there are no numeric features to perturb.")
    else:
        reasons.append(
            f"Under feature noise the mean lift on the default split was {noise.noisy_mean_lift_pp:+.2f} pp "
            f"(clean: {noise.clean_lift_pp:+.2f} pp)."
        )

    if k == 0:
        return verdict("not_reproduced", "rule_2_not_reproduced", reasons)
    if k < config.CONSISTENT_MIN_SEEDS:
        return verdict("mixed", "rule_3_mixed_seeds", reasons)
    if (
        noise is not None
        and noise.noisy_mean_lift_pp < threshold_pp - config.THRESHOLD_EPSILON
        and noise.clean_lift_pp - noise.noisy_mean_lift_pp >= config.NOISE_MATERIALITY_PP - config.THRESHOLD_EPSILON
    ):
        return verdict("mixed", "rule_4_mixed_noise", reasons)
    return verdict("consistent", "rule_5_consistent", reasons)
