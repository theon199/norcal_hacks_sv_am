"""The finite, allowlisted set of audit stages. Nothing outside this list can run."""

from labmirror.schemas import Stage

# (id, label, why, implemented)
STAGES: list[tuple[str, str, str, bool]] = [
    (
        "validate",
        "Validating data",
        "Confirms the target is binary, classes are large enough and every selected feature is usable.",
        True,
    ),
    (
        "default_split",
        "Default split comparison",
        "Fits both models on one stratified 80/20 split (seed 42): the kind of single result a claim is usually based on.",
        True,
    ),
    (
        "seed_sensitivity",
        "Repeating on five other splits",
        "A real advantage should survive a different random train/test split; a fragile one will not.",
        True,
    ),
    (
        "noise_robustness",
        "Stress-testing with feature noise",
        "Adds small seeded Gaussian noise to numeric test features to see whether the advantage depends on exact values.",
        True,
    ),
    (
        "leakage_diagnostics",
        "Checking for leakage signs",
        "Looks for duplicated rows across train and test, identifier-like columns and suspicious feature names.",
        True,
    ),
    (
        "verdict",
        "Auditing the evidence",
        "Applies a fixed, published rule to the measurements. No model output decides the verdict.",
        True,
    ),
    (
        "report",
        "Generating report",
        "Records every setting needed to rerun this audit: data hash, seeds, hyperparameters and library versions.",
        True,
    ),
]


def initial_stages() -> list[Stage]:
    return [Stage(id=sid, label=label, why=why) for sid, label, why, _ in STAGES]


def is_implemented(stage_id: str) -> bool:
    return next(impl for sid, _, _, impl in STAGES if sid == stage_id)
