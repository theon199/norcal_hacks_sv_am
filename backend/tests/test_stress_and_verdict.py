import numpy as np
import pandas as pd
import pytest

from labmirror import config
from labmirror.engine import verdict as verdict_rules
from labmirror.engine.diagnostics import run_diagnostics
from labmirror.engine.run import run_audit
from labmirror.engine.splits import run_paired_split
from labmirror.engine.tests_noise import run_noise
from labmirror.engine.validation import prepare
from labmirror.schemas import (
    AuditRequest,
    ClaimSpec,
    DiagnosticFinding,
    NoiseModelResult,
    NoiseResult,
    SeedSummary,
    SplitResult,
)


def _request(claim):
    return AuditRequest(dataset_id="t", claim=claim, excluded_columns=[])


# --- noise ----------------------------------------------------------------
def test_noise_is_deterministic_and_skips_constant_training_feature(mixed_df, claim):
    data = prepare(mixed_df, claim, ["record_id", "notes"])
    fitted = run_paired_split(data, claim, 42)
    # make x2 constant within the training rows only: it must be skipped, not perturbed
    data.X.loc[data.X.index[fitted.train_idx], "x2"] = 1.0
    a, b = run_noise(data, fitted), run_noise(data, fitted)
    assert a == b
    assert a.perturbed_features == ["x1"] and a.skipped_features == ["x2"]
    assert a.n_draws == 20
    for m in a.per_model:
        assert m.noisy_min <= m.noisy_mean_accuracy <= m.noisy_max
        assert m.delta_pp == pytest.approx((m.noisy_mean_accuracy - m.clean_accuracy) * 100)
    clean = {s.model: s.accuracy for s in fitted.result.scores}
    assert {m.model: m.clean_accuracy for m in a.per_model} == pytest.approx(
        {"candidate": clean["candidate"], "baseline": clean["baseline"]}
    )
    assert a.clean_lift_pp == pytest.approx(fitted.result.lift_pp)


def test_noise_skipped_without_numeric_features(claim):
    rng = np.random.default_rng(1)
    n = 200
    a = rng.choice(["p", "q", "r"], n)
    df = pd.DataFrame({"a": a, "b": rng.choice(["u", "v"], n), "outcome": np.where(a == "p", "yes", "no")})
    report, stages = run_audit(df, sha256="x", filename="c.csv", request=_request(claim))
    assert report.noise is None
    assert {s.id: s.status for s in stages}["noise_robustness"] == "skipped"
    assert report.verdict is not None and "skipped" in " ".join(report.verdict.reasons)
    # two small categorical columns repeat by nature: informational, never a blocker
    dup = next(f for f in report.diagnostics if f.check == "cross_split_duplicates")
    assert dup.severity == "info" and dup.evidence["distinct_feature_vectors"] == 6
    assert report.verdict.label != "inconclusive"


# --- diagnostics ----------------------------------------------------------
def test_duplicate_detector_reports_exact_counts(mixed_df, claim):
    data = prepare(mixed_df, claim, ["record_id", "notes"])
    fitted = run_paired_split(data, claim, 42)
    assert not [f for f in run_diagnostics(data, fitted, "outcome") if f.check == "cross_split_duplicates"]

    # plant: copy 7 training rows' features onto 7 test rows; 4 keep the train label, 3 get the opposite one
    train, test = fitted.train_idx[:7], fitted.test_idx[:7]
    data.X.iloc[test] = data.X.iloc[train].to_numpy()
    data.y[test[:4]] = data.y[train[:4]]
    data.y[test[4:]] = 1 - data.y[train[4:]]
    found = {f.check: f for f in run_diagnostics(data, fitted, "outcome")}
    dup = found["cross_split_duplicates"]
    assert dup.evidence["test_rows_with_training_twin"] == 7
    assert dup.evidence["same_label_exact_duplicates"] == 4
    assert dup.evidence["same_features_different_label"] == 3
    assert dup.severity == "critical"          # 7 of 60 test rows is above 10%
    assert found["conflicting_label_duplicates"].evidence["conflicting_groups"] == 3
    assert "cannot prove" in dup.caveat


