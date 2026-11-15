"""Phase 4 LLM layer (A4.1, A4.2): the model can reorder tests and replace the narrative, nothing else.
The Claude call itself is faked; these tests pin the boundaries, not the model's wording."""

import pytest

from labmirror import config
from labmirror.engine import llm
from labmirror.engine.profiling import sha256_bytes
from labmirror.engine.run import run_audit

VOLATILE = {"audit_id", "created_at", "runtime_seconds", "trace", "narrative"}


def _run(df, request):
    report, stages = run_audit(df, sha256=sha256_bytes(b"x"), filename="t.csv", request=request)
    return report, stages


def _measurements(report) -> dict:
    return report.model_dump(mode="json", exclude=VOLATILE)


@pytest.fixture
def baseline(mixed_df, request_for):
    return _run(mixed_df, request_for())[0]


def test_disabled_uses_template_and_no_ai_trace(monkeypatch, mixed_df, request_for):
    monkeypatch.setattr(config, "LLM_ENABLED", False)
    baseline = _run(mixed_df, request_for())[0]
    assert baseline.narrative.source == "template"
    assert all(t.actor == "engine" for t in baseline.trace)


def test_forced_exception_leaves_scores_untouched(monkeypatch, mixed_df, request_for, baseline):
    monkeypatch.setattr(config, "LLM_ENABLED", True)

    def boom(*_a, **_k):
        raise RuntimeError("model down")

    monkeypatch.setattr(llm, "_ask", boom)
    report, stages = _run(mixed_df, request_for())
    assert _measurements(report) == _measurements(baseline)
    assert report.narrative.source == "template"
    assert all(s.status in ("done", "skipped") for s in stages)
    assert any(t.step == "skeptic" and "unavailable" in t.decision for t in report.trace)


def test_skeptic_reorders_drops_unknown_ids_and_still_runs_everything(monkeypatch, mixed_df, request_for, baseline):
    monkeypatch.setattr(config, "LLM_ENABLED", True)
    started: list[str] = []

    def fake_ask(system, payload, schema):
        assert "rows" not in payload and "preview" not in payload   # no raw data leaves the engine
        if schema is llm._Plan:
            return llm._Plan(picks=[
                llm._Pick(test_id="leakage_diagnostics", rationale="Check leakage first."),
                llm._Pick(test_id="rm -rf /", rationale="Not on the allowlist."),
                llm._Pick(test_id="noise_robustness", rationale="Then noise."),
            ])
        return llm._Narrative(text="The verdict is invented: 99.99% accuracy.")   # fails the number check

    monkeypatch.setattr(llm, "_ask", fake_ask)

    def on_update(stages, _report):
        running = next((s.id for s in stages if s.status == "running"), None)
        if running and running not in started:
            started.append(running)

    report, stages = run_audit(
        mixed_df, sha256=sha256_bytes(b"x"), filename="t.csv", request=request_for(), on_update=on_update
    )
    stress = [s for s in started if s in llm.STRESS_TESTS]
    assert stress == ["leakage_diagnostics", "noise_robustness", "seed_sensitivity"]
    assert _measurements(report) == _measurements(baseline)
    skeptic = [t for t in report.trace if t.actor == "skeptic"]
    assert [t.step for t in skeptic] == stress
    assert all("AI-suggested" in t.decision for t in skeptic)
    assert report.narrative.source == "template"
    writer = next(t for t in report.trace if t.actor == "writer")
    assert "99.99" in writer.rationale


def test_writer_accepted_only_when_every_number_is_in_the_report(monkeypatch, mixed_df, request_for, baseline):
    monkeypatch.setattr(config, "LLM_ENABLED", True)
    d = baseline.default_split
    good = (
        f"On the default split with seed {d.seed} the lift was {d.lift_pp:.2f} pp against a claimed "
        f"{baseline.claim.threshold_pp:.1f} pp. {baseline.verdict.headline}."
    )

    def fake_ask(system, payload, schema):
        if schema is llm._Plan:
            raise RuntimeError("skeptic off for this test")
        return llm._Narrative(text=good)

    monkeypatch.setattr(llm, "_ask", fake_ask)
    report, _ = _run(mixed_df, request_for())
    assert report.narrative.source == "llm"
    assert report.narrative.text == good
    assert _measurements(report) == _measurements(baseline)


@pytest.mark.parametrize(
    "text, reason",
    [
        ("", "empty"),
        ("The improvement is statistically significant.", "banned"),
        ("We found a p-value below the cutoff.", "banned"),
        ("Random Forest reached 123.456 accuracy.", "numbers"),
    ],
)
def test_check_narrative_rejects(baseline, text, reason):
    assert reason in llm.check_narrative(text, baseline)
