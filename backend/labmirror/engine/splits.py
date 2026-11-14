"""One paired comparison: every model is fitted and scored on the same train/test rows."""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from labmirror import config
from labmirror.engine import units
from labmirror.engine.pipelines import MODEL_SETTINGS, build_pipeline
from labmirror.engine.validation import PreparedData
from labmirror.schemas import ClaimSpec, ModelScore, SplitResult


@dataclass
class FittedSplit:
    result: SplitResult
    train_idx: np.ndarray
    test_idx: np.ndarray
    pipelines: dict[str, Pipeline]   # keyed by role: candidate, baseline, dummy


def split_indices(y: np.ndarray, seed: int) -> tuple[np.ndarray, np.ndarray]:
    idx = np.arange(len(y))
    train_idx, test_idx = train_test_split(idx, test_size=config.TEST_SIZE, stratify=y, random_state=seed)
    return np.sort(train_idx), np.sort(test_idx)


def score(model_role: str, estimator_name: str, y_true: np.ndarray, y_pred: np.ndarray) -> ModelScore:
    return ModelScore(
        model=model_role,
        estimator=estimator_name,
        accuracy=float(accuracy_score(y_true, y_pred)),
        balanced_accuracy=float(balanced_accuracy_score(y_true, y_pred)),
        f1=float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
    )


def run_paired_split(data: PreparedData, claim: ClaimSpec, seed: int) -> FittedSplit:
    train_idx, test_idx = split_indices(data.y, seed)
    X_train, X_test = data.X.iloc[train_idx], data.X.iloc[test_idx]
    y_train, y_test = data.y[train_idx], data.y[test_idx]

    roles = {"candidate": claim.candidate, "baseline": claim.baseline, "dummy": "dummy"}
    pipelines: dict[str, Pipeline] = {}
    scores: list[ModelScore] = []
    for role, model_key in roles.items():
        pipe = build_pipeline(model_key, data.numeric_features, data.categorical_features)
        pipe.fit(X_train, y_train)
        pipelines[role] = pipe
        scores.append(score(role, MODEL_SETTINGS[model_key]["estimator"], y_test, pipe.predict(X_test)))

    by_role = {s.model: s for s in scores}
    lift = units.lift_pp(by_role["candidate"].accuracy, by_role["baseline"].accuracy)
    n_pos = int(y_test.sum())
    result = SplitResult(
        seed=seed,
        n_train=int(len(train_idx)),
        n_test=int(len(test_idx)),
        test_class_counts={data.positive_class: n_pos, data.negative_class: int(len(y_test) - n_pos)},
        scores=scores,
        lift_pp=lift,
        candidate_wins=lift > 0,
        meets_threshold=units.meets_threshold(lift, claim.threshold_pp),
    )
    return FittedSplit(result=result, train_idx=train_idx, test_idx=test_idx, pipelines=pipelines)
