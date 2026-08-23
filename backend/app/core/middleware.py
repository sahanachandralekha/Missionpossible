"""FastAPI Application Middleware for Request Correlation, Timing & Security Headers.

STATUS: FULLY IMPLEMENTED (Part 16)

Provides:
- RequestCorrelationMiddleware: Binds request_id, sets X-Request-ID header, logs request lifecycle, and measures latency.
- SecurityHeadersMiddleware: Attaches modern security headers (nosniff, DENY, Referrer-Policy, CSP).
"""

import logging
import re
import time
import uuid
from contextvars import ContextVar

from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from backend.app.core.logging import get_logger, log_event
from backend.app.core.metrics import metrics_collector

logger = get_logger("middleware")

# ContextVar for storing current request ID across thread execution context
current_request_id: ContextVar[Optional[str]] = ContextVar("current_request_id", default=None)


def get_current_request_id() -> Optional[str]:
    """Retrieve the current request ID from execution context."""
    return current_request_id.get()


class RequestCorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware for request correlation ID extraction/generation, timing, and logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Extract client header or payload request ID, fallback to UUID
        raw_header = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID")
        req_id: str
        if raw_header:
            clean = raw_header.strip()
            if re.match(r"^[a-zA-Z0-9_-]{1,128}$", clean):
                req_id = clean
            else:
                req_id = f"req_{uuid.uuid4().hex[:16]}"
        else:
            req_id = f"req_{uuid.uuid4().hex[:16]}"

        # Bind to ContextVar
        token = current_request_id.set(req_id)

        log_event(
            logger,
            logging.INFO,
            f"API Request intake: {request.method} {request.url.path}",
            request_id=req_id,
            component="HTTP_INBOUND",
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
            duration_s = time.perf_counter() - start_time

            # Set X-Request-ID header
            response.headers["X-Request-ID"] = req_id

            # Telemetry metrics
            metrics_collector.record_request(duration_s, response.status_code)

            log_event(
                logger,
                logging.INFO,
                f"API Response: {request.method} {request.url.path} -> {response.status_code} ({round(duration_s * 1000, 2)}ms)",
                request_id=req_id,
                component="HTTP_OUTBOUND",
                status_code=response.status_code,
                duration_ms=round(duration_s * 1000, 2),
            )

            return response
        except Exception as e:
            duration_s = time.perf_counter() - start_time
            metrics_collector.record_request(duration_s, 500)

            log_event(
                logger,
                logging.ERROR,
                f"Unhandled Exception on {request.method} {request.url.path}: {str(e)}",
                request_id=req_id,
                component="HTTP_EXCEPTION",
                error=str(e),
            )
            raise
        finally:
            current_request_id.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware attaching production security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Safe Content Security Policy allowing local Vite/React app and APIs
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "connect-src *;"
            )

        return response
