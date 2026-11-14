"""Check a claim against a dataset and resolve the exact feature set and encoded target."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from labmirror import config
from labmirror.engine import EngineError
from labmirror.engine.profiling import is_numeric, label_str, profile_column
from labmirror.schemas import ClaimSpec


@dataclass
class PreparedData:
    X: pd.DataFrame            # selected feature columns; categoricals as str objects with NaN
    y: np.ndarray              # 0/1, where 1 is the positive (minority) class
    numeric_features: list[str]
    categorical_features: list[str]
    excluded_columns: list[str]
    class_counts: dict[str, int]
    positive_class: str
    negative_class: str


def prepare(df: pd.DataFrame, claim: ClaimSpec, excluded_columns: list[str]) -> PreparedData:
    if claim.candidate == claim.baseline:
        raise EngineError("same_model", "Candidate and baseline must be different models.", "baseline")
    if not (0 < claim.threshold_pp <= 100):
        raise EngineError("invalid_threshold", "The threshold must be greater than 0 and at most 100 pp.", "threshold_pp")
    if not claim.target or claim.target not in df.columns:
        raise EngineError("unknown_target", f"Target column '{claim.target}' is not in the dataset.", "target")

    target = df[claim.target]
    n_missing = int(target.isna().sum())
    if n_missing:
        raise EngineError(
            "target_has_missing",
            f"The target column has {n_missing} missing value(s). Remove or fill those rows; LabMirror does not drop them silently.",
            "target",
        )
    counts = target.map(label_str).value_counts()
    if len(counts) != 2:
        raise EngineError(
            "target_not_binary",
            f"The target column has {len(counts)} distinct values; exactly 2 are required (binary classification only).",
            "target",
        )
    if int(counts.min()) < config.MIN_CLASS_COUNT:
        raise EngineError(
            "class_too_small",
            f"The smaller class has {int(counts.min())} rows; at least {config.MIN_CLASS_COUNT} per class are required.",
            "target",
        )

    # Positive class = minority class; a tie is broken by sorted label order (last wins).
    labels = sorted(counts.index)
    if counts[labels[0]] < counts[labels[1]]:
        positive, negative = labels[0], labels[1]
    else:
        positive, negative = labels[1], labels[0]
    y = (target.map(label_str) == positive).to_numpy().astype(int)

    excluded = [c for c in dict.fromkeys(excluded_columns) if c in df.columns and c != claim.target]
    feature_names = [c for c in df.columns if c != claim.target and c not in excluded]

    numeric, categorical = [], []
    for name in feature_names:
        info = profile_column(df[name])
        if info.kind == "unusable":
            reason = ", ".join(info.flags) or "unusable"
            raise EngineError(
                "high_cardinality_feature",
                f"Column '{name}' cannot be used as a feature ({reason}). Exclude it and run again.",
                "excluded_columns",
            )
        (numeric if info.kind == "numeric" else categorical).append(name)

    n_features = len(numeric) + len(categorical)
    if n_features < config.MIN_FEATURES:
        raise EngineError(
            "no_usable_features",
            f"{n_features} usable feature column(s) remain after exclusions; at least {config.MIN_FEATURES} are required.",
            "excluded_columns",
        )
    if n_features > config.MAX_FEATURES:
        raise EngineError(
            "too_many_columns",
            f"{n_features} feature columns are selected; the limit is {config.MAX_FEATURES}. Exclude some columns.",
            "excluded_columns",
        )
    if len(df) * n_features > config.MAX_CELLS:
        raise EngineError(
            "too_many_columns",
            f"{len(df)} rows x {n_features} feature columns is {len(df) * n_features:,} values; the limit is "
            f"{config.MAX_CELLS:,} so the audit finishes in time. Exclude columns (at most "
            f"{config.MAX_CELLS // len(df)} for this file) or use fewer rows.",
            "excluded_columns",
        )

    X = df[numeric + categorical].copy()
    for name in numeric:
        X[name] = pd.to_numeric(X[name], errors="coerce").astype(float)
    for name in categorical:
        col = X[name]
        X[name] = col.astype(object).where(col.notna(), np.nan).map(lambda v: v if isinstance(v, float) and np.isnan(v) else str(v))
    assert all(is_numeric(X[c]) for c in numeric)

    return PreparedData(
        X=X.reset_index(drop=True),
        y=y,
        numeric_features=numeric,
        categorical_features=categorical,
        excluded_columns=excluded,
        class_counts={str(k): int(v) for k, v in counts.sort_index().items()},
        positive_class=positive,
        negative_class=negative,
    )
