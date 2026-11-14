"""Audit job runner.

One worker thread takes jobs off a bounded queue and runs each in its own spawned child process.
The child rewrites runs/{id}/job.json after every stage; the API only ever reads that file.
The worker thread is the watchdog: a child still alive after JOB_TIMEOUT_S is terminated.
"""

import json
import multiprocessing
import os
import queue
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from labmirror import config
from labmirror.engine import EngineError
from labmirror.engine.registry import initial_stages
from labmirror.engine.run import now_iso
from labmirror.schemas import AuditJob, AuditReport, AuditRequest, JobError, Stage

_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_TERMINAL = {"succeeded", "failed", "timeout"}

_queue: "queue.Queue[tuple[str, str]]" = queue.Queue(maxsize=config.MAX_QUEUED)
_worker: Optional[threading.Thread] = None
_worker_lock = threading.Lock()


# --- job.json I/O ---------------------------------------------------------
def _run_dir(data_dir: Path, audit_id: str) -> Path:
    return Path(data_dir) / "runs" / audit_id


def write_job(data_dir: Path, job: AuditJob) -> None:
    folder = _run_dir(data_dir, job.audit_id)
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / f"job.{os.getpid()}.tmp"
    tmp.write_text(job.model_dump_json(), encoding="utf-8")
    for attempt in range(20):   # on Windows a concurrent reader can briefly block the replace
        try:
            os.replace(tmp, folder / "job.json")
            return
        except PermissionError:
            time.sleep(0.01 * (attempt + 1))
    os.replace(tmp, folder / "job.json")


def read_job(audit_id: str, data_dir: Optional[Path] = None) -> AuditJob:
    data_dir = data_dir or config.DATA_DIR
    path = _run_dir(data_dir, audit_id) / "job.json"
    if not _ID_RE.match(audit_id) or not path.exists():
        raise EngineError("unknown_audit", "That audit was not found. Saved runs expire; start a new audit.")
    last: Exception | None = None
    for attempt in range(20):
        try:
            return AuditJob.model_validate_json(path.read_text(encoding="utf-8"))
        except (PermissionError, ValueError) as exc:
            last = exc
            time.sleep(0.01 * (attempt + 1))
    raise EngineError("internal_error", f"The audit status could not be read ({type(last).__name__}).")


# --- child process --------------------------------------------------------
def _child_main(audit_id: str, data_dir: str) -> None:
    config.DATA_DIR = Path(data_dir)
    from labmirror import storage
    from labmirror.engine.run import run_audit

    job = read_job(audit_id, config.DATA_DIR)
    job.status, job.started_at = "running", now_iso()
    write_job(config.DATA_DIR, job)

    def on_update(stages: list[Stage], report: Optional[AuditReport]) -> None:
        job.stages, job.report = stages, report
        write_job(config.DATA_DIR, job)

    try:
        request = AuditRequest.model_validate_json(
            (_run_dir(config.DATA_DIR, audit_id) / "request.json").read_text(encoding="utf-8")
        )
        df, summary = storage.load_dataset(request.dataset_id)
        report, stages = run_audit(
            df, sha256=summary.sha256, filename=summary.filename, request=request, audit_id=audit_id, on_update=on_update
        )
        job.stages, job.report, job.status = stages, report, "succeeded"
    except EngineError as exc:
        job.status, job.error = "failed", JobError(code=exc.code, message=exc.message)
    except Exception as exc:
        job.status = "failed"
        job.error = JobError(code="internal_error", message=f"The audit stopped on an unexpected error ({type(exc).__name__}).")
    job.finished_at = now_iso()
    write_job(config.DATA_DIR, job)


# --- parent: worker / watchdog -------------------------------------------
def _fail_from_parent(audit_id: str, data_dir: Path, status: str, code: str, message: str) -> None:
    job = read_job(audit_id, data_dir)
    if job.status in _TERMINAL:
        return
    for stage in job.stages:
        if stage.status == "running":
            stage.status, stage.finished_at, stage.message = "failed", now_iso(), message
    job.status, job.error, job.finished_at = status, JobError(code=code, message=message), now_iso()
    write_job(data_dir, job)


def _run_one(audit_id: str, data_dir: str) -> None:
    ctx = multiprocessing.get_context("spawn")
    process = ctx.Process(target=_child_main, args=(audit_id, data_dir), daemon=True)
    process.start()
    process.join(config.JOB_TIMEOUT_S)
    if process.is_alive():
        process.terminate()
        process.join(5)
        _fail_from_parent(
            audit_id,
            Path(data_dir),
            "timeout",
            "timeout",
            f"The audit exceeded the {config.JOB_TIMEOUT_S}-second limit and was stopped. Try fewer rows or columns.",
        )
    elif process.exitcode != 0:
        _fail_from_parent(
            audit_id, Path(data_dir), "failed", "internal_error", "The audit process stopped unexpectedly. No result was produced."
        )


def _worker_loop() -> None:
    while True:
        audit_id, data_dir = _queue.get()
        try:
            _run_one(audit_id, data_dir)
        except Exception:
            try:
                _fail_from_parent(audit_id, Path(data_dir), "failed", "internal_error", "The audit could not be started.")
            except Exception:
                pass
        finally:
            _queue.task_done()


def _ensure_worker() -> None:
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_worker_loop, name="labmirror-audit-worker", daemon=True)
            _worker.start()


def submit(request: AuditRequest) -> AuditJob:
    """Queue a validated request. Raises EngineError('queue_full') when the queue is at capacity."""
    if _queue.full():
        raise EngineError("queue_full", "The audit queue is full right now. Wait a few seconds and try again.")
    audit_id = uuid.uuid4().hex[:12]
    job = AuditJob(audit_id=audit_id, status="queued", created_at=now_iso(), stages=initial_stages())
    folder = _run_dir(config.DATA_DIR, audit_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "request.json").write_text(request.model_dump_json(), encoding="utf-8")
    write_job(config.DATA_DIR, job)
    try:
        _queue.put_nowait((audit_id, str(config.DATA_DIR)))
    except queue.Full:
        raise EngineError("queue_full", "The audit queue is full right now. Wait a few seconds and try again.")
    _ensure_worker()
    return job
