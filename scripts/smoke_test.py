"""End-to-end smoke test against a running LabMirror API (standard library only).

    python scripts/smoke_test.py https://labmirror-api.onrender.com

Loads the first demo, runs its suggested claim, waits for the verdict and checks the report.
Exits non-zero on any failure.
"""

import json
import sys
import time
import urllib.request


def call(base: str, path: str, body: dict | None = None, method: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method or ("POST" if body is not None else "GET"),
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read())


def main(base: str) -> int:
    base = base.rstrip("/")
    started = time.time()
    assert call(base, "/api/health")["status"] == "ok"
    demo = call(base, "/api/demos")[0]
    dataset = call(base, f"/api/datasets/demo/{demo['id']}", method="POST")
    job = call(
        base,
        "/api/audits",
        {"dataset_id": dataset["dataset_id"], "claim": demo["suggested_claim"], "excluded_columns": []},
    )
    submitted = time.time()
    while job["status"] in ("queued", "running"):
        if time.time() - submitted > 180:
            print("FAIL: audit did not finish within 180 s")
            return 1
        time.sleep(1)
        job = call(base, f"/api/audits/{job['audit_id']}")
    if job["status"] != "succeeded":
        print(f"FAIL: audit ended as {job['status']}: {job.get('error')}")
        return 1
    report = call(base, f"/api/audits/{job['audit_id']}/report.json")
    assert report["dataset"]["sha256"] == dataset["sha256"]
    assert len(report["seed_runs"]) == 5 and report["verdict"]["label"]
    assert all(stage["status"] in ("done", "skipped") for stage in job["stages"])
    print(
        f"OK  {demo['id']}: verdict={report['verdict']['label']}  "
        f"threshold met on {report['seed_summary']['n_meets_threshold']}/5  "
        f"engine {report['runtime_seconds']} s  audit wall {time.time() - submitted:.1f} s  total {time.time() - started:.1f} s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"))
