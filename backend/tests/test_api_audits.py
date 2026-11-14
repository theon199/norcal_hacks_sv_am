import queue as queue_module
import time

import pytest
from fastapi.testclient import TestClient

from labmirror import config, jobs
from labmirror.api import app
from labmirror.schemas import AuditJob


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return TestClient(app, raise_server_exceptions=False)


def _wait(client, audit_id, seconds=90):
    deadline = time.time() + seconds
    while time.time() < deadline:
        job = client.get(f"/api/audits/{audit_id}").json()
        if job["status"] in ("succeeded", "failed", "timeout"):
            return job
        time.sleep(0.2)
    raise AssertionError("audit did not finish")


def _demo_request(client):
    demo = client.get("/api/demos").json()[0]
    dataset_id = client.post(f"/api/datasets/demo/{demo['id']}").json()["dataset_id"]
    return {"dataset_id": dataset_id, "claim": demo["suggested_claim"], "excluded_columns": []}


def test_audit_end_to_end_and_rerun_is_identical(client):
    body = _demo_request(client)
    r = client.post("/api/audits", json=body)
    assert r.status_code == 202 and r.json()["status"] == "queued"
    job = _wait(client, r.json()["audit_id"])
    AuditJob.model_validate(job)
    assert job["status"] == "succeeded", job.get("error")
    assert [s["status"] for s in job["stages"]] == ["done"] * 7
    report = job["report"]
    assert report["audit_id"] == job["audit_id"]
    assert report["verdict"]["label"] in ("consistent", "mixed", "not_reproduced", "inconclusive")
    assert report["noise"]["n_draws"] == 20 and len(report["seed_runs"]) == 5

    job2 = _wait(client, client.post("/api/audits", json=body).json()["audit_id"])
    for key in ("default_split", "seed_runs", "seed_summary", "noise", "diagnostics", "verdict"):
        assert job2["report"][key] == report[key]

    download = client.get(f"/api/audits/{job['audit_id']}/report.json")
    assert download.status_code == 200 and "attachment" in download.headers["content-disposition"]
    assert download.json()["dataset"]["sha256"] == report["dataset"]["sha256"]


def test_audit_request_errors(client):
    body = _demo_request(client)

    def code(patch_claim=None, **patch):
        b = {**body, **patch, "claim": {**body["claim"], **(patch_claim or {})}}
        r = client.post("/api/audits", json=b)
        return r.status_code, r.json()["error"]["code"]

    assert code(dataset_id="000000000000") == (404, "unknown_dataset")
    assert code({"target": ""}) == (400, "unknown_target")
    assert code({"target": "mean_radius"}) == (400, "target_not_binary")
    assert code({"threshold_pp": 0}) == (422, "invalid_threshold")
    assert code({"baseline": "random_forest"}) == (400, "same_model")
    assert client.get("/api/audits/ffffffffffff").json()["error"]["code"] == "unknown_audit"
    assert client.get("/api/audits/not-an-id").json()["error"]["code"] == "unknown_audit"


def test_timeout_kills_job(client, monkeypatch):
    monkeypatch.setattr(config, "JOB_TIMEOUT_S", 0.05)   # the child cannot even finish importing in this time
    r = client.post("/api/audits", json=_demo_request(client))
    job = _wait(client, r.json()["audit_id"])
    assert job["status"] == "timeout" and job["error"]["code"] == "timeout"
    assert job["report"] is None
    assert client.get(f"/api/audits/{job['audit_id']}/report.json").status_code == 404


def test_queue_full_returns_429(client, monkeypatch):
    monkeypatch.setattr(jobs, "_queue", queue_module.Queue(maxsize=config.MAX_QUEUED))
    monkeypatch.setattr(jobs, "_ensure_worker", lambda: None)   # nothing drains the queue
    body = _demo_request(client)
    for _ in range(config.MAX_QUEUED):
        assert client.post("/api/audits", json=body).status_code == 202
    r = client.post("/api/audits", json=body)
    assert r.status_code == 429 and r.json()["error"]["code"] == "queue_full"
