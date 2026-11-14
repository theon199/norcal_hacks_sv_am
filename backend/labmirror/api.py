"""FastAPI application: thin HTTP layer over the engine."""

import os

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from labmirror import __version__, config, storage
from labmirror.engine import EngineError
from labmirror.schemas import DatasetSummary, DemoDescriptor

app = FastAPI(title="LabMirror API", version=__version__)

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_STATUS = {
    "file_too_large": 413,
    "unknown_dataset": 404,
    "unknown_audit": 404,
    "queue_full": 429,
    "timeout": 504,
    "internal_error": 500,
}


def _error(code: str, message: str, field: str | None = None, status: int | None = None) -> JSONResponse:
    body = {"code": code, "message": message}
    if field:
        body["field"] = field
    return JSONResponse({"error": body}, status_code=status or _STATUS.get(code, 400))


@app.exception_handler(EngineError)
async def engine_error_handler(_: Request, exc: EngineError) -> JSONResponse:
    return _error(exc.code, exc.message, exc.field)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    loc = [str(p) for p in first.get("loc", []) if p != "body"]
    field = loc[-1] if loc else None
    if field == "file":
        return _error("no_file", "No file was sent. Choose a CSV file to upload.", "file")
    code = "invalid_threshold" if field == "threshold_pp" else "invalid_request"
    return _error(code, f"Invalid value for {field or 'request'}: {first.get('msg', 'invalid')}.", field, 422)


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    return _error("internal_error", f"Unexpected server error ({type(exc).__name__}). Nothing was computed.")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@app.get("/api/demos", response_model=list[DemoDescriptor])
def demos() -> list[DemoDescriptor]:
    return storage.list_demos()


@app.post("/api/datasets", response_model=DatasetSummary, status_code=201)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetSummary:
    limit = config.MAX_UPLOAD_MB * 1024 * 1024
    raw = await file.read(limit + 1)
    if len(raw) > limit:
        raise EngineError("file_too_large", f"The file is larger than {config.MAX_UPLOAD_MB} MB.")
    storage.sweep_expired()
    return storage.save_dataset(raw, file.filename)


@app.post("/api/datasets/demo/{demo_id}", response_model=DatasetSummary, status_code=201)
def load_demo(demo_id: str) -> DatasetSummary:
    raw, filename = storage.load_demo_bytes(demo_id)
    storage.sweep_expired()
    return storage.save_dataset(raw, filename, is_demo=True)
