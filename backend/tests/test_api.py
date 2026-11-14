import pytest
from fastapi.testclient import TestClient

from labmirror import config, storage
from labmirror.api import app
from labmirror.schemas import ClaimSpec


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return TestClient(app, raise_server_exceptions=False)


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_demo_flow(client):
    demos = client.get("/api/demos").json()
    assert demos and "file" not in demos[0]
    ClaimSpec.model_validate(demos[0]["suggested_claim"])
    r = client.post(f"/api/datasets/demo/{demos[0]['id']}")
    assert r.status_code == 201
    summary = r.json()
    assert summary["is_demo"] and summary["n_rows"] == 569
    assert demos[0]["suggested_claim"]["target"] in summary["binary_target_candidates"]
    df, stored = storage.load_dataset(summary["dataset_id"])
    assert len(df) == 569 and stored.sha256 == summary["sha256"]


def test_upload_and_errors(client, mixed_df):
    ok = client.post("/api/datasets", files={"file": ("my data.csv", mixed_df.to_csv(index=False), "text/csv")})
    assert ok.status_code == 201 and ok.json()["filename"] == "my data.csv"

    def err(**kwargs):
        r = client.post("/api/datasets", **kwargs)
        return r.status_code, r.json()["error"]["code"]

    assert err() == (400, "no_file")
    assert err(files={"file": ("e.csv", b"", "text/csv")}) == (400, "no_file")
    assert err(files={"file": ("s.csv", b"a,b\n1,2\n", "text/csv")}) == (400, "too_few_rows")
    assert client.post("/api/datasets/demo/nope").json()["error"]["code"] == "unknown_dataset"


def test_oversized_upload_rejected(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0)
    r = client.post("/api/datasets", files={"file": ("big.csv", b"a,b\n" + b"1,2\n" * 200, "text/csv")})
    assert r.status_code == 413 and r.json()["error"]["code"] == "file_too_large"


def test_unknown_dataset_id_cannot_escape_storage(client):
    from labmirror.engine import EngineError

    for bad in ("../../etc", "zzzzzzzzzzzz", ""):
        with pytest.raises(EngineError):
            storage.load_dataset(bad)