def test_name_and_balance_diagnostics(mixed_df, claim):
    df = mixed_df.rename(columns={"x2": "post_outcome_score"})
    df["outcome"] = ["yes"] * 45 + ["no"] * 255
    data = prepare(df, claim, ["notes"])        # record_id deliberately left in
    fitted = run_paired_split(data, claim, 42)
    found = {f.check: f for f in run_diagnostics(data, fitted, "outcome")}
    assert found["identifier_like"].evidence["columns"] == ["record_id"]
    assert found["leakage_name"].evidence["columns"] == ["post_outcome_score"]
    assert found["class_imbalance"].severity == "warning"
    assert found["class_imbalance"].evidence["minority_rows"] == 45
    assert found["small_test_class"].evidence["minority_test_rows"] == 9


def test_clean_dataset_gets_exact_no_issue_statement():
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"a": rng.normal(size=200), "b": rng.normal(size=200), "y": [0, 1] * 100})
    c = ClaimSpec(target="y", candidate="random_forest", baseline="logistic_regression", threshold_pp=5)
    report, _ = run_audit(df, sha256="x", filename="c.csv", request=_request(c))
    assert report.diagnostics == [] and report.no_issue_statement == config.NO_ISSUE_STATEMENT


# --- verdict --------------------------------------------------------------
def _split(lift):
    return SplitResult(seed=42, n_train=80, n_test=20, test_class_counts={"a": 10, "b": 10}, scores=[],
                       lift_pp=lift, candidate_wins=lift > 0, meets_threshold=lift >= 5)


def _seeds(k):
    return SeedSummary(n_seeds=5, n_candidate_wins=5, n_meets_threshold=k, median_lift_pp=5, min_lift_pp=1,
                       max_lift_pp=9, candidate_accuracy_range=(0.8, 0.9), baseline_accuracy_range=(0.7, 0.8))


def _noise(clean, noisy):
    pm = [
        NoiseModelResult(model=m, clean_accuracy=0.9, noisy_mean_accuracy=0.9, noisy_min=0.9, noisy_max=0.9, delta_pp=0)
        for m in ("candidate", "baseline")
    ]
    return NoiseResult(noise_scale=0.1, n_draws=20, rng_seed=1000, perturbed_features=["x"], skipped_features=[],
                       per_model=pm, clean_lift_pp=clean, noisy_mean_lift_pp=noisy)


CRITICAL = DiagnosticFinding(check="cross_split_duplicates", severity="critical", description="d", evidence={}, caveat="c")
WARNING = DiagnosticFinding(check="identifier_like", severity="warning", description="d", evidence={}, caveat="c")


@pytest.mark.parametrize(
    "k, noise, diagnostics, failed, label, rule",
    [
        (5, _noise(6, 6), [CRITICAL], set(), "inconclusive", "rule_1_inconclusive"),
        (5, _noise(6, 6), None, {"leakage_diagnostics"}, "inconclusive", "rule_1_inconclusive"),
        (0, _noise(6, 6), [WARNING], set(), "not_reproduced", "rule_2_not_reproduced"),
        (1, _noise(6, 6), [], set(), "mixed", "rule_3_mixed_seeds"),
        (3, _noise(6, 6), [], set(), "mixed", "rule_3_mixed_seeds"),
        (4, _noise(6.5, 4.5), [], set(), "mixed", "rule_4_mixed_noise"),       # below threshold and dropped 2.0
        (4, _noise(6.5, 4.6), [], set(), "consistent", "rule_5_consistent"),   # dropped only 1.9
        (5, _noise(9.0, 5.0), [], set(), "consistent", "rule_5_consistent"),   # big drop but still at threshold
        (5, None, [WARNING], set(), "consistent", "rule_5_consistent"),        # noise skipped; warnings do not block
        (4, None, [], {"noise_robustness"}, "consistent", "rule_5_consistent"),
    ],
)
def test_verdict_rules(k, noise, diagnostics, failed, label, rule):
    v = verdict_rules.decide(threshold_pp=5.0, default_split=_split(6.0), seed_summary=_seeds(k), noise=noise,
                             diagnostics=diagnostics, failed_stages=failed)
    assert (v.label, v.triggered_rules) == (label, [rule])
    assert all(text in v.rule_text for text in verdict_rules.RULES.values())
    assert "significan" not in (v.headline + " ".join(v.reasons)).lower()


def test_scientific_constants_are_pinned():
    assert (config.CONSISTENT_MIN_SEEDS, config.NOISE_MATERIALITY_PP, config.CRITICAL_DUPLICATE_SHARE) == (4, 2.0, 0.10)
    assert (config.DEFAULT_SEED, config.SENSITIVITY_SEEDS, config.TEST_SIZE) == (42, [11, 23, 37, 51, 79], 0.2)
    assert (config.NOISE_SCALE, config.NOISE_DRAWS) == (0.10, 20)
