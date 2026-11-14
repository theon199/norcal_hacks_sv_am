"""Deterministic narrative and Markdown export (plan task A3.1).

Every number written here is a value from the AuditReport, formatted either as-is, as a percentage
(fraction x 100) or as percentage points. tests/test_report_md.py checks this. Identifiers, hashes,
timestamps and versions are wrapped in backticks and are not treated as measurements.
"""

from decimal import ROUND_HALF_UP, Decimal

from labmirror.engine.pipelines import MODEL_LABELS
from labmirror.schemas import AuditReport, ModelScore, SplitResult

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def fixed(value: float, digits: int) -> str:
    """Round like JavaScript's Number.prototype.toFixed (exact binary value, ties away from zero), so the
    Markdown shows the same digits as the dashboard. Python's format() would round exact ties to even."""
    q = Decimal(value).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    return f"{q:.{digits}f}"


def _pct(fraction: float) -> str:
    return f"{fixed(fraction * 100, 1)}%"


def _pp(value: float) -> str:
    text = fixed(value, 2)
    return f"{'' if text.startswith('-') else '+'}{text} pp"


def _score(split: SplitResult, role: str) -> ModelScore:
    return next(s for s in split.scores if s.model == role)


def build_narrative(report: AuditReport) -> str:
    """A short, templated summary. Only states what the measurements show."""
    claim = report.claim
    cand, base = MODEL_LABELS[claim.candidate], MODEL_LABELS[claim.baseline]
    parts: list[str] = []
    d = report.default_split
    if d is not None:
        parts.append(
            f"On the default split (seed {d.seed}), {cand} scored {_pct(_score(d, 'candidate').accuracy)} and "
            f"{base} scored {_pct(_score(d, 'baseline').accuracy)}, a lift of {_pp(d.lift_pp)} against a claimed "
            f"{claim.threshold_pp:.1f} pp, so the claim {'was' if d.meets_threshold else 'was not'} met on that split."
        )
    s = report.seed_summary
    if s is not None:
        parts.append(
            f"Across {s.n_seeds} other splits the claimed threshold was met on {s.n_meets_threshold} of {s.n_seeds}, "
            f"and {cand} was ahead at all on {s.n_candidate_wins} of {s.n_seeds}; the lift ranged from "
            f"{_pp(s.min_lift_pp)} to {_pp(s.max_lift_pp)} (median {_pp(s.median_lift_pp)})."
        )
    n = report.noise
    if n is not None:
        parts.append(
            f"With Gaussian noise added to the numeric test features ({n.n_draws} draws), the mean lift on the "
            f"default split was {_pp(n.noisy_mean_lift_pp)}, compared with {_pp(n.clean_lift_pp)} on clean data."
        )
    if report.diagnostics:
        worst = min(report.diagnostics, key=lambda f: SEVERITY_ORDER[f.severity])
        parts.append(
            f"The validity checks raised {len(report.diagnostics)} finding(s); the most severe ({worst.severity}) "
            f"was: {worst.description}"
        )
    elif report.no_issue_statement:
        parts.append(report.no_issue_statement)
    if report.verdict is not None:
        parts.append(f"Under the fixed verdict rule, the result is: {report.verdict.headline}.")
    return " ".join(parts)


def _split_row(label: str, split: SplitResult) -> str:
    c, b, dm = (_score(split, r) for r in ("candidate", "baseline", "dummy"))
    meets = "yes" if split.meets_threshold else "no"
    return (
        f"| {label} | {split.seed} | {_pct(c.accuracy)} | {_pct(b.accuracy)} | {_pct(dm.accuracy)} | "
        f"{_pp(split.lift_pp)} | {meets} |"
    )


