"""Deterministic experiment engine. No web imports in this package."""


class EngineError(Exception):
    """A user-facing validation or execution error with a stable code (see plan §3.1)."""

    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
