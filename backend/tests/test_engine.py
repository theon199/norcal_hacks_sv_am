import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from labmirror import config
from labmirror.engine import EngineError, units
from labmirror.engine.profiling import default_exclusions, load_csv, profile_dataset, sha256_bytes
from labmirror.engine.run import run_audit
from labmirror.engine.splits import run_paired_split, split_indices
from labmirror.engine.validation import prepare
from labmirror.schemas import AuditReport, ClaimSpec

ROOT = Path(__file__).resolve().parents[2]


# --- units ----------------------------------------------------------------
def test_unit_conversions():
    assert units.to_percent(0.875) == pytest.approx(87.5)
    assert units.lift_pp(0.90, 0.85) == pytest.approx(5.0)
    assert units.lift_pp(0.80, 0.85) == pytest.approx(-5.0)


def test_threshold_boundary_is_inclusive():
    assert units.meets_threshold(units.lift_pp(0.90, 0.85), 5.0)   # float noise must not flip this
    assert not units.meets_threshold(4.99, 5.0)


# --- profiling ------------------------------------------------------------
def _summary(df):
    raw = df.to_csv(index=False).encode()
    return profile_dataset(load_csv(raw), dataset_id="t", sha256=sha256_bytes(raw), filename="t.csv")


def test_profiling_kinds_and_flags(mixed_df):
    s = _summary(mixed_df)
    cols = {c.name: c for c in s.columns}
    assert cols["x1"].kind == "numeric" and cols["x1"].flags == []
    assert cols["color"].kind == "categorical"
    assert cols["notes"].kind == "unusable" and "free_text" in cols["notes"].flags
    assert "identifier_like" in cols["record_id"].flags
    assert "leakage_name" in cols["outcome"].flags
    assert cols["x2"].missing_fraction == pytest.approx(20 / 300)
    assert s.binary_target_candidates == ["outcome"]
    assert set(default_exclusions(s, "outcome")) == {"record_id", "notes"}
    assert len(s.preview.rows) == config.PREVIEW_ROWS


def test_continuous_integer_feature_is_not_flagged_as_identifier():
    df = pd.DataFrame({"income": np.random.default_rng(0).integers(20_000, 90_000, 200), "y": [0, 1] * 100})
    cols = {c.name: c for c in _summary(df).columns}
    assert cols["income"].flags == []


@pytest.mark.parametrize(
    "raw, code",
    [
        (b"", "no_file"),
        (b"a,b\n1,2\n", "too_few_rows"),
        (b'a,b\n"unterminated,1\n' + b"1,2\n" * 5, "malformed_csv"),
    ],
)
def test_load_csv_errors(raw, code):
    with pytest.raises(EngineError) as exc:
        load_csv(raw)
    assert exc.value.code == code


# --- validation -----------------------------------------------------------
def test_validation_error_codes(mixed_df, claim):
    def code(df, c, excluded=("record_id", "notes")):
        with pytest.raises(EngineError) as exc:
            prepare(df, c, list(excluded))
        return exc.value.code

    assert code(mixed_df, claim.model_copy(update={"target": "nope"})) == "unknown_target"
    assert code(mixed_df, claim.model_copy(update={"baseline": "random_forest"})) == "same_model"
    assert code(mixed_df, claim.model_copy(update={"target": "x1"})) == "target_not_binary"
    assert code(mixed_df, claim, excluded=("record_id",)) == "high_cardinality_feature"
    assert code(mixed_df, claim, excluded=("record_id", "notes", "x1", "x2")) == "no_usable_features"

    missing = mixed_df.copy()
    missing.loc[0, "outcome"] = np.nan
    assert code(missing, claim) == "target_has_missing"

    small = mixed_df.copy()
    small["outcome"] = ["yes"] * 10 + ["no"] * 290
    assert code(small, claim) == "class_too_small"


def test_invalid_threshold_rejected_by_schema():
    for bad in (0, -1, 101):
        with pytest.raises(ValueError):
            ClaimSpec(target="y", candidate="random_forest", baseline="logistic_regression", threshold_pp=bad)


def test_positive_class_is_minority(mixed_df, claim):
    data = prepare(mixed_df, claim, ["record_id", "notes"])
    assert data.class_counts[data.positive_class] == min(data.class_counts.values())
    assert data.y.sum() == data.class_counts[data.positive_class]


