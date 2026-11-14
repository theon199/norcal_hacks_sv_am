"""The demo cards promise a specific story. Pin each demo's real engine outcome so a code change cannot
silently turn the split-sensitivity example into something else."""

import hashlib
import json

import pytest

from labmirror import config
from labmirror.engine.profiling import load_csv, sha256_bytes
from labmirror.engine.run import run_audit
from labmirror.schemas import AuditRequest, ClaimSpec

DEMOS = json.loads((config.DEMO_DIR / "demos.json").read_text(encoding="utf-8"))


def _audit(demo):
    raw = (config.DEMO_DIR / demo["file"]).read_bytes()
    claim = ClaimSpec.model_validate(demo["suggested_claim"])
    report, _ = run_audit(
        load_csv(raw),
        sha256=sha256_bytes(raw),
        filename=demo["file"],
        request=AuditRequest(dataset_id="t", claim=claim, excluded_columns=[]),
        on_update=lambda *_: None,
    )
    return report


def test_synthetic_fixture_matches_provenance():
    provenance = json.loads((config.DEMO_DIR / "sensor_fault_synthetic.provenance.json").read_text(encoding="utf-8"))
    raw = (config.DEMO_DIR / provenance["file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == provenance["sha256"]


@pytest.mark.parametrize(
    "demo_id, verdict, k",
    [("sensor_fault_synthetic", "mixed", 2), ("breast_cancer_wisconsin", "not_reproduced", 0)],
)
def test_demo_verdicts(demo_id, verdict, k):
    report = _audit(next(d for d in DEMOS if d["id"] == demo_id))
    assert report.verdict.label == verdict
    assert report.seed_summary.n_meets_threshold == k
    if demo_id == "sensor_fault_synthetic":
        assert report.default_split.meets_threshold  # the default split looks like a win
        assert not any(d.severity == "critical" for d in report.diagnostics)
