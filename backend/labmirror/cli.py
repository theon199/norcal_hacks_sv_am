"""Command line entry point: the same engine the API uses.

    python -m labmirror.cli profile data.csv
    python -m labmirror.cli audit data.csv --target y --threshold 5 --out report.json
"""

import argparse
import json
import sys
from pathlib import Path

from labmirror.engine import EngineError
from labmirror.engine.profiling import default_exclusions, load_csv, profile_dataset, sha256_bytes
from labmirror.engine.run import run_audit
from labmirror.schemas import AuditRequest, ClaimSpec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="labmirror")
    sub = parser.add_subparsers(dest="command", required=True)

    p_profile = sub.add_parser("profile", help="Print a DatasetSummary for a CSV")
    p_profile.add_argument("csv", type=Path)

    p_audit = sub.add_parser("audit", help="Run an audit and print the AuditReport JSON")
    p_audit.add_argument("csv", type=Path)
    p_audit.add_argument("--target", required=True)
    p_audit.add_argument("--candidate", default="random_forest")
    p_audit.add_argument("--baseline", default="logistic_regression")
    p_audit.add_argument("--threshold", type=float, required=True, help="claimed minimum lift, in percentage points")
    p_audit.add_argument("--exclude", default=None, help="comma-separated columns; default: unusable and identifier-like")
    p_audit.add_argument("--out", type=Path, default=None)

    args = parser.parse_args(argv)
    raw = args.csv.read_bytes()
    try:
        df = load_csv(raw)
        sha = sha256_bytes(raw)
        summary = profile_dataset(df, dataset_id="cli", sha256=sha, filename=args.csv.name)
        if args.command == "profile":
            print(summary.model_dump_json(indent=2))
            return 0
        excluded = (
            [c.strip() for c in args.exclude.split(",") if c.strip()]
            if args.exclude is not None
            else default_exclusions(summary, args.target)
        )
        request = AuditRequest(
            dataset_id="cli",
            claim=ClaimSpec(
                target=args.target, candidate=args.candidate, baseline=args.baseline, threshold_pp=args.threshold
            ),
            excluded_columns=excluded,
        )
        report, _ = run_audit(
            df,
            sha256=sha,
            filename=args.csv.name,
            request=request,
            on_update=lambda stages, _r: print(
                "  ".join(f"{s.id}:{s.status}" for s in stages if s.status != "pending"), file=sys.stderr
            ),
        )
    except EngineError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message}}), file=sys.stderr)
        return 2
    text = report.model_dump_json(indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
