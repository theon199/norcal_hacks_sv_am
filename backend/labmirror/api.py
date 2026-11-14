"""FastAPI application. Phase 1 skeleton: health endpoint only."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from labmirror import __version__

app = FastAPI(title="LabMirror API", version=__version__)

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
