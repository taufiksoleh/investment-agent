"""Request-id correlation middleware.

Binds a unique id to every request's structlog context (see
`infrastructure/logger.py`'s `merge_contextvars` processor) so all log lines
emitted while handling that request can be correlated, and echoes it back as
a response header for client-side correlation too.
"""

import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response


def add_request_id_middleware(app: FastAPI) -> None:
    """Register the request-id middleware on `app`."""

    @app.middleware("http")
    async def _bind_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