# --- leak safety and pairing ---------------------------------------------
def test_preprocessing_is_fitted_on_train_rows_only(mixed_df, claim):
    data = prepare(mixed_df, claim, ["record_id", "notes"])
    fitted = run_paired_split(data, claim, seed=42)
    train = data.X.iloc[fitted.train_idx]
    for role in ("candidate", "baseline"):
        numeric = fitted.pipelines[role].named_steps["preprocess"].named_transformers_["numeric"]
        medians = numeric.named_steps["impute"].statistics_
        expected = train[data.numeric_features].median().to_numpy()
        assert np.allclose(medians, expected)
        # and they differ from the full-data medians, so the test can actually fail
        assert not np.allclose(medians, data.X[data.numeric_features].median().to_numpy())
        imputed = train[data.numeric_features].fillna(train[data.numeric_features].median())
        assert np.allclose(numeric.named_steps["scale"].mean_, imputed.mean().to_numpy())


def test_models_share_identical_rows(mixed_df, claim):
    data = prepare(mixed_df, claim, ["record_id", "notes"])
    fitted = run_paired_split(data, claim, seed=11)
    assert set(fitted.train_idx).isdisjoint(fitted.test_idx)
    assert len(fitted.train_idx) + len(fitted.test_idx) == len(data.y)
    assert fitted.result.n_test == len(fitted.test_idx) == 60
    assert sum(fitted.result.test_class_counts.values()) == 60
    # the dummy model's accuracy pins down the shared test rows: majority share of exactly these labels
    y_test = data.y[fitted.test_idx]
    dummy = next(s for s in fitted.result.scores if s.model == "dummy")
    assert dummy.accuracy == pytest.approx(max(y_test.mean(), 1 - y_test.mean()))
    again_train, again_test = split_indices(data.y, 11)
    assert np.array_equal(again_test, fitted.test_idx) and np.array_equal(again_train, fitted.train_idx)


# --- orchestrator ---------------------------------------------------------
VOLATILE = {"audit_id", "created_at", "runtime_seconds"}


def _stable(report: AuditReport) -> dict:
    return {k: v for k, v in report.model_dump().items() if k not in VOLATILE}


def test_audit_is_reproducible_and_complete(mixed_df, request_for):
    updates = []
    kwargs = dict(sha256="abc", filename="t.csv", request=request_for())
    first, stages = run_audit(mixed_df, on_update=lambda s, r: updates.append([x.status for x in s]), **kwargs)
    second, _ = run_audit(mixed_df, **kwargs)
    assert _stable(first) == _stable(second)

    assert first.default_split.seed == config.DEFAULT_SEED
    assert [r.seed for r in first.seed_runs] == config.SENSITIVITY_SEEDS
    assert first.seed_summary.n_meets_threshold == sum(r.meets_threshold for r in first.seed_runs)
    for run in [first.default_split, *first.seed_runs]:
        acc = {s.model: s.accuracy for s in run.scores}
        assert run.lift_pp == pytest.approx((acc["candidate"] - acc["baseline"]) * 100)
        assert run.meets_threshold == (run.lift_pp >= 5.0 - 1e-9)
    assert first.dataset.sha256 == "abc"
    assert first.config.models["candidate"]["params"]["n_estimators"] == 100
    assert {"python", "numpy", "pandas", "scikit_learn"} <= set(first.environment)
    assert {s.id: s.status for s in stages}["seed_sensitivity"] == "done"
    assert any("running" in u for u in updates)


def test_failed_validation_marks_stage(mixed_df, request_for):
    seen = []
    with pytest.raises(EngineError):
        run_audit(mixed_df, sha256="x", filename="t.csv", request=request_for(excluded=("record_id",)),
                  on_update=lambda s, r: seen.append(s[0].status))
    assert seen[-1] == "failed"


def test_categorical_only_dataset_runs(claim):
    rng = np.random.default_rng(1)
    n = 200
    a = rng.choice(["p", "q", "r"], n)
    b = rng.choice(["u", "v"], n)
    y = np.where((a == "p") ^ (rng.random(n) < 0.2), "yes", "no")
    df = pd.DataFrame({"a": a, "b": b, "outcome": y})
    report, _ = run_audit(df, sha256="x", filename="c.csv",
                          request=type("R", (), {"claim": claim, "excluded_columns": []})())
    assert report.dataset.numeric_features == [] and len(report.seed_runs) == 5


# --- contract handoff -----------------------------------------------------
def test_sample_report_matches_contract():
    sample = ROOT / "contracts" / "sample_report.json"
    report = AuditReport.model_validate(json.loads(sample.read_text(encoding="utf-8")))
    assert report.schema_version == config.SCHEMA_VERSION
    assert report.seed_summary is not None
