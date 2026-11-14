"""Required test 4: transparent leakage and validity heuristics. Every finding carries exact evidence."""

import pandas as pd

from labmirror import config
from labmirror.engine.profiling import profile_column
from labmirror.engine.splits import FittedSplit
from labmirror.engine.validation import PreparedData
from labmirror.schemas import DiagnosticFinding


def _finding(check: str, severity: str, description: str, evidence: dict) -> DiagnosticFinding:
    return DiagnosticFinding(
        check=check, severity=severity, description=description, evidence=evidence, caveat=config.HEURISTIC_CAVEAT
    )


def _row_keys(X: pd.DataFrame) -> pd.Series:
    """One hashable key per row over the feature columns; NaN equals NaN."""
    return pd.util.hash_pandas_object(X, index=False).reset_index(drop=True)


def run_diagnostics(data: PreparedData, default: FittedSplit, target: str) -> list[DiagnosticFinding]:
    findings: list[DiagnosticFinding] = []
    keys = _row_keys(data.X)
    y = pd.Series(data.y)

    # 1. Identical feature vectors on both sides of the default split.
    train_keys = keys.iloc[default.train_idx]
    test_keys = keys.iloc[default.test_idx]
    train_labels: dict[int, set[int]] = {}
    for k, label in zip(train_keys, y.iloc[default.train_idx]):
        train_labels.setdefault(k, set()).add(int(label))
    same_label = different_label = 0
    for k, label in zip(test_keys, y.iloc[default.test_idx]):
        seen = train_labels.get(k)
        if seen is None:
            continue
        if int(label) in seen:
            same_label += 1          # exact duplicate: same features and same label
        else:
            different_label += 1     # same features, different label
    twins = same_label + different_label
    if twins:
        share = twins / len(test_keys)
        distinct = int(keys.nunique())
        distinct_share = distinct / len(keys)
        # When the features only take a few combinations (e.g. two small categorical columns), repeated
        # feature vectors are expected and say nothing about leakage, so the finding is informational.
        coarse = distinct_share < config.COARSE_FEATURE_SPACE_SHARE
        if coarse:
            severity = "info"
            tail = (
                f"The selected features take only {distinct} distinct combinations across {len(keys)} rows, "
                "so repeats are expected here and are not treated as a sign of leakage."
            )
        else:
            severity = "critical" if share >= config.CRITICAL_DUPLICATE_SHARE else "warning"
            tail = "Models can score well on these by memorizing them."
        findings.append(
            _finding(
                "cross_split_duplicates",
                severity,
                f"{twins} of {len(test_keys)} test rows in the default split have an identical feature vector in the "
                f"training rows ({share:.1%}). {tail}",
                {
                    "test_rows_with_training_twin": twins,
                    "n_test": int(len(test_keys)),
                    "share_of_test": round(share, 4),
                    "same_label_exact_duplicates": same_label,
                    "same_features_different_label": different_label,
                    "distinct_feature_vectors": distinct,
                    "distinct_share_of_rows": round(distinct_share, 4),
                    "split_seed": default.result.seed,
                },
            )
        )

    # 2. Identical feature vectors carrying both labels anywhere in the dataset.
    labels_per_key = y.groupby(keys.to_numpy()).nunique()
    conflicting = labels_per_key[labels_per_key > 1].index
    if len(conflicting):
        n_rows = int(keys.isin(conflicting).sum())
        findings.append(
            _finding(
                "conflicting_label_duplicates",
                "warning",
                f"{len(conflicting)} group(s) of rows share identical features but have different labels "
                f"({n_rows} rows). No model can classify all of them correctly.",
                {"conflicting_groups": int(len(conflicting)), "rows_involved": n_rows},
            )
        )

    # 3 and 4. Column-name and uniqueness heuristics on the features actually used.
    id_like, leak_named = [], []
    target_lower = target.lower()
    for name in data.numeric_features + data.categorical_features:
        info = profile_column(data.X[name])
        if "identifier_like" in info.flags:
            id_like.append(name)
        if "leakage_name" in info.flags or target_lower in name.lower():
            leak_named.append(name)
    if id_like:
        findings.append(
            _finding(
                "identifier_like",
                "warning",
                f"{len(id_like)} feature(s) look like record identifiers. Identifiers carry no generalizable signal "
                "and can encode the label by accident.",
                {"columns": id_like},
            )
        )
    if leak_named:
        findings.append(
            _finding(
                "leakage_name",
                "warning",
                f"{len(leak_named)} feature name(s) suggest a direct label or a value recorded after the outcome.",
                {"columns": leak_named, "matched_terms": list(config.LEAKAGE_NAME_TERMS) + [target_lower]},
            )
        )

    # 5. Class balance.
    minority = int(min(data.class_counts.values()))
    share = minority / len(data.y)
    if share < config.IMBALANCE_INFO_SHARE:
        findings.append(
            _finding(
                "class_imbalance",
                "warning" if share < config.IMBALANCE_WARNING_SHARE else "info",
                f"The smaller class is {share:.1%} of the rows. Accuracy can look high for a model that mostly "
                "predicts the larger class; compare against the most-frequent-class baseline and balanced accuracy.",
                {"minority_class": data.positive_class, "minority_rows": minority, "minority_share": round(share, 4)},
            )
        )

    # 6. Tiny minority class in the default test split.
    test_minority = int(min(default.result.test_class_counts.values()))
    if test_minority < config.SMALL_TEST_CLASS:
        findings.append(
            _finding(
                "small_test_class",
                "warning",
                f"The default test split has only {test_minority} rows of the smaller class, so one prediction "
                f"moves accuracy by {100 / default.result.n_test:.1f} pp.",
                {"minority_test_rows": test_minority, "n_test": default.result.n_test},
            )
        )
    return findings