def to_markdown(report: AuditReport) -> str:
    claim = report.claim
    cand, base = MODEL_LABELS[claim.candidate], MODEL_LABELS[claim.baseline]
    ds = report.dataset
    out: list[str] = []
    add = out.append

    add(f"# LabMirror audit `{report.audit_id}`")
    add("")
    add(f"Created `{report.created_at}` · schema `{report.schema_version}`")
    add("")
    if report.verdict is not None:
        add(f"## Verdict: {report.verdict.headline}")
        add("")
        for reason in report.verdict.reasons:
            add(f"- {reason}")
        add("")
        add(f"Triggered rule: `{report.verdict.triggered_rules[0]}`")
        add("")
        add("<details><summary>Verdict rule</summary>")
        add("")
        add(report.verdict.rule_text)
        add("")
        add("</details>")
        add("")

    add("## Claim")
    add("")
    add(report.claim_sentence)
    add("")
    if claim.reported_candidate_accuracy is not None or claim.reported_baseline_accuracy is not None:
        add("Reported by the user, not verified by LabMirror:")
        if claim.reported_candidate_accuracy is not None:
            add(f"- {cand}: {_pct(claim.reported_candidate_accuracy)}")
        if claim.reported_baseline_accuracy is not None:
            add(f"- {base}: {_pct(claim.reported_baseline_accuracy)}")
        add("")
    if claim.source_note:
        add(f"Source note (user-supplied context): {claim.source_note}")
        add("")

    if report.narrative is not None:
        add("## Summary")
        add("")
        add(report.narrative.text)
        add("")

    add("## Dataset")
    add("")
    add(f"- File: `{ds.filename}`, {ds.n_rows} rows")
    add(f"- SHA-256: `{ds.sha256}`")
    add(f"- Target: `{claim.target}`; class counts: " + ", ".join(f"`{k}` {v}" for k, v in ds.class_counts.items()))
    add(f"- Positive class for F1: `{ds.positive_class}`")
    add(
        f"- Features used: {len(ds.features_used)} ({len(ds.numeric_features)} numeric, "
        f"{len(ds.categorical_features)} categorical)"
    )
    add("- Excluded columns: " + (", ".join(f"`{c}`" for c in ds.excluded_columns) or "none"))
    add("")

    if report.default_split is not None or report.seed_runs:
        add("## Results by split")
        add("")
        add(f"Accuracy on held-out rows. Claimed lift: at least {claim.threshold_pp:.1f} pp.")
        add("")
        add(f"| Split | Seed | {cand} | {base} | Most-frequent baseline | Lift | Meets claim |")
        add("|---|---|---|---|---|---|---|")
        if report.default_split is not None:
            add(_split_row("Default", report.default_split))
        for run in report.seed_runs or []:
            add(_split_row("Repeat", run))
        add("")
        if report.seed_summary is not None:
            s = report.seed_summary
            add(
                f"Repeat splits meeting the claim: {s.n_meets_threshold} of {s.n_seeds}. "
                f"{cand} ahead at all: {s.n_candidate_wins} of {s.n_seeds}. "
                "These counts describe the tested splits and are not probabilities."
            )
            add("")

    add("## Feature-noise test")
    add("")
    n = report.noise
    if n is None:
        add("Not run or skipped; see the audit trace.")
    else:
        add(
            f"Gaussian noise at {n.noise_scale} x each numeric feature's training standard deviation, "
            f"{n.n_draws} draws (first draw seed {n.rng_seed}). Models were not refitted."
        )
        add("")
        add("| Model | Clean | Noisy mean | Noisy min | Noisy max | Change |")
        add("|---|---|---|---|---|---|")
        for m in n.per_model:
            label = cand if m.model == "candidate" else base
            add(
                f"| {label} | {_pct(m.clean_accuracy)} | {_pct(m.noisy_mean_accuracy)} | {_pct(m.noisy_min)} | "
                f"{_pct(m.noisy_max)} | {_pp(m.delta_pp)} |"
            )
        add("")
        add(f"Lift: clean {_pp(n.clean_lift_pp)}, under noise {_pp(n.noisy_mean_lift_pp)}.")
        if n.skipped_features:
            add("")
            add("Not perturbed: " + ", ".join(f"`{f}`" for f in n.skipped_features))
    add("")

    add("## Validity checks")
    add("")
    if report.diagnostics is None:
        add("The diagnostics stage did not complete; no findings are reported.")
    elif not report.diagnostics:
        add(report.no_issue_statement or "")
    else:
        for f in sorted(report.diagnostics, key=lambda f: SEVERITY_ORDER[f.severity]):
            add(f"- **{f.severity}** `{f.check}`: {f.description} _{f.caveat}_")
    add("")

    add("## Audit trace")
    add("")
    for t in report.trace:
        add(f"- `{t.step}` ({t.actor}): {t.decision}. {t.rationale}")
    add("")

    add("## Reproducibility")
    add("")
    cfg = report.config
    add(f"- Test fraction `{cfg.test_size}`, stratified; default seed `{cfg.default_seed}`; repeat seeds `{cfg.seeds}`")
    add(f"- Preprocessing: `{cfg.preprocessing}`")
    for role, model in cfg.models.items():
        add(f"- {role}: `{model}`")
    if cfg.noise:
        add(f"- Noise: `{cfg.noise}`")
    add("- Environment: " + ", ".join(f"`{k} {v}`" for k, v in report.environment.items()))
    if report.runtime_seconds is not None:
        add(f"- Runtime: `{report.runtime_seconds} s`")
    add("")

    add("## Limitations")
    add("")
    for item in report.limitations:
        add(f"- {item}")
    add("")
    return "\n".join(out)
