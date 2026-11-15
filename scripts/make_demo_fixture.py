"""Generate the split-sensitivity demo dataset (plan section 6).

The dataset is SELECTED, not found: we search generator seeds for a synthetic dataset on which the
claim "Random Forest beats Logistic Regression by >= 5.0 pp of accuracy" is met on the default split
(seed 42) but on only 1-3 of the 5 alternate splits. Every candidate is scored by the production engine
(engine.run_audit) on the exact CSV bytes that are written, so the selection uses the same code path as
the website. No value is edited after generation. The provenance file records the whole search.

    cd backend && python ../scripts/make_demo_fixture.py labmirror/demo_data
"""

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.datasets import make_classification

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from labmirror.engine.profiling import load_csv, sha256_bytes  # noqa: E402
from labmirror.engine.run import run_audit  # noqa: E402
from labmirror.engine.tests_default import run_default_split  # noqa: E402
from labmirror.engine.validation import prepare  # noqa: E402
from labmirror.schemas import AuditRequest, ClaimSpec  # noqa: E402

FILE_NAME = "sensor_fault_synthetic.csv"
TARGET = "machine_fault"
THRESHOLD_PP = 5.0
GENERATOR = dict(
    n_samples=400,
    n_features=8,
    n_informative=4,
    n_redundant=2,
    n_repeated=0,
    n_classes=2,
    n_clusters_per_class=2,
    flip_y=0.05,
    class_sep=1.0,
)
SEED_RANGE = range(0, 200)

# Each generated column becomes a named machine reading: value = center + scale * generated value,
# rounded to a realistic precision. The mapping is fixed before the search runs; it gives the columns
# plausible units for the demo and is the only transformation applied.
# (column name, center, scale, decimals)
READINGS = [
    ("temperature_c", 68.0, 2.5, 1),
    ("vibration_mm_s", 4.0, 0.4, 2),
    ("oil_pressure_bar", 5.0, 0.4, 2),
    ("motor_current_amps", 15.0, 1.2, 2),
    ("rotation_speed_rpm", 1450.0, 25.0, 0),
    ("oil_quality_pct", 75.0, 2.5, 1),
    ("sound_level_db", 72.0, 1.5, 1),
    ("hours_since_service", 600.0, 60.0, 0),
]

CLAIM = ClaimSpec(target=TARGET, candidate="random_forest", baseline="logistic_regression", threshold_pp=THRESHOLD_PP)


def build_csv(seed: int) -> bytes:
    X, y = make_classification(**GENERATOR, random_state=seed)
    lines = [",".join([name for name, *_ in READINGS] + [TARGET])]
    for row, label in zip(X, y):
        cells = [f"{center + scale * value:.{decimals}f}" for value, (_, center, scale, decimals) in zip(row, READINGS)]
        lines.append(",".join(cells + ["yes" if label == 1 else "no"]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def main(out_dir: Path) -> int:
    examined = 0
    default_passes = 0
    for seed in SEED_RANGE:
        examined += 1
        raw = build_csv(seed)
        df = load_csv(raw)
        # Cheap pre-filter: the default split alone, using the engine's own function.
        if not run_default_split(prepare(df, CLAIM, []), CLAIM).result.meets_threshold:
            continue
        default_passes += 1
        report, _ = run_audit(
            df,
            sha256=sha256_bytes(raw),
            filename=FILE_NAME,
            request=AuditRequest(dataset_id="fixture", claim=CLAIM, excluded_columns=[]),
            on_update=lambda *_: None,
        )
        k = report.seed_summary.n_meets_threshold
        critical = any(d.severity == "critical" for d in report.diagnostics)
        print(f"seed {seed}: default lift {report.default_split.lift_pp:+.2f} pp, k={k}/5, "
              f"verdict={report.verdict.label}", file=sys.stderr)
        if 1 <= k <= 3 and not critical and report.verdict.label == "mixed":
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / FILE_NAME).write_bytes(raw)
            provenance = {
                "file": FILE_NAME,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "generator": "sklearn.datasets.make_classification",
                "generator_parameters": GENERATOR,
                "generator_seed": seed,
                "readings": [
                    {"column": n, "center": c, "scale": k, "decimals": d} for n, c, k, d in READINGS
                ],
                "target_mapping": {"0": "no", "1": "yes"},
                "selection_criterion": (
                    f"First generator seed in {SEED_RANGE.start}..{SEED_RANGE.stop - 1} where the production engine "
                    f"finds the claim (Random Forest beats Logistic Regression by >= {THRESHOLD_PP} pp accuracy) met on "
                    "the default split (seed 42) and on 1-3 of the 5 alternate splits, with no critical diagnostic."
                ),
                "candidates_examined": examined,
                "candidates_meeting_default_split": default_passes,
                "selected_result": {
                    "default_lift_pp": report.default_split.lift_pp,
                    "alternate_splits_meeting_threshold": k,
                    "verdict": report.verdict.label,
                },
                "honesty_note": (
                    "This dataset was selected to illustrate split sensitivity. It is synthetic and does not "
                    "describe real machines; the column names and units were assigned for readability. All numbers shown in LabMirror are recomputed live."
                ),
            }
            (out_dir / "sensor_fault_synthetic.provenance.json").write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(provenance, indent=2))
            print(df.describe().loc[["min", "mean", "max"]].round(2).to_string(), file=sys.stderr)
            return 0
    print(f"No qualifying seed in {examined} candidates ({default_passes} met the default split).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
