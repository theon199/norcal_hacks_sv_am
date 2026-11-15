> **Past result, saved for reference.** A real LabMirror run on the bundled synthetic sensor-fault demo, exported on 2026-11-15 (plan task 5.5). Rerun it with the command in the README; the numbers should match.

# LabMirror audit `bb16cabc7dda`

Created `2026-11-15T06:22:51+00:00` · schema `1.0`

## Verdict: Mixed: sensitive to conditions

- The claimed threshold of 5.0 pp was met on 3 of 5 evaluated splits.
- On the default split the measured lift was +7.50 pp.
- Across the 5 splits the lift ranged from +0.00 to +5.00 pp (median +5.00 pp).
- Under feature noise the mean lift on the default split was +6.88 pp (clean: +7.50 pp).

Triggered rule: `rule_3_mixed_seeds`

<details><summary>Verdict rule</summary>

Rules are evaluated in order and the first match wins. They are product labels, not statistical tests.
1. Inconclusive: a required test (default split, seed sensitivity or diagnostics) failed, or a critical diagnostic is present.
2. Not reproduced in tested settings: the claimed threshold was met on 0 of 5 splits.
3. Mixed / sensitive to conditions: the threshold was met on 1, 2 or 3 of 5 splits.
4. Mixed / sensitive to conditions: the threshold was met on at least 4 of 5 splits, but under feature noise the mean lift falls below the threshold and drops by at least 2.0 pp.
5. Consistent with claim in tested settings: the threshold was met on at least 4 of 5 splits and rule 4 did not apply.

</details>

## Claim

Audit whether Random Forest exceeds Logistic Regression by at least 5.0 percentage points of test-set accuracy on this dataset.

Source note (user-supplied context): Illustrative claim written for this example; it is not taken from a published paper.

## Summary

On the default split (seed 42), Random Forest scored 91.3% and Logistic Regression scored 83.8%, a lift of +7.50 pp against a claimed 5.0 pp, so the claim was met on that split. Across 5 other splits the claimed threshold was met on 3 of 5, and Random Forest was ahead at all on 4 of 5; the lift ranged from +0.00 pp to +5.00 pp (median +5.00 pp). With Gaussian noise added to the numeric test features (20 draws), the mean lift on the default split was +6.88 pp, compared with +7.50 pp on clean data. No issues were found in the checks performed. These checks cannot establish the absence of leakage. Under the fixed verdict rule, the result is: Mixed: sensitive to conditions.

## Dataset

- File: `sensor_fault_synthetic.csv`, 400 rows
- SHA-256: `12db1061fe7ce69f47e4676c8d8d8953f3c8b4bf9c59ce301dbb9098bba9f6e3`
- Target: `machine_fault`; class counts: `no` 192, `yes` 208
- Positive class for F1: `no`
- Features used: 8 (8 numeric, 0 categorical)
- Excluded columns: none

## Results by split

Accuracy on held-out rows. Claimed lift: at least 5.0 pp.

| Split | Seed | Random Forest | Logistic Regression | Most-frequent baseline | Lift | Meets claim |
|---|---|---|---|---|---|---|
| Default | 42 | 91.3% | 83.8% | 52.5% | +7.50 pp | yes |
| Repeat | 11 | 85.0% | 80.0% | 52.5% | +5.00 pp | yes |
| Repeat | 23 | 86.3% | 86.3% | 52.5% | +0.00 pp | no |
| Repeat | 37 | 90.0% | 87.5% | 52.5% | +2.50 pp | no |
| Repeat | 51 | 85.0% | 80.0% | 52.5% | +5.00 pp | yes |
| Repeat | 79 | 96.3% | 91.3% | 52.5% | +5.00 pp | yes |

Repeat splits meeting the claim: 3 of 5. Random Forest ahead at all: 4 of 5. These counts describe the tested splits and are not probabilities.

## Feature-noise test

Gaussian noise at 0.1 x each numeric feature's training standard deviation, 20 draws (first draw seed 1000). Models were not refitted.

| Model | Clean | Noisy mean | Noisy min | Noisy max | Change |
|---|---|---|---|---|---|
| Random Forest | 91.3% | 90.3% | 87.5% | 92.5% | -1.00 pp |
| Logistic Regression | 83.8% | 83.4% | 81.3% | 85.0% | -0.38 pp |

Lift: clean +7.50 pp, under noise +6.88 pp.

## Validity checks

No issues were found in the checks performed. These checks cannot establish the absence of leakage.

## Audit trace

- `validate` (engine): Accepted 8 features and a binary target. Positive class for F1 is the minority class 'no'.
- `default_split` (engine): Measured a lift of +7.50 pp on the default split. One stratified 80/20 split with seed 42; all models share the same rows.
- `seed_sensitivity` (engine): The claimed threshold was met on 3 of 5 evaluated splits. Same pipelines and hyperparameters refitted on five other stratified splits.
- `noise_robustness` (engine): Under noise the mean lift was +6.88 pp (clean +7.50 pp). 20 seeded draws of Gaussian noise at 10% of each feature's training standard deviation.
- `leakage_diagnostics` (engine): Found no issues in the checks performed. Duplicate rows across the split, identifier-like columns, suspicious names, class balance.
- `verdict` (engine): Mixed: sensitive to conditions. Fixed rule applied to the measurements: rule_3_mixed_seeds.

## Reproducibility

- Test fraction `0.2`, stratified; default seed `42`; repeat seeds `[11, 23, 37, 51, 79]`
- Preprocessing: `{'numeric': ["SimpleImputer(strategy='median')", 'StandardScaler()'], 'categorical': ["SimpleImputer(strategy='most_frequent')", "OneHotEncoder(handle_unknown='ignore')"], 'fitted_on': 'training rows only, inside a scikit-learn Pipeline', 'shared_by_all_models': True}`
- candidate: `{'key': 'random_forest', 'estimator': 'RandomForestClassifier', 'params': {'n_estimators': 100, 'max_depth': None, 'random_state': 0, 'n_jobs': 1}}`
- baseline: `{'key': 'logistic_regression', 'estimator': 'LogisticRegression', 'params': {'C': 1.0, 'solver': 'lbfgs', 'max_iter': 1000, 'random_state': 0}}`
- dummy: `{'key': 'dummy', 'estimator': 'DummyClassifier', 'params': {'strategy': 'most_frequent'}}`
- Noise: `{'distribution': 'Gaussian, mean 0', 'scale': '0.1 x training-set standard deviation, per numeric feature', 'n_draws': 20, 'rng': 'numpy default_rng(1000 + draw index)', 'applied_to': 'numeric features of the default-split test rows only; models are not refitted', 'skip_rule': 'features whose training standard deviation is zero or not finite are left unchanged'}`
- Environment: `python 3.13.11`, `numpy 2.5.4`, `pandas 3.1.1`, `scikit_learn 1.9.1`, `labmirror 0.1.0`
- Runtime: `0.764 s`

## Limitations

- LabMirror independently re-evaluates a claim on the data and protocol shown here. It is not a reproduction of any published study unless that study's exact data, splits and code were used. Verdict labels are product labels derived from the stated rule; they are not statistical significance results. Counts such as "2 of 5 splits" describe the tested splits and are not probabilities. Passing these tests does not guarantee that a result generalizes.
- Only binary classification on tabular CSV data with the two listed scikit-learn models is supported.
- Hyperparameters are fixed and untuned; a tuned model could behave differently.
- The model random_state is held fixed across splits, so this measures split-seed sensitivity, not sensitivity to model initialization.
- Leakage checks are heuristics and cannot establish the absence of leakage.
