"""Temporary file storage for uploaded datasets. Raw rows are never logged."""

import json
import re
import shutil
import time
import uuid
from pathlib import Path

import pandas as pd

from labmirror import config
from labmirror.engine import EngineError
from labmirror.engine.profiling import load_csv, profile_dataset, sha256_bytes
from labmirror.schemas import DatasetSummary, DemoDescriptor

_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _datasets_dir() -> Path:
    path = config.DATA_DIR / "datasets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sweep_expired() -> None:
    """Delete uploaded datasets older than the retention window."""
    cutoff = time.time() - config.RETENTION_HOURS * 3600
    for child in _datasets_dir().iterdir():
        try:
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
        except OSError:
            continue


def safe_filename(name: str | None) -> str:
    base = Path(name or "upload.csv").name.strip() or "upload.csv"
    return re.sub(r"[^\w.\- ]", "_", base)[:100]


def save_dataset(raw: bytes, filename: str | None, *, is_demo: bool = False) -> DatasetSummary:
    df = load_csv(raw)
    dataset_id = uuid.uuid4().hex[:12]
    summary = profile_dataset(
        df, dataset_id=dataset_id, sha256=sha256_bytes(raw), filename=safe_filename(filename), is_demo=is_demo
    )
    folder = _datasets_dir() / dataset_id
    folder.mkdir(parents=True)
    (folder / "data.csv").write_bytes(raw)
    (folder / "summary.json").write_text(summary.model_dump_json(), encoding="utf-8")
    return summary


def load_dataset(dataset_id: str) -> tuple[pd.DataFrame, DatasetSummary]:
    folder = _datasets_dir() / dataset_id
    if not _ID_RE.match(dataset_id) or not (folder / "data.csv").exists():
        raise EngineError("unknown_dataset", "That dataset was not found. It may have expired; upload it again.")
    summary = DatasetSummary.model_validate_json((folder / "summary.json").read_text(encoding="utf-8"))
    return load_csv((folder / "data.csv").read_bytes()), summary


def list_demos() -> list[DemoDescriptor]:
    entries = json.loads((config.DEMO_DIR / "demos.json").read_text(encoding="utf-8"))
    return [DemoDescriptor.model_validate({k: v for k, v in e.items() if k != "file"}) for e in entries]


def load_demo_bytes(demo_id: str) -> tuple[bytes, str]:
    entries = json.loads((config.DEMO_DIR / "demos.json").read_text(encoding="utf-8"))
    entry = next((e for e in entries if e["id"] == demo_id), None)
    if entry is None:
        raise EngineError("unknown_dataset", f"There is no example dataset called '{demo_id}'.")
    return (config.DEMO_DIR / entry["file"]).read_bytes(), entry["file"]
