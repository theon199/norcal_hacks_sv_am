"""A3.1 acceptance: the Markdown report contains the required sections, and every number in it is a value
from the JSON report (as-is, as a percentage, or rounded). Backticked spans (hashes, ids, versions,
timestamps, raw config) are identifiers, not measurements, and are skipped."""

import json
import math
import re

import pytest

from labmirror import config
from labmirror.engine.profiling import load_csv, sha256_bytes
from labmirror.engine.report_md import to_markdown
from labmirror.engine.run import run_audit
from labmirror.schemas import AuditRequest, ClaimSpec

NUMBER = re.compile(r"(?<![\w.])[+\-−]?\d+(?:\.\d+)?")
DEMOS = json.loads((config.DEMO_DIR / "demos.json").read_text(encoding="utf-8"))


def _report(demo, **claim_overrides):
    raw = (config.DEMO_DIR / demo["file"]).read_bytes()
    claim = ClaimSpec.model_validate({**demo["suggested_claim"], **claim_overrides})
    report, _ = run_audit(
        load_csv(raw),
        sha256=sha256_bytes(raw),
        filename=demo["file"],
        request=AuditRequest(dataset_id="t", claim=claim, excluded_columns=[]),
        on_update=lambda *_: None,
    )
    return report


def _json_numbers(obj) -> list[float]:
    if isinstance(obj, bool):
        return []
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):   # numbers quoted inside reasons, rule text, disclosures
        return [float(m.replace("−", "-")) for m in NUMBER.findall(obj)]
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in _json_numbers(v)]
    if isinstance(obj, (list, tuple)):
        return [n for v in obj for n in _json_numbers(v)]
    return []


def _traceable(token: str, sources: list[float]) -> bool:
    value = abs(float(token.replace("−", "-")))
    decimals = len(token.split(".")[1]) if "." in token else 0
    tol = 0.5 * 10 ** -decimals + 1e-9
    return any(
        math.isclose(abs(src) * scale, value, abs_tol=tol) for src in sources for scale in (1, 100)
    ) or (decimals == 0 and value in {abs(s) for s in sources})


@pytest.mark.parametrize("demo", DEMOS, ids=[d["id"] for d in DEMOS])
def test_markdown_numbers_come_from_the_json(demo):
    report = _report(demo, reported_candidate_accuracy=0.95, reported_baseline_accuracy=0.9)
    md = to_markdown(report)
    data = report.model_dump(mode="json")
    sources = _json_numbers(data)

    for heading in ("## Verdict", "## Claim", "## Summary", "## Dataset", "## Results by split",
                    "## Feature-noise test", "## Validity checks", "## Audit trace",
                    "## Reproducibility", "## Limitations"):
        assert heading in md
    assert report.dataset.sha256 in md and config.DISCLOSURE in md
    assert all(str(s) in md for s in report.config.seeds)
    assert "Reported by the user, not verified by LabMirror" in md

    prose = re.sub(r"`[^`]*`", " ", md).replace("SHA-256", "SHA")   # a label, not a measurement
    untraced = [t for t in NUMBER.findall(prose) if not _traceable(t, sources)]
    assert not untraced, f"numbers in Markdown with no JSON source: {untraced}"


def test_rounding_matches_javascript_tofixed():
    from labmirror.engine.report_md import fixed

    # Expected strings are what (x).toFixed(d) returns in JavaScript.
    assert fixed(0.9125 * 100, 1) == "91.3"      # exact tie: away from zero (Python's format gives 91.2)
    assert fixed(-2.5, 0) == "-3"
    assert fixed(1.005, 2) == "1.00"             # binary value is just below 1.005
    assert fixed(1.2499999999999998, 1) == "1.2"


def test_narrative_is_templated_and_avoids_significance_language():
    report = _report(DEMOS[0])
    assert report.narrative is not None and report.narrative.source == "template"
    assert report.verdict.headline in report.narrative.text
    md = to_markdown(report).replace(config.DISCLOSURE, "")
    assert "significant" not in md.lower() and "p-value" not in md.lower()
